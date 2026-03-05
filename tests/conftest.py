"""
Pytest configuration and fixtures for HyperEternalAgent tests.
"""

import asyncio
import pytest
from typing import AsyncGenerator

from hypereternal.persistence.storage import MemoryStorageBackend
from hypereternal.persistence.state_manager import StateManager
from hypereternal.persistence.task_queue import TaskQueue
from hypereternal.agents.manager import AgentManager


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def memory_storage() -> AsyncGenerator[MemoryStorageBackend, None]:
    """Create a memory storage backend for testing."""
    storage = MemoryStorageBackend()
    await storage.connect()
    yield storage
    await storage.disconnect()


@pytest.fixture
async def state_manager(memory_storage: MemoryStorageBackend) -> StateManager:
    """Create a state manager for testing."""
    return StateManager(memory_storage)


@pytest.fixture
async def task_queue(memory_storage: MemoryStorageBackend) -> AsyncGenerator[TaskQueue, None]:
    """Create a task queue for testing."""
    queue = TaskQueue(memory_storage)
    await queue.initialize()
    yield queue


@pytest.fixture
async def agent_manager() -> AsyncGenerator[AgentManager, None]:
    """Create an agent manager for testing."""
    manager = AgentManager()
    yield manager
    await manager.shutdown()


# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an asyncio test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
