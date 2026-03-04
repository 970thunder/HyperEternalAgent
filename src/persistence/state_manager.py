"""
State management for HyperEternalAgent framework.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from ..core.types import StateScope, generate_id
from .logging import get_logger
from .storage import StorageBackend

logger = get_logger(__name__)


@dataclass
class StateEntry:
    """State entry with metadata."""

    key: str
    value: Any
    scope: StateScope
    owner_id: Optional[str] = None
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    ttl: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "scope": self.scope.value,
            "owner_id": self.owner_id,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "ttl": self.ttl,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateEntry":
        """Create from dictionary."""
        return cls(
            key=data["key"],
            value=data["value"],
            scope=StateScope(data["scope"]),
            owner_id=data.get("owner_id"),
            version=data.get("version", 1),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            ttl=data.get("ttl"),
            metadata=data.get("metadata", {}),
        )


class StateManager:
    """
    State manager for managing application state.

    Features:
    - Scoped state management (global, session, flow, agent, task)
    - TTL support for expiring state
    - Versioning for state entries
    - Thread-safe operations
    """

    def __init__(self, storage: StorageBackend, cache_size: int = 10000):
        self.storage = storage
        self.cache_size = cache_size
        self._cache: Dict[str, StateEntry] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def get(
        self,
        key: str,
        scope: StateScope = StateScope.GLOBAL,
        owner_id: Optional[str] = None,
    ) -> Optional[Any]:
        """
        Get state value.

        Args:
            key: State key
            scope: State scope
            owner_id: Owner ID (for scoped state)

        Returns:
            State value or None if not found
        """
        full_key = self._make_key(key, scope, owner_id)

        # Check cache first
        if full_key in self._cache:
            entry = self._cache[full_key]
            if not self._is_expired(entry):
                return entry.value
            else:
                del self._cache[full_key]

        # Load from storage
        entry_data = await self.storage.get(full_key)
        if entry_data:
            entry = StateEntry.from_dict(entry_data)
            if not self._is_expired(entry):
                self._cache[full_key] = entry
                return entry.value

        return None

    async def set(
        self,
        key: str,
        value: Any,
        scope: StateScope = StateScope.GLOBAL,
        owner_id: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> StateEntry:
        """
        Set state value.

        Args:
            key: State key
            value: State value
            scope: State scope
            owner_id: Owner ID (for scoped state)
            ttl: Time-to-live in seconds

        Returns:
            State entry
        """
        full_key = self._make_key(key, scope, owner_id)

        async with await self._get_lock(full_key):
            # Get existing entry or create new
            existing_data = await self.storage.get(full_key)

            if existing_data:
                existing = StateEntry.from_dict(existing_data)
                entry = StateEntry(
                    key=key,
                    value=value,
                    scope=scope,
                    owner_id=owner_id,
                    version=existing.version + 1,
                    created_at=existing.created_at,
                    updated_at=datetime.now(),
                    ttl=ttl,
                    metadata=existing.metadata,
                )
            else:
                entry = StateEntry(
                    key=key,
                    value=value,
                    scope=scope,
                    owner_id=owner_id,
                    ttl=ttl,
                )

            # Save to storage
            await self.storage.set(full_key, entry.to_dict(), ttl=ttl)

            # Update cache
            self._update_cache(full_key, entry)

            logger.debug(
                "state_set",
                key=key,
                scope=scope.value,
                version=entry.version,
            )

            return entry

    async def delete(
        self,
        key: str,
        scope: StateScope = StateScope.GLOBAL,
        owner_id: Optional[str] = None,
    ) -> bool:
        """
        Delete state value.

        Args:
            key: State key
            scope: State scope
            owner_id: Owner ID

        Returns:
            True if deleted, False if not found
        """
        full_key = self._make_key(key, scope, owner_id)

        await self.storage.delete(full_key)
        self._cache.pop(full_key, None)

        logger.debug("state_deleted", key=key, scope=scope.value)
        return True

    async def exists(
        self,
        key: str,
        scope: StateScope = StateScope.GLOBAL,
        owner_id: Optional[str] = None,
    ) -> bool:
        """Check if state exists."""
        value = await self.get(key, scope, owner_id)
        return value is not None

    async def increment(
        self,
        key: str,
        amount: int = 1,
        scope: StateScope = StateScope.GLOBAL,
        owner_id: Optional[str] = None,
    ) -> int:
        """
        Increment a numeric state value.

        Args:
            key: State key
            amount: Amount to increment
            scope: State scope
            owner_id: Owner ID

        Returns:
            New value after increment
        """
        full_key = self._make_key(key, scope, owner_id)

        async with await self._get_lock(full_key):
            current = await self.get(key, scope, owner_id) or 0
            new_value = current + amount
            await self.set(key, new_value, scope, owner_id)
            return new_value

    async def list_keys(
        self,
        scope: StateScope,
        owner_id: Optional[str] = None,
        prefix: Optional[str] = None,
    ) -> List[str]:
        """
        List state keys in a scope.

        Args:
            scope: State scope
            owner_id: Owner ID
            prefix: Key prefix filter

        Returns:
            List of keys
        """
        pattern = self._make_key(prefix or "*", scope, owner_id)
        full_keys = await self.storage.list_keys(pattern)

        # Extract original keys from full keys
        keys = []
        prefix_parts = 2 if owner_id else 1  # scope:owner:key or scope:key

        for full_key in full_keys:
            parts = full_key.split(":", prefix_parts + 1)
            if len(parts) > prefix_parts:
                keys.append(parts[-1])

        return keys

    async def clear_scope(
        self,
        scope: StateScope,
        owner_id: Optional[str] = None,
    ) -> int:
        """
        Clear all state in a scope.

        Args:
            scope: State scope
            owner_id: Owner ID

        Returns:
            Number of keys cleared
        """
        keys = await self.list_keys(scope, owner_id)
        count = 0

        for key in keys:
            await self.delete(key, scope, owner_id)
            count += 1

        logger.info("scope_cleared", scope=scope.value, count=count)
        return count

    async def get_all(
        self,
        scope: StateScope,
        owner_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get all state in a scope.

        Args:
            scope: State scope
            owner_id: Owner ID

        Returns:
            Dictionary of key-value pairs
        """
        keys = await self.list_keys(scope, owner_id)
        result = {}

        for key in keys:
            value = await self.get(key, scope, owner_id)
            if value is not None:
                result[key] = value

        return result

    def _make_key(
        self,
        key: str,
        scope: StateScope,
        owner_id: Optional[str],
    ) -> str:
        """Generate full storage key."""
        parts = [scope.value]
        if owner_id:
            parts.append(owner_id)
        parts.append(key)
        return ":".join(parts)

    def _is_expired(self, entry: StateEntry) -> bool:
        """Check if entry is expired."""
        if entry.ttl is None:
            return False
        elapsed = (datetime.now() - entry.updated_at).total_seconds()
        return elapsed > entry.ttl

    async def _get_lock(self, key: str) -> asyncio.Lock:
        """Get or create lock for key."""
        async with self._global_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]

    def _update_cache(self, key: str, entry: StateEntry) -> None:
        """Update cache with LRU eviction."""
        if len(self._cache) >= self.cache_size:
            # Simple LRU: remove oldest entry
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].updated_at,
            )
            del self._cache[oldest_key]

        self._cache[key] = entry


class SessionManager:
    """
    Manager for session-based state.
    """

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self._active_sessions: Set[str] = set()

    async def create_session(
        self,
        session_id: Optional[str] = None,
        initial_state: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> str:
        """
        Create a new session.

        Args:
            session_id: Optional session ID (auto-generated if not provided)
            initial_state: Initial state values
            ttl: Session TTL in seconds

        Returns:
            Session ID
        """
        session_id = session_id or generate_id()

        # Set initial state
        if initial_state:
            for key, value in initial_state.items():
                await self.state_manager.set(
                    key,
                    value,
                    scope=StateScope.SESSION,
                    owner_id=session_id,
                    ttl=ttl,
                )

        # Mark session as active
        await self.state_manager.set(
            "_active",
            True,
            scope=StateScope.SESSION,
            owner_id=session_id,
            ttl=ttl,
        )

        self._active_sessions.add(session_id)
        logger.info("session_created", session_id=session_id)

        return session_id

    async def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get all state for a session."""
        return await self.state_manager.get_all(
            scope=StateScope.SESSION,
            owner_id=session_id,
        )

    async def end_session(self, session_id: str) -> None:
        """End a session and clear its state."""
        await self.state_manager.clear_scope(
            scope=StateScope.SESSION,
            owner_id=session_id,
        )
        self._active_sessions.discard(session_id)
        logger.info("session_ended", session_id=session_id)

    async def is_active(self, session_id: str) -> bool:
        """Check if session is active."""
        return session_id in self._active_sessions

    async def list_active_sessions(self) -> List[str]:
        """List all active sessions."""
        return list(self._active_sessions)
