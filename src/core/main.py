"""
Main entry point for HyperEternalAgent framework.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

from ..core.config import ConfigLoader, SystemConfig
from ..core.exceptions import HyperEternalError
from ..core.types import Task, TaskResult, TaskStatus, generate_id
from ..infrastructure.logging import get_logger, setup_logging
from ..agents.base import BaseAgent
from ..agents.manager import AgentManager
from ..persistence.state_manager import SessionManager, StateManager
from ..persistence.storage import StorageBackend, create_storage_backend
from ..persistence.task_queue import TaskQueue
from ..reflection.correction import (
    AutoCorrectionEngine,
    ErrorDetectionEngine,
    FeedbackLoop,
)
from ..reflection.quality import QualityAssuranceEngine

logger = get_logger(__name__)


@dataclass
class TaskSubmission:
    """Task submission result."""

    task_id: str
    status: TaskStatus
    submitted_at: datetime = field(default_factory=datetime.now)


@dataclass
class SystemStatus:
    """System status information."""

    running: bool
    uptime_seconds: float
    tasks_pending: int
    tasks_running: int
    tasks_completed: int
    agents_active: int
    memory_usage_mb: float = 0.0
    last_activity: Optional[datetime] = None


class HyperEternalAgent:
    """
    Main entry point for the HyperEternalAgent framework.

    This class provides a high-level API for:
    - Starting and stopping the system
    - Submitting and managing tasks
    - Managing agents
    - Accessing system status

    Usage:
        async with HyperEternalAgent(config_path="./config/config.yaml") as system:
            result = await system.submit_task(
                flow="auto_coding_flow",
                input={"project_name": "my_project"}
            )
            await system.wait_for_completion(result.task_id)
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        config: Optional[SystemConfig] = None,
    ):
        """
        Initialize HyperEternalAgent.

        Args:
            config_path: Path to configuration file
            config: System configuration object (overrides config_path)
        """
        # Load configuration
        if config:
            self.config = config
        elif config_path:
            loader = ConfigLoader()
            self.config = loader.load_system_config(config_path)
        else:
            self.config = SystemConfig()

        # Initialize components
        self._storage: Optional[StorageBackend] = None
        self._state_manager: Optional[StateManager] = None
        self._session_manager: Optional[SessionManager] = None
        self._task_queue: Optional[TaskQueue] = None
        self._agent_manager: Optional[AgentManager] = None
        self._quality_engine: Optional[QualityAssuranceEngine] = None
        self._error_detector: Optional[ErrorDetectionEngine] = None
        self._auto_corrector: Optional[AutoCorrectionEngine] = None

        # State
        self._running = False
        self._started_at: Optional[datetime] = None
        self._main_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """
        Start the HyperEternalAgent system.

        Initializes all components and starts background tasks.
        """
        if self._running:
            logger.warning("system_already_running")
            return

        logger.info("system_starting", name=self.config.name, version=self.config.version)

        # Set up logging
        setup_logging(
            log_level=self.config.monitoring.log_level,
            log_file=self.config.monitoring.log_file,
        )

        # Initialize storage
        self._storage = create_storage_backend(
            backend_type=self.config.persistence.backend,
            url=self.config.persistence.url,
        )
        await self._storage.connect()

        # Initialize state manager
        self._state_manager = StateManager(self._storage)
        self._session_manager = SessionManager(self._state_manager)

        # Initialize task queue
        self._task_queue = TaskQueue(self._storage)
        await self._task_queue.initialize()

        # Initialize agent manager
        self._agent_manager = AgentManager()

        # Initialize reflection components
        self._quality_engine = QualityAssuranceEngine()
        self._error_detector = ErrorDetectionEngine()
        self._auto_corrector = AutoCorrectionEngine()

        # Mark as running
        self._running = True
        self._started_at = datetime.now()

        logger.info(
            "system_started",
            name=self.config.name,
            persistence_backend=self.config.persistence.backend,
        )

    async def stop(self) -> None:
        """
        Stop the HyperEternalAgent system.

        Gracefully shuts down all components.
        """
        if not self._running:
            return

        logger.info("system_stopping")

        self._running = False

        # Shutdown agent manager
        if self._agent_manager:
            await self._agent_manager.shutdown_all()

        # Disconnect storage
        if self._storage:
            await self._storage.disconnect()

        logger.info("system_stopped")

    async def submit_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: int = 5,
        timeout: Optional[int] = None,
    ) -> TaskSubmission:
        """
        Submit a task for execution.

        Args:
            task_type: Type of task
            payload: Task payload
            priority: Task priority (0-20, higher = more important)
            timeout: Task timeout in seconds

        Returns:
            Task submission result
        """
        if not self._task_queue:
            raise HyperEternalError("System not started")

        task = Task(
            task_type=task_type,
            payload=payload,
            priority=priority,
            timeout=timeout,
        )

        await self._task_queue.enqueue(task)

        logger.info(
            "task_submitted",
            task_id=task.task_id,
            task_type=task_type,
            priority=priority,
        )

        return TaskSubmission(
            task_id=task.task_id,
            status=task.status,
        )

    async def submit_flow(
        self,
        flow_name: str,
        input_data: Dict[str, Any],
    ) -> TaskSubmission:
        """
        Submit a flow for execution.

        Args:
            flow_name: Name of the flow to execute
            input_data: Flow input data

        Returns:
            Task submission result
        """
        return await self.submit_task(
            task_type=f"flow:{flow_name}",
            payload=input_data,
        )

    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the status of a task."""
        if not self._task_queue:
            return None

        task = await self._task_queue.get_task(task_id)
        return task.status if task else None

    async def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Get the result of a completed task."""
        if not self._task_queue:
            return None

        return await self._task_queue.get_result(task_id)

    async def wait_for_completion(
        self,
        task_id: str,
        timeout: Optional[float] = None,
    ) -> Optional[TaskResult]:
        """
        Wait for a task to complete.

        Args:
            task_id: Task ID to wait for
            timeout: Maximum time to wait (seconds)

        Returns:
            Task result or None if timeout
        """
        start_time = datetime.now()

        while True:
            status = await self.get_task_status(task_id)

            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return await self.get_task_result(task_id)

            if timeout:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= timeout:
                    return None

            await asyncio.sleep(0.5)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        if not self._task_queue:
            return False

        return await self._task_queue.cancel(task_id)

    def register_agent_type(
        self,
        agent_type: str,
        agent_class: Type[BaseAgent],
    ) -> None:
        """
        Register an agent type.

        Args:
            agent_type: Type name
            agent_class: Agent class
        """
        if not self._agent_manager:
            raise HyperEternalError("System not started")

        self._agent_manager.register_agent_type(agent_type, agent_class)

    async def create_agent(
        self,
        agent_type: str,
        agent_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> BaseAgent:
        """
        Create an agent instance.

        Args:
            agent_type: Type of agent to create
            agent_id: Optional agent ID
            config: Agent configuration

        Returns:
            Created agent
        """
        if not self._agent_manager:
            raise HyperEternalError("System not started")

        return await self._agent_manager.create_agent(agent_type, agent_id, config)

    async def execute_task_with_agent(
        self,
        agent: BaseAgent,
        task: Task,
    ) -> TaskResult:
        """
        Execute a task with a specific agent.

        Args:
            agent: Agent to execute task
            task: Task to execute

        Returns:
            Task result
        """
        result = await agent.execute(task)

        # Complete task in queue
        if self._task_queue:
            if result.success:
                await self._task_queue.complete(task.task_id, result.output)
            else:
                await self._task_queue.fail(
                    task.task_id,
                    "; ".join(result.errors),
                    retry=False,
                )

        return result

    async def get_status(self) -> SystemStatus:
        """Get system status."""
        uptime = 0.0
        if self._started_at:
            uptime = (datetime.now() - self._started_at).total_seconds()

        queue_stats = {}
        if self._task_queue:
            queue_stats = await self._task_queue.get_stats()

        agent_health = {}
        if self._agent_manager:
            agent_health = await self._agent_manager.health_check()

        return SystemStatus(
            running=self._running,
            uptime_seconds=uptime,
            tasks_pending=queue_stats.get("by_status", {}).get("pending", 0),
            tasks_running=queue_stats.get("by_status", {}).get("running", 0),
            tasks_completed=queue_stats.get("by_status", {}).get("completed", 0),
            agents_active=agent_health.get("total_agents", 0),
        )

    @property
    def state_manager(self) -> Optional[StateManager]:
        """Get state manager."""
        return self._state_manager

    @property
    def task_queue(self) -> Optional[TaskQueue]:
        """Get task queue."""
        return self._task_queue

    @property
    def agent_manager(self) -> Optional[AgentManager]:
        """Get agent manager."""
        return self._agent_manager

    @property
    def quality_engine(self) -> Optional[QualityAssuranceEngine]:
        """Get quality assurance engine."""
        return self._quality_engine

    @property
    def error_detector(self) -> Optional[ErrorDetectionEngine]:
        """Get error detection engine."""
        return self._error_detector

    @property
    def auto_corrector(self) -> Optional[AutoCorrectionEngine]:
        """Get auto-correction engine."""
        return self._auto_corrector

    async def __aenter__(self) -> "HyperEternalAgent":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.stop()


# Convenience function to create system
async def create_system(
    config_path: Optional[str] = None,
    config: Optional[SystemConfig] = None,
) -> HyperEternalAgent:
    """
    Create and start a HyperEternalAgent system.

    Args:
        config_path: Path to configuration file
        config: System configuration

    Returns:
        Started HyperEternalAgent instance
    """
    system = HyperEternalAgent(config_path=config_path, config=config)
    await system.start()
    return system
