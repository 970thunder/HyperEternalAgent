"""
Task queue implementation for HyperEternalAgent framework.
"""

import asyncio
import heapq
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from ..core.exceptions import QueueEmptyError, QueueFullError, TaskDependencyError, TaskError
from ..core.types import Task, TaskResult, TaskStatus, generate_id
from ..infrastructure.logging import get_logger
from .storage import StorageBackend

logger = get_logger(__name__)


@dataclass(order=True)
class PrioritizedTask:
    """Task wrapper for priority queue."""

    priority: int
    sequence: int
    task: Task = field(compare=False)


class TaskQueue:
    """
    Priority-based task queue with dependency support.

    Features:
    - Priority-based ordering
    - Task dependencies
    - Timeout handling
    - Retry support
    - Dead letter queue
    """

    def __init__(
        self,
        storage: StorageBackend,
        max_size: int = 10000,
        visibility_timeout: int = 300,
    ):
        self.storage = storage
        self.max_size = max_size
        self.visibility_timeout = visibility_timeout

        # Priority queue
        self._queue: List[PrioritizedTask] = []
        self._sequence = 0

        # Task storage
        self._tasks: Dict[str, Task] = {}

        # Indexes
        self._status_index: Dict[TaskStatus, Set[str]] = {status: set() for status in TaskStatus}
        self._type_index: Dict[str, Set[str]] = {}

        # Locks
        self._lock = asyncio.Lock()

        # Event for waiting
        self._task_available = asyncio.Event()

        # Callbacks
        self._on_task_completed: Optional[Callable] = None
        self._on_task_failed: Optional[Callable] = None

    async def initialize(self) -> None:
        """Initialize the queue and load persisted tasks."""
        # Load existing tasks from storage
        task_keys = await self.storage.list_keys("task:*")

        for key in task_keys:
            task_data = await self.storage.get(key)
            if task_data:
                task = Task.from_dict(task_data)
                self._tasks[task.task_id] = task

                # Update indexes
                self._status_index[task.status].add(task.task_id)

                if task.task_type not in self._type_index:
                    self._type_index[task.task_type] = set()
                self._type_index[task.task_type].add(task.task_id)

                # Re-queue pending tasks
                if task.status == TaskStatus.PENDING:
                    heapq.heappush(
                        self._queue,
                        PrioritizedTask(-task.priority, self._sequence, task),
                    )
                    self._sequence += 1

        logger.info("task_queue_initialized", task_count=len(self._tasks))

    async def enqueue(self, task: Task) -> bool:
        """
        Add a task to the queue.

        Args:
            task: Task to enqueue

        Returns:
            True if successful

        Raises:
            QueueFullError: If queue is at capacity
            TaskDependencyError: If dependencies cannot be satisfied
        """
        async with self._lock:
            if len(self._tasks) >= self.max_size:
                raise QueueFullError("Task queue is full")

            # Check dependencies
            for dep_id in task.dependencies:
                if dep_id not in self._tasks:
                    raise TaskDependencyError(f"Dependency not found: {dep_id}")

            # Store task
            self._tasks[task.task_id] = task
            task.status = TaskStatus.QUEUED

            # Add to priority queue
            heapq.heappush(
                self._queue,
                PrioritizedTask(-task.priority, self._sequence, task),
            )
            self._sequence += 1

            # Update indexes
            self._status_index[TaskStatus.QUEUED].add(task.task_id)

            if task.task_type not in self._type_index:
                self._type_index[task.task_type] = set()
            self._type_index[task.task_type].add(task.task_id)

            # Persist
            await self.storage.set(f"task:{task.task_id}", task.to_dict())

            # Signal
            self._task_available.set()

            logger.debug(
                "task_enqueued",
                task_id=task.task_id,
                task_type=task.task_type,
                priority=task.priority,
            )

            return True

    async def dequeue(
        self,
        task_types: Optional[List[str]] = None,
        timeout: Optional[float] = None,
    ) -> Optional[Task]:
        """
        Get the next available task.

        Args:
            task_types: Filter by task types
            timeout: Maximum time to wait (None for blocking)

        Returns:
            Task or None if timeout
        """
        start_time = time.time()

        while True:
            async with self._lock:
                task = self._find_available_task(task_types)

                if task:
                    # Mark as running
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now()

                    # Update indexes
                    self._status_index[TaskStatus.QUEUED].discard(task.task_id)
                    self._status_index[TaskStatus.RUNNING].add(task.task_id)

                    # Persist
                    await self.storage.set(f"task:{task.task_id}", task.to_dict())

                    logger.debug(
                        "task_dequeued",
                        task_id=task.task_id,
                        task_type=task.task_type,
                    )

                    return task

            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return None

            # Wait for new task
            self._task_available.clear()
            try:
                await asyncio.wait_for(self._task_available.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

    async def complete(
        self,
        task_id: str,
        result: Any = None,
    ) -> bool:
        """
        Mark a task as completed.

        Args:
            task_id: Task ID
            result: Task result

        Returns:
            True if successful
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()

            # Store result
            await self.storage.set(
                f"result:{task_id}",
                TaskResult(
                    task_id=task_id,
                    success=True,
                    output=result,
                ).to_dict(),
            )

            # Update indexes
            self._status_index[TaskStatus.RUNNING].discard(task_id)
            self._status_index[TaskStatus.COMPLETED].add(task_id)

            # Persist
            await self.storage.set(f"task:{task_id}", task.to_dict())

            logger.info(
                "task_completed",
                task_id=task_id,
                task_type=task.task_type,
            )

            # Callback
            if self._on_task_completed:
                await self._on_task_completed(task, result)

            return True

    async def fail(
        self,
        task_id: str,
        error: str,
        retry: bool = True,
    ) -> bool:
        """
        Mark a task as failed.

        Args:
            task_id: Task ID
            error: Error message
            retry: Whether to retry

        Returns:
            True if successful
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            if retry and task.retry_count < task.max_retries:
                # Retry
                task.status = TaskStatus.RETRYING
                task.retry_count += 1

                # Re-queue
                heapq.heappush(
                    self._queue,
                    PrioritizedTask(-task.priority, self._sequence, task),
                )
                self._sequence += 1

                self._status_index[TaskStatus.RUNNING].discard(task_id)
                self._status_index[TaskStatus.RETRYING].add(task_id)

                logger.warning(
                    "task_retrying",
                    task_id=task_id,
                    retry_count=task.retry_count,
                    error=error,
                )
            else:
                # Mark as failed
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()

                # Store result
                await self.storage.set(
                    f"result:{task_id}",
                    TaskResult(
                        task_id=task_id,
                        success=False,
                        errors=[error],
                    ).to_dict(),
                )

                self._status_index[TaskStatus.RUNNING].discard(task_id)
                self._status_index[TaskStatus.FAILED].add(task_id)

                logger.error(
                    "task_failed",
                    task_id=task_id,
                    error=error,
                )

                # Callback
                if self._on_task_failed:
                    await self._on_task_failed(task, error)

            # Persist
            await self.storage.set(f"task:{task_id}", task.to_dict())

            return True

    async def cancel(self, task_id: str) -> bool:
        """Cancel a pending task."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            if task.status not in [TaskStatus.PENDING, TaskStatus.QUEUED]:
                return False

            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()

            self._status_index[task.status].discard(task_id)
            self._status_index[TaskStatus.CANCELLED].add(task_id)

            await self.storage.set(f"task:{task_id}", task.to_dict())

            logger.info("task_cancelled", task_id=task_id)
            return True

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self._tasks.get(task_id)

    async def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get task result."""
        result_data = await self.storage.get(f"result:{task_id}")
        if result_data:
            return TaskResult(
                task_id=result_data["task_id"],
                success=result_data["success"],
                output=result_data.get("output"),
                metrics=result_data.get("metrics", {}),
                errors=result_data.get("errors", []),
                completed_at=datetime.fromisoformat(result_data["completed_at"]),
            )
        return None

    async def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        async with self._lock:
            return {
                "total_tasks": len(self._tasks),
                "queue_size": len(self._queue),
                "by_status": {
                    status.value: len(ids)
                    for status, ids in self._status_index.items()
                    if ids
                },
                "by_type": {
                    task_type: len(ids)
                    for task_type, ids in self._type_index.items()
                    if ids
                },
            }

    def on_task_completed(self, callback: Callable) -> None:
        """Set callback for task completion."""
        self._on_task_completed = callback

    def on_task_failed(self, callback: Callable) -> None:
        """Set callback for task failure."""
        self._on_task_failed = callback

    def _find_available_task(
        self,
        task_types: Optional[List[str]] = None,
    ) -> Optional[Task]:
        """Find an available task from the queue."""
        temp_queue = []

        while self._queue:
            prioritized = heapq.heappop(self._queue)
            task = prioritized.task

            # Check status
            if task.status != TaskStatus.QUEUED and task.status != TaskStatus.RETRYING:
                continue

            # Check type filter
            if task_types and task.task_type not in task_types:
                temp_queue.append(prioritized)
                continue

            # Check dependencies
            if not self._check_dependencies(task):
                temp_queue.append(prioritized)
                continue

            # Found available task
            for item in temp_queue:
                heapq.heappush(self._queue, item)

            return task

        # No task found, restore temp queue
        for item in temp_queue:
            heapq.heappush(self._queue, item)

        return None

    def _check_dependencies(self, task: Task) -> bool:
        """Check if all dependencies are satisfied."""
        for dep_id in task.dependencies:
            dep_task = self._tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True


class DeadLetterQueue:
    """Queue for failed tasks that cannot be retried."""

    def __init__(self, storage: StorageBackend, max_size: int = 1000):
        self.storage = storage
        self.max_size = max_size
        self._dead_letters: Dict[str, Dict[str, Any]] = {}

    async def add(
        self,
        task: Task,
        reason: str,
        error_trace: Optional[str] = None,
    ) -> bool:
        """Add a failed task to the dead letter queue."""
        if len(self._dead_letters) >= self.max_size:
            # Remove oldest
            oldest_id = min(
                self._dead_letters.keys(),
                key=lambda k: self._dead_letters[k]["created_at"],
            )
            del self._dead_letters[oldest_id]
            await self.storage.delete(f"dead_letter:{oldest_id}")

        dead_letter = {
            "task_id": task.task_id,
            "task": task.to_dict(),
            "reason": reason,
            "error_trace": error_trace,
            "created_at": datetime.now().isoformat(),
            "requeue_count": 0,
        }

        self._dead_letters[task.task_id] = dead_letter
        await self.storage.set(f"dead_letter:{task.task_id}", dead_letter)

        logger.info(
            "dead_letter_added",
            task_id=task.task_id,
            reason=reason,
        )

        return True

    async def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get dead letter by task ID."""
        return self._dead_letters.get(task_id)

    async def list(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List dead letters."""
        sorted_letters = sorted(
            self._dead_letters.values(),
            key=lambda x: x["created_at"],
            reverse=True,
        )
        return sorted_letters[offset : offset + limit]

    async def purge(self) -> int:
        """Clear all dead letters."""
        count = len(self._dead_letters)

        for task_id in list(self._dead_letters.keys()):
            await self.storage.delete(f"dead_letter:{task_id}")

        self._dead_letters.clear()
        return count
