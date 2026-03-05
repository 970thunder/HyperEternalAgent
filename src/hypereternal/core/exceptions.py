"""
Exception definitions for HyperEternalAgent framework.
"""


class HyperEternalError(Exception):
    """Base exception for HyperEternalAgent."""

    pass


# =============================================================================
# Agent Exceptions
# =============================================================================


class AgentError(HyperEternalError):
    """Base exception for agent-related errors."""

    pass


class AgentInitializationError(AgentError):
    """Agent initialization failed."""

    pass


class AgentExecutionError(AgentError):
    """Agent execution failed."""

    pass


class AgentNotFoundError(AgentError):
    """Agent not found."""

    pass


class AgentTimeoutError(AgentError):
    """Agent execution timeout."""

    pass


# =============================================================================
# Task Exceptions
# =============================================================================


class TaskError(HyperEternalError):
    """Base exception for task-related errors."""

    pass


class TaskNotFoundError(TaskError):
    """Task not found."""

    pass


class TaskTimeoutError(TaskError):
    """Task execution timeout."""

    pass


class TaskValidationError(TaskError):
    """Task validation failed."""

    pass


class TaskDependencyError(TaskError):
    """Task dependency error."""

    pass


# =============================================================================
# Queue Exceptions
# =============================================================================


class QueueError(HyperEternalError):
    """Base exception for queue-related errors."""

    pass


class QueueFullError(QueueError):
    """Queue is full."""

    pass


class QueueEmptyError(QueueError):
    """Queue is empty."""

    pass


# =============================================================================
# Flow Exceptions
# =============================================================================


class FlowError(HyperEternalError):
    """Base exception for flow-related errors."""

    pass


class FlowNotFoundError(FlowError):
    """Flow not found."""

    pass


class FlowExecutionError(FlowError):
    """Flow execution failed."""

    pass


class FlowValidationError(FlowError):
    """Flow validation failed."""

    pass


class CyclicDependencyError(FlowError):
    """Cyclic dependency detected."""

    pass


# =============================================================================
# State Exceptions
# =============================================================================


class StateError(HyperEternalError):
    """Base exception for state-related errors."""

    pass


class StateNotFoundError(StateError):
    """State not found."""

    pass


class StateCorruptionError(StateError):
    """State corruption detected."""

    pass


# =============================================================================
# Storage Exceptions
# =============================================================================


class StorageError(HyperEternalError):
    """Base exception for storage-related errors."""

    pass


class StorageConnectionError(StorageError):
    """Storage connection failed."""

    pass


class StorageOperationError(StorageError):
    """Storage operation failed."""

    pass


# =============================================================================
# LLM Exceptions
# =============================================================================


class LLMError(HyperEternalError):
    """Base exception for LLM-related errors."""

    pass


class LLMConnectionError(LLMError):
    """LLM connection failed."""

    pass


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""

    pass


class LLMAuthenticationError(LLMError):
    """LLM authentication failed."""

    pass


class LLMResponseError(LLMError):
    """LLM response error."""

    pass


# =============================================================================
# Configuration Exceptions
# =============================================================================


class ConfigurationError(HyperEternalError):
    """Base exception for configuration-related errors."""

    pass


class ConfigurationNotFoundError(ConfigurationError):
    """Configuration not found."""

    pass


class ConfigurationValidationError(ConfigurationError):
    """Configuration validation failed."""

    pass


# =============================================================================
# Reflection Exceptions
# =============================================================================


class ReflectionError(HyperEternalError):
    """Base exception for reflection-related errors."""

    pass


class QualityCheckError(ReflectionError):
    """Quality check failed."""

    pass


class CorrectionError(ReflectionError):
    """Auto-correction failed."""

    pass


class ConvergenceError(ReflectionError):
    """Convergence not achieved."""

    pass


# =============================================================================
# Recovery Exceptions
# =============================================================================


class RecoveryError(HyperEternalError):
    """Base exception for recovery-related errors."""

    pass


class ChecksumMismatchError(RecoveryError):
    """Checksum verification failed."""

    pass


class SnapshotError(RecoveryError):
    """Snapshot operation failed."""

    pass
