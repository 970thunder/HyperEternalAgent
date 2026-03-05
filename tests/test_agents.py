"""
Tests for agent system.
"""

import asyncio
import pytest
from datetime import datetime
from typing import Any, Dict

from hypereternal.agents.base import (
    BaseAgent,
    WorkerAgent,
    ReviewerAgent,
    PlannerAgent,
    CriticAgent,
    AgentCapabilities,
    AgentState,
    AgentType,
)
from hypereternal.agents.manager import AgentManager, AgentPool
from hypereternal.core.types import Task, TaskResult, TaskStatus, generate_id
from hypereternal.core.exceptions import AgentError


class MockWorkerAgent(BaseAgent):
    """Mock worker agent for testing."""

    def __init__(self, agent_id: str = None, config: Dict[str, Any] = None):
        super().__init__(agent_id, config)
        self.execute_count = 0

    @property
    def agent_type(self) -> AgentType:
        return AgentType.WORKER

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="Mock Worker",
            description="A mock worker agent for testing",
            input_types=["task"],
            output_types=["result"],
        )

    async def execute(self, task: Task) -> TaskResult:
        self.execute_count += 1
        await asyncio.sleep(0.01)  # Simulate work
        return TaskResult(
            task_id=task.task_id,
            success=True,
            output={"processed": True, "count": self.execute_count},
        )


class MockReviewerAgent(BaseAgent):
    """Mock reviewer agent for testing."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.REVIEWER

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="Mock Reviewer",
            description="A mock reviewer agent for testing",
            input_types=["work"],
            output_types=["review"],
        )

    async def execute(self, task: Task) -> TaskResult:
        return TaskResult(
            task_id=task.task_id,
            success=True,
            output={"reviewed": True, "quality_score": 0.85},
        )


class FailingAgent(BaseAgent):
    """Agent that always fails."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.WORKER

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="Failing Agent",
            description="An agent that always fails",
            input_types=["task"],
            output_types=["error"],
        )

    async def execute(self, task: Task) -> TaskResult:
        raise RuntimeError("Intentional failure for testing")


class TestBaseAgent:
    """Tests for BaseAgent."""

    def test_agent_creation(self):
        """Test basic agent creation."""
        agent = MockWorkerAgent(agent_id="test_agent")
        assert agent.agent_id == "test_agent"
        assert agent.state == AgentState.IDLE

    def test_agent_auto_id(self):
        """Test automatic ID generation."""
        agent = MockWorkerAgent()
        assert agent.agent_id is not None
        assert len(agent.agent_id) > 0

    def test_agent_state_transitions(self):
        """Test agent state transitions."""
        agent = MockWorkerAgent()
        assert agent.state == AgentState.IDLE

        agent._set_state(AgentState.RUNNING)
        assert agent.state == AgentState.RUNNING

        agent._set_state(AgentState.IDLE)
        assert agent.state == AgentState.IDLE

    def test_is_idle(self):
        """Test is_idle check."""
        agent = MockWorkerAgent()
        assert agent.is_idle() is True

        agent._set_state(AgentState.RUNNING)
        assert agent.is_idle() is False

    @pytest.mark.asyncio
    async def test_agent_execute(self):
        """Test agent task execution."""
        agent = MockWorkerAgent()
        task = Task(task_type="test", payload={"data": "value"})

        result = await agent.execute(task)
        assert result.success is True
        assert result.output["processed"] is True
        assert agent.execute_count == 1

    @pytest.mark.asyncio
    async def test_agent_state_during_execution(self):
        """Test agent state during execution."""
        agent = MockWorkerAgent()
        task = Task(task_type="test", payload={})

        # State should change during execution
        async def check_state():
            await asyncio.sleep(0.005)
            assert agent.state == AgentState.RUNNING

        execute_task = asyncio.create_task(agent.execute(task))
        state_task = asyncio.create_task(check_state())

        await asyncio.gather(execute_task, state_task)
        assert agent.state == AgentState.IDLE


class TestWorkerAgent:
    """Tests for WorkerAgent."""

    @pytest.fixture
    def worker(self):
        """Create a worker agent."""
        return WorkerAgent(
            agent_id="worker_1",
            config={"max_concurrent_tasks": 2},
        )

    def test_worker_type(self, worker):
        """Test worker agent type."""
        assert worker.agent_type == AgentType.WORKER

    def test_worker_capabilities(self, worker):
        """Test worker capabilities."""
        caps = worker.capabilities
        assert caps.name == "Worker Agent"
        assert "task" in caps.input_types

    @pytest.mark.asyncio
    async def test_worker_execute(self, worker):
        """Test worker execution."""
        task = Task(task_type="test", payload={"input": "data"})
        result = await worker.execute(task)
        assert result.success is True
        assert result.task_id == task.task_id


class TestReviewerAgent:
    """Tests for ReviewerAgent."""

    @pytest.fixture
    def reviewer(self):
        """Create a reviewer agent."""
        return ReviewerAgent(agent_id="reviewer_1")

    def test_reviewer_type(self, reviewer):
        """Test reviewer agent type."""
        assert reviewer.agent_type == AgentType.REVIEWER

    @pytest.mark.asyncio
    async def test_reviewer_execute(self, reviewer):
        """Test reviewer execution."""
        task = Task(
            task_type="review",
            payload={"work": {"code": "print('hello')"}},
        )
        result = await reviewer.execute(task)
        assert result.success is True
        assert "approved" in result.output


class TestPlannerAgent:
    """Tests for PlannerAgent."""

    @pytest.fixture
    def planner(self):
        """Create a planner agent."""
        return PlannerAgent(agent_id="planner_1")

    def test_planner_type(self, planner):
        """Test planner agent type."""
        assert planner.agent_type == AgentType.PLANNER

    @pytest.mark.asyncio
    async def test_planner_execute(self, planner):
        """Test planner execution."""
        task = Task(
            task_type="plan",
            payload={"goal": "Build a web application"},
        )
        result = await planner.execute(task)
        assert result.success is True
        assert "plan" in result.output


class TestCriticAgent:
    """Tests for CriticAgent."""

    @pytest.fixture
    def critic(self):
        """Create a critic agent."""
        return CriticAgent(agent_id="critic_1")

    def test_critic_type(self, critic):
        """Test critic agent type."""
        assert critic.agent_type == AgentType.CRITIC

    @pytest.mark.asyncio
    async def test_critic_execute(self, critic):
        """Test critic execution."""
        task = Task(
            task_type="critique",
            payload={"work": {"content": "Some work to critique"}},
        )
        result = await critic.execute(task)
        assert result.success is True
        assert "score" in result.output


class TestAgentCapabilities:
    """Tests for AgentCapabilities."""

    def test_capabilities_creation(self):
        """Test creating capabilities."""
        caps = AgentCapabilities(
            name="Test Agent",
            description="Test description",
            input_types=["text", "json"],
            output_types=["result"],
            tags=["test", "example"],
        )
        assert caps.name == "Test Agent"
        assert len(caps.input_types) == 2
        assert len(caps.tags) == 2

    def test_capabilities_defaults(self):
        """Test capabilities defaults."""
        caps = AgentCapabilities(
            name="Test",
            description="Test",
            input_types=[],
            output_types=[],
        )
        assert caps.tags == []
        assert caps.max_concurrent_tasks == 1


class TestAgentManager:
    """Tests for AgentManager."""

    @pytest.fixture
    async def manager(self):
        """Create an agent manager."""
        manager = AgentManager()
        yield manager
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_register_agent_type(self, manager):
        """Test registering an agent type."""
        manager.register_agent_type("mock_worker", MockWorkerAgent)
        assert "mock_worker" in manager._agent_types

    @pytest.mark.asyncio
    async def test_create_agent(self, manager):
        """Test creating an agent."""
        manager.register_agent_type("mock_worker", MockWorkerAgent)
        agent = await manager.create_agent("mock_worker")
        assert agent is not None
        assert isinstance(agent, MockWorkerAgent)

    @pytest.mark.asyncio
    async def test_create_agent_with_id(self, manager):
        """Test creating an agent with specific ID."""
        manager.register_agent_type("mock_worker", MockWorkerAgent)
        agent = await manager.create_agent("mock_worker", agent_id="custom_id")
        assert agent.agent_id == "custom_id"

    @pytest.mark.asyncio
    async def test_get_agent(self, manager):
        """Test getting an agent by ID."""
        manager.register_agent_type("mock_worker", MockWorkerAgent)
        created = await manager.create_agent("mock_worker", agent_id="test_id")
        retrieved = await manager.get_agent("test_id")
        assert retrieved is created

    @pytest.mark.asyncio
    async def test_get_nonexistent_agent(self, manager):
        """Test getting nonexistent agent."""
        agent = await manager.get_agent("nonexistent")
        assert agent is None

    @pytest.mark.asyncio
    async def test_get_agents_by_type(self, manager):
        """Test getting agents by type."""
        manager.register_agent_type("mock_worker", MockWorkerAgent)
        manager.register_agent_type("mock_reviewer", MockReviewerAgent)

        await manager.create_agent("mock_worker", agent_id="w1")
        await manager.create_agent("mock_worker", agent_id="w2")
        await manager.create_agent("mock_reviewer", agent_id="r1")

        workers = await manager.get_agents_by_type("mock_worker")
        assert len(workers) == 2

    @pytest.mark.asyncio
    async def test_destroy_agent(self, manager):
        """Test destroying an agent."""
        manager.register_agent_type("mock_worker", MockWorkerAgent)
        await manager.create_agent("mock_worker", agent_id="to_destroy")

        result = await manager.destroy_agent("to_destroy")
        assert result is True

        agent = await manager.get_agent("to_destroy")
        assert agent is None

    @pytest.mark.asyncio
    async def test_destroy_nonexistent_agent(self, manager):
        """Test destroying nonexistent agent."""
        result = await manager.destroy_agent("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_all_agents(self, manager):
        """Test getting all agents."""
        manager.register_agent_type("mock_worker", MockWorkerAgent)
        await manager.create_agent("mock_worker", agent_id="a1")
        await manager.create_agent("mock_worker", agent_id="a2")

        all_agents = await manager.get_all_agents()
        assert len(all_agents) == 2

    @pytest.mark.asyncio
    async def test_get_available_agents(self, manager):
        """Test getting available (idle) agents."""
        manager.register_agent_type("mock_worker", MockWorkerAgent)
        await manager.create_agent("mock_worker", agent_id="idle1")
        agent2 = await manager.create_agent("mock_worker", agent_id="busy1")
        agent2._set_state(AgentState.RUNNING)

        available = await manager.get_available_agents()
        assert len(available) == 1
        assert available[0].agent_id == "idle1"


class TestAgentPool:
    """Tests for AgentPool."""

    @pytest.fixture
    async def pool(self):
        """Create an agent pool."""
        pool = AgentPool(
            pool_name="test_pool",
            agent_type="mock_worker",
            min_size=1,
            max_size=3,
        )
        pool._agent_factory = lambda agent_id: MockWorkerAgent(agent_id=agent_id)
        await pool.initialize()
        yield pool
        await pool.shutdown()

    @pytest.mark.asyncio
    async def test_pool_initialize(self, pool):
        """Test pool initialization."""
        assert pool.size >= pool.min_size

    @pytest.mark.asyncio
    async def test_acquire_release(self, pool):
        """Test acquiring and releasing agents."""
        agent = await pool.acquire()
        assert agent is not None
        assert isinstance(agent, MockWorkerAgent)

        await pool.release(agent)
        # Agent should be back in pool

    @pytest.mark.asyncio
    async def test_pool_scaling(self, pool):
        """Test pool scaling."""
        initial_size = pool.size

        # Acquire more agents to trigger scaling
        agents = []
        for _ in range(3):
            agent = await pool.acquire()
            if agent:
                agents.append(agent)

        assert pool.size >= initial_size

        # Release all
        for agent in agents:
            await pool.release(agent)


class TestAgentEnums:
    """Tests for agent-related enums."""

    def test_agent_state_values(self):
        """Test AgentState enum values."""
        assert AgentState.IDLE.value == "idle"
        assert AgentState.RUNNING.value == "running"
        assert AgentState.ERROR.value == "error"
        assert AgentState.STOPPED.value == "stopped"

    def test_agent_type_values(self):
        """Test AgentType enum values."""
        assert AgentType.WORKER.value == "worker"
        assert AgentType.REVIEWER.value == "reviewer"
        assert AgentType.PLANNER.value == "planner"
        assert AgentType.CRITIC.value == "critic"
        assert AgentType.COORDINATOR.value == "coordinator"
        assert AgentType.CUSTOM.value == "custom"
