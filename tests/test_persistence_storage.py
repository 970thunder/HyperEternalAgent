"""
Tests for storage backends.
"""

import pytest
import asyncio

from hypereternal.persistence.storage import (
    MemoryStorageBackend,
    FileStorageBackend,
    create_storage_backend,
)


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
        assert "prefix:key1" in keys
        assert "prefix:key2" in keys

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


class TestCreateStorageBackend:
    """Tests for create_storage_backend factory function."""

    def test_create_memory_backend(self):
        """Test creating memory backend."""
        storage = create_storage_backend("memory")
        assert isinstance(storage, MemoryStorageBackend)

    def test_create_file_backend(self):
        """Test creating file backend."""
        storage = create_storage_backend("file", storage_path="./test_storage")
        assert isinstance(storage, FileStorageBackend)

    def test_create_unknown_backend(self):
        """Test creating unknown backend raises error."""
        with pytest.raises(Exception):
            create_storage_backend("unknown")
