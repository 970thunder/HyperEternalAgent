# HyperEternalAgent API Reference

## Core Classes

### HyperEternalAgent

Main entry point for the framework.

```python
from hypereternal import HyperEternalAgent

# Create instance with config file
async with HyperEternalAgent(config_path="./config/config.yaml") as system:
    # Use the system
    pass

# Or with config object
from hypereternal import SystemConfig

config = SystemConfig(name="MySystem", version="1.0.0")
system = HyperEternalAgent(config=config)
await system.start()
```

#### Methods

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `start()` | Start the system | - | `None` |
| `stop()` | Stop the system | - | `None` |
| `submit_task()` | Submit a task | `task_type`, `payload`, `priority?`, `timeout?` | `TaskSubmission` |
| `submit_flow()` | Submit a flow | `flow_name`, `input_data` | `TaskSubmission` |
| `get_task_status()` | Get task status | `task_id` | `Optional[TaskStatus]` |
| `get_task_result()` | Get task result | `task_id` | `Optional[TaskResult]` |
| `wait_for_completion()` | Wait for task | `task_id`, `timeout?` | `Optional[TaskResult]` |
| `cancel_task()` | Cancel task | `task_id` | `bool` |
| `get_status()` | Get system status | - | `SystemStatus` |
| `register_agent_type()` | Register agent | `agent_type`, `agent_class` | `None` |
| `create_agent()` | Create agent instance | `agent_type`, `agent_id?`, `config?` | `BaseAgent` |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `state_manager` | `StateManager` | State management |
| `task_queue` | `TaskQueue` | Task queue |
| `agent_manager` | `AgentManager` | Agent management |
| `quality_engine` | `QualityAssuranceEngine` | Quality assessment |
| `error_detector` | `ErrorDetectionEngine` | Error detection |
| `auto_corrector` | `AutoCorrectionEngine` | Auto-correction |

---

## Task Types

### Task

```python
from hypereternal import Task

task = Task(
    task_type="code_generation",
    payload={"prompt": "Write a function"},
    priority=10,
    timeout=300,
    max_retries=3,
    dependencies=["task_1", "task_2"],
)
```

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `task_id` | `str` | Auto-generated | Unique task identifier |
| `task_type` | `str` | Required | Type of task |
| `payload` | `Dict[str, Any]` | `{}` | Task payload/data |
| `priority` | `int` | `5` | Priority (0-20, higher = more important) |
| `timeout` | `Optional[int]` | `None` | Timeout in seconds |
| `retry_count` | `int` | `0` | Current retry count |
| `max_retries` | `int` | `3` | Maximum retries |
| `dependencies` | `List[str]` | `[]` | Dependency task IDs |
| `created_at` | `datetime` | Now | Creation timestamp |
| `started_at` | `Optional[datetime]` | `None` | Start timestamp |
| `completed_at` | `Optional[datetime]` | `None` | Completion timestamp |

### TaskResult

```python
from hypereternal import TaskResult

result = TaskResult(
    task_id="task_123",
    success=True,
    output={"code": "..."},
    metrics={"duration": 5.2},
    errors=[],
)
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | `str` | Task identifier |
| `success` | `bool` | Whether task succeeded |
| `output` | `Any` | Task output |
| `metrics` | `Dict[str, Any]` | Execution metrics |
| `errors` | `List[str]` | Error messages |
| `completed_at` | `datetime` | Completion timestamp |

### TaskStatus

| Status | Description |
|--------|-------------|
| `PENDING` | Task is waiting to be processed |
| `QUEUED` | Task is in the queue |
| `RUNNING` | Task is being executed |
| `COMPLETED` | Task finished successfully |
| `FAILED` | Task execution failed |
| `CANCELLED` | Task was cancelled |
| `RETRYING` | Task is being retried |
| `TIMEOUT` | Task timed out |

---

## Agent System

### BaseAgent

Abstract base class for all agents.

```python
from hypereternal import BaseAgent, AgentCapabilities, AgentType

class MyAgent(BaseAgent):
    @property
    def agent_type(self) -> AgentType:
        return AgentType.WORKER

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="My Agent",
            description="Does something",
            input_types=["text"],
            output_types=["result"],
        )

    async def execute(self, task: Task) -> TaskResult:
        # Implement task execution
        result = await self._process(task.payload)
        return TaskResult(
            task_id=task.task_id,
            success=True,
            output=result,
        )
```

#### Agent Types

| Type | Description |
|------|-------------|
| `WORKER` | Executes tasks |
| `REVIEWER` | Reviews output |
| `PLANNER` | Plans workflows |
| `CRITIC` | Evaluates quality |
| `COORDINATOR` | Coordinates agents |
| `CUSTOM` | Custom type |

### Agent Capabilities

```python
from hypereternal import AgentCapabilities

capabilities = AgentCapabilities(
    name="Code Writer",
    description="Generates code from specifications",
    input_types=["specification", "requirements"],
    output_types=["code", "documentation"],
    tags=["code", "generation", "python"],
)
```

---

## Flow System

### FlowDefinition

```python
from hypereternal import FlowDefinition, FlowStep, StepType

flow = FlowDefinition(
    flow_id="my_flow",
    name="My Workflow",
    description="A custom workflow",
    version="1.0.0",
    variables={"input": "${input.value}"},
    steps=[
        FlowStep(
            step_id="step_1",
            name="First Step",
            step_type=StepType.TASK,
            agent_type="my_agent",
            config={"param": "value"},
            dependencies=[],
        ),
    ],
)
```

### Step Types

| Type | Description |
|------|-------------|
| `TASK` | Single task execution |
| `PARALLEL` | Parallel branch execution |
| `SEQUENTIAL` | Sequential step execution |
| `CONDITION` | Conditional branching |
| `LOOP` | Iterative execution |
| `WAIT` | Wait for condition |
| `SUBFLOW` | Nested flow execution |

---

## State Management

### StateManager

```python
# Access via system
state = system.state_manager

# Set state
await state.set("key", value, StateScope.GLOBAL, ttl=3600)

# Get state
value = await state.get("key", StateScope.GLOBAL)

# Delete state
await state.delete("key", StateScope.GLOBAL)

# Check existence
exists = await state.exists("key", StateScope.GLOBAL)

# Atomic increment
new_value = await state.increment("counter", 1, StateScope.GLOBAL)

# List keys
keys = await state.list_keys(StateScope.SESSION, owner_id="session_123")

# Clear scope
count = await state.clear_scope(StateScope.SESSION, owner_id="session_123")
```

### State Scopes

| Scope | Description |
|-------|-------------|
| `GLOBAL` | System-wide state |
| `SESSION` | Per-session state |
| `FLOW` | Flow execution state |
| `AGENT` | Agent-specific state |
| `TASK` | Task execution state |

---

## Quality Assurance

### QualityAssuranceEngine

```python
# Access via system
qa = system.quality_engine

# Perform assessment
assessment = await qa.assess(content, context)

print(f"Score: {assessment.overall_score}")
print(f"Passed: {assessment.passed}")
for score in assessment.dimension_scores:
    print(f"  {score.dimension.value}: {score.score}")
```

### QualityScore

```python
from hypereternal.reflection.quality import QualityScore

score = QualityScore(
    dimension=QualityDimension.CORRECTNESS,
    score=0.85,
    weight=1.0,
    passed=True,
    issues=["Minor style issue"],
)
```

### Quality Dimensions

| Dimension | Description |
|-----------|-------------|
| `CORRECTNESS` | Output correctness |
| `COMPLETENESS` | Requirement coverage |
| `CONSISTENCY` | Internal consistency |
| `EFFICIENCY` | Performance efficiency |
| `READABILITY` | Code/text readability |
| `MAINTAINABILITY` | Code maintainability |
| `SECURITY` | Security considerations |

---

## Error Detection

### ErrorDetectionEngine

```python
# Access via system
detector = system.error_detector

# Detect errors
errors = await detector.detect(content, context)

for error in errors:
    print(f"Error: {error.message}")
    print(f"Severity: {error.severity}")
    print(f"Suggestions: {error.suggestions}")
```

### DetectedError

```python
from hypereternal.reflection.correction import DetectedError

error = DetectedError(
    category=ErrorCategory.SYNTAX,
    severity="high",
    message="Missing closing bracket",
    location={"line": 42, "column": 10},
    suggestions=["Add '}' at the end"],
)
```

### Error Categories

| Category | Description |
|----------|-------------|
| `SYNTAX` | Syntax errors |
| `LOGIC` | Logic errors |
| `RUNTIME` | Runtime errors |
| `RESOURCE` | Resource errors |
| `INTEGRATION` | Integration errors |
| `SECURITY` | Security issues |

---

## Auto-Correction

### AutoCorrectionEngine

```python
# Access via system
corrector = system.auto_corrector

# Generate correction
correction = await corrector.generate_correction(error, context)

if correction:
    print(f"Strategy: {correction.strategy}")
    print(f"Confidence: {correction.confidence}")

    # Apply correction
    corrected, success = await corrector.apply_correction(content, correction)
```

### Correction Strategies

| Strategy | Description |
|----------|-------------|
| `automatic` | Apply without review |
| `guided` | Apply with confirmation |
| `suggested` | Suggest for manual review |
| `manual` | Requires manual fix |

---

## Exceptions

### Exception Hierarchy

```
HyperEternalError (base)
├── AgentError
│   ├── AgentInitializationError
│   ├── AgentExecutionError
│   ├── AgentNotFoundError
│   └── AgentTimeoutError
├── TaskError
│   ├── TaskNotFoundError
│   ├── TaskTimeoutError
│   ├── TaskValidationError
│   └── TaskDependencyError
├── FlowError
│   ├── FlowNotFoundError
│   ├── FlowExecutionError
│   ├── FlowValidationError
│   └── CyclicDependencyError
├── StateError
│   ├── StateNotFoundError
│   └── StateCorruptionError
├── StorageError
│   ├── StorageConnectionError
│   └── StorageOperationError
├── LLMError
│   ├── LLMConnectionError
│   ├── LLMRateLimitError
│   ├── LLMAuthenticationError
│   └── LLMResponseError
├── QueueError
│   ├── QueueFullError
│   └── QueueEmptyError
└── ReflectionError
    ├── QualityCheckError
    ├── CorrectionError
    └── ConvergenceError
```

### Usage

```python
from hypereternal import (
    HyperEternalError,
    AgentError,
    TaskError,
    FlowError,
)

try:
    result = await system.submit_task(...)
except TaskError as e:
    print(f"Task error: {e}")
except AgentError as e:
    print(f"Agent error: {e}")
except HyperEternalError as e:
    print(f"General error: {e}")
```

---

## Configuration

### SystemConfig

```python
from hypereternal import (
    SystemConfig,
    RuntimeConfig,
    PersistenceConfig,
    MonitoringConfig,
    LLMConfig,
)

config = SystemConfig(
    name="MySystem",
    version="1.0.0",
    runtime=RuntimeConfig(
        max_workers=10,
        task_timeout=3600,
        heartbeat_interval=30,
    ),
    persistence=PersistenceConfig(
        backend="redis",
        url="redis://localhost:6379/0",
        checkpoint_interval=300,
    ),
    monitoring=MonitoringConfig(
        enabled=True,
        metrics_port=9090,
        log_level="INFO",
        log_file="./logs/app.log",
    ),
    llm={
        "openai": LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key="sk-...",
            temperature=0.7,
            max_tokens=4000,
        ),
    },
)
```

---

## Utility Functions

### generate_id()

Generate a unique identifier.

```python
from hypereternal import generate_id

task_id = generate_id()  # UUID string
```

### create_system()

Create and start a system instance.

```python
from hypereternal import create_system

system = await create_system(config_path="./config/config.yaml")
```

---

## Type Definitions

For complete type definitions, see the source code in `src/core/types.py`.
