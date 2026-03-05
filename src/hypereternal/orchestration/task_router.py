"""
Task routing system for HyperEternalAgent framework.
"""

import asyncio
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..agents.base import BaseAgent
from ..agents.manager import AgentManager, AgentPool
from ..core.exceptions import TaskError
from ..core.types import Task, TaskResult, TaskStatus
from ..infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AgentStats:
    """Statistics for an agent."""

    agent_id: str
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_response_time: float = 0.0
    weight: float = 1.0
    last_heartbeat: Optional[datetime] = None
    total_response_time: float = 0.0

    def update_avg_response_time(self, response_time: float) -> None:
        """Update average response time."""
        total_tasks = self.completed_tasks + self.failed_tasks
        if total_tasks > 0:
            self.total_response_time += response_time
            self.avg_response_time = self.total_response_time / total_tasks


@dataclass
class RoutingRule:
    """Rule for routing tasks to agent pools."""

    rule_id: str
    condition: Callable[[Task], bool]
    target_pool: str
    priority: int = 0

    def matches(self, task: Task) -> bool:
        """Check if rule matches a task."""
        try:
            return self.condition(task)
        except Exception:
            return False


@dataclass
class RoutingResult:
    """Result of task routing."""

    task_id: str
    target_agent_id: Optional[str] = None
    target_pool: Optional[str] = None
    routed_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None


class LoadBalancerStrategy(ABC):
    """Abstract base class for load balancing strategies."""

    @abstractmethod
    def select_agent(
        self,
        agents: List[BaseAgent],
        stats: Dict[str, AgentStats],
    ) -> Optional[BaseAgent]:
        """Select an agent from the pool."""
        pass


class RoundRobinStrategy(LoadBalancerStrategy):
    """Round-robin load balancing strategy."""

    def __init__(self):
        self._index = 0

    def select_agent(
        self,
        agents: List[BaseAgent],
        stats: Dict[str, AgentStats],
    ) -> Optional[BaseAgent]:
        """Select next agent in round-robin order."""
        if not agents:
            return None

        agent = agents[self._index % len(agents)]
        self._index += 1
        return agent


class LeastConnectionsStrategy(LoadBalancerStrategy):
    """Least connections load balancing strategy."""

    def select_agent(
        self,
        agents: List[BaseAgent],
        stats: Dict[str, AgentStats],
    ) -> Optional[BaseAgent]:
        """Select agent with least active tasks."""
        if not agents:
            return None

        return min(
            agents,
            key=lambda a: stats.get(a.agent_id, AgentStats(agent_id=a.agent_id)).active_tasks,
        )


class WeightedRandomStrategy(LoadBalancerStrategy):
    """Weighted random load balancing strategy."""

    def select_agent(
        self,
        agents: List[BaseAgent],
        stats: Dict[str, AgentStats],
    ) -> Optional[BaseAgent]:
        """Select agent based on weights."""
        if not agents:
            return None

        weights = [
            stats.get(a.agent_id, AgentStats(agent_id=a.agent_id)).weight
            for a in agents
        ]

        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(agents)

        r = random.uniform(0, total_weight)
        cumulative = 0.0

        for agent, weight in zip(agents, weights):
            cumulative += weight
            if r <= cumulative:
                return agent

        return agents[-1]


class ResponseTimeStrategy(LoadBalancerStrategy):
    """Response time based load balancing strategy."""

    def select_agent(
        self,
        agents: List[BaseAgent],
        stats: Dict[str, AgentStats],
    ) -> Optional[BaseAgent]:
        """Select agent with lowest average response time."""
        if not agents:
            return None

        return min(
            agents,
            key=lambda a: stats.get(
                a.agent_id, AgentStats(agent_id=a.agent_id)
            ).avg_response_time,
        )


class TaskDispatcher:
    """
    Dispatcher for routing and executing tasks.

    Features:
    - Multiple load balancing strategies
    - Routing rules
    - Agent pool management
    """

    def __init__(
        self,
        agent_manager: AgentManager,
        strategy: str = "least_connections",
    ):
        self.agent_manager = agent_manager
        self.routing_rules: List[RoutingRule] = []
        self.agent_stats: Dict[str, AgentStats] = {}

        # Set up load balancer
        self._strategies: Dict[str, LoadBalancerStrategy] = {
            "round_robin": RoundRobinStrategy(),
            "least_connections": LeastConnectionsStrategy(),
            "weighted_random": WeightedRandomStrategy(),
            "response_time": ResponseTimeStrategy(),
        }
        self._load_balancer = self._strategies.get(
            strategy, LeastConnectionsStrategy()
        )

    def add_routing_rule(self, rule: RoutingRule) -> None:
        """Add a routing rule."""
        self.routing_rules.append(rule)
        self.routing_rules.sort(key=lambda r: r.priority, reverse=True)

        logger.info(
            "routing_rule_added",
            rule_id=rule.rule_id,
            target_pool=rule.target_pool,
            priority=rule.priority,
        )

    def remove_routing_rule(self, rule_id: str) -> bool:
        """Remove a routing rule."""
        for i, rule in enumerate(self.routing_rules):
            if rule.rule_id == rule_id:
                self.routing_rules.pop(i)
                return True
        return False

    async def dispatch(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """
        Dispatch a task to an appropriate agent.

        Args:
            task: Task to dispatch
            context: Execution context

        Returns:
            Task execution result
        """
        context = context or {}

        # Find target pool
        pool_name = self._select_pool(task)

        # Get agent pool
        pool = await self.agent_manager.get_pool(pool_name)

        if pool:
            # Use pool
            agent = await pool.acquire()
            try:
                result = await self._execute_with_tracking(agent, task, context)
                return result
            finally:
                await pool.release(agent)
        else:
            # Find agent directly
            agent = await self._find_agent(task.task_type)

            if not agent:
                raise TaskError(f"No agent available for task type: {task.task_type}")

            return await self._execute_with_tracking(agent, task, context)

    async def dispatch_batch(
        self,
        tasks: List[Task],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[TaskResult]:
        """
        Dispatch multiple tasks in parallel.

        Args:
            tasks: Tasks to dispatch
            context: Execution context

        Returns:
            List of task results
        """
        results = await asyncio.gather(
            *[self.dispatch(task, context) for task in tasks],
            return_exceptions=True,
        )

        # Convert exceptions to failed results
        task_results = []
        for task, result in zip(tasks, results):
            if isinstance(result, Exception):
                task_results.append(
                    TaskResult(
                        task_id=task.task_id,
                        success=False,
                        errors=[str(result)],
                    )
                )
            else:
                task_results.append(result)

        return task_results

    def _select_pool(self, task: Task) -> str:
        """Select target pool for task."""
        for rule in self.routing_rules:
            if rule.matches(task):
                return rule.target_pool

        # Default pool based on task type
        return task.task_type

    async def _find_agent(self, task_type: str) -> Optional[BaseAgent]:
        """Find an available agent for task type."""
        # Try to get idle agent of the right type
        agents = await self.agent_manager.get_agents_by_type(task_type)

        for agent in agents:
            if agent.is_idle():
                return agent

        # Return first available if none idle
        if agents:
            return agents[0]

        return None

    async def _execute_with_tracking(
        self,
        agent: BaseAgent,
        task: Task,
        context: Dict[str, Any],
    ) -> TaskResult:
        """Execute task with statistics tracking."""
        # Update stats
        stats = self.agent_stats.get(
            agent.agent_id, AgentStats(agent_id=agent.agent_id)
        )
        stats.active_tasks += 1
        self.agent_stats[agent.agent_id] = stats

        start_time = datetime.now()

        try:
            result = await agent.execute(task)

            # Update success stats
            stats = self.agent_stats[agent.agent_id]
            stats.completed_tasks += 1
            stats.active_tasks -= 1
            stats.update_avg_response_time(
                (datetime.now() - start_time).total_seconds()
            )

            return result

        except Exception as e:
            # Update failure stats
            stats = self.agent_stats[agent.agent_id]
            stats.failed_tasks += 1
            stats.active_tasks -= 1

            return TaskResult(
                task_id=task.task_id,
                success=False,
                errors=[str(e)],
            )

    def update_agent_weight(self, agent_id: str, weight: float) -> None:
        """Update agent weight for load balancing."""
        stats = self.agent_stats.get(agent_id, AgentStats(agent_id=agent_id))
        stats.weight = weight
        self.agent_stats[agent_id] = stats

    def get_agent_stats(self, agent_id: str) -> Optional[AgentStats]:
        """Get statistics for an agent."""
        return self.agent_stats.get(agent_id)

    def get_all_stats(self) -> Dict[str, AgentStats]:
        """Get statistics for all agents."""
        return self.agent_stats.copy()


class CircuitBreaker:
    """
    Circuit breaker for fault tolerance.

    States:
    - CLOSED: Normal operation
    - OPEN: Failing, reject requests
    - HALF_OPEN: Testing if recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_requests: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests

        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"
        self.half_open_successes = 0

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (should reject)."""
        if self.state == "open":
            # Check if should transition to half-open
            if self._should_attempt_recovery():
                self.state = "half_open"
                self.half_open_successes = 0
                return False
            return True
        return False

    def record_success(self) -> None:
        """Record a successful operation."""
        if self.state == "half_open":
            self.half_open_successes += 1
            if self.half_open_successes >= self.half_open_requests:
                self._reset()
        else:
            self.failures = 0

    def record_failure(self) -> None:
        """Record a failed operation."""
        self.failures += 1
        self.last_failure_time = datetime.now()

        if self.state == "half_open":
            self.state = "open"
        elif self.failures >= self.failure_threshold:
            self.state = "open"

    def _should_attempt_recovery(self) -> bool:
        """Check if should attempt recovery."""
        if not self.last_failure_time:
            return False
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout

    def _reset(self) -> None:
        """Reset circuit breaker."""
        self.failures = 0
        self.state = "closed"
        self.last_failure_time = None
        self.half_open_successes = 0


class FailureHandler:
    """
    Handler for task failures.

    Features:
    - Retry strategies
    - Circuit breaker
    - Fallback handling
    """

    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_strategies: Dict[str, Callable] = {}
        self.fallback_handlers: Dict[str, Callable] = {}

    def get_circuit_breaker(
        self,
        key: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
    ) -> CircuitBreaker:
        """Get or create circuit breaker for a key."""
        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
            )
        return self.circuit_breakers[key]

    def register_retry_strategy(
        self,
        error_type: str,
        strategy: Callable,
    ) -> None:
        """Register a retry strategy for an error type."""
        self.retry_strategies[error_type] = strategy

    def register_fallback_handler(
        self,
        task_type: str,
        handler: Callable,
    ) -> None:
        """Register a fallback handler for a task type."""
        self.fallback_handlers[task_type] = handler

    async def handle_failure(
        self,
        error: Exception,
        task: Task,
        context: Dict[str, Any],
    ) -> Tuple[str, Any]:
        """
        Handle a task failure.

        Args:
            error: The exception that occurred
            task: The failed task
            context: Execution context

        Returns:
            Tuple of (action, data)
        """
        error_type = type(error).__name__
        task_type = task.task_type

        # Update circuit breaker
        circuit = self.get_circuit_breaker(task_type)
        circuit.record_failure()

        # Check if circuit is open
        if circuit.is_open:
            # Try fallback
            if task_type in self.fallback_handlers:
                try:
                    result = await self.fallback_handlers[task_type](task, context)
                    return ("fallback", result)
                except Exception:
                    pass

            return ("circuit_open", None)

        # Try retry strategy
        if error_type in self.retry_strategies:
            action = await self.retry_strategies[error_type](error, task, context)
            return (action, None)

        # Default: retry if possible
        if task.retry_count < task.max_retries:
            return ("retry", None)

        return ("fail", None)


class TaskRouter:
    """
    Main task routing system.

    Combines dispatcher, failure handler, and circuit breaker.
    """

    def __init__(
        self,
        agent_manager: AgentManager,
        load_balance_strategy: str = "least_connections",
    ):
        self.dispatcher = TaskDispatcher(agent_manager, load_balance_strategy)
        self.failure_handler = FailureHandler()

        self._pending_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def route(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """
        Route a task to an agent for execution.

        Args:
            task: Task to route
            context: Execution context

        Returns:
            Task execution result
        """
        context = context or {}
        max_attempts = task.max_retries + 1

        for attempt in range(max_attempts):
            try:
                result = await self.dispatcher.dispatch(task, context)

                # Update circuit breaker on success
                circuit = self.failure_handler.get_circuit_breaker(task.task_type)
                circuit.record_success()

                return result

            except Exception as e:
                # Handle failure
                action, data = await self.failure_handler.handle_failure(
                    e, task, context
                )

                if action == "retry" and attempt < max_attempts - 1:
                    task.retry_count += 1
                    logger.warning(
                        "task_retry",
                        task_id=task.task_id,
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    continue

                elif action == "fallback" and data is not None:
                    return TaskResult(
                        task_id=task.task_id,
                        success=True,
                        output=data,
                        metadata={"fallback": True},
                    )

                # Return failure
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    errors=[str(e)],
                )

        return TaskResult(
            task_id=task.task_id,
            success=False,
            errors=["Max retries exceeded"],
        )

    async def route_batch(
        self,
        tasks: List[Task],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[TaskResult]:
        """Route multiple tasks in parallel."""
        results = await asyncio.gather(
            *[self.route(task, context) for task in tasks],
            return_exceptions=True,
        )

        # Convert exceptions
        task_results = []
        for task, result in zip(tasks, results):
            if isinstance(result, Exception):
                task_results.append(
                    TaskResult(
                        task_id=task.task_id,
                        success=False,
                        errors=[str(result)],
                    )
                )
            else:
                task_results.append(result)

        return task_results

    def add_routing_rule(
        self,
        rule_id: str,
        condition: Callable[[Task], bool],
        target_pool: str,
        priority: int = 0,
    ) -> None:
        """Add a routing rule."""
        rule = RoutingRule(
            rule_id=rule_id,
            condition=condition,
            target_pool=target_pool,
            priority=priority,
        )
        self.dispatcher.add_routing_rule(rule)

    def remove_routing_rule(self, rule_id: str) -> bool:
        """Remove a routing rule."""
        return self.dispatcher.remove_routing_rule(rule_id)

    def register_fallback(
        self,
        task_type: str,
        handler: Callable,
    ) -> None:
        """Register a fallback handler."""
        self.failure_handler.register_fallback_handler(task_type, handler)

    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        return {
            "agent_stats": self.dispatcher.get_all_stats(),
            "circuit_breakers": {
                k: {"state": v.state, "failures": v.failures}
                for k, v in self.failure_handler.circuit_breakers.items()
            },
        }
