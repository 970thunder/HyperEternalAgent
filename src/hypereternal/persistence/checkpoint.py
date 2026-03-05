"""
Checkpoint and recovery system for HyperEternalAgent framework.
"""

import asyncio
import gzip
import hashlib
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.exceptions import ChecksumMismatchError, SnapshotError
from ..core.types import StateScope, generate_id
from ..infrastructure.logging import get_logger
from .state_manager import StateManager
from .task_queue import TaskQueue

logger = get_logger(__name__)


@dataclass
class Snapshot:
    """Snapshot metadata and data."""

    snapshot_id: str
    label: Optional[str]
    timestamp: datetime
    state_data: Dict[str, Any]
    checksum: str
    size_bytes: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "snapshot_id": self.snapshot_id,
            "label": self.label,
            "timestamp": self.timestamp.isoformat(),
            "state_data": self.state_data,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "metadata": self.metadata,
        }


@dataclass
class IncrementRecord:
    """Incremental change record."""

    increment_id: str
    changes: List[Dict[str, Any]]
    timestamp: datetime
    previous_save: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "increment_id": self.increment_id,
            "changes": self.changes,
            "timestamp": self.timestamp.isoformat(),
            "previous_save": self.previous_save.isoformat() if self.previous_save else None,
        }


class SnapshotManager:
    """
    Manager for creating and restoring snapshots.

    Features:
    - Full state snapshots
    - Compression support
    - Checksum verification
    - Automatic cleanup of old snapshots
    """

    def __init__(
        self,
        state_manager: StateManager,
        storage_path: str = "./checkpoints",
        max_snapshots: int = 10,
    ):
        self.state_manager = state_manager
        self.storage_path = Path(storage_path)
        self.max_snapshots = max_snapshots
        self.snapshots: Dict[str, Snapshot] = {}

        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """Load existing snapshots from disk."""
        for snapshot_file in self.storage_path.glob("*.snapshot.gz"):
            try:
                snapshot = await self._load_snapshot_from_file(snapshot_file)
                if snapshot:
                    self.snapshots[snapshot.snapshot_id] = snapshot
            except Exception as e:
                logger.warning(
                    "snapshot_load_failed",
                    file=str(snapshot_file),
                    error=str(e),
                )

        logger.info("snapshots_loaded", count=len(self.snapshots))

    async def create_snapshot(
        self,
        label: Optional[str] = None,
        include_metadata: bool = True,
    ) -> Snapshot:
        """
        Create a new snapshot.

        Args:
            label: Optional label for the snapshot
            include_metadata: Include metadata in snapshot

        Returns:
            Created snapshot
        """
        snapshot_id = generate_id()
        timestamp = datetime.now()

        # Collect state data
        state_data = await self._collect_state()

        # Calculate checksum
        checksum = self._calculate_checksum(state_data)

        # Calculate size
        size_bytes = len(pickle.dumps(state_data))

        # Create snapshot
        snapshot = Snapshot(
            snapshot_id=snapshot_id,
            label=label,
            timestamp=timestamp,
            state_data=state_data,
            checksum=checksum,
            size_bytes=size_bytes,
            metadata={"created_by": "system"} if include_metadata else {},
        )

        # Save to disk
        await self._save_snapshot_to_file(snapshot)

        # Store in memory
        self.snapshots[snapshot_id] = snapshot

        # Cleanup old snapshots
        await self._cleanup_old_snapshots()

        logger.info(
            "snapshot_created",
            snapshot_id=snapshot_id,
            label=label,
            size_bytes=size_bytes,
        )

        return snapshot

    async def restore_snapshot(self, snapshot_id: str) -> bool:
        """
        Restore from a snapshot.

        Args:
            snapshot_id: ID of snapshot to restore

        Returns:
            True if successful

        Raises:
            SnapshotError: If snapshot not found
            ChecksumMismatchError: If checksum verification fails
        """
        snapshot = self.snapshots.get(snapshot_id)

        if not snapshot:
            # Try loading from disk
            snapshot_file = self.storage_path / f"{snapshot_id}.snapshot.gz"
            if snapshot_file.exists():
                snapshot = await self._load_snapshot_from_file(snapshot_file)

        if not snapshot:
            raise SnapshotError(f"Snapshot not found: {snapshot_id}")

        # Verify checksum
        if not self._verify_checksum(snapshot):
            raise ChecksumMismatchError("Snapshot checksum verification failed")

        # Restore state
        await self._restore_state(snapshot.state_data)

        logger.info(
            "snapshot_restored",
            snapshot_id=snapshot_id,
            label=snapshot.label,
        )

        return True

    async def list_snapshots(self) -> List[Snapshot]:
        """List all snapshots sorted by timestamp (newest first)."""
        return sorted(
            self.snapshots.values(),
            key=lambda s: s.timestamp,
            reverse=True,
        )

    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot."""
        if snapshot_id not in self.snapshots:
            return False

        # Delete file
        snapshot_file = self.storage_path / f"{snapshot_id}.snapshot.gz"
        if snapshot_file.exists():
            snapshot_file.unlink()

        del self.snapshots[snapshot_id]

        logger.info("snapshot_deleted", snapshot_id=snapshot_id)
        return True

    async def _collect_state(self) -> Dict[str, Any]:
        """Collect all state data."""
        state_data: Dict[str, Any] = {
            "global_state": {},
            "sessions": {},
            "flows": {},
            "agents": {},
        }

        # Collect global state
        global_keys = await self.state_manager.list_keys(StateScope.GLOBAL)
        for key in global_keys:
            value = await self.state_manager.get(key, StateScope.GLOBAL)
            if value is not None:
                state_data["global_state"][key] = value

        # Collect session state
        session_keys = await self.state_manager.list_keys(StateScope.SESSION)
        for key in session_keys:
            value = await self.state_manager.get(key, StateScope.SESSION)
            if value is not None:
                state_data["sessions"][key] = value

        return state_data

    async def _restore_state(self, state_data: Dict[str, Any]) -> None:
        """Restore state from data."""
        # Restore global state
        for key, value in state_data.get("global_state", {}).items():
            await self.state_manager.set(key, value, StateScope.GLOBAL)

        # Restore session state
        for key, value in state_data.get("sessions", {}).items():
            await self.state_manager.set(key, value, StateScope.SESSION)

    async def _save_snapshot_to_file(self, snapshot: Snapshot) -> None:
        """Save snapshot to disk."""
        snapshot_file = self.storage_path / f"{snapshot.snapshot_id}.snapshot.gz"

        data = snapshot.to_dict()

        with gzip.open(snapshot_file, "wb") as f:
            pickle.dump(data, f)

    async def _load_snapshot_from_file(self, file_path: Path) -> Optional[Snapshot]:
        """Load snapshot from disk."""
        try:
            with gzip.open(file_path, "rb") as f:
                data = pickle.load(f)

            return Snapshot(
                snapshot_id=data["snapshot_id"],
                label=data.get("label"),
                timestamp=datetime.fromisoformat(data["timestamp"]),
                state_data=data["state_data"],
                checksum=data["checksum"],
                size_bytes=data["size_bytes"],
                metadata=data.get("metadata", {}),
            )
        except Exception as e:
            logger.error("snapshot_load_error", file=str(file_path), error=str(e))
            return None

    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate SHA256 checksum of data."""
        return hashlib.sha256(
            pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        ).hexdigest()

    def _verify_checksum(self, snapshot: Snapshot) -> bool:
        """Verify snapshot checksum."""
        current_checksum = self._calculate_checksum(snapshot.state_data)
        return current_checksum == snapshot.checksum

    async def _cleanup_old_snapshots(self) -> None:
        """Remove old snapshots if over limit."""
        if len(self.snapshots) <= self.max_snapshots:
            return

        # Sort by timestamp
        sorted_snapshots = sorted(
            self.snapshots.items(),
            key=lambda x: x[1].timestamp,
        )

        # Remove oldest
        for snapshot_id, _ in sorted_snapshots[: -self.max_snapshots]:
            await self.delete_snapshot(snapshot_id)


class IncrementalSaver:
    """
    Incremental state saver for periodic saves.
    """

    def __init__(
        self,
        state_manager: StateManager,
        storage_path: str = "./checkpoints",
        save_interval: int = 60,
    ):
        self.state_manager = state_manager
        self.storage_path = Path(storage_path)
        self.save_interval = save_interval

        self.changes: List[Dict[str, Any]] = []
        self.last_save: Optional[datetime] = None
        self.running = False
        self._task: Optional[asyncio.Task] = None

        self.storage_path.mkdir(parents=True, exist_ok=True)

    def record_change(
        self,
        key: str,
        old_value: Any,
        new_value: Any,
        operation: str,
    ) -> None:
        """Record a state change."""
        change = {
            "key": key,
            "old_value": old_value,
            "new_value": new_value,
            "operation": operation,
            "timestamp": datetime.now().isoformat(),
        }
        self.changes.append(change)

    async def start(self) -> None:
        """Start incremental saving."""
        self.running = True
        self._task = asyncio.create_task(self._save_loop())
        logger.info("incremental_saver_started")

    async def stop(self) -> None:
        """Stop incremental saving."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Save final changes
        await self._save_changes()
        logger.info("incremental_saver_stopped")

    async def _save_loop(self) -> None:
        """Periodic save loop."""
        while self.running:
            await asyncio.sleep(self.save_interval)

            if self.changes:
                await self._save_changes()

    async def _save_changes(self) -> None:
        """Save accumulated changes."""
        if not self.changes:
            return

        increment = IncrementRecord(
            increment_id=generate_id(),
            changes=self.changes.copy(),
            timestamp=datetime.now(),
            previous_save=self.last_save,
        )

        # Save to file
        increment_file = self.storage_path / f"increment_{increment.increment_id}.dat"
        with open(increment_file, "wb") as f:
            pickle.dump(increment.to_dict(), f)

        # Clear changes
        self.changes.clear()
        self.last_save = increment.timestamp

        logger.debug("increment_saved", increment_id=increment.increment_id)


@dataclass
class RecoveryResult:
    """Result of a recovery operation."""

    strategy: str
    success: bool = False
    message: str = ""
    error: Optional[str] = None
    snapshot_id: Optional[str] = None
    restored_state: bool = False
    recovered_tasks: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class RecoveryManager:
    """
    Manager for system recovery.
    """

    def __init__(
        self,
        snapshot_manager: SnapshotManager,
        state_manager: StateManager,
        task_queue: TaskQueue,
    ):
        self.snapshot_manager = snapshot_manager
        self.state_manager = state_manager
        self.task_queue = task_queue

    async def recover(self, strategy: str = "latest") -> RecoveryResult:
        """
        Perform system recovery.

        Args:
            strategy: Recovery strategy ("latest", "clean")

        Returns:
            Recovery result
        """
        result = RecoveryResult(
            strategy=strategy,
            started_at=datetime.now(),
        )

        try:
            if strategy == "latest":
                await self._recover_latest(result)
            elif strategy == "clean":
                await self._recover_clean(result)
            else:
                raise ValueError(f"Unknown recovery strategy: {strategy}")

            result.success = True

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error("recovery_failed", strategy=strategy, error=str(e))

        result.completed_at = datetime.now()
        return result

    async def _recover_latest(self, result: RecoveryResult) -> None:
        """Recover to latest snapshot."""
        snapshots = await self.snapshot_manager.list_snapshots()

        if not snapshots:
            result.message = "No snapshots available for recovery"
            return

        latest = snapshots[0]
        result.snapshot_id = latest.snapshot_id

        await self.snapshot_manager.restore_snapshot(latest.snapshot_id)
        result.restored_state = True

        # Get task queue stats
        stats = await self.task_queue.get_stats()
        result.recovered_tasks = stats.get("total_tasks", 0)

        result.message = f"Recovered to snapshot {latest.snapshot_id}"

    async def _recover_clean(self, result: RecoveryResult) -> None:
        """Perform clean recovery (clear all state)."""
        await self.state_manager.clear_scope(StateScope.GLOBAL)
        await self.state_manager.clear_scope(StateScope.SESSION)

        result.message = "Performed clean recovery"
