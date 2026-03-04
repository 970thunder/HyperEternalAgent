"""
Agent manager for HyperEternalAgent framework.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type

from ..core.exceptions import AgentError, AgentNotFoundError
from ..core.types import AgentState, AgentType
from .base import BaseAgent
from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class AgentStats:
    """Agent statistics."""

    agent_id: str
    agent_type: str
    state: AgentState
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_duration: float = 0.0
    last_task_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def avg_duration(self) -> float:
        """Calculate average task duration."""
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 0.0
        return self.total_duration / total


class AgentRegistry:
    """Registry for agent types."""

    def __init__(self):
        self._registry: Dict[str, Type[BaseAgent]] = {}

    def register(self, agent_type: str, agent_class: Type[BaseAgent]) -> None:
        """Register an agent type."""
        self._registry[agent_type] = agent_class
        logger.info("agent_type_registered", agent_type=agent_type)

    def unregister(self, agent_type: str) -> None:
        """Unregister an agent type."""
        self._registry.pop(agent_type, None)

    def get(self, agent_type: str) -> Optional[Type[BaseAgent]]:
        """Get agent class by type."""
        return self._registry.get(agent_type)

    def list_types(self) -> List[str]:
        """List all registered agent types."""
        return list(self._registry.keys())

    def is_registered(self, agent_type: str) -> bool:
        """Check if agent type is registered."""
        return agent_type in self._registry


class AgentPool:
    """Pool of agents of the same type."""

    def __init__(
        self,
        agent_type: str,
        min_size: int = 1,
        max_size: int = 10,
        auto_scale: bool = True,
    ):
        self.agent_type = agent_type
        self.min_size = min_size
        self.max_size = max_size
        self.auto_scale = auto_scale

        self.agents: Dict[str, BaseAgent] = {}
        self.available: asyncio.Queue[BaseAgent] = asyncio.Queue()
        self._lock = asyncio.Lock()

    @property
    def size(self) -> int:
        """Current pool size."""
        return len(self.agents)

    @property
    def available_count(self) -> int:
        """Number of available agents."""
        return self.available.qsize()

    async def initialize(self, agent_manager: "AgentManager") -> None:
        """Initialize pool with minimum agents."""
        for i in range(self.min_size):
            agent_id = f"{self.agent_type}_{i}"
            agent = await agent_manager.create_agent(
                self.agent_type,
                agent_id,
                {},
            )
            self.agents[agent_id] = agent
            await self.available.put(agent)

        logger.info(
            "agent_pool_initialized",
            agent_type=self.agent_type,
            size=self.size,
        )

    async def acquire(self, timeout: float = 30.0) -> BaseAgent:
        """
        Acquire an agent from the pool.

        Args:
            timeout: Maximum time to wait

        Returns:
            Available agent

        Raises:
            asyncio.TimeoutError: If no agent available within timeout
        """
        try:
            agent = await asyncio.wait_for(self.available.get(), timeout=timeout)
            return agent
        except asyncio.TimeoutError:
            if self.auto_scale and self.size < self.max_size:
                # Auto-scale: create new agent
                raise AgentError("Auto-scaling not implemented yet")
            raise

    async def release(self, agent: BaseAgent) -> None:
        """Release an agent back to the pool."""
        await self.available.put(agent)

    async def scale(self, target_size: int, agent_manager: "AgentManager") -> None:
        """Scale pool to target size."""
        async with self._lock:
            current = self.size

            if target_size > current and target_size <= self.max_size:
                # Scale up
                for i in range(current, target_size):
                    agent_id = f"{self.agent_type}_{i}"
                    agent = await agent_manager.create_agent(
                        self.agent_type,
                        agent_id,
                        {},
                    )
                    self.agents[agent_id] = agent
                    await self.available.put(agent)

            elif target_size < current and target_size >= self.min_size:
                # Scale down
                for _ in range(current - target_size):
                    if not self.available.empty():
                        agent = await self.available.get()
                        await agent.shutdown()
                        del self.agents[agent.agent_id]

        logger.info(
            "agent_pool_scaled",
            agent_type=self.agent_type,
            old_size=current,
            new_size=self.size,
        )


class AgentManager:
    """
    Manager for agent lifecycle and execution.

    Features:
    - Agent creation and destruction
    - Agent pools for scaling
    - Health monitoring
    - Statistics collection
    """

    def __init__(self):
        self.registry = AgentRegistry()
        self.agents: Dict[str, BaseAgent] = {}
        self.pools: Dict[str, AgentPool] = {}
        self.stats: Dict[str, AgentStats] = {}

        self._lock = asyncio.Lock()

    def register_agent_type(
        self,
        agent_type: str,
        agent_class: Type[BaseAgent],
    ) -> None:
        """Register an agent type."""
        self.registry.register(agent_type, agent_class)

    def unregister_agent_type(self, agent_type: str) -> None:
        """Unregister an agent type."""
        self.registry.unregister(agent_type)

    async def create_agent(
        self,
        agent_type: str,
        agent_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> BaseAgent:
        """
        Create a new agent instance.

        Args:
            agent_type: Type of agent to create
            agent_id: Optional agent ID (auto-generated if not provided)
            config: Agent configuration

        Returns:
            Created agent

        Raises:
            AgentError: If agent type not registered
        """
        agent_class = self.registry.get(agent_type)
        if not agent_class:
            raise AgentError(f"Unknown agent type: {agent_type}")

        agent_id = agent_id or f"{agent_type}_{len(self.agents)}"
        config = config or {}

        agent = agent_class(agent_id, config)
        await agent.initialize()

        async with self._lock:
            self.agents[agent_id] = agent
            self.stats[agent_id] = AgentStats(
                agent_id=agent_id,
                agent_type=agent_type,
                state=agent.state,
            )

        logger.info(
            "agent_created",
            agent_id=agent_id,
            agent_type=agent_type,
        )

        return agent

    async def destroy_agent(self, agent_id: str) -> bool:
        """
        Destroy an agent instance.

        Args:
            agent_id: ID of agent to destroy

        Returns:
            True if destroyed, False if not found
        """
        async with self._lock:
            agent = self.agents.get(agent_id)
            if not agent:
                return False

            await agent.shutdown()
            del self.agents[agent_id]
            self.stats.pop(agent_id, None)

        logger.info("agent_destroyed", agent_id=agent_id)
        return True

    async def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)

    async def get_agents_by_type(self, agent_type: str) -> List[BaseAgent]:
        """Get all agents of a specific type."""
        return [
            agent
            for agent in self.agents.values()
            if agent.agent_type.value == agent_type or agent.__class__.__name__ == agent_type
        ]

    async def get_agents_by_state(self, state: AgentState) -> List[BaseAgent]:
        """Get all agents in a specific state."""
        return [agent for agent in self.agents.values() if agent.state == state]

    async def get_idle_agents(self) -> List[BaseAgent]:
        """Get all idle agents."""
        return await self.get_agents_by_state(AgentState.IDLE)

    async def create_pool(
        self,
        agent_type: str,
        min_size: int = 1,
        max_size: int = 10,
        auto_scale: bool = True,
    ) -> AgentPool:
        """
        Create an agent pool.

        Args:
            agent_type: Type of agents in pool
            min_size: Minimum pool size
            max_size: Maximum pool size
            auto_scale: Enable auto-scaling

        Returns:
            Created pool
        """
        pool = AgentPool(
            agent_type=agent_type,
            min_size=min_size,
            max_size=max_size,
            auto_scale=auto_scale,
        )

        await pool.initialize(self)
        self.pools[agent_type] = pool

        return pool

    async def get_pool(self, agent_type: str) -> Optional[AgentPool]:
        """Get pool by agent type."""
        return self.pools.get(agent_type)

    async def destroy_pool(self, agent_type: str) -> bool:
        """Destroy a pool and all its agents."""
        pool = self.pools.get(agent_type)
        if not pool:
            return False

        for agent_id, agent in list(pool.agents.items()):
            await agent.shutdown()
            del self.agents[agent_id]
            self.stats.pop(agent_id, None)

        del self.pools[agent_type]

        logger.info("agent_pool_destroyed", agent_type=agent_type)
        return True

    async def update_stats(
        self,
        agent_id: str,
        task_completed: bool,
        duration: float,
    ) -> None:
        """Update agent statistics."""
        stats = self.stats.get(agent_id)
        if not stats:
            return

        if task_completed:
            stats.tasks_completed += 1
        else:
            stats.tasks_failed += 1

        stats.total_duration += duration
        stats.last_task_at = datetime.now()

    async def get_stats(self, agent_id: str) -> Optional[AgentStats]:
        """Get statistics for an agent."""
        return self.stats.get(agent_id)

    async def get_all_stats(self) -> Dict[str, AgentStats]:
        """Get statistics for all agents."""
        return self.stats.copy()

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all agents.

        Returns:
            Health check results
        """
        results = {
            "total_agents": len(self.agents),
            "by_state": {},
            "unhealthy": [],
        }

        for state in AgentState:
            count = len([a for a in self.agents.values() if a.state == state])
            results["by_state"][state.value] = count

        # Check for unhealthy agents
        for agent in self.agents.values():
            if agent.state == AgentState.ERROR:
                results["unhealthy"].append(
                    {
                        "agent_id": agent.agent_id,
                        "agent_type": agent.agent_type.value,
                        "state": agent.state.value,
                    }
                )

        return results

    async def shutdown_all(self) -> None:
        """Shutdown all agents."""
        logger.info("shutting_down_all_agents", count=len(self.agents))

        for agent_id in list(self.agents.keys()):
            await self.destroy_agent(agent_id)

        for pool_type in list(self.pools.keys()):
            await self.destroy_pool(pool_type)

    async def __aenter__(self) -> "AgentManager":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.shutdown_all()
