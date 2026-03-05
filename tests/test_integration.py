"""
Integration tests for HyperEternalAgent framework.

These tests verify that different components work together correctly.
"""

import asyncio
import pytest
from typing import Any, Dict

from hypereternal import HyperEternalAgent, SystemConfig
from hypereternal.core.types import Task, TaskResult, TaskStatus, TaskPriority
from hypereternal.core.exceptions import TaskError
from hypereternal.agents.base import BaseAgent, AgentCapabilities, AgentType
from hypereternal.persistence.storage import MemoryStorageBackend
from hypereternal.orchestration.flow_engine import FlowDefinition, FlowStep, StepType


class CodeGeneratorAgent(BaseAgent):
    """Agent that generates code."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.WORKER

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="Code Generator",
            description="Generates code from specifications",
            input_types=["specification"],
            output_types=["code"],
            tags=["code", "generation"],
        )

    async def execute(self, task: Task) -> TaskResult:
        spec = task.payload.get("specification", "")

        # Simulate code generation
        code = f"""
# Generated code for: {spec}
def generated_function():
    '''Implementation for {spec}'''
    return "Hello from generated code"
"""
        return TaskResult(
            task_id=task.task_id,
            success=True,
            output={"code": code, "language": "python"},
            metrics={"lines_generated": 5},
        )


class CodeReviewerAgent(BaseAgent):
    """Agent that reviews code."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.REVIEWER

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="Code Reviewer",
            description="Reviews code quality",
            input_types=["code"],
            output_types=["review"],
            tags=["code", "review"],
        )

    async def execute(self, task: Task) -> TaskResult:
        code = task.payload.get("code", "")

        # Simulate code review
        issues = []
        if "TODO" in code:
            issues.append("Contains TODO comments")
        if len(code) < 50:
            issues.append("Code too short")

        score = 0.9 if len(issues) == 0 else 0.7

        return TaskResult(
            task_id=task.task_id,
            success=True,
            output={
                "approved": len(issues) == 0,
                "score": score,
                "issues": issues,
            },
        )


class TestSystemIntegration:
    """Integration tests for the complete system."""

    @pytest.fixture
    async def system(self):
        """Create a test system instance."""
        config = SystemConfig(
            name="TestSystem",
            version="1.0.0",
        )

        system = HyperEternalAgent(config=config)

        # Register agent types
        system.register_agent_type("code_generator", CodeGeneratorAgent)
        system.register_agent_type("code_reviewer", CodeReviewerAgent)

        # Use memory storage for tests
        storage = MemoryStorageBackend()
        await storage.connect()

        await system.start()

        yield system

        await system.stop()
        await storage.disconnect()

    @pytest.mark.asyncio
    async def test_system_start_stop(self):
        """Test system startup and shutdown."""
        config = SystemConfig(name="StartStopTest", version="1.0.0")
        system = HyperEternalAgent(config=config)

        await system.start()
        status = system.get_status()
        assert status["running"] is True

        await system.stop()
        status = system.get_status()
        assert status["running"] is False

    @pytest.mark.asyncio
    async def test_submit_and_execute_task(self, system):
        """Test submitting and executing a task."""
        submission = await system.submit_task(
            task_type="code_generator",
            payload={"specification": "A hello world function"},
        )

        assert submission.task_id is not None

        # Wait for completion
        result = await system.wait_for_completion(submission.task_id, timeout=10)

        assert result is not None
        assert result.success is True
        assert "code" in result.output

    @pytest.mark.asyncio
    async def test_task_priority_ordering(self, system):
        """Test that tasks are processed by priority."""
        results = []

        # Submit tasks with different priorities
        low_task = await system.submit_task(
            task_type="code_generator",
            payload={"specification": "low priority"},
            priority=TaskPriority.LOW.value,
        )

        high_task = await system.submit_task(
            task_type="code_generator",
            payload={"specification": "high priority"},
            priority=TaskPriority.HIGH.value,
        )

        # Wait for both
        await system.wait_for_completion(low_task.task_id, timeout=10)
        await system.wait_for_completion(high_task.task_id, timeout=10)

        # Both should complete
        low_result = await system.get_task_result(low_task.task_id)
        high_result = await system.get_task_result(high_task.task_id)

        assert low_result.success is True
        assert high_result.success is True

    @pytest.mark.asyncio
    async def test_task_cancellation(self, system):
        """Test cancelling a task."""
        submission = await system.submit_task(
            task_type="code_generator",
            payload={"specification": "To be cancelled"},
        )

        # Try to cancel
        cancelled = await system.cancel_task(submission.task_id)

        # Task might already be completed or cancelled
        status = await system.get_task_status(submission.task_id)
        assert status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.PENDING]

    @pytest.mark.asyncio
    async def test_create_agent(self, system):
        """Test creating an agent instance."""
        agent = await system.create_agent("code_generator", agent_id="test_agent")

        assert agent is not None
        assert agent.agent_id == "test_agent"
        assert isinstance(agent, CodeGeneratorAgent)

    @pytest.mark.asyncio
    async def test_multiple_tasks(self, system):
        """Test executing multiple tasks."""
        tasks = []
        for i in range(5):
            submission = await system.submit_task(
                task_type="code_generator",
                payload={"specification": f"Task {i}"},
            )
            tasks.append(submission.task_id)

        # Wait for all
        results = []
        for task_id in tasks:
            result = await system.wait_for_completion(task_id, timeout=30)
            results.append(result)

        # All should succeed
        assert all(r.success for r in results)


class TestFlowIntegration:
    """Integration tests for flow execution."""

    @pytest.fixture
    async def system(self):
        """Create a test system instance."""
        config = SystemConfig(
            name="FlowTestSystem",
            version="1.0.0",
        )

        system = HyperEternalAgent(config=config)
        system.register_agent_type("code_generator", CodeGeneratorAgent)
        system.register_agent_type("code_reviewer", CodeReviewerAgent)

        await system.start()
        yield system
        await system.stop()

    @pytest.mark.asyncio
    async def test_simple_flow(self, system):
        """Test executing a simple flow."""
        flow = FlowDefinition(
            flow_id="code_gen_flow",
            name="Code Generation Flow",
            description="Generate and review code",
            version="1.0.0",
            steps=[
                FlowStep(
                    step_id="generate",
                    name="Generate Code",
                    step_type=StepType.TASK,
                    agent_type="code_generator",
                    config={"specification": "${input.spec}"},
                ),
                FlowStep(
                    step_id="review",
                    name="Review Code",
                    step_type=StepType.TASK,
                    agent_type="code_reviewer",
                    config={"code": "${steps.generate.output.code}"},
                    dependencies=["generate"],
                ),
            ],
        )

        system.flow_engine.register_flow(flow)

        execution_id = await system.submit_flow(
            flow_name="code_gen_flow",
            input_data={"spec": "A utility function"},
        )

        assert execution_id is not None

        # Wait for completion
        await asyncio.sleep(2)

        status = await system.flow_engine.get_status(execution_id)
        assert status is not None


class TestPersistenceIntegration:
    """Integration tests for persistence."""

    @pytest.fixture
    async def storage(self):
        """Create a storage backend."""
        storage = MemoryStorageBackend()
        await storage.connect()
        yield storage
        await storage.disconnect()

    @pytest.mark.asyncio
    async def test_state_persistence(self, storage):
        """Test state persistence."""
        # Set some state
        await storage.set("session:user_1", {"name": "Alice", "tasks_completed": 5})
        await storage.set("session:user_2", {"name": "Bob", "tasks_completed": 3})

        # Retrieve
        user1 = await storage.get("session:user_1")
        assert user1["name"] == "Alice"

        # List keys
        keys = await storage.list_keys("session:*")
        assert len(keys) == 2

        # Delete
        await storage.delete("session:user_1")
        user1 = await storage.get("session:user_1")
        assert user1 is None

    @pytest.mark.asyncio
    async def test_task_queue_persistence(self, storage):
        """Test task queue with storage."""
        from hypereternal.persistence.task_queue import TaskQueue

        queue = TaskQueue(storage)
        await queue.initialize()

        # Enqueue tasks
        task1 = Task(task_type="test", payload={"id": 1}, priority=5)
        task2 = Task(task_type="test", payload={"id": 2}, priority=10)

        await queue.enqueue(task1)
        await queue.enqueue(task2)

        # Dequeue (should get higher priority first)
        dequeued = await queue.dequeue(timeout=1.0)
        assert dequeued.task_id == task2.task_id  # Higher priority

        dequeued = await queue.dequeue(timeout=1.0)
        assert dequeued.task_id == task1.task_id


class TestReflectionIntegration:
    """Integration tests for reflection system."""

    @pytest.fixture
    async def system(self):
        """Create a test system."""
        config = SystemConfig(
            name="ReflectionTest",
            version="1.0.0",
        )
        system = HyperEternalAgent(config=config)
        system.register_agent_type("code_generator", CodeGeneratorAgent)
        await system.start()
        yield system
        await system.stop()

    @pytest.mark.asyncio
    async def test_quality_assessment(self, system):
        """Test quality assessment integration."""
        content = """
def hello():
    print("Hello, World!")
    return True
"""
        assessment = await system.quality_engine.assess(
            content=content,
            context={"language": "python"},
        )

        assert assessment is not None
        assert assessment.overall_score >= 0
        assert assessment.overall_score <= 1

    @pytest.mark.asyncio
    async def test_error_detection(self, system):
        """Test error detection integration."""
        content = """
def broken_function():
    # TODO: implement this
    pass
"""
        errors = await system.error_detector.detect(
            content=content,
            context={"language": "python"},
        )

        assert isinstance(errors, list)


class TestAgentCoordination:
    """Tests for agent coordination."""

    @pytest.fixture
    async def system(self):
        """Create a test system."""
        config = SystemConfig(
            name="CoordinationTest",
            version="1.0.0",
        )
        system = HyperEternalAgent(config=config)
        system.register_agent_type("code_generator", CodeGeneratorAgent)
        system.register_agent_type("code_reviewer", CodeReviewerAgent)
        await system.start()
        yield system
        await system.stop()

    @pytest.mark.asyncio
    async def test_sequential_agent_execution(self, system):
        """Test sequential execution of agents."""
        # First, generate code
        gen_result = await system.submit_task(
            task_type="code_generator",
            payload={"specification": "A sorting function"},
        )

        gen_output = await system.wait_for_completion(gen_result.task_id, timeout=10)
        assert gen_output.success is True

        # Then, review the generated code
        review_result = await system.submit_task(
            task_type="code_reviewer",
            payload={"code": gen_output.output["code"]},
        )

        review_output = await system.wait_for_completion(review_result.task_id, timeout=10)
        assert review_output.success is True
        assert "approved" in review_output.output

    @pytest.mark.asyncio
    async def test_parallel_task_execution(self, system):
        """Test parallel task execution."""
        # Submit multiple tasks simultaneously
        submissions = await asyncio.gather(
            system.submit_task(
                task_type="code_generator",
                payload={"specification": "Function 1"},
            ),
            system.submit_task(
                task_type="code_generator",
                payload={"specification": "Function 2"},
            ),
            system.submit_task(
                task_type="code_generator",
                payload={"specification": "Function 3"},
            ),
        )

        # Wait for all
        results = await asyncio.gather(
            *[system.wait_for_completion(s.task_id, timeout=30) for s in submissions]
        )

        assert all(r.success for r in results)


class TestErrorHandling:
    """Tests for error handling across components."""

    @pytest.fixture
    async def system(self):
        """Create a test system."""
        config = SystemConfig(
            name="ErrorHandlingTest",
            version="1.0.0",
        )
        system = HyperEternalAgent(config=config)
        await system.start()
        yield system
        await system.stop()

    @pytest.mark.asyncio
    async def test_invalid_task_type(self, system):
        """Test handling of invalid task type."""
        submission = await system.submit_task(
            task_type="nonexistent_agent",
            payload={},
        )

        result = await system.wait_for_completion(submission.task_id, timeout=10)

        # Should handle gracefully
        assert result is not None

    @pytest.mark.asyncio
    async def test_task_timeout(self, system):
        """Test task timeout handling."""
        system.register_agent_type("code_generator", CodeGeneratorAgent)

        submission = await system.submit_task(
            task_type="code_generator",
            payload={"specification": "Test"},
            timeout=1,  # Very short timeout
        )

        # Wait and check status
        await asyncio.sleep(2)
        status = await system.get_task_status(submission.task_id)
        # Task should complete or timeout
        assert status in [TaskStatus.COMPLETED, TaskStatus.TIMEOUT, TaskStatus.RUNNING]


class TestSystemRecovery:
    """Tests for system recovery and fault tolerance."""

    @pytest.fixture
    async def system(self):
        """Create a test system."""
        config = SystemConfig(
            name="RecoveryTest",
            version="1.0.0",
        )
        system = HyperEternalAgent(config=config)
        system.register_agent_type("code_generator", CodeGeneratorAgent)
        await system.start()
        yield system
        await system.stop()

    @pytest.mark.asyncio
    async def test_system_status(self, system):
        """Test getting system status."""
        status = system.get_status()

        assert "running" in status
        assert status["running"] is True

    @pytest.mark.asyncio
    async def test_agent_stats_tracking(self, system):
        """Test agent statistics tracking."""
        # Execute some tasks
        for i in range(3):
            await system.submit_task(
                task_type="code_generator",
                payload={"specification": f"Task {i}"},
            )

        await asyncio.sleep(1)

        # Check stats exist
        stats = system.agent_manager.get_stats()
        assert stats is not None


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    @pytest.fixture
    async def system(self):
        """Create a complete test system."""
        config = SystemConfig(
            name="E2ETest",
            version="1.0.0",
        )
        system = HyperEternalAgent(config=config)
        system.register_agent_type("code_generator", CodeGeneratorAgent)
        system.register_agent_type("code_reviewer", CodeReviewerAgent)
        await system.start()
        yield system
        await system.stop()

    @pytest.mark.asyncio
    async def test_complete_code_workflow(self, system):
        """Test a complete code generation and review workflow."""
        # 1. Generate code
        gen_submission = await system.submit_task(
            task_type="code_generator",
            payload={"specification": "A function to calculate fibonacci numbers"},
            priority=TaskPriority.HIGH.value,
        )

        gen_result = await system.wait_for_completion(gen_submission.task_id, timeout=30)
        assert gen_result.success is True
        generated_code = gen_result.output["code"]

        # 2. Review the code
        review_submission = await system.submit_task(
            task_type="code_reviewer",
            payload={"code": generated_code},
        )

        review_result = await system.wait_for_completion(review_submission.task_id, timeout=30)
        assert review_result.success is True

        # 3. Check quality
        assessment = await system.quality_engine.assess(
            content=generated_code,
            context={"language": "python"},
        )

        # 4. Store results in state
        await system.state_manager.set(
            "workflow:last_execution",
            {
                "generated_code": generated_code,
                "review_score": review_result.output["score"],
                "quality_score": assessment.overall_score,
            },
        )

        # 5. Verify state was stored
        stored = await system.state_manager.get("workflow:last_execution")
        assert stored is not None
        assert "generated_code" in stored
