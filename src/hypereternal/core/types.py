"""
Core types and base classes for HyperEternalAgent framework.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


def generate_id() -> str:
    """Generate a unique identifier."""
    return str(uuid4())


# =============================================================================
# Agent Types
# =============================================================================


class AgentState(Enum):
    """Agent state enumeration."""

    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    TERMINATED = "terminated"


class AgentType(Enum):
    """Agent type enumeration."""

    WORKER = "worker"
    REVIEWER = "reviewer"
    PLANNER = "planner"
    CRITIC = "critic"
    COORDINATOR = "coordinator"
    CUSTOM = "custom"


# =============================================================================
# Task Types
# =============================================================================


class TaskStatus(Enum):
    """Task status enumeration."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    TIMEOUT = "timeout"


class TaskPriority(Enum):
    """Task priority levels."""

    LOW = 0
    NORMAL = 5
    HIGH = 10
    CRITICAL = 15
    URGENT = 20


@dataclass
class Task:
    """Task definition."""

    task_id: str = field(default_factory=generate_id)
    task_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = TaskPriority.NORMAL.value
    timeout: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "payload": self.payload,
            "priority": self.priority,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "dependencies": self.dependencies,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create from dictionary."""
        return cls(
            task_id=data.get("task_id", generate_id()),
            task_type=data.get("task_type", ""),
            payload=data.get("payload", {}),
            priority=data.get("priority", TaskPriority.NORMAL.value),
            timeout=data.get("timeout"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            dependencies=data.get("dependencies", []),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            scheduled_at=datetime.fromisoformat(data["scheduled_at"]) if data.get("scheduled_at") else None,
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            metadata=data.get("metadata", {}),
        )


@dataclass
class TaskResult:
    """Task execution result."""

    task_id: str
    success: bool
    output: Any = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    completed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "success": self.success,
            "output": self.output,
            "metrics": self.metrics,
            "errors": self.errors,
            "completed_at": self.completed_at.isoformat(),
        }


# =============================================================================
# Flow Types
# =============================================================================


class FlowStatus(Enum):
    """Flow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepType(Enum):
    """Flow step type."""

    TASK = "task"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    CONDITION = "condition"
    LOOP = "loop"
    WAIT = "wait"
    SUBFLOW = "subflow"


# =============================================================================
# State Types
# =============================================================================


class StateScope(Enum):
    """State scope enumeration."""

    GLOBAL = "global"
    SESSION = "session"
    FLOW = "flow"
    AGENT = "agent"
    TASK = "task"


# =============================================================================
# Error Types
# =============================================================================


class ErrorCategory(Enum):
    """Error category enumeration."""

    SYNTAX = "syntax"
    LOGIC = "logic"
    RUNTIME = "runtime"
    RESOURCE = "resource"
    INTEGRATION = "integration"
    SECURITY = "security"


# =============================================================================
# Quality Types
# =============================================================================


class QualityDimension(Enum):
    """Quality dimension enumeration."""

    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    EFFICIENCY = "efficiency"
    READABILITY = "readability"
    MAINTAINABILITY = "maintainability"
    SECURITY = "security"
