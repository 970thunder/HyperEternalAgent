"""
Tests for orchestration system (flow engine and task router).
"""

import pytest
import asyncio
from datetime import datetime
from typing import Any, Dict

from hypereternal.orchestration.flow_engine import (
    FlowEngine,
    FlowParser,
    FlowDefinition,
    FlowStep,
    FlowContext,
    FlowStatus,
    StepType,
)
from hypereternal.orchestration.task_router import (
    TaskDispatcher,
    TaskRouter,
    LoadBalancerStrategy,
    RoundRobinStrategy,
    LeastConnectionsStrategy,
    WeightedRandomStrategy,
    ResponseTimeStrategy,
    CircuitBreaker,
    FailureHandler,
    RoutingRule,
    AgentStats,
)
from hypereternal.agents.base import BaseAgent, AgentCapabilities, AgentType
from hypereternal.agents.manager import AgentManager
from hypereternal.core.types import Task, TaskResult, generate_id


class MockAgent(BaseAgent):
    """Mock agent for testing."""

    def __init__(self, agent_id: str = None, config: Dict[str, Any] = None):
        super().__init__(agent_id, config)
        self.execute_count = 0

    @property
    def agent_type(self) -> AgentType:
        return AgentType.WORKER

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="Mock Agent",
            description="Test agent",
            input_types=["any"],
            output_types=["result"],
        )

    async def execute(self, task: Task) -> TaskResult:
        self.execute_count += 1
        return TaskResult(
            task_id=task.task_id,
            success=True,
            output={"result": f"processed_{self.execute_count}"},
        )


class TestFlowStep:
    """Tests for FlowStep."""

    def test_step_creation(self):
        """Test creating a flow step."""
        step = FlowStep(
            step_id="step_1",
            name="Test Step",
            step_type=StepType.TASK,
            agent_type="worker",
            config={"param": "value"},
        )
        assert step.step_id == "step_1"
        assert step.step_type == StepType.TASK
        assert step.config["param"] == "value"

    def test_step_with_dependencies(self):
        """Test step with dependencies."""
        step = FlowStep(
            step_id="step_2",
            name="Dependent Step",
            step_type=StepType.TASK,
            agent_type="worker",
            dependencies=["step_1"],
        )
        assert "step_1" in step.dependencies

    def test_step_to_dict(self):
        """Test step serialization."""
        step = FlowStep(
            step_id="step_3",
            name="Serialization Test",
            step_type=StepType.PARALLEL,
            agent_type="worker",
        )
        data = step.to_dict()
        assert data["step_id"] == "step_3"
        assert data["step_type"] == "parallel"


class TestFlowDefinition:
    """Tests for FlowDefinition."""

    def test_flow_creation(self):
        """Test creating a flow definition."""
        flow = FlowDefinition(
            flow_id="test_flow",
            name="Test Flow",
            description="A test flow",
            version="1.0.0",
            steps=[
                FlowStep(
                    step_id="step_1",
                    name="First Step",
                    step_type=StepType.TASK,
                    agent_type="worker",
                ),
            ],
        )
        assert flow.flow_id == "test_flow"
        assert len(flow.steps) == 1

    def test_flow_with_variables(self):
        """Test flow with variables."""
        flow = FlowDefinition(
            flow_id="var_flow",
            name="Variable Flow",
            description="Flow with variables",
            version="1.0.0",
            variables={"input_value": "${input.data}"},
            steps=[],
        )
        assert "input_value" in flow.variables

    def test_flow_to_dict(self):
        """Test flow serialization."""
        flow = FlowDefinition(
            flow_id="serialize_test",
            name="Serialize Test",
            version="1.0.0",
            steps=[],
        )
        data = flow.to_dict()
        assert data["flow_id"] == "serialize_test"


class TestFlowContext:
    """Tests for FlowContext."""

    def test_context_creation(self):
        """Test creating a flow context."""
        context = FlowContext(
            flow_id="test_flow",
            execution_id="exec_1",
        )
        assert context.flow_id == "test_flow"
        assert context.status == FlowStatus.PENDING

    def test_context_variables(self):
        """Test context variables."""
        context = FlowContext(
            flow_id="test_flow",
            execution_id="exec_2",
            variables={"key": "value"},
        )
        assert context.get_variable("key") == "value"

    def test_context_set_variable(self):
        """Test setting context variable."""
        context = FlowContext(
            flow_id="test_flow",
            execution_id="exec_3",
        )
        context.set_variable("new_key", "new_value")
        assert context.get_variable("new_key") == "new_value"

    def test_context_step_results(self):
        """Test step results storage."""
        context = FlowContext(
            flow_id="test_flow",
            execution_id="exec_4",
        )
        context.set_step_result("step_1", {"output": "data"})
        result = context.get_step_result("step_1")
        assert result["output"] == "data"


class TestVariableResolver:
    """Tests for VariableResolver."""

    @pytest.fixture
    def resolver(self):
        """Create a variable resolver."""
        return VariableResolver()

    def test_resolve_simple(self, resolver):
        """Test resolving simple variable."""
        context = FlowContext(
            flow_id="test",
            execution_id="exec",
            variables={"name": "test_value"},
        )
        result = resolver.resolve("${name}", context)
        assert result == "test_value"

    def test_resolve_nested(self, resolver):
        """Test resolving nested variable."""
        context = FlowContext(
            flow_id="test",
            execution_id="exec",
            variables={"data": {"nested": {"value": 42}}},
        )
        result = resolver.resolve("${data.nested.value}", context)
        assert result == 42

    def test_resolve_with_default(self, resolver):
        """Test resolving with default value."""
        context = FlowContext(
            flow_id="test",
            execution_id="exec",
            variables={},
        )
        result = resolver.resolve("${missing:default_value}", context)
        assert result == "default_value"

    def test_resolve_no_placeholder(self, resolver):
        """Test resolving without placeholder."""
        context = FlowContext(
            flow_id="test",
            execution_id="exec",
            variables={},
        )
        result = resolver.resolve("plain_text", context)
        assert result == "plain_text"


class TestFlowParser:
    """Tests for FlowParser."""

    @pytest.fixture
    def parser(self):
        """Create a flow parser."""
        return FlowParser()

    def test_parse_simple_flow(self, parser):
        """Test parsing a simple flow."""
        yaml_content = """
flow_id: simple_flow
name: Simple Flow
description: A simple test flow
version: 1.0.0
steps:
  - step_id: step_1
    name: First Step
    step_type: task
    agent_type: worker
    config:
      param: value
"""
        flow = parser.parse(yaml_content)
        assert flow.flow_id == "simple_flow"
        assert len(flow.steps) == 1
        assert flow.steps[0].step_type == StepType.TASK

    def test_parse_flow_with_variables(self, parser):
        """Test parsing flow with variables."""
        yaml_content = """
flow_id: var_flow
name: Variable Flow
version: 1.0.0
variables:
  input_data: ${input.value}
steps:
  - step_id: step_1
    name: Process
    step_type: task
    agent_type: worker
"""
        flow = parser.parse(yaml_content)
        assert "input_data" in flow.variables

    def test_parse_parallel_step(self, parser):
        """Test parsing parallel step."""
        yaml_content = """
flow_id: parallel_flow
name: Parallel Flow
version: 1.0.0
steps:
  - step_id: parallel_1
    name: Parallel Branch
    step_type: parallel
    branches:
      - step_id: branch_a
        name: Branch A
        step_type: task
        agent_type: worker_a
      - step_id: branch_b
        name: Branch B
        step_type: task
        agent_type: worker_b
"""
        flow = parser.parse(yaml_content)
        assert flow.steps[0].step_type == StepType.PARALLEL

    def test_parse_condition_step(self, parser):
        """Test parsing condition step."""
        yaml_content = """
flow_id: condition_flow
name: Condition Flow
version: 1.0.0
steps:
  - step_id: cond_1
    name: Check Condition
    step_type: condition
    condition: "${input.value} > 10"
    true_step:
      step_id: true_branch
      name: True Branch
      step_type: task
      agent_type: worker
    false_step:
      step_id: false_branch
      name: False Branch
      step_type: task
      agent_type: worker
"""
        flow = parser.parse(yaml_content)
        assert flow.steps[0].step_type == StepType.CONDITION


class TestFlowExecutor:
    """Tests for FlowExecutor."""

    @pytest.fixture
    async def executor(self):
        """Create a flow executor."""
        agent_manager = AgentManager()
        agent_manager.register_agent_type("worker", MockAgent)
        await agent_manager.create_agent("worker", agent_id="worker_1")

        executor = FlowExecutor(agent_manager)
        yield executor
        await agent_manager.shutdown()

    @pytest.mark.asyncio
    async def test_execute_task_step(self, executor):
        """Test executing a task step."""
        step = FlowStep(
            step_id="task_1",
            name="Test Task",
            step_type=StepType.TASK,
            agent_type="worker",
        )
        context = FlowContext(
            flow_id="test_flow",
            execution_id="exec_1",
        )

        result = await executor.execute_step(step, context)
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_parallel_step(self, executor):
        """Test executing a parallel step."""
        step = FlowStep(
            step_id="parallel_1",
            name="Parallel Tasks",
            step_type=StepType.PARALLEL,
            branches=[
                FlowStep(
                    step_id="branch_1",
                    name="Branch 1",
                    step_type=StepType.TASK,
                    agent_type="worker",
                ),
                FlowStep(
                    step_id="branch_2",
                    name="Branch 2",
                    step_type=StepType.TASK,
                    agent_type="worker",
                ),
            ],
        )
        context = FlowContext(
            flow_id="test_flow",
            execution_id="exec_2",
        )

        result = await executor.execute_step(step, context)
        assert result is not None


class TestFlowEngine:
    """Tests for FlowEngine."""

    @pytest.fixture
    async def engine(self):
        """Create a flow engine."""
        agent_manager = AgentManager()
        agent_manager.register_agent_type("worker", MockAgent)
        await agent_manager.create_agent("worker", agent_id="worker_1")

        engine = FlowEngine(agent_manager)
        yield engine
        await agent_manager.shutdown()

    @pytest.mark.asyncio
    async def test_register_flow(self, engine):
        """Test registering a flow."""
        flow = FlowDefinition(
            flow_id="test_flow",
            name="Test Flow",
            version="1.0.0",
            steps=[
                FlowStep(
                    step_id="step_1",
                    name="First Step",
                    step_type=StepType.TASK,
                    agent_type="worker",
                ),
            ],
        )
        engine.register_flow(flow)
        assert "test_flow" in engine._flows

    @pytest.mark.asyncio
    async def test_execute_flow(self, engine):
        """Test executing a flow."""
        flow = FlowDefinition(
            flow_id="exec_flow",
            name="Execution Test",
            version="1.0.0",
            steps=[
                FlowStep(
                    step_id="step_1",
                    name="Process",
                    step_type=StepType.TASK,
                    agent_type="worker",
                ),
            ],
        )
        engine.register_flow(flow)

        execution_id = await engine.execute("exec_flow", {"input": "data"})
        assert execution_id is not None

    @pytest.mark.asyncio
    async def test_get_flow_status(self, engine):
        """Test getting flow status."""
        flow = FlowDefinition(
            flow_id="status_flow",
            name="Status Test",
            version="1.0.0",
            steps=[],
        )
        engine.register_flow(flow)

        execution_id = await engine.execute("status_flow", {})
        status = await engine.get_status(execution_id)
        assert status is not None


class TestAgentStats:
    """Tests for AgentStats."""

    def test_stats_creation(self):
        """Test creating agent stats."""
        stats = AgentStats(agent_id="agent_1")
        assert stats.agent_id == "agent_1"
        assert stats.active_tasks == 0
        assert stats.completed_tasks == 0

    def test_update_avg_response_time(self):
        """Test updating average response time."""
        stats = AgentStats(agent_id="agent_1")
        stats.completed_tasks = 1
        stats.update_avg_response_time(1.0)
        assert stats.avg_response_time == 1.0

        stats.completed_tasks = 2
        stats.update_avg_response_time(2.0)
        assert stats.avg_response_time == 1.5


class TestRoutingRule:
    """Tests for RoutingRule."""

    def test_rule_creation(self):
        """Test creating a routing rule."""
        rule = RoutingRule(
            rule_id="rule_1",
            condition=lambda task: task.priority > 10,
            target_pool="high_priority",
            priority=1,
        )
        assert rule.rule_id == "rule_1"

    def test_rule_matches(self):
        """Test rule matching."""
        rule = RoutingRule(
            rule_id="rule_2",
            condition=lambda task: task.task_type == "special",
            target_pool="special_pool",
        )

        matching_task = Task(task_type="special", payload={})
        non_matching_task = Task(task_type="normal", payload={})

        assert rule.matches(matching_task) is True
        assert rule.matches(non_matching_task) is False

    def test_rule_exception_handling(self):
        """Test rule handles exceptions."""
        rule = RoutingRule(
            rule_id="rule_3",
            condition=lambda task: task.payload["required_field"] == "value",
            target_pool="test",
        )

        task = Task(task_type="test", payload={})  # Missing required_field
        assert rule.matches(task) is False  # Should not raise


class TestLoadBalancerStrategies:
    """Tests for load balancing strategies."""

    @pytest.fixture
    def agents(self):
        """Create mock agents."""
        return [
            MockAgent(agent_id="agent_1"),
            MockAgent(agent_id="agent_2"),
            MockAgent(agent_id="agent_3"),
        ]

    @pytest.fixture
    def stats(self):
        """Create agent stats."""
        return {
            "agent_1": AgentStats(agent_id="agent_1", active_tasks=2, weight=1.0, avg_response_time=1.0),
            "agent_2": AgentStats(agent_id="agent_2", active_tasks=1, weight=2.0, avg_response_time=0.5),
            "agent_3": AgentStats(agent_id="agent_3", active_tasks=3, weight=1.5, avg_response_time=2.0),
        }

    def test_round_robin_strategy(self, agents, stats):
        """Test round-robin strategy."""
        strategy = RoundRobinStrategy()

        # Should cycle through agents
        selected = [strategy.select_agent(agents, stats) for _ in range(6)]
        assert selected[0].agent_id == "agent_1"
        assert selected[1].agent_id == "agent_2"
        assert selected[2].agent_id == "agent_3"
        assert selected[3].agent_id == "agent_1"

    def test_least_connections_strategy(self, agents, stats):
        """Test least connections strategy."""
        strategy = LeastConnectionsStrategy()

        selected = strategy.select_agent(agents, stats)
        assert selected.agent_id == "agent_2"  # Has least active tasks (1)

    def test_weighted_random_strategy(self, agents, stats):
        """Test weighted random strategy."""
        strategy = WeightedRandomStrategy()

        # Run multiple times to verify distribution
        selections = {}
        for _ in range(100):
            selected = strategy.select_agent(agents, stats)
            selections[selected.agent_id] = selections.get(selected.agent_id, 0) + 1

        # agent_2 has highest weight (2.0), should be selected more often
        assert selections["agent_2"] > selections["agent_1"]

    def test_response_time_strategy(self, agents, stats):
        """Test response time strategy."""
        strategy = ResponseTimeStrategy()

        selected = strategy.select_agent(agents, stats)
        assert selected.agent_id == "agent_2"  # Has lowest avg response time (0.5)

    def test_strategy_empty_agents(self):
        """Test strategies with empty agent list."""
        strategy = LeastConnectionsStrategy()
        selected = strategy.select_agent([], {})
        assert selected is None


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_initial_state(self):
        """Test initial circuit breaker state."""
        cb = CircuitBreaker()
        assert cb.state == "closed"
        assert cb.is_open is False

    def test_open_after_failures(self):
        """Test circuit opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=3)

        for _ in range(3):
            cb.record_failure()

        assert cb.state == "open"
        assert cb.is_open is True

    def test_close_after_success(self):
        """Test circuit closes after success."""
        cb = CircuitBreaker(failure_threshold=2)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        # Record success (should reset when closed)
        cb.state = "closed"
        cb.record_success()
        assert cb.failures == 0

    def test_half_open_state(self):
        """Test half-open state transition."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)

        # Open the circuit
        cb.record_failure()
        assert cb.state == "open"

        # Force recovery check (with timeout=0)
        cb.last_failure_time = datetime.fromtimestamp(0)
        assert cb.is_open is False  # Should transition to half_open
        assert cb.state == "half_open"


class TestFailureHandler:
    """Tests for FailureHandler."""

    @pytest.fixture
    def handler(self):
        """Create a failure handler."""
        return FailureHandler()

    def test_get_circuit_breaker(self, handler):
        """Test getting circuit breaker."""
        cb = handler.get_circuit_breaker("test_key")
        assert cb is not None

        # Same key returns same breaker
        cb2 = handler.get_circuit_breaker("test_key")
        assert cb is cb2

    def test_register_retry_strategy(self, handler):
        """Test registering retry strategy."""
        async def strategy(error, task, context):
            return "retry"

        handler.register_retry_strategy("ValueError", strategy)
        assert "ValueError" in handler.retry_strategies

    def test_register_fallback_handler(self, handler):
        """Test registering fallback handler."""
        async def fallback(task, context):
            return {"fallback": True}

        handler.register_fallback_handler("test_type", fallback)
        assert "test_type" in handler.fallback_handlers

    @pytest.mark.asyncio
    async def test_handle_failure(self, handler):
        """Test handling failure."""
        task = Task(task_type="test", payload={}, max_retries=2)
        error = ValueError("Test error")

        action, data = await handler.handle_failure(error, task, {})
        assert action in ["retry", "fail", "circuit_open", "fallback"]


class TestTaskDispatcher:
    """Tests for TaskDispatcher."""

    @pytest.fixture
    async def dispatcher(self):
        """Create a task dispatcher."""
        agent_manager = AgentManager()
        agent_manager.register_agent_type("worker", MockAgent)
        await agent_manager.create_agent("worker", agent_id="worker_1")

        dispatcher = TaskDispatcher(agent_manager)
        yield dispatcher
        await agent_manager.shutdown()

    @pytest.mark.asyncio
    async def test_add_routing_rule(self, dispatcher):
        """Test adding routing rule."""
        rule = RoutingRule(
            rule_id="priority_rule",
            condition=lambda t: t.priority > 10,
            target_pool="high_priority",
        )
        dispatcher.add_routing_rule(rule)
        assert len(dispatcher.routing_rules) == 1

    @pytest.mark.asyncio
    async def test_remove_routing_rule(self, dispatcher):
        """Test removing routing rule."""
        rule = RoutingRule(
            rule_id="remove_rule",
            condition=lambda t: True,
            target_pool="test",
        )
        dispatcher.add_routing_rule(rule)
        assert len(dispatcher.routing_rules) == 1

        result = dispatcher.remove_routing_rule("remove_rule")
        assert result is True
        assert len(dispatcher.routing_rules) == 0

    @pytest.mark.asyncio
    async def test_dispatch_task(self, dispatcher):
        """Test dispatching a task."""
        task = Task(task_type="worker", payload={"data": "test"})

        result = await dispatcher.dispatch(task)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_dispatch_batch(self, dispatcher):
        """Test dispatching multiple tasks."""
        tasks = [
            Task(task_type="worker", payload={"id": 1}),
            Task(task_type="worker", payload={"id": 2}),
        ]

        results = await dispatcher.dispatch_batch(tasks)
        assert len(results) == 2


class TestTaskRouter:
    """Tests for TaskRouter."""

    @pytest.fixture
    async def router(self):
        """Create a task router."""
        agent_manager = AgentManager()
        agent_manager.register_agent_type("worker", MockAgent)
        await agent_manager.create_agent("worker", agent_id="worker_1")

        router = TaskRouter(agent_manager)
        yield router
        await agent_manager.shutdown()

    @pytest.mark.asyncio
    async def test_route_task(self, router):
        """Test routing a task."""
        task = Task(task_type="worker", payload={"test": "data"})

        result = await router.route(task)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_route_batch(self, router):
        """Test routing multiple tasks."""
        tasks = [
            Task(task_type="worker", payload={"id": 1}),
            Task(task_type="worker", payload={"id": 2}),
        ]

        results = await router.route_batch(tasks)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_add_routing_rule(self, router):
        """Test adding routing rule to router."""
        router.add_routing_rule(
            rule_id="test_rule",
            condition=lambda t: t.priority > 5,
            target_pool="high_priority",
        )
        assert len(router.dispatcher.routing_rules) == 1

    @pytest.mark.asyncio
    async def test_get_stats(self, router):
        """Test getting router stats."""
        task = Task(task_type="worker", payload={})
        await router.route(task)

        stats = router.get_stats()
        assert "agent_stats" in stats
        assert "circuit_breakers" in stats


class TestStepType:
    """Tests for StepType enum."""

    def test_step_type_values(self):
        """Test step type values."""
        assert StepType.TASK.value == "task"
        assert StepType.PARALLEL.value == "parallel"
        assert StepType.SEQUENTIAL.value == "sequential"
        assert StepType.CONDITION.value == "condition"
        assert StepType.LOOP.value == "loop"
        assert StepType.WAIT.value == "wait"
        assert StepType.SUBFLOW.value == "subflow"


class TestFlowStatus:
    """Tests for FlowStatus enum."""

    def test_status_values(self):
        """Test flow status values."""
        assert FlowStatus.PENDING.value == "pending"
        assert FlowStatus.RUNNING.value == "running"
        assert FlowStatus.COMPLETED.value == "completed"
        assert FlowStatus.FAILED.value == "failed"
        assert FlowStatus.CANCELLED.value == "cancelled"
