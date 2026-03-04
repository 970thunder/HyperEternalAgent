# 持久层设计文档

## 1. 概述

持久层（Persistence Layer）是 HyperEternalAgent 框架的基础设施，确保系统能够长时间稳定运行并从故障中恢复。本文档详细描述状态管理、任务队列和检查点系统的设计。

## 2. 核心组件

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Persistence Layer                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                       State Manager                                 │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────────┐  │ │
│  │  │ Global State │ │ Session State│ │    State Versioning        │  │ │
│  │  └──────────────┘ └──────────────┘ └────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                       Task Queue                                    │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────────┐  │ │
│  │  │   Priority   │ │   Dead       │ │    Task                    │  │ │
│  │  │   Queue      │ │   Letter     │ │    Persistence             │  │ │
│  │  └──────────────┘ └──────────────┘ └────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    Checkpoint System                                │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────────┐  │ │
│  │  │   Snapshot   │ │   Incremental│ │    Recovery                │  │ │
│  │  │   Manager    │ │   Saver      │ │    Manager                 │  │ │
│  │  └──────────────┘ └──────────────┘ └────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                     Storage Backends                                │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────────┐  │ │
│  │  │   Redis      │ │  PostgreSQL  │ │    File System             │  │ │
│  │  └──────────────┘ └──────────────┘ └────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 3. State Manager (状态管理器)

### 3.1 状态模型

```python
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from datetime import datetime
from enum import Enum
import json
import hashlib

class StateScope(Enum):
    """状态作用域"""
    GLOBAL = "global"       # 全局状态
    SESSION = "session"     # 会话状态
    FLOW = "flow"           # 流程状态
    AGENT = "agent"         # Agent状态
    TASK = "task"           # 任务状态

@dataclass
class StateEntry:
    """状态条目"""
    key: str
    value: Any
    scope: StateScope
    owner_id: Optional[str] = None
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    ttl: Optional[int] = None  # 过期时间(秒)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "scope": self.scope.value,
            "owner_id": self.owner_id,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "ttl": self.ttl,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateEntry":
        return cls(
            key=data["key"],
            value=data["value"],
            scope=StateScope(data["scope"]),
            owner_id=data.get("owner_id"),
            version=data.get("version", 1),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            ttl=data.get("ttl"),
            metadata=data.get("metadata", {})
        )
```

### 3.2 State Manager 实现

```python
import asyncio
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

class StateManager:
    """状态管理器"""

    def __init__(self, storage_backend: StorageBackend):
        self.storage = storage_backend
        self.cache: Dict[str, StateEntry] = {}
        self.locks: Dict[str, asyncio.Lock] = {}
        self._lock = asyncio.Lock()

    async def get(
        self,
        key: str,
        scope: StateScope = StateScope.GLOBAL,
        owner_id: Optional[str] = None
    ) -> Optional[Any]:
        """获取状态值"""
        full_key = self._make_key(key, scope, owner_id)

        # 先查缓存
        if full_key in self.cache:
            entry = self.cache[full_key]
            if not self._is_expired(entry):
                return entry.value

        # 从存储加载
        entry = await self.storage.get(full_key)
        if entry:
            self.cache[full_key] = entry
            return entry.value

        return None

    async def set(
        self,
        key: str,
        value: Any,
        scope: StateScope = StateScope.GLOBAL,
        owner_id: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> StateEntry:
        """设置状态值"""
        full_key = self._make_key(key, scope, owner_id)

        async with await self._get_lock(full_key):
            # 获取现有条目或创建新条目
            existing = await self.storage.get(full_key)

            if existing:
                entry = StateEntry(
                    key=key,
                    value=value,
                    scope=scope,
                    owner_id=owner_id,
                    version=existing.version + 1,
                    created_at=existing.created_at,
                    updated_at=datetime.now(),
                    ttl=ttl,
                    metadata=existing.metadata
                )
            else:
                entry = StateEntry(
                    key=key,
                    value=value,
                    scope=scope,
                    owner_id=owner_id,
                    ttl=ttl
                )

            # 保存到存储和缓存
            await self.storage.set(full_key, entry)
            self.cache[full_key] = entry

            return entry

    async def delete(
        self,
        key: str,
        scope: StateScope = StateScope.GLOBAL,
        owner_id: Optional[str] = None
    ) -> bool:
        """删除状态"""
        full_key = self._make_key(key, scope, owner_id)

        await self.storage.delete(full_key)
        self.cache.pop(full_key, None)

        return True

    async def list_keys(
        self,
        scope: StateScope,
        owner_id: Optional[str] = None,
        prefix: Optional[str] = None
    ) -> List[str]:
        """列出所有键"""
        pattern = self._make_key(prefix or "*", scope, owner_id)
        return await self.storage.list_keys(pattern)

    async def clear_scope(
        self,
        scope: StateScope,
        owner_id: Optional[str] = None
    ) -> int:
        """清除作用域内所有状态"""
        keys = await self.list_keys(scope, owner_id)
        count = 0

        for key in keys:
            await self.delete(key, scope, owner_id)
            count += 1

        return count

    def _make_key(
        self,
        key: str,
        scope: StateScope,
        owner_id: Optional[str]
    ) -> str:
        """生成完整键"""
        parts = [scope.value]
        if owner_id:
            parts.append(owner_id)
        parts.append(key)
        return ":".join(parts)

    def _is_expired(self, entry: StateEntry) -> bool:
        """检查是否过期"""
        if entry.ttl is None:
            return False
        elapsed = (datetime.now() - entry.updated_at).total_seconds()
        return elapsed > entry.ttl

    async def _get_lock(self, key: str) -> asyncio.Lock:
        """获取键锁"""
        async with self._lock:
            if key not in self.locks:
                self.locks[key] = asyncio.Lock()
            return self.locks[key]
```

### 3.3 状态版本控制

```python
@dataclass
class StateVersion:
    """状态版本"""
    version_id: str
    state_snapshot: Dict[str, Any]
    changes: List[StateChange]
    created_at: datetime
    parent_version: Optional[str] = None

@dataclass
class StateChange:
    """状态变更"""
    key: str
    old_value: Any
    new_value: Any
    operation: str  # "set", "delete"
    timestamp: datetime

class StateVersioning:
    """状态版本控制"""

    def __init__(self, state_manager: StateManager, max_versions: int = 100):
        self.state_manager = state_manager
        self.max_versions = max_versions
        self.versions: Dict[str, StateVersion] = {}
        self.current_version: Optional[str] = None
        self.change_log: List[StateChange] = []

    async def checkpoint(self, label: str = None) -> str:
        """创建检查点"""
        # 获取当前状态快照
        snapshot = await self._create_snapshot()

        # 创建版本
        version_id = self._generate_version_id(label)
        version = StateVersion(
            version_id=version_id,
            state_snapshot=snapshot,
            changes=self.change_log.copy(),
            created_at=datetime.now(),
            parent_version=self.current_version
        )

        self.versions[version_id] = version
        self.current_version = version_id
        self.change_log.clear()

        # 清理旧版本
        await self._cleanup_old_versions()

        return version_id

    async def restore(self, version_id: str) -> bool:
        """恢复到指定版本"""
        if version_id not in self.versions:
            return False

        version = self.versions[version_id]

        # 恢复状态
        for key, value in version.state_snapshot.items():
            await self.state_manager.set(
                key,
                value,
                scope=StateScope.GLOBAL
            )

        self.current_version = version_id
        return True

    async def get_history(self, key: str) -> List[StateChange]:
        """获取键的变更历史"""
        history = []

        for version in self.versions.values():
            for change in version.changes:
                if change.key == key:
                    history.append(change)

        return sorted(history, key=lambda c: c.timestamp)

    async def diff_versions(
        self,
        version_id1: str,
        version_id2: str
    ) -> Dict[str, Any]:
        """比较两个版本的差异"""
        v1 = self.versions.get(version_id1)
        v2 = self.versions.get(version_id2)

        if not v1 or not v2:
            return {}

        diff = {
            "added": {},
            "removed": {},
            "modified": {}
        }

        keys1 = set(v1.state_snapshot.keys())
        keys2 = set(v2.state_snapshot.keys())

        # 新增的键
        for key in keys2 - keys1:
            diff["added"][key] = v2.state_snapshot[key]

        # 删除的键
        for key in keys1 - keys2:
            diff["removed"][key] = v1.state_snapshot[key]

        # 修改的键
        for key in keys1 & keys2:
            if v1.state_snapshot[key] != v2.state_snapshot[key]:
                diff["modified"][key] = {
                    "old": v1.state_snapshot[key],
                    "new": v2.state_snapshot[key]
                }

        return diff

    async def _create_snapshot(self) -> Dict[str, Any]:
        """创建状态快照"""
        keys = await self.state_manager.list_keys(StateScope.GLOBAL)
        snapshot = {}

        for key in keys:
            value = await self.state_manager.get(key, StateScope.GLOBAL)
            if value is not None:
                snapshot[key] = value

        return snapshot

    async def _cleanup_old_versions(self) -> None:
        """清理旧版本"""
        if len(self.versions) <= self.max_versions:
            return

        # 按时间排序，保留最新的
        sorted_versions = sorted(
            self.versions.items(),
            key=lambda x: x[1].created_at,
            reverse=True
        )

        # 删除旧版本
        for version_id, _ in sorted_versions[self.max_versions:]:
            del self.versions[version_id]
```

## 4. Task Queue (任务队列)

### 4.1 任务队列模型

```python
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"           # 等待执行
    QUEUED = "queued"             # 已入队
    RUNNING = "running"           # 执行中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    CANCELLED = "cancelled"       # 已取消
    RETRYING = "retrying"         # 重试中
    TIMEOUT = "timeout"           # 超时

@dataclass
class QueuedTask:
    """队列任务"""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: int = 0
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "payload": self.payload,
            "priority": self.priority,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata
        }
```

### 4.2 Task Queue 实现

```python
import asyncio
import heapq
from typing import List, Optional, Callable
from collections import defaultdict

class TaskQueue:
    """任务队列"""

    def __init__(
        self,
        storage_backend: StorageBackend,
        max_size: int = 10000,
        visibility_timeout: int = 300
    ):
        self.storage = storage_backend
        self.max_size = max_size
        self.visibility_timeout = visibility_timeout

        # 优先级队列
        self.priority_queue: List[tuple] = []
        self.sequence = 0

        # 任务存储
        self.tasks: Dict[str, QueuedTask] = {}

        # 状态索引
        self.status_index: Dict[TaskStatus, Set[str]] = defaultdict(set)
        self.type_index: Dict[str, Set[str]] = defaultdict(set)

        # 锁
        self.lock = asyncio.Lock()

        # 事件
        self.task_available = asyncio.Event()

    async def enqueue(
        self,
        task: QueuedTask
    ) -> bool:
        """入队"""
        async with self.lock:
            if len(self.tasks) >= self.max_size:
                raise QueueFullError("Task queue is full")

            # 保存任务
            self.tasks[task.task_id] = task
            task.status = TaskStatus.QUEUED

            # 添加到优先级队列
            heapq.heappush(
                self.priority_queue,
                (-task.priority, self.sequence, task.task_id)
            )
            self.sequence += 1

            # 更新索引
            self.status_index[TaskStatus.QUEUED].add(task.task_id)
            self.type_index[task.task_type].add(task.task_id)

            # 持久化
            await self.storage.set(f"task:{task.task_id}", task)

            # 通知
            self.task_available.set()

            return True

    async def dequeue(
        self,
        task_types: List[str] = None,
        timeout: float = None
    ) -> Optional[QueuedTask]:
        """出队"""
        start_time = asyncio.get_event_loop().time()

        while True:
            async with self.lock:
                # 查找可用任务
                task = self._find_available_task(task_types)

                if task:
                    # 标记为运行中
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now()

                    # 更新索引
                    self.status_index[TaskStatus.QUEUED].discard(task.task_id)
                    self.status_index[TaskStatus.RUNNING].add(task.task_id)

                    # 持久化
                    await self.storage.set(f"task:{task.task_id}", task)

                    return task

            # 检查超时
            if timeout is not None:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    return None

            # 等待新任务
            self.task_available.clear()
            try:
                await asyncio.wait_for(
                    self.task_available.wait(),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                continue

    async def complete(
        self,
        task_id: str,
        result: Any = None
    ) -> bool:
        """标记任务完成"""
        async with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result

            # 更新索引
            self.status_index[TaskStatus.RUNNING].discard(task_id)
            self.status_index[TaskStatus.COMPLETED].add(task_id)

            # 持久化
            await self.storage.set(f"task:{task_id}", task)

            return True

    async def fail(
        self,
        task_id: str,
        error: str,
        retry: bool = True
    ) -> bool:
        """标记任务失败"""
        async with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False

            task.error = error

            if retry and task.retry_count < task.max_retries:
                # 重试
                task.status = TaskStatus.RETRYING
                task.retry_count += 1

                # 重新入队
                heapq.heappush(
                    self.priority_queue,
                    (-task.priority, self.sequence, task.task_id)
                )
                self.sequence += 1

                self.status_index[TaskStatus.RUNNING].discard(task_id)
                self.status_index[TaskStatus.RETRYING].add(task_id)
            else:
                # 标记失败
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()

                self.status_index[TaskStatus.RUNNING].discard(task_id)
                self.status_index[TaskStatus.FAILED].add(task_id)

            await self.storage.set(f"task:{task_id}", task)
            return True

    async def cancel(self, task_id: str) -> bool:
        """取消任务"""
        async with self.lock:
            task = self.tasks.get(task_id)
            if not task or task.status not in [TaskStatus.PENDING, TaskStatus.QUEUED]:
                return False

            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()

            # 更新索引
            self.status_index[task.status].discard(task_id)
            self.status_index[TaskStatus.CANCELLED].add(task_id)

            await self.storage.set(f"task:{task_id}", task)
            return True

    def _find_available_task(
        self,
        task_types: List[str] = None
    ) -> Optional[QueuedTask]:
        """查找可用任务"""
        temp_queue = []

        while self.priority_queue:
            _, _, task_id = heapq.heappop(self.priority_queue)
            task = self.tasks.get(task_id)

            if not task:
                continue

            # 检查状态
            if task.status != TaskStatus.QUEUED:
                continue

            # 检查类型
            if task_types and task.task_type not in task_types:
                temp_queue.append((-task.priority, self.sequence, task.task_id))
                self.sequence += 1
                continue

            # 检查依赖
            if not self._check_dependencies(task):
                temp_queue.append((-task.priority, self.sequence, task.task_id))
                self.sequence += 1
                continue

            # 找到可用任务
            for item in temp_queue:
                heapq.heappush(self.priority_queue, item)

            return task

        for item in temp_queue:
            heapq.heappush(self.priority_queue, item)

        return None

    def _check_dependencies(self, task: QueuedTask) -> bool:
        """检查依赖是否满足"""
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    async def get_stats(self) -> Dict[str, Any]:
        """获取队列统计"""
        async with self.lock:
            return {
                "total_tasks": len(self.tasks),
                "queue_size": len(self.priority_queue),
                "by_status": {
                    status.value: len(ids)
                    for status, ids in self.status_index.items()
                },
                "by_type": {
                    task_type: len(ids)
                    for task_type, ids in self.type_index.items()
                }
            }
```

### 4.3 Dead Letter Queue

```python
class DeadLetterQueue:
    """死信队列"""

    def __init__(self, storage_backend: StorageBackend, max_size: int = 1000):
        self.storage = storage_backend
        self.max_size = max_size
        self.dead_letters: Dict[str, DeadLetter] = {}

    async def add(
        self,
        task: QueuedTask,
        reason: str,
        error_trace: Optional[str] = None
    ) -> bool:
        """添加到死信队列"""
        if len(self.dead_letters) >= self.max_size:
            # 移除最旧的
            oldest = min(
                self.dead_letters.values(),
                key=lambda x: x.created_at
            )
            del self.dead_letters[oldest.task_id]

        dead_letter = DeadLetter(
            task_id=task.task_id,
            original_task=task,
            reason=reason,
            error_trace=error_trace,
            created_at=datetime.now()
        )

        self.dead_letters[task.task_id] = dead_letter
        await self.storage.set(f"dead_letter:{task.task_id}", dead_letter)

        return True

    async def get(self, task_id: str) -> Optional[DeadLetter]:
        """获取死信"""
        return self.dead_letters.get(task_id)

    async def list(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[DeadLetter]:
        """列出死信"""
        sorted_letters = sorted(
            self.dead_letters.values(),
            key=lambda x: x.created_at,
            reverse=True
        )
        return sorted_letters[offset:offset + limit]

    async def requeue(self, task_id: str) -> bool:
        """重新入队"""
        dead_letter = self.dead_letters.get(task_id)
        if not dead_letter:
            return False

        # 重置任务状态
        task = dead_letter.original_task
        task.status = TaskStatus.PENDING
        task.retry_count = 0
        task.error = None

        # 从死信队列移除
        del self.dead_letters[task_id]
        await self.storage.delete(f"dead_letter:{task_id}")

        return True

    async def purge(self) -> int:
        """清空死信队列"""
        count = len(self.dead_letters)

        for task_id in list(self.dead_letters.keys()):
            await self.storage.delete(f"dead_letter:{task_id}")

        self.dead_letters.clear()
        return count

@dataclass
class DeadLetter:
    """死信"""
    task_id: str
    original_task: QueuedTask
    reason: str
    error_trace: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    requeue_count: int = 0
```

## 5. Checkpoint System (检查点系统)

### 5.1 快照管理器

```python
import pickle
import gzip
from pathlib import Path

class SnapshotManager:
    """快照管理器"""

    def __init__(
        self,
        state_manager: StateManager,
        storage_path: str = "./checkpoints",
        max_snapshots: int = 10
    ):
        self.state_manager = state_manager
        self.storage_path = Path(storage_path)
        self.max_snapshots = max_snapshots
        self.snapshots: Dict[str, Snapshot] = {}

        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def create_snapshot(
        self,
        label: str = None,
        include_metadata: bool = True
    ) -> Snapshot:
        """创建快照"""
        snapshot_id = self._generate_snapshot_id()
        timestamp = datetime.now()

        # 收集状态
        state_data = await self._collect_state()

        # 计算校验和
        checksum = self._calculate_checksum(state_data)

        # 创建快照对象
        snapshot = Snapshot(
            snapshot_id=snapshot_id,
            label=label,
            timestamp=timestamp,
            state_data=state_data,
            checksum=checksum,
            size_bytes=len(pickle.dumps(state_data))
        )

        # 保存到磁盘
        await self._save_snapshot(snapshot)

        # 记录
        self.snapshots[snapshot_id] = snapshot

        # 清理旧快照
        await self._cleanup_old_snapshots()

        return snapshot

    async def restore_snapshot(self, snapshot_id: str) -> bool:
        """恢复快照"""
        snapshot = self.snapshots.get(snapshot_id)

        if not snapshot:
            # 尝试从磁盘加载
            snapshot = await self._load_snapshot(snapshot_id)

        if not snapshot:
            return False

        # 验证校验和
        if not self._verify_checksum(snapshot):
            raise ChecksumMismatchError("Snapshot checksum verification failed")

        # 恢复状态
        await self._restore_state(snapshot.state_data)

        return True

    async def list_snapshots(self) -> List[Snapshot]:
        """列出所有快照"""
        return sorted(
            self.snapshots.values(),
            key=lambda s: s.timestamp,
            reverse=True
        )

    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """删除快照"""
        if snapshot_id not in self.snapshots:
            return False

        snapshot = self.snapshots[snapshot_id]

        # 删除文件
        snapshot_path = self._get_snapshot_path(snapshot_id)
        if snapshot_path.exists():
            snapshot_path.unlink()

        del self.snapshots[snapshot_id]
        return True

    async def _collect_state(self) -> Dict[str, Any]:
        """收集状态数据"""
        state_data = {
            "global_state": {},
            "sessions": {},
            "flows": {},
            "agents": {}
        }

        # 收集全局状态
        keys = await self.state_manager.list_keys(StateScope.GLOBAL)
        for key in keys:
            value = await self.state_manager.get(key, StateScope.GLOBAL)
            state_data["global_state"][key] = value

        # 收集会话状态
        session_keys = await self.state_manager.list_keys(StateScope.SESSION)
        for key in session_keys:
            value = await self.state_manager.get(key, StateScope.SESSION)
            state_data["sessions"][key] = value

        return state_data

    async def _restore_state(self, state_data: Dict[str, Any]) -> None:
        """恢复状态"""
        # 恢复全局状态
        for key, value in state_data.get("global_state", {}).items():
            await self.state_manager.set(key, value, StateScope.GLOBAL)

        # 恢复会话状态
        for key, value in state_data.get("sessions", {}).items():
            await self.state_manager.set(key, value, StateScope.SESSION)

    async def _save_snapshot(self, snapshot: Snapshot) -> None:
        """保存快照到磁盘"""
        snapshot_path = self._get_snapshot_path(snapshot.snapshot_id)

        data = {
            "snapshot_id": snapshot.snapshot_id,
            "label": snapshot.label,
            "timestamp": snapshot.timestamp.isoformat(),
            "state_data": snapshot.state_data,
            "checksum": snapshot.checksum,
            "size_bytes": snapshot.size_bytes
        }

        with gzip.open(snapshot_path, 'wb') as f:
            pickle.dump(data, f)

    async def _load_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """从磁盘加载快照"""
        snapshot_path = self._get_snapshot_path(snapshot_id)

        if not snapshot_path.exists():
            return None

        with gzip.open(snapshot_path, 'rb') as f:
            data = pickle.load(f)

        snapshot = Snapshot(
            snapshot_id=data["snapshot_id"],
            label=data["label"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            state_data=data["state_data"],
            checksum=data["checksum"],
            size_bytes=data["size_bytes"]
        )

        self.snapshots[snapshot_id] = snapshot
        return snapshot

    def _get_snapshot_path(self, snapshot_id: str) -> Path:
        """获取快照文件路径"""
        return self.storage_path / f"{snapshot_id}.snapshot.gz"

    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """计算校验和"""
        return hashlib.sha256(
            pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        ).hexdigest()

    def _verify_checksum(self, snapshot: Snapshot) -> bool:
        """验证校验和"""
        current_checksum = self._calculate_checksum(snapshot.state_data)
        return current_checksum == snapshot.checksum

    async def _cleanup_old_snapshots(self) -> None:
        """清理旧快照"""
        if len(self.snapshots) <= self.max_snapshots:
            return

        # 按时间排序
        sorted_snapshots = sorted(
            self.snapshots.items(),
            key=lambda x: x[1].timestamp
        )

        # 删除最旧的
        for snapshot_id, _ in sorted_snapshots[:-self.max_snapshots]:
            await self.delete_snapshot(snapshot_id)

@dataclass
class Snapshot:
    """快照"""
    snapshot_id: str
    label: Optional[str]
    timestamp: datetime
    state_data: Dict[str, Any]
    checksum: str
    size_bytes: int
```

### 5.2 增量保存器

```python
class IncrementalSaver:
    """增量保存器"""

    def __init__(
        self,
        state_manager: StateManager,
        storage_backend: StorageBackend,
        save_interval: int = 60
    ):
        self.state_manager = state_manager
        self.storage = storage_backend
        self.save_interval = save_interval

        self.changes: List[StateChange] = []
        self.last_save: Optional[datetime] = None
        self.running = False

    async def start(self) -> None:
        """启动增量保存"""
        self.running = True
        asyncio.create_task(self._save_loop())

    async def stop(self) -> None:
        """停止增量保存"""
        self.running = False
        # 保存最后的变更
        await self._save_changes()

    def record_change(
        self,
        key: str,
        old_value: Any,
        new_value: Any,
        operation: str
    ) -> None:
        """记录变更"""
        change = StateChange(
            key=key,
            old_value=old_value,
            new_value=new_value,
            operation=operation,
            timestamp=datetime.now()
        )
        self.changes.append(change)

    async def _save_loop(self) -> None:
        """保存循环"""
        while self.running:
            await asyncio.sleep(self.save_interval)

            if self.changes:
                await self._save_changes()

    async def _save_changes(self) -> None:
        """保存变更"""
        if not self.changes:
            return

        # 创建增量记录
        increment = IncrementRecord(
            increment_id=str(uuid.uuid4()),
            changes=self.changes.copy(),
            timestamp=datetime.now(),
            previous_save=self.last_save
        )

        # 保存
        await self.storage.set(f"increment:{increment.increment_id}", increment)

        # 清空变更
        self.changes.clear()
        self.last_save = increment.timestamp

@dataclass
class IncrementRecord:
    """增量记录"""
    increment_id: str
    changes: List[StateChange]
    timestamp: datetime
    previous_save: Optional[datetime] = None
```

### 5.3 恢复管理器

```python
class RecoveryManager:
    """恢复管理器"""

    def __init__(
        self,
        snapshot_manager: SnapshotManager,
        incremental_saver: IncrementalSaver,
        task_queue: TaskQueue
    ):
        self.snapshot_manager = snapshot_manager
        self.incremental_saver = incremental_saver
        self.task_queue = task_queue

    async def recover(self, strategy: str = "latest") -> RecoveryResult:
        """执行恢复"""
        result = RecoveryResult(
            strategy=strategy,
            started_at=datetime.now()
        )

        try:
            if strategy == "latest":
                await self._recover_latest(result)
            elif strategy == "point_in_time":
                await self._recover_point_in_time(result)
            elif strategy == "clean":
                await self._recover_clean(result)
            else:
                raise ValueError(f"Unknown recovery strategy: {strategy}")

            result.success = True

        except Exception as e:
            result.success = False
            result.error = str(e)

        result.completed_at = datetime.now()
        return result

    async def _recover_latest(self, result: RecoveryResult) -> None:
        """恢复到最新状态"""
        # 获取最新快照
        snapshots = await self.snapshot_manager.list_snapshots()
        if not snapshots:
            result.message = "No snapshots available"
            return

        latest_snapshot = snapshots[0]
        result.snapshot_id = latest_snapshot.snapshot_id

        # 恢复快照
        await self.snapshot_manager.restore_snapshot(latest_snapshot.snapshot_id)
        result.restored_state = True

        # 应用增量
        await self._apply_pending_increments(result)

        # 恢复任务队列
        await self._recover_task_queue(result)

        result.message = f"Recovered to snapshot {latest_snapshot.snapshot_id}"

    async def _recover_point_in_time(self, result: RecoveryResult) -> None:
        """恢复到指定时间点"""
        # TODO: 实现时间点恢复
        pass

    async def _recover_clean(self, result: RecoveryResult) -> None:
        """干净恢复"""
        # 清除所有状态
        await self._clear_all_state()
        result.message = "Performed clean recovery"

    async def _apply_pending_increments(self, result: RecoveryResult) -> None:
        """应用待处理的增量"""
        # TODO: 实现增量应用
        pass

    async def _recover_task_queue(self, result: RecoveryResult) -> None:
        """恢复任务队列"""
        stats = await self.task_queue.get_stats()
        result.recovered_tasks = stats.get("total_tasks", 0)

    async def _clear_all_state(self) -> None:
        """清除所有状态"""
        await self.state_manager.clear_scope(StateScope.GLOBAL)
        await self.state_manager.clear_scope(StateScope.SESSION)

@dataclass
class RecoveryResult:
    """恢复结果"""
    strategy: str
    success: bool = False
    message: str = ""
    error: Optional[str] = None
    snapshot_id: Optional[str] = None
    restored_state: bool = False
    recovered_tasks: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
```

## 6. Storage Backends (存储后端)

### 6.1 抽象接口

```python
from abc import ABC, abstractmethod

class StorageBackend(ABC):
    """存储后端抽象接口"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """获取值"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """设置值"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除值"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查是否存在"""
        pass

    @abstractmethod
    async def list_keys(self, pattern: str) -> List[str]:
        """列出匹配的键"""
        pass

    @abstractmethod
    async def clear(self) -> int:
        """清空存储"""
        pass
```

### 6.2 Redis 后端

```python
import redis.asyncio as redis

class RedisStorageBackend(StorageBackend):
    """Redis存储后端"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """连接Redis"""
        self.client = await redis.from_url(self.redis_url)

    async def disconnect(self) -> None:
        """断开连接"""
        if self.client:
            await self.client.close()

    async def get(self, key: str) -> Optional[Any]:
        """获取值"""
        data = await self.client.get(key)
        if data:
            return pickle.loads(data)
        return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """设置值"""
        data = pickle.dumps(value)
        if ttl:
            await self.client.setex(key, ttl, data)
        else:
            await self.client.set(key, data)
        return True

    async def delete(self, key: str) -> bool:
        """删除值"""
        await self.client.delete(key)
        return True

    async def exists(self, key: str) -> bool:
        """检查是否存在"""
        return await self.client.exists(key) > 0

    async def list_keys(self, pattern: str) -> List[str]:
        """列出匹配的键"""
        keys = []
        async for key in self.client.scan_iter(match=pattern):
            keys.append(key.decode())
        return keys

    async def clear(self) -> int:
        """清空存储"""
        await self.client.flushdb()
        return 0
```

### 6.3 PostgreSQL 后端

```python
import asyncpg

class PostgreSQLStorageBackend(StorageBackend):
    """PostgreSQL存储后端"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """连接数据库"""
        self.pool = await asyncpg.create_pool(self.database_url)

        # 创建表
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS state_store (
                    key VARCHAR(255) PRIMARY KEY,
                    value JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at ON state_store(expires_at)
            """)

    async def disconnect(self) -> None:
        """断开连接"""
        if self.pool:
            await self.pool.close()

    async def get(self, key: str) -> Optional[Any]:
        """获取值"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT value FROM state_store
                WHERE key = $1
                AND (expires_at IS NULL OR expires_at > NOW())
                """,
                key
            )
            if row:
                return row["value"]
            return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """设置值"""
        expires_at = None
        if ttl:
            expires_at = datetime.now() + timedelta(seconds=ttl)

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO state_store (key, value, updated_at, expires_at)
                VALUES ($1, $2, NOW(), $3)
                ON CONFLICT (key)
                DO UPDATE SET value = $2, updated_at = NOW(), expires_at = $3
                """,
                key, json.dumps(value), expires_at
            )
            return True

    async def delete(self, key: str) -> bool:
        """删除值"""
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM state_store WHERE key = $1", key)
            return True

    async def exists(self, key: str) -> bool:
        """检查是否存在"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM state_store
                    WHERE key = $1
                    AND (expires_at IS NULL OR expires_at > NOW())
                )
                """,
                key
            )
            return result

    async def list_keys(self, pattern: str) -> List[str]:
        """列出匹配的键"""
        sql_pattern = pattern.replace("*", "%")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT key FROM state_store
                WHERE key LIKE $1
                AND (expires_at IS NULL OR expires_at > NOW())
                """,
                sql_pattern
            )
            return [row["key"] for row in rows]

    async def clear(self) -> int:
        """清空存储"""
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM state_store")
            return int(result.split()[-1])
```

## 7. 配置示例

```yaml
# persistence_config.yaml
persistence:
  state_manager:
    default_scope: "global"
    cache_size: 10000
    lock_timeout: 30

  task_queue:
    max_size: 10000
    visibility_timeout: 300
    dead_letter_max_size: 1000
    retry_policy:
      max_retries: 3
      backoff_factor: 2.0
      max_backoff: 300

  checkpoint:
    enabled: true
    storage_path: "./checkpoints"
    max_snapshots: 10
    snapshot_interval: 3600  # 每小时
    incremental_save:
      enabled: true
      save_interval: 60  # 每分钟

  storage:
    primary:
      type: "redis"
      url: "${REDIS_URL:redis://localhost:6379/0}"
    secondary:
      type: "postgresql"
      url: "${DATABASE_URL:postgresql://localhost/hypereternal}"

  recovery:
    default_strategy: "latest"
    auto_recovery: true
    recovery_check_interval: 60
```
