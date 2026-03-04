"""
Base agent implementation for HyperEternalAgent framework.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..core.exceptions import AgentError, AgentExecutionError, AgentInitializationError
from ..core.types import AgentState, AgentType, Task, TaskResult, generate_id
from ..infrastructure.llm_client import LLMClientWrapper
from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class AgentContext:
    """Agent runtime context."""

    agent_id: str
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    state: AgentState = AgentState.IDLE


@dataclass
class AgentCapabilities:
    """Agent capabilities description."""

    name: str
    description: str
    input_types: List[str] = field(default_factory=list)
    output_types: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    Lifecycle:
    1. __init__ - Create agent instance
    2. initialize - Prepare agent for work
    3. execute - Process tasks
    4. shutdown - Clean up resources
    """

    def __init__(self, agent_id: str, config: Dict[str, Any]):
        """
        Initialize agent.

        Args:
            agent_id: Unique agent identifier
            config: Agent configuration
        """
        self.agent_id = agent_id
        self.config = config
        self.context: Optional[AgentContext] = None
        self.state = AgentState.IDLE
        self._llm_client: Optional[LLMClientWrapper] = None

    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """Get agent type."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> AgentCapabilities:
        """Get agent capabilities."""
        pass

    async def initialize(self) -> None:
        """
        Initialize agent for work.

        Called once when agent is created.
        Override to set up resources, connections, etc.
        """
        self.state = AgentState.INITIALIZING

        try:
            # Initialize LLM client if configured
            llm_config = self.config.get("llm")
            if llm_config:
                from ..core.config import LLMConfig

                if isinstance(llm_config, dict):
                    self._llm_client = LLMClientWrapper(LLMConfig(**llm_config))
                else:
                    self._llm_client = LLMClientWrapper(llm_config)
                await self._llm_client.initialize()

            # Create context
            self.context = AgentContext(
                agent_id=self.agent_id,
                session_id=generate_id(),
                state=AgentState.IDLE,
            )

            self.state = AgentState.IDLE
            logger.info(
                "agent_initialized",
                agent_id=self.agent_id,
                agent_type=self.agent_type.value,
            )

        except Exception as e:
            self.state = AgentState.ERROR
            logger.error("agent_initialization_failed", agent_id=self.agent_id, error=str(e))
            raise AgentInitializationError(f"Failed to initialize agent: {e}")

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """
        Execute a task.

        Args:
            task: Task to execute

        Returns:
            Task execution result
        """
        pass

    async def shutdown(self) -> None:
        """
        Shutdown agent and release resources.

        Called once when agent is being destroyed.
        """
        self.state = AgentState.TERMINATED

        if self._llm_client:
            await self._llm_client.close()

        logger.info(
            "agent_shutdown",
            agent_id=self.agent_id,
            agent_type=self.agent_type.value,
        )

    async def pause(self) -> None:
        """Pause agent execution."""
        if self.state == AgentState.RUNNING:
            self.state = AgentState.PAUSED
            logger.info("agent_paused", agent_id=self.agent_id)

    async def resume(self) -> None:
        """Resume agent execution."""
        if self.state == AgentState.PAUSED:
            self.state = AgentState.RUNNING
            logger.info("agent_resumed", agent_id=self.agent_id)

    def get_state(self) -> AgentState:
        """Get current agent state."""
        return self.state

    def is_idle(self) -> bool:
        """Check if agent is idle."""
        return self.state == AgentState.IDLE

    def is_running(self) -> bool:
        """Check if agent is running."""
        return self.state == AgentState.RUNNING

    async def _set_running(self) -> None:
        """Set agent state to running."""
        self.state = AgentState.RUNNING

    async def _set_idle(self) -> None:
        """Set agent state to idle."""
        self.state = AgentState.IDLE

    async def _set_error(self, error: str) -> None:
        """Set agent state to error."""
        self.state = AgentState.ERROR
        logger.error("agent_error", agent_id=self.agent_id, error=error)

    async def _call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """
        Call LLM with prompt.

        Args:
            prompt: User prompt
            system_prompt: System prompt
            **kwargs: Additional LLM arguments

        Returns:
            LLM response text
        """
        if not self._llm_client:
            raise AgentError("LLM client not configured")

        return await self._llm_client.generate(prompt, system_prompt, **kwargs)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.agent_id}, type={self.agent_type.value}, state={self.state.value})"


class WorkerAgent(BaseAgent):
    """
    Base class for worker agents that execute tasks.

    Worker agents perform the actual work (coding, writing, analysis, etc.)
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.WORKER

    async def execute(self, task: Task) -> TaskResult:
        """Execute a task with error handling."""
        await self._set_running()

        start_time = datetime.now()

        try:
            # Parse task
            parsed_input = await self._parse_task(task)

            # Build prompt
            prompt = await self._build_prompt(parsed_input)

            # Execute work
            if self._llm_client:
                response = await self._call_llm(prompt)
                output = await self._process_output(response)
            else:
                output = await self._do_work(parsed_input)

            # Success
            duration = (datetime.now() - start_time).total_seconds()

            await self._set_idle()

            return TaskResult(
                task_id=task.task_id,
                success=True,
                output=output,
                metrics={"duration_seconds": duration},
                errors=[],
            )

        except Exception as e:
            await self._set_error(str(e))

            return TaskResult(
                task_id=task.task_id,
                success=False,
                output=None,
                metrics={},
                errors=[str(e)],
            )

    @abstractmethod
    async def _parse_task(self, task: Task) -> Dict[str, Any]:
        """Parse task into structured input."""
        pass

    @abstractmethod
    async def _build_prompt(self, parsed_input: Dict[str, Any]) -> str:
        """Build LLM prompt from parsed input."""
        pass

    @abstractmethod
    async def _process_output(self, response: str) -> Any:
        """Process LLM response into output."""
        pass

    async def _do_work(self, parsed_input: Dict[str, Any]) -> Any:
        """Override to implement work without LLM."""
        raise AgentError("Either _do_work must be implemented or LLM must be configured")


class ReviewerAgent(BaseAgent):
    """
    Base class for reviewer agents that check output quality.
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.REVIEWER

    async def execute(self, task: Task) -> TaskResult:
        """Execute a review task."""
        await self._set_running()

        try:
            content = task.payload.get("content")
            content_type = task.payload.get("content_type", "generic")

            # Perform review
            review_result = await self._review(content, content_type)

            await self._set_idle()

            return TaskResult(
                task_id=task.task_id,
                success=True,
                output=review_result,
                metrics={"score": review_result.get("score", 0)},
                errors=[],
            )

        except Exception as e:
            await self._set_error(str(e))

            return TaskResult(
                task_id=task.task_id,
                success=False,
                output=None,
                metrics={},
                errors=[str(e)],
            )

    @abstractmethod
    async def _review(self, content: Any, content_type: str) -> Dict[str, Any]:
        """Perform review and return results."""
        pass


class PlannerAgent(BaseAgent):
    """
    Base class for planner agents that break down goals into tasks.
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.PLANNER

    async def execute(self, task: Task) -> TaskResult:
        """Execute a planning task."""
        await self._set_running()

        try:
            goal = task.payload.get("goal")
            constraints = task.payload.get("constraints", {})

            # Create plan
            plan = await self._create_plan(goal, constraints)

            # Optimize plan
            optimized_plan = await self._optimize_plan(plan)

            await self._set_idle()

            return TaskResult(
                task_id=task.task_id,
                success=True,
                output=optimized_plan,
                metrics={"step_count": len(optimized_plan.get("steps", []))},
                errors=[],
            )

        except Exception as e:
            await self._set_error(str(e))

            return TaskResult(
                task_id=task.task_id,
                success=False,
                output=None,
                metrics={},
                errors=[str(e)],
            )

    @abstractmethod
    async def _create_plan(self, goal: str, constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Create execution plan."""
        pass

    async def _optimize_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize execution plan."""
        # Default: sort steps by priority
        steps = plan.get("steps", [])
        if steps:
            steps.sort(key=lambda s: s.get("priority", 0), reverse=True)
            plan["steps"] = steps
        return plan


class CriticAgent(BaseAgent):
    """
    Base class for critic agents that evaluate overall performance.
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.CRITIC

    async def execute(self, task: Task) -> TaskResult:
        """Execute a critique task."""
        await self._set_running()

        try:
            work_output = task.payload.get("work_output")
            original_task = task.payload.get("original_task", {})

            # Perform critique
            critique = await self._critique(work_output, original_task)

            await self._set_idle()

            return TaskResult(
                task_id=task.task_id,
                success=True,
                output=critique,
                metrics={"overall_score": critique.get("overall_score", 0)},
                errors=[],
            )

        except Exception as e:
            await self._set_error(str(e))

            return TaskResult(
                task_id=task.task_id,
                success=False,
                output=None,
                metrics={},
                errors=[str(e)],
            )

    @abstractmethod
    async def _critique(
        self, work_output: Any, original_task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform critique and return results."""
        pass


class CoordinatorAgent(BaseAgent):
    """
    Base class for coordinator agents that manage other agents.
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.COORDINATOR

    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, config)
        self._subordinates: List[str] = []

    def add_subordinate(self, agent_id: str) -> None:
        """Add a subordinate agent."""
        self._subordinates.append(agent_id)

    def remove_subordinate(self, agent_id: str) -> None:
        """Remove a subordinate agent."""
        self._subordinates.remove(agent_id)

    def get_subordinates(self) -> List[str]:
        """Get list of subordinate agent IDs."""
        return self._subordinates.copy()
