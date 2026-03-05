"""
Storage backend implementations for HyperEternalAgent framework.
"""

import asyncio
import json
import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.exceptions import StorageConnectionError, StorageError, StorageOperationError
from ..infrastructure.logging import get_logger

logger = get_logger(__name__)


class StorageBackend(ABC):
    """Abstract storage backend interface."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value with optional TTL (seconds)."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value by key."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass

    @abstractmethod
    async def list_keys(self, pattern: str = "*") -> List[str]:
        """List keys matching pattern."""
        pass

    @abstractmethod
    async def clear(self) -> int:
        """Clear all data. Returns number of keys deleted."""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Connect to storage."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from storage."""
        pass


class MemoryStorageBackend(StorageBackend):
    """In-memory storage backend for testing and development."""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._ttl: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Connect (no-op for memory storage)."""
        pass

    async def disconnect(self) -> None:
        """Disconnect and clear data."""
        async with self._lock:
            self._data.clear()
            self._ttl.clear()

    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        async with self._lock:
            # Check TTL
            if key in self._ttl:
                if datetime.now() > self._ttl[key]:
                    del self._data[key]
                    del self._ttl[key]
                    return None

            return self._data.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value with optional TTL."""
        async with self._lock:
            self._data[key] = value

            if ttl:
                self._ttl[key] = datetime.now() + timedelta(seconds=ttl)
            elif key in self._ttl:
                del self._ttl[key]

            return True

    async def delete(self, key: str) -> bool:
        """Delete value by key."""
        async with self._lock:
            if key in self._data:
                del self._data[key]
                self._ttl.pop(key, None)
                return True
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        value = await self.get(key)
        return value is not None

    async def list_keys(self, pattern: str = "*") -> List[str]:
        """List keys matching pattern."""
        import fnmatch

        async with self._lock:
            keys = list(self._data.keys())

            if pattern == "*":
                return keys

            return [k for k in keys if fnmatch.fnmatch(k, pattern)]

    async def clear(self) -> int:
        """Clear all data."""
        async with self._lock:
            count = len(self._data)
            self._data.clear()
            self._ttl.clear()
            return count


class FileStorageBackend(StorageBackend):
    """File-based storage backend."""

    def __init__(self, storage_path: str = "./data/storage"):
        self.storage_path = Path(storage_path)
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Create storage directory."""
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def disconnect(self) -> None:
        """Disconnect (no-op for file storage)."""
        pass

    def _get_file_path(self, key: str) -> Path:
        """Get file path for key."""
        # Sanitize key for filesystem
        safe_key = key.replace(":", "_").replace("/", "_")
        return self.storage_path / f"{safe_key}.dat"

    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        file_path = self._get_file_path(key)

        async with self._lock:
            if not file_path.exists():
                return None

            try:
                with open(file_path, "rb") as f:
                    data = pickle.load(f)

                # Check TTL
                if "expires_at" in data:
                    if datetime.now() > data["expires_at"]:
                        file_path.unlink()
                        return None

                return data.get("value")

            except Exception as e:
                logger.error("file_storage_get_error", key=key, error=str(e))
                return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value with optional TTL."""
        file_path = self._get_file_path(key)

        data = {
            "value": value,
            "created_at": datetime.now(),
        }

        if ttl:
            data["expires_at"] = datetime.now() + timedelta(seconds=ttl)

        async with self._lock:
            try:
                with open(file_path, "wb") as f:
                    pickle.dump(data, f)
                return True
            except Exception as e:
                logger.error("file_storage_set_error", key=key, error=str(e))
                return False

    async def delete(self, key: str) -> bool:
        """Delete value by key."""
        file_path = self._get_file_path(key)

        async with self._lock:
            if file_path.exists():
                file_path.unlink()
                return True
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        value = await self.get(key)
        return value is not None

    async def list_keys(self, pattern: str = "*") -> List[str]:
        """List keys matching pattern."""
        import fnmatch

        keys = []
        async with self._lock:
            for file_path in self.storage_path.glob("*.dat"):
                key = file_path.stem.replace("_", ":")
                if fnmatch.fnmatch(key, pattern):
                    keys.append(key)

        return keys

    async def clear(self) -> int:
        """Clear all data."""
        count = 0
        async with self._lock:
            for file_path in self.storage_path.glob("*.dat"):
                file_path.unlink()
                count += 1
        return count


class RedisStorageBackend(StorageBackend):
    """Redis storage backend."""

    def __init__(self, url: str = "redis://localhost:6379/0"):
        self.url = url
        self._client: Optional[Any] = None

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            import redis.asyncio as redis

            self._client = redis.from_url(self.url)
            await self._client.ping()
            logger.info("redis_storage_connected", url=self.url)
        except ImportError:
            raise StorageError("redis package not installed. Run: pip install redis")
        except Exception as e:
            raise StorageConnectionError(f"Failed to connect to Redis: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._client = None

    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        if not self._client:
            raise StorageError("Not connected to Redis")

        try:
            data = await self._client.get(key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            logger.error("redis_storage_get_error", key=key, error=str(e))
            raise StorageOperationError(f"Redis get operation failed: {e}")

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value with optional TTL."""
        if not self._client:
            raise StorageError("Not connected to Redis")

        try:
            data = pickle.dumps(value)
            if ttl:
                await self._client.setex(key, ttl, data)
            else:
                await self._client.set(key, data)
            return True
        except Exception as e:
            logger.error("redis_storage_set_error", key=key, error=str(e))
            raise StorageOperationError(f"Redis set operation failed: {e}")

    async def delete(self, key: str) -> bool:
        """Delete value by key."""
        if not self._client:
            raise StorageError("Not connected to Redis")

        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.error("redis_storage_delete_error", key=key, error=str(e))
            raise StorageOperationError(f"Redis delete operation failed: {e}")

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._client:
            raise StorageError("Not connected to Redis")

        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.error("redis_storage_exists_error", key=key, error=str(e))
            raise StorageOperationError(f"Redis exists operation failed: {e}")

    async def list_keys(self, pattern: str = "*") -> List[str]:
        """List keys matching pattern."""
        if not self._client:
            raise StorageError("Not connected to Redis")

        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key.decode() if isinstance(key, bytes) else key)
            return keys
        except Exception as e:
            logger.error("redis_storage_list_keys_error", pattern=pattern, error=str(e))
            raise StorageOperationError(f"Redis list_keys operation failed: {e}")

    async def clear(self) -> int:
        """Clear all data in current database."""
        if not self._client:
            raise StorageError("Not connected to Redis")

        try:
            await self._client.flushdb()
            return 0  # flushdb doesn't return count
        except Exception as e:
            logger.error("redis_storage_clear_error", error=str(e))
            raise StorageOperationError(f"Redis clear operation failed: {e}")


def create_storage_backend(
    backend_type: str = "memory",
    **kwargs: Any,
) -> StorageBackend:
    """
    Factory function to create storage backend.

    Args:
        backend_type: Type of storage backend ("memory", "file", "redis")
        **kwargs: Backend-specific arguments

    Returns:
        Storage backend instance
    """
    backend_type = backend_type.lower()

    if backend_type == "memory":
        return MemoryStorageBackend()
    elif backend_type == "file":
        return FileStorageBackend(storage_path=kwargs.get("storage_path", "./data/storage"))
    elif backend_type == "redis":
        return RedisStorageBackend(url=kwargs.get("url", "redis://localhost:6379/0"))
    else:
        raise StorageError(f"Unknown storage backend type: {backend_type}")
