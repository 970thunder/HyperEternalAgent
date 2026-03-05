"""
Tests for persistence layer.
"""

import asyncio
import pytest
from datetime import datetime
from pathlib import Path

from hypereternal.core.types import Task, TaskStatus
from hypereternal.persistence.storage import (
    MemoryStorageBackend,
    FileStorageBackend,
    create_storage_backend,
)
from hypereternal.persistence.state_manager import StateManager, StateScope
from hypereternal.persistence.task_queue import TaskQueue


class TestMemoryStorageBackend:
    """Tests for MemoryStorageBackend."""

    @pytest.fixture
    async def storage(self):
        """Create a memory storage backend."""
        storage = MemoryStorageBackend()
        await storage.connect()
        yield storage
        await storage.disconnect()

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Test connection and disconnection."""
        storage = MemoryStorageBackend()
        await storage.connect()
        await storage.disconnect()

    @pytest.mark.asyncio
    async def test_set_and_get(self, storage):
        """Test setting and getting values."""
        await storage.set("key1", "value1")
        result = await storage.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, storage):
        """Test getting nonexistent key."""
        result = await storage.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, storage):
        """Test deleting values."""
        await storage.set("key1", "value1")
        await storage.delete("key1")
        result = await storage.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_exists(self, storage):
        """Test checking key existence."""
        await storage.set("key1", "value1")
        assert await storage.exists("key1") is True
        assert await storage.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_list_keys(self, storage):
        """Test listing keys."""
        await storage.set("prefix:key1", "value1")
        await storage.set("prefix:key2", "value2")
        await storage.set("other:key3", "value3")

        keys = await storage.list_keys("prefix:*")
        assert len(keys) == 2

    @pytest.mark.asyncio
    async def test_list_all_keys(self, storage):
        """Test listing all keys."""
        await storage.set("key1", "value1")
        await storage.set("key2", "value2")

        keys = await storage.list_keys("*")
        assert len(keys) == 2

    @pytest.mark.asyncio
    async def test_clear(self, storage):
        """Test clearing storage."""
        await storage.set("key1", "value1")
        await storage.set("key2", "value2")

        count = await storage.clear()
        assert count == 2

        keys = await storage.list_keys("*")
        assert len(keys) == 0

    @pytest.mark.asyncio
    async def test_ttl(self, storage):
        """Test TTL expiration."""
        await storage.set("key1", "value1", ttl=1)

        # Should exist immediately
        result = await storage.get("key1")
        assert result == "value1"

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Should be expired
        result = await storage.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_complex_value(self, storage):
        """Test storing complex values."""
        value = {
            "string": "hello",
            "number": 42,
            "nested": {"list": [1, 2, 3]},
        }
        await storage.set("complex", value)
        result = await storage.get("complex")
        assert result == value

    @pytest.mark.asyncio
    async def test_overwrite(self, storage):
        """Test overwriting values."""
        await storage.set("key1", "value1")
        await storage.set("key1", "value2")
        result = await storage.get("key1")
        assert result == "value2"


class TestFileStorageBackend:
    """Tests for FileStorageBackend."""

    @pytest.fixture
    async def storage(self, tmp_path):
        """Create a file storage backend with temp directory."""
        storage = FileStorageBackend(storage_path=str(tmp_path / "storage"))
        await storage.connect()
        yield storage
        await storage.disconnect()

    @pytest.mark.asyncio
    async def test_set_and_get(self, storage):
        """Test setting and getting values."""
        await storage.set("key1", "value1")
        result = await storage.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_persistence(self, tmp_path):
        """Test that data persists across connections."""
        storage_path = str(tmp_path / "storage")

        # First connection
        storage1 = FileStorageBackend(storage_path=storage_path)
        await storage1.connect()
        await storage1.set("key1", "value1")
        await storage1.disconnect()

        # Second connection
        storage2 = FileStorageBackend(storage_path=storage_path)
        await storage2.connect()
        result = await storage2.get("key1")
        assert result == "value1"
        await storage2.disconnect()

    @pytest.mark.asyncio
    async def test_delete(self, storage):
        """Test deleting values."""
        await storage.set("key1", "value1")
        await storage.delete("key1")
        result = await storage.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_keys(self, storage):
        """Test listing keys with pattern."""
        await storage.set("prefix_key1", "value1")
        await storage.set("prefix_key2", "value2")
        await storage.set("other_key3", "value3")

        keys = await storage.list_keys("prefix_*")
        assert len(keys) == 2


class TestCreateStorageBackend:
    """Tests for create_storage_backend factory function."""

    def test_create_memory_backend(self):
        """Test creating memory backend."""
        storage = create_storage_backend("memory")
        assert isinstance(storage, MemoryStorageBackend)

    def test_create_file_backend(self):
        """Test creating file backend."""
        storage = create_storage_backend("file", storage_path="./test_data")
        assert isinstance(storage, FileStorageBackend)

    def test_create_unknown_backend(self):
        """Test creating unknown backend raises error."""
        with pytest.raises(Exception):
            create_storage_backend("unknown")


class TestStateManager:
    """Tests for StateManager."""

    @pytest.fixture
    async def state_manager(self):
        """Create a state manager with memory storage."""
        storage = MemoryStorageBackend()
        await storage.connect()
        manager = StateManager(storage)
        yield manager
        await storage.disconnect()

    @pytest.mark.asyncio
    async def test_set_and_get_global(self, state_manager):
        """Test setting and getting global state."""
        await state_manager.set("key1", "value1", StateScope.GLOBAL)
        result = await state_manager.get("key1", StateScope.GLOBAL)
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_set_and_get_session(self, state_manager):
        """Test setting and getting session state."""
        await state_manager.set("key1", "value1", StateScope.SESSION, "session1")
        result = await state_manager.get("key1", StateScope.SESSION, "session1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_scope_isolation(self, state_manager):
        """Test that scopes are isolated."""
        await state_manager.set("key1", "global_value", StateScope.GLOBAL)
        await state_manager.set("key1", "session_value", StateScope.SESSION, "s1")

        global_result = await state_manager.get("key1", StateScope.GLOBAL)
        session_result = await state_manager.get("key1", StateScope.SESSION, "s1")

        assert global_result == "global_value"
        assert session_result == "session_value"

    @pytest.mark.asyncio
    async def test_delete(self, state_manager):
        """Test deleting state."""
        await state_manager.set("key1", "value1", StateScope.GLOBAL)
        await state_manager.delete("key1", StateScope.GLOBAL)
        result = await state_manager.get("key1", StateScope.GLOBAL)
        assert result is None

    @pytest.mark.asyncio
    async def test_exists(self, state_manager):
        """Test checking state existence."""
        await state_manager.set("key1", "value1", StateScope.GLOBAL)
        assert await state_manager.exists("key1", StateScope.GLOBAL) is True
        assert await state_manager.exists("nonexistent", StateScope.GLOBAL) is False

    @pytest.mark.asyncio
    async def test_increment(self, state_manager):
        """Test atomic increment."""
        result = await state_manager.increment("counter", 1, StateScope.GLOBAL)
        assert result == 1

        result = await state_manager.increment("counter", 5, StateScope.GLOBAL)
        assert result == 6

    @pytest.mark.asyncio
    async def test_list_keys(self, state_manager):
        """Test listing keys in scope."""
        await state_manager.set("key1", "value1", StateScope.GLOBAL)
        await state_manager.set("key2", "value2", StateScope.GLOBAL)

        keys = await state_manager.list_keys(StateScope.GLOBAL)
        assert len(keys) == 2
        assert "key1" in keys
        assert "key2" in keys

    @pytest.mark.asyncio
    async def test_clear_scope(self, state_manager):
        """Test clearing scope."""
        await state_manager.set("key1", "value1", StateScope.GLOBAL)
        await state_manager.set("key2", "value2", StateScope.GLOBAL)

        count = await state_manager.clear_scope(StateScope.GLOBAL)
        assert count == 2

        keys = await state_manager.list_keys(StateScope.GLOBAL)
        assert len(keys) == 0

    @pytest.mark.asyncio
    async def test_ttl(self, state_manager):
        """Test TTL expiration."""
        await state_manager.set("key1", "value1", StateScope.GLOBAL, ttl=1)

        result = await state_manager.get("key1", StateScope.GLOBAL)
        assert result == "value1"

        await asyncio.sleep(1.5)

        result = await state_manager.get("key1", StateScope.GLOBAL)
        assert result is None

    @pytest.mark.asyncio
    async def test_version_increment(self, state_manager):
        """Test version increment on updates."""
        entry1 = await state_manager.set("key1", "value1", StateScope.GLOBAL)
        assert entry1.version == 1

        entry2 = await state_manager.set("key1", "value2", StateScope.GLOBAL)
        assert entry2.version == 2


class TestTaskQueue:
    """Tests for TaskQueue."""

    @pytest.fixture
    async def task_queue(self):
        """Create a task queue with memory storage."""
        storage = MemoryStorageBackend()
        await storage.connect()
        queue = TaskQueue(storage)
        await queue.initialize()
        yield queue
        await storage.disconnect()

    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self, task_queue):
        """Test enqueueing and dequeueing tasks."""
        task = Task(task_type="test", payload={"data": "value"})
        await task_queue.enqueue(task)

        dequeued = await task_queue.dequeue(timeout=1.0)
        assert dequeued is not None
        assert dequeued.task_id == task.task_id
        assert dequeued.task_type == "test"

    @pytest.mark.asyncio
    async def test_priority_ordering(self, task_queue):
        """Test that higher priority tasks are dequeued first."""
        low_task = Task(task_type="test", payload={}, priority=1)
        high_task = Task(task_type="test", payload={}, priority=10)

        await task_queue.enqueue(low_task)
        await task_queue.enqueue(high_task)

        first = await task_queue.dequeue(timeout=1.0)
        assert first.priority == 10

        second = await task_queue.dequeue(timeout=1.0)
        assert second.priority == 1

    @pytest.mark.asyncio
    async def test_complete(self, task_queue):
        """Test completing a task."""
        task = Task(task_type="test", payload={})
        await task_queue.enqueue(task)
        dequeued = await task_queue.dequeue(timeout=1.0)

        await task_queue.complete(dequeued.task_id, {"result": "success"})

        result = await task_queue.get_result(dequeued.task_id)
        assert result is not None
        assert result.success is True
        assert result.output == {"result": "success"}

    @pytest.mark.asyncio
    async def test_fail(self, task_queue):
        """Test failing a task."""
        task = Task(task_type="test", payload={}, max_retries=0)
        await task_queue.enqueue(task)
        dequeued = await task_queue.dequeue(timeout=1.0)

        await task_queue.fail(dequeued.task_id, "Test error", retry=False)

        result = await task_queue.get_result(dequeued.task_id)
        assert result is not None
        assert result.success is False
        assert "Test error" in result.errors

    @pytest.mark.asyncio
    async def test_cancel(self, task_queue):
        """Test canceling a task."""
        task = Task(task_type="test", payload={})
        await task_queue.enqueue(task)

        success = await task_queue.cancel(task.task_id)
        assert success is True

        dequeued_task = await task_queue.get_task(task.task_id)
        assert dequeued_task.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_get_stats(self, task_queue):
        """Test getting queue statistics."""
        task1 = Task(task_type="type1", payload={})
        task2 = Task(task_type="type2", payload={})

        await task_queue.enqueue(task1)
        await task_queue.enqueue(task2)

        stats = await task_queue.get_stats()

        assert stats["total_tasks"] == 2
        assert "by_status" in stats
        assert "by_type" in stats

    @pytest.mark.asyncio
    async def test_dequeue_empty(self, task_queue):
        """Test dequeueing from empty queue returns None."""
        result = await task_queue.dequeue(timeout=0.5)
        assert result is None

    @pytest.mark.asyncio
    async def test_dependencies(self, task_queue):
        """Test task dependencies."""
        task1 = Task(task_type="test", payload={})
        await task_queue.enqueue(task1)

        task2 = Task(task_type="test", payload={}, dependencies=[task1.task_id])
        await task_queue.enqueue(task2)

        # Task2 should not be available until task1 is complete
        dequeued = await task_queue.dequeue(timeout=0.5)
        assert dequeued.task_id == task1.task_id

        # Complete task1
        await task_queue.complete(task1.task_id, {})

        # Now task2 should be available
        dequeued = await task_queue.dequeue(timeout=1.0)
        assert dequeued.task_id == task2.task_id
