"""
Flow Engine for HyperEternalAgent framework.
"""

import asyncio
import heapq
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Type

import yaml

from ..core.exceptions import (
    CyclicDependencyError,
    FlowError,
    FlowExecutionError,
    FlowNotFoundError,
    FlowValidationError,
)
from ..core.types import FlowStatus, StepType, Task, TaskResult, generate_id
from ..infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FlowStep:
    """A single step in a flow."""

    step_id: str
    name: str
    step_type: StepType
    agent_type: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    condition: Optional[str] = None
    retry_policy: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = None
    on_success: Optional[str] = None
    on_failure: Optional[str] = None
    # For parallel steps
    branches: List["FlowStep"] = field(default_factory=list)
    # For loop steps
    iterate_over: Optional[str] = None
    loop_step: Optional["FlowStep"] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "step_id": self.step_id,
            "name": self.name,
            "step_type": self.step_type.value,
            "agent_type": self.agent_type,
            "config": self.config,
            "dependencies": self.dependencies,
            "condition": self.condition,
            "retry_policy": self.retry_policy,
            "timeout": self.timeout,
            "on_success": self.on_success,
            "on_failure": self.on_failure,
        }
        if self.branches:
            result["branches"] = [b.to_dict() for b in self.branches]
        if self.loop_step:
            result["loop_step"] = self.loop_step.to_dict()
        if self.iterate_over:
            result["iterate_over"] = self.iterate_over
        return result


@dataclass
class FlowDefinition:
    """Definition of a flow."""

    flow_id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    steps: List[FlowStep] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    triggers: List[Dict[str, Any]] = field(default_factory=list)
    error_handler: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "flow_id": self.flow_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "steps": [s.to_dict() for s in self.steps],
            "variables": self.variables,
            "triggers": self.triggers,
            "error_handler": self.error_handler,
            "metadata": self.metadata,
        }


@dataclass
class FlowExecution:
    """Execution instance of a flow."""

    execution_id: str = field(default_factory=generate_id)
    flow_id: str = ""
    status: FlowStatus = FlowStatus.PENDING
    current_step: Optional[str] = None
    step_results: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    parent_execution_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "flow_id": self.flow_id,
            "status": self.status.value,
            "current_step": self.current_step,
            "step_results": self.step_results,
            "variables": self.variables,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "parent_execution_id": self.parent_execution_id,
        }


class FlowParser:
    """Parser for flow definitions."""

    def __init__(self):
        self._variable_resolver = VariableResolver()

    def parse(self, definition: Dict[str, Any]) -> FlowDefinition:
        """Parse a flow definition from dictionary."""
        flow_data = definition.get("flow", definition)

        flow = FlowDefinition(
            flow_id=flow_data.get("id", generate_id()),
            name=flow_data.get("name", "Unnamed Flow"),
            description=flow_data.get("description", ""),
            version=flow_data.get("version", "1.0.0"),
            variables=flow_data.get("variables", {}),
            triggers=flow_data.get("triggers", []),
            error_handler=flow_data.get("error_handler"),
            metadata=flow_data.get("metadata", {}),
        )

        # Parse steps
        for step_def in flow_data.get("steps", []):
            step = self._parse_step(step_def)
            flow.steps.append(step)

        # Validate flow
        self._validate_flow(flow)

        return flow

    def parse_yaml(self, yaml_content: str) -> FlowDefinition:
        """Parse a flow definition from YAML."""
        definition = yaml.safe_load(yaml_content)
        return self.parse(definition)

    def parse_file(self, file_path: str) -> FlowDefinition:
        """Parse a flow definition from file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return self.parse_yaml(f.read())

    def _parse_step(self, step_def: Dict[str, Any]) -> FlowStep:
        """Parse a single step definition."""
        step_type = StepType(step_def.get("type", "task"))

        step = FlowStep(
            step_id=step_def["id"],
            name=step_def.get("name", step_def["id"]),
            step_type=step_type,
            agent_type=step_def.get("agent"),
            config=step_def.get("config", {}),
            dependencies=step_def.get("dependencies", []),
            condition=step_def.get("condition"),
            retry_policy=step_def.get("retry_policy"),
            timeout=step_def.get("timeout"),
            on_success=step_def.get("on_success"),
            on_failure=step_def.get("on_failure"),
        )

        # Parse parallel branches
        if step_type == StepType.PARALLEL:
            step.branches = [
                self._parse_step(branch)
                for branch in step_def.get("branches", [])
            ]

        # Parse loop step
        if step_type == StepType.LOOP:
            step.iterate_over = step_def.get("iterate_over")
            if "step" in step_def:
                step.loop_step = self._parse_step(step_def["step"])

        return step

    def _validate_flow(self, flow: FlowDefinition) -> None:
        """Validate a flow definition."""
        # Check step ID uniqueness
        step_ids = [s.step_id for s in flow.steps]
        if len(step_ids) != len(set(step_ids)):
            raise FlowValidationError("Duplicate step IDs found")

        # Collect all step IDs including nested ones
        all_step_ids = set(step_ids)
        for step in flow.steps:
            all_step_ids.update(self._collect_step_ids(step))

        # Validate dependencies
        for step in flow.steps:
            self._validate_step_dependencies(step, all_step_ids)

        # Check for cycles
        self._check_cycles(flow)

    def _collect_step_ids(self, step: FlowStep) -> Set[str]:
        """Collect all step IDs including nested steps."""
        ids = {step.step_id}
        for branch in step.branches:
            ids.update(self._collect_step_ids(branch))
        if step.loop_step:
            ids.update(self._collect_step_ids(step.loop_step))
        return ids

    def _validate_step_dependencies(
        self, step: FlowStep, valid_ids: Set[str]
    ) -> None:
        """Validate step dependencies."""
        for dep_id in step.dependencies:
            if dep_id not in valid_ids:
                raise FlowValidationError(
                    f"Invalid dependency '{dep_id}' in step '{step.step_id}'"
                )

        # Validate branches
        for branch in step.branches:
            self._validate_step_dependencies(branch, valid_ids)

        # Validate loop step
        if step.loop_step:
            self._validate_step_dependencies(step.loop_step, valid_ids)

    def _check_cycles(self, flow: FlowDefinition) -> None:
        """Check for cyclic dependencies."""
        visited = set()
        rec_stack = set()

        def has_cycle(step_id: str, steps: Dict[str, FlowStep]) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)

            step = steps.get(step_id)
            if step:
                for dep_id in step.dependencies:
                    if dep_id not in visited:
                        if has_cycle(dep_id, steps):
                            return True
                    elif dep_id in rec_stack:
                        return True

            rec_stack.remove(step_id)
            return False

        # Build step lookup
        steps = {s.step_id: s for s in flow.steps}

        for step in flow.steps:
            if step.step_id not in visited:
                if has_cycle(step.step_id, steps):
                    raise CyclicDependencyError("Cyclic dependency detected in flow")


class VariableResolver:
    """Resolver for flow variables."""

    def resolve(
        self,
        value: Any,
        variables: Dict[str, Any],
        step_results: Dict[str, Any],
    ) -> Any:
        """Resolve variables in a value."""
        if isinstance(value, str):
            return self._resolve_string(value, variables, step_results)
        elif isinstance(value, dict):
            return {
                k: self.resolve(v, variables, step_results)
                for k, v in value.items()
            }
        elif isinstance(value, list):
            return [self.resolve(item, variables, step_results) for item in value]
        return value

    def _resolve_string(
        self,
        value: str,
        variables: Dict[str, Any],
        step_results: Dict[str, Any],
    ) -> Any:
        """Resolve variables in a string."""
        import re

        # Match ${variable} or ${path.to.variable}
        pattern = r"\$\{([^}]+)\}"

        def replace_var(match):
            path = match.group(1)
            return str(self._get_value(path, variables, step_results))

        result = re.sub(pattern, replace_var, value)

        # If the entire string was a variable, return the actual value
        if re.fullmatch(pattern, value):
            path = re.match(pattern, value).group(1)
            return self._get_value(path, variables, step_results)

        return result

    def _get_value(
        self,
        path: str,
        variables: Dict[str, Any],
        step_results: Dict[str, Any],
    ) -> Any:
        """Get a value by path."""
        parts = path.split(".")
        root = parts[0]

        # Determine root source
        if root == "variables":
            source = variables
            parts = parts[1:]
        elif root == "steps":
            source = step_results
            parts = parts[1:]
        elif root == "input":
            source = variables
            parts = parts[1:]
        elif root == "context":
            source = variables.get("context", {})
            parts = parts[1:]
        elif root == "loop":
            source = variables.get("loop", {})
            parts = parts[1:]
        else:
            source = variables

        # Navigate path
        value = source
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                value = value[int(part)]
            else:
                return None

        return value

    async def evaluate(
        self,
        condition: str,
        variables: Dict[str, Any],
        step_results: Dict[str, Any],
    ) -> bool:
        """Evaluate a condition expression."""
        # Resolve variables in condition
        resolved = self._resolve_string(condition, variables, step_results)

        # Simple evaluation for common patterns
        # Support: ${value} >= number, ${value} == "string", etc.
        import re

        # Check for comparison operators
        operators = [">=", "<=", "==", "!=", ">", "<"]
        for op in operators:
            if op in resolved:
                parts = resolved.split(op, 1)
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()

                    # Try to convert to numbers
                    try:
                        left_val = float(left)
                        right_val = float(right)

                        if op == ">=":
                            return left_val >= right_val
                        elif op == "<=":
                            return left_val <= right_val
                        elif op == "==":
                            return left_val == right_val
                        elif op == "!=":
                            return left_val != right_val
                        elif op == ">":
                            return left_val > right_val
                        elif op == "<":
                            return left_val < right_val
                    except ValueError:
                        # String comparison
                        left_val = left.strip('"\'')
                        right_val = right.strip('"\'')

                        if op == "==":
                            return left_val == right_val
                        elif op == "!=":
                            return left_val != right_val

        # Default: check if truthy
        return bool(resolved) and resolved not in ["False", "false", "0", ""]


class ExecutionGraph:
    """Graph representation of flow execution."""

    def __init__(self):
        self.steps: Dict[str, FlowStep] = {}
        self.edges: Dict[str, List[str]] = {}
        self.in_degree: Dict[str, int] = {}

    def add_step(self, step: FlowStep) -> None:
        """Add a step to the graph."""
        self.steps[step.step_id] = step
        if step.step_id not in self.edges:
            self.edges[step.step_id] = []
        if step.step_id not in self.in_degree:
            self.in_degree[step.step_id] = 0

        for dep_id in step.dependencies:
            if dep_id not in self.edges:
                self.edges[dep_id] = []
            self.edges[dep_id].append(step.step_id)
            self.in_degree[step.step_id] = self.in_degree.get(step.step_id, 0) + 1

    def get_ready_steps(self, completed: Set[str]) -> List[FlowStep]:
        """Get steps that are ready to execute."""
        ready = []

        for step_id, step in self.steps.items():
            if step_id in completed:
                continue

            # Check if all dependencies are completed
            if all(dep_id in completed for dep_id in step.dependencies):
                ready.append(step)

        return ready


class StepHandler(ABC):
    """Abstract base class for step handlers."""

    @abstractmethod
    async def execute(
        self,
        step: FlowStep,
        execution: FlowExecution,
        flow: FlowDefinition,
        context: Dict[str, Any],
    ) -> Any:
        """Execute a step."""
        pass


class TaskStepHandler(StepHandler):
    """Handler for task steps."""

    def __init__(self, agent_executor: Callable):
        self.agent_executor = agent_executor

    async def execute(
        self,
        step: FlowStep,
        execution: FlowExecution,
        flow: FlowDefinition,
        context: Dict[str, Any],
    ) -> Any:
        """Execute a task step."""
        if not step.agent_type:
            raise FlowExecutionError(f"Step '{step.step_id}' has no agent type")

        # Create task
        task = Task(
            task_type=step.agent_type,
            payload=step.config,
            timeout=step.timeout,
        )

        # Execute via agent
        result = await self.agent_executor(step.agent_type, task, context)

        return result


class ParallelStepHandler(StepHandler):
    """Handler for parallel steps."""

    def __init__(self, flow_engine: "FlowEngine"):
        self.flow_engine = flow_engine

    async def execute(
        self,
        step: FlowStep,
        execution: FlowExecution,
        flow: FlowDefinition,
        context: Dict[str, Any],
    ) -> Any:
        """Execute parallel branches."""
        tasks = []

        for branch in step.branches:
            tasks.append(
                self.flow_engine._execute_step(branch, execution, flow, context)
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        branch_results = {}
        for branch, result in zip(step.branches, results):
            if isinstance(result, Exception):
                branch_results[branch.step_id] = {
                    "success": False,
                    "error": str(result),
                }
            else:
                branch_results[branch.step_id] = result

        return branch_results


class ConditionStepHandler(StepHandler):
    """Handler for condition steps."""

    def __init__(self, variable_resolver: VariableResolver):
        self.resolver = variable_resolver

    async def execute(
        self,
        step: FlowStep,
        execution: FlowExecution,
        flow: FlowDefinition,
        context: Dict[str, Any],
    ) -> Any:
        """Evaluate condition and return next step."""
        if not step.condition:
            raise FlowExecutionError(f"Step '{step.step_id}' has no condition")

        result = await self.resolver.evaluate(
            step.condition,
            execution.variables,
            execution.step_results,
        )

        return {
            "condition_result": result,
            "next_step": step.on_success if result else step.on_failure,
        }


class LoopStepHandler(StepHandler):
    """Handler for loop steps."""

    def __init__(self, flow_engine: "FlowEngine", resolver: VariableResolver):
        self.flow_engine = flow_engine
        self.resolver = resolver

    async def execute(
        self,
        step: FlowStep,
        execution: FlowExecution,
        flow: FlowDefinition,
        context: Dict[str, Any],
    ) -> Any:
        """Execute loop over items."""
        if not step.iterate_over or not step.loop_step:
            raise FlowExecutionError(f"Step '{step.step_id}' is not properly configured for loop")

        # Get items to iterate over
        items = self.resolver.resolve(
            step.iterate_over,
            execution.variables,
            execution.step_results,
        )

        if not isinstance(items, (list, tuple)):
            items = [items]

        results = []
        for i, item in enumerate(items):
            # Set loop variable
            execution.variables["loop"] = {"index": i, "item": item}

            # Execute loop step
            result = await self.flow_engine._execute_step(
                step.loop_step, execution, flow, context
            )
            results.append(result)

        return results


class FlowEngine:
    """
    Engine for executing flows.

    Features:
    - Sequential and parallel step execution
    - Condition branching
    - Loop iteration
    - Variable resolution
    - Error handling
    """

    def __init__(self, agent_executor: Callable, state_manager: Any = None):
        self.agent_executor = agent_executor
        self.state_manager = state_manager
        self.parser = FlowParser()
        self.resolver = VariableResolver()

        # Register step handlers
        self._handlers: Dict[StepType, StepHandler] = {
            StepType.TASK: TaskStepHandler(agent_executor),
            StepType.PARALLEL: ParallelStepHandler(self),
            StepType.CONDITION: ConditionStepHandler(self.resolver),
            StepType.LOOP: LoopStepHandler(self, self.resolver),
        }

        # Execution storage
        self._executions: Dict[str, FlowExecution] = {}
        self._flows: Dict[str, FlowDefinition] = {}

    def register_flow(self, flow: FlowDefinition) -> None:
        """Register a flow definition."""
        self._flows[flow.flow_id] = flow
        logger.info("flow_registered", flow_id=flow.flow_id, name=flow.name)

    def register_flow_from_yaml(self, yaml_content: str) -> FlowDefinition:
        """Register a flow from YAML content."""
        flow = self.parser.parse_yaml(yaml_content)
        self.register_flow(flow)
        return flow

    def register_flow_from_file(self, file_path: str) -> FlowDefinition:
        """Register a flow from file."""
        flow = self.parser.parse_file(file_path)
        self.register_flow(flow)
        return flow

    def get_flow(self, flow_id: str) -> Optional[FlowDefinition]:
        """Get a flow definition."""
        return self._flows.get(flow_id)

    async def execute(
        self,
        flow_id: str,
        input_variables: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None,
    ) -> FlowExecution:
        """
        Execute a flow.

        Args:
            flow_id: ID of flow to execute
            input_variables: Input variables for the flow
            execution_id: Optional execution ID

        Returns:
            Flow execution result
        """
        flow = self._flows.get(flow_id)
        if not flow:
            raise FlowNotFoundError(f"Flow not found: {flow_id}")

        # Create execution instance
        execution = FlowExecution(
            execution_id=execution_id or generate_id(),
            flow_id=flow_id,
            status=FlowStatus.RUNNING,
            variables={**flow.variables, **(input_variables or {})},
            started_at=datetime.now(),
        )

        self._executions[execution.execution_id] = execution

        logger.info(
            "flow_execution_started",
            execution_id=execution.execution_id,
            flow_id=flow_id,
        )

        try:
            # Build execution graph
            graph = self._build_execution_graph(flow)

            # Execute steps
            await self._execute_steps(flow, execution, graph)

            # Mark completed
            execution.status = FlowStatus.COMPLETED
            execution.completed_at = datetime.now()

            logger.info(
                "flow_execution_completed",
                execution_id=execution.execution_id,
                flow_id=flow_id,
            )

        except Exception as e:
            execution.status = FlowStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.now()

            logger.error(
                "flow_execution_failed",
                execution_id=execution.execution_id,
                flow_id=flow_id,
                error=str(e),
            )

            # Execute error handler if configured
            if flow.error_handler:
                await self._handle_error(flow, execution, e)

        return execution

    def _build_execution_graph(self, flow: FlowDefinition) -> ExecutionGraph:
        """Build execution graph from flow definition."""
        graph = ExecutionGraph()

        for step in flow.steps:
            self._add_step_to_graph(step, graph)

        return graph

    def _add_step_to_graph(self, step: FlowStep, graph: ExecutionGraph) -> None:
        """Add a step and its children to the execution graph."""
        graph.add_step(step)

        for branch in step.branches:
            self._add_step_to_graph(branch, graph)

        if step.loop_step:
            self._add_step_to_graph(step.loop_step, graph)

    async def _execute_steps(
        self,
        flow: FlowDefinition,
        execution: FlowExecution,
        graph: ExecutionGraph,
    ) -> None:
        """Execute flow steps."""
        completed: Set[str] = set()

        while len(completed) < len(graph.steps):
            # Get ready steps
            ready_steps = graph.get_ready_steps(completed)

            if not ready_steps:
                if len(completed) < len(graph.steps):
                    raise FlowExecutionError("Deadlock detected in flow execution")
                break

            # Execute ready steps in parallel
            tasks = []
            for step in ready_steps:
                tasks.append(self._execute_step(step, execution, flow, {}))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for step, result in zip(ready_steps, results):
                if isinstance(result, Exception):
                    raise result

                execution.step_results[step.step_id] = result
                completed.add(step.step_id)

                logger.debug(
                    "flow_step_completed",
                    execution_id=execution.execution_id,
                    step_id=step.step_id,
                )

    async def _execute_step(
        self,
        step: FlowStep,
        execution: FlowExecution,
        flow: FlowDefinition,
        context: Dict[str, Any],
    ) -> Any:
        """Execute a single step."""
        # Update current step
        execution.current_step = step.step_id

        logger.debug(
            "flow_step_started",
            execution_id=execution.execution_id,
            step_id=step.step_id,
            step_type=step.step_type.value,
        )

        # Get handler
        handler = self._handlers.get(step.step_type)
        if not handler:
            raise FlowExecutionError(
                f"No handler for step type: {step.step_type.value}"
            )

        # Resolve config variables
        resolved_config = self.resolver.resolve(
            step.config,
            execution.variables,
            execution.step_results,
        )

        # Create step copy with resolved config
        resolved_step = FlowStep(
            step_id=step.step_id,
            name=step.name,
            step_type=step.step_type,
            agent_type=step.agent_type,
            config=resolved_config,
            dependencies=step.dependencies,
            condition=step.condition,
            retry_policy=step.retry_policy,
            timeout=step.timeout,
            on_success=step.on_success,
            on_failure=step.on_failure,
            branches=step.branches,
            iterate_over=step.iterate_over,
            loop_step=step.loop_step,
        )

        # Execute with timeout
        try:
            if step.timeout:
                result = await asyncio.wait_for(
                    handler.execute(resolved_step, execution, flow, context),
                    timeout=step.timeout,
                )
            else:
                result = await handler.execute(resolved_step, execution, flow, context)

            return result

        except asyncio.TimeoutError:
            raise FlowExecutionError(f"Step '{step.step_id}' timed out")

    async def _handle_error(
        self,
        flow: FlowDefinition,
        execution: FlowExecution,
        error: Exception,
    ) -> None:
        """Handle flow execution error."""
        error_handler = flow.error_handler
        if not error_handler:
            return

        strategy = error_handler.get("strategy", "fail")

        if strategy == "retry":
            max_retries = error_handler.get("max_retries", 1)
            # Would implement retry logic here
            logger.info(
                "flow_error_handler_retry",
                execution_id=execution.execution_id,
                max_retries=max_retries,
            )

        elif strategy == "fallback_flow":
            fallback_flow_id = error_handler.get("fallback_flow")
            if fallback_flow_id:
                logger.info(
                    "flow_error_handler_fallback",
                    execution_id=execution.execution_id,
                    fallback_flow_id=fallback_flow_id,
                )

    def get_execution(self, execution_id: str) -> Optional[FlowExecution]:
        """Get an execution by ID."""
        return self._executions.get(execution_id)

    async def pause_execution(self, execution_id: str) -> bool:
        """Pause a running execution."""
        execution = self._executions.get(execution_id)
        if execution and execution.status == FlowStatus.RUNNING:
            execution.status = FlowStatus.PAUSED
            return True
        return False

    async def resume_execution(self, execution_id: str) -> bool:
        """Resume a paused execution."""
        execution = self._executions.get(execution_id)
        if execution and execution.status == FlowStatus.PAUSED:
            execution.status = FlowStatus.RUNNING
            # Would need to resume execution here
            return True
        return False

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an execution."""
        execution = self._executions.get(execution_id)
        if execution and execution.status in [FlowStatus.RUNNING, FlowStatus.PAUSED]:
            execution.status = FlowStatus.CANCELLED
            execution.completed_at = datetime.now()
            return True
        return False
