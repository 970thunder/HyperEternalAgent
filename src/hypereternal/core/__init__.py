"""
Core module for HyperEternalAgent framework.
"""

from .main import HyperEternalAgent
from .types import (
    Task,
    TaskResult,
    TaskStatus,
    TaskPriority,
    AgentState,
    AgentType,
    FlowStatus,
    StepType,
    StateScope,
    ErrorCategory,
    QualityDimension,
    generate_id,
)
from .config import SystemConfig, RuntimeConfig, PersistenceConfig, MonitoringConfig, LLMConfig
from .exceptions import (
    HyperEternalError,
    AgentError,
    TaskError,
    FlowError,
    StateError,
    StorageError,
    LLMError,
    QueueError,
    ReflectionError,
)

__all__ = [
    # Main
    "HyperEternalAgent",
    # Types
    "Task",
    "TaskResult",
    "TaskStatus",
    "TaskPriority",
    "AgentState",
    "AgentType",
    "FlowStatus",
    "StepType",
    "StateScope",
    "ErrorCategory",
    "QualityDimension",
    "generate_id",
    # Config
    "SystemConfig",
    "RuntimeConfig",
    "PersistenceConfig",
    "MonitoringConfig",
    "LLMConfig",
    # Exceptions
    "HyperEternalError",
    "AgentError",
    "TaskError",
    "FlowError",
    "StateError",
    "StorageError",
    "LLMError",
    "QueueError",
    "ReflectionError",
]
