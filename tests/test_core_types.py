"""
Tests for core types.
"""

import pytest
from datetime import datetime

from hypereternal.core.types import (
    AgentState,
    AgentType,
    Task,
    TaskPriority,
    TaskResult,
    TaskStatus,
    FlowStatus,
    StepType,
    StateScope,
    ErrorCategory,
    QualityDimension,
    generate_id,
)


class TestGenerateId:
    """Tests for generate_id function."""

    def test_generates_unique_ids(self):
        """Test that generated IDs are unique."""
        ids = [generate_id() for _ in range(100)]
        assert len(ids) == len(set(ids))

    def test_generates_string_id(self):
        """Test that generated ID is a string."""
        id_value = generate_id()
        assert isinstance(id_value, str)

    def test_generates_non_empty_id(self):
        """Test that generated ID is not empty."""
        id_value = generate_id()
        assert len(id_value) > 0


class TestTask:
    """Tests for Task class."""

    def test_task_creation_defaults(self):
        """Test task creation with default values."""
        task = Task()
        assert task.task_type == ""
        assert task.payload == {}
        assert task.priority == TaskPriority.NORMAL.value
        assert task.max_retries == 3
        assert task.dependencies == []

    def test_task_creation_with_values(self):
        """Test task creation with custom values."""
        task = Task(
            task_type="code_generation",
            payload={"language": "python"},
            priority=TaskPriority.HIGH.value,
            max_retries=5,
        )
        assert task.task_type == "code_generation"
        assert task.payload == {"language": "python"}
        assert task.priority == 10
        assert task.max_retries == 5

    def test_task_to_dict(self):
        """Test task serialization to dictionary."""
        task = Task(
            task_id="test_123",
            task_type="test_type",
            payload={"key": "value"},
        )
        data = task.to_dict()

        assert data["task_id"] == "test_123"
        assert data["task_type"] == "test_type"
        assert data["payload"] == {"key": "value"}
        assert "created_at" in data

    def test_task_from_dict(self):
        """Test task deserialization from dictionary."""
        data = {
            "task_id": "test_456",
            "task_type": "test_type",
            "payload": {"key": "value"},
            "priority": 15,
            "created_at": datetime.now().isoformat(),
        }
        task = Task.from_dict(data)

        assert task.task_id == "test_456"
        assert task.task_type == "test_type"
        assert task.payload == {"key": "value"}
        assert task.priority == 15

    def test_task_roundtrip(self):
        """Test task serialization roundtrip."""
        original = Task(
            task_type="test",
            payload={"nested": {"data": [1, 2, 3]}},
            priority=20,
            dependencies=["dep1", "dep2"],
        )
        data = original.to_dict()
        restored = Task.from_dict(data)

        assert restored.task_type == original.task_type
        assert restored.payload == original.payload
        assert restored.priority == original.priority
        assert restored.dependencies == original.dependencies


class TestTaskResult:
    """Tests for TaskResult class."""

    def test_task_result_success(self):
        """Test successful task result."""
        result = TaskResult(
            task_id="task_123",
            success=True,
            output={"data": "value"},
        )
        assert result.success is True
        assert result.output == {"data": "value"}
        assert result.errors == []

    def test_task_result_failure(self):
        """Test failed task result."""
        result = TaskResult(
            task_id="task_456",
            success=False,
            errors=["Error 1", "Error 2"],
        )
        assert result.success is False
        assert result.output is None
        assert len(result.errors) == 2

    def test_task_result_to_dict(self):
        """Test task result serialization."""
        result = TaskResult(
            task_id="task_789",
            success=True,
            output="result",
            metrics={"duration": 1.5},
        )
        data = result.to_dict()

        assert data["task_id"] == "task_789"
        assert data["success"] is True
        assert data["output"] == "result"
        assert data["metrics"]["duration"] == 1.5


class TestEnums:
    """Tests for enum types."""

    def test_agent_state_values(self):
        """Test AgentState enum values."""
        assert AgentState.IDLE.value == "idle"
        assert AgentState.RUNNING.value == "running"
        assert AgentState.ERROR.value == "error"

    def test_task_status_values(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"

    def test_task_priority_values(self):
        """Test TaskPriority enum values."""
        assert TaskPriority.LOW.value == 0
        assert TaskPriority.NORMAL.value == 5
        assert TaskPriority.HIGH.value == 10
        assert TaskPriority.CRITICAL.value == 15
        assert TaskPriority.URGENT.value == 20

    def test_flow_status_values(self):
        """Test FlowStatus enum values."""
        assert FlowStatus.RUNNING.value == "running"
        assert FlowStatus.COMPLETED.value == "completed"

    def test_step_type_values(self):
        """Test StepType enum values."""
        assert StepType.TASK.value == "task"
        assert StepType.PARALLEL.value == "parallel"
        assert StepType.CONDITION.value == "condition"
        assert StepType.LOOP.value == "loop"

    def test_state_scope_values(self):
        """Test StateScope enum values."""
        assert StateScope.GLOBAL.value == "global"
        assert StateScope.SESSION.value == "session"
        assert StateScope.AGENT.value == "agent"

    def test_error_category_values(self):
        """Test ErrorCategory enum values."""
        assert ErrorCategory.SYNTAX.value == "syntax"
        assert ErrorCategory.LOGIC.value == "logic"
        assert ErrorCategory.RUNTIME.value == "runtime"

    def test_quality_dimension_values(self):
        """Test QualityDimension enum values."""
        assert QualityDimension.CORRECTNESS.value == "correctness"
        assert QualityDimension.COMPLETENESS.value == "completeness"
        assert QualityDimension.READABILITY.value == "readability"


class TestTaskPriority:
    """Tests for TaskPriority enum."""

    def test_priority_ordering(self):
        """Test priority ordering."""
        assert TaskPriority.LOW.value < TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.CRITICAL.value
        assert TaskPriority.CRITICAL.value < TaskPriority.URGENT.value
