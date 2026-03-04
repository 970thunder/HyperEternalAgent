# Agent 系统设计文档

## 1. 概述

Agent系统是HyperEternalAgent框架的核心组件，负责执行各类智能任务。本文档详细描述Agent的设计理念、类型定义、生命周期管理以及通信机制。

## 2. Agent 基础模型

### 2.1 Agent 抽象基类

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class AgentState(Enum):
    """Agent状态枚举"""
    IDLE = "idle"                    # 空闲
    INITIALIZING = "initializing"    # 初始化中
    RUNNING = "running"              # 运行中
    PAUSED = "paused"                # 暂停
    ERROR = "error"                  # 错误
    TERMINATED = "terminated"        # 已终止

@dataclass
class AgentContext:
    """Agent运行上下文"""
    agent_id: str
    session_id: str
    created_at: datetime
    metadata: Dict[str, Any]
    state: AgentState

@dataclass
class Task:
    """任务定义"""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: int = 0
    timeout: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = None

@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    success: bool
    output: Any
    metrics: Dict[str, Any]
    errors: List[str]
    completed_at: datetime

class BaseAgent(ABC):
    """Agent抽象基类"""

    def __init__(self, agent_id: str, config: Dict[str, Any]):
        self.agent_id = agent_id
        self.config = config
        self.context: Optional[AgentContext] = None
        self.state = AgentState.IDLE

    @abstractmethod
    async def initialize(self) -> None:
        """初始化Agent"""
        pass

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """执行任务"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """关闭Agent"""
        pass

    async def pause(self) -> None:
        """暂停Agent"""
        self.state = AgentState.PAUSED

    async def resume(self) -> None:
        """恢复Agent"""
        if self.state == AgentState.PAUSED:
            self.state = AgentState.RUNNING

    def get_capabilities(self) -> List[str]:
        """获取Agent能力列表"""
        return []
```

### 2.2 Agent 接口设计

```python
from typing import Protocol

class IAgent(Protocol):
    """Agent接口协议"""

    @property
    def agent_id(self) -> str: ...

    @property
    def state(self) -> AgentState: ...

    async def initialize(self) -> None: ...

    async def execute(self, task: Task) -> TaskResult: ...

    async def shutdown(self) -> None: ...

    def get_capabilities(self) -> List[str]: ...

class IAgentFactory(Protocol):
    """Agent工厂接口"""

    def create_agent(self, agent_type: str, config: Dict[str, Any]) -> IAgent: ...

    def destroy_agent(self, agent_id: str) -> None: ...
```

## 3. Agent 类型定义

### 3.1 类型层次结构

```
BaseAgent (抽象基类)
│
├── WorkerAgent (执行型Agent)
│   ├── CodeWriterAgent      # 代码编写
│   ├── CodeReviewerAgent    # 代码审核
│   ├── ResearchAgent        # 研究分析
│   └── WriterAgent          # 内容写作
│
├── ReviewerAgent (审核型Agent)
│   ├── QualityReviewerAgent # 质量审核
│   ├── SecurityReviewerAgent # 安全审核
│   └── StyleReviewerAgent   # 风格审核
│
├── PlannerAgent (规划型Agent)
│   ├── TaskPlannerAgent     # 任务规划
│   ├── ResourcePlannerAgent # 资源规划
│   └── SchedulePlannerAgent # 调度规划
│
├── CriticAgent (评估型Agent)
│   ├── PerformanceCriticAgent # 性能评估
│   ├── QualityCriticAgent     # 质量评估
│   └── CostCriticAgent        # 成本评估
│
└── CoordinatorAgent (协调型Agent)
    ├── MasterAgent          # 主控Agent
    └── SupervisorAgent      # 监督Agent
```

### 3.2 WorkerAgent 设计

```python
class WorkerAgent(BaseAgent):
    """
    执行型Agent基类

    职责：执行具体的工作任务，如代码编写、文档撰写等
    """

    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, config)
        self.llm_client = None  # LLM客户端
        self.tools: List[Tool] = []  # 可用工具列表

    async def initialize(self) -> None:
        """初始化Worker Agent"""
        self.state = AgentState.INITIALIZING

        # 初始化LLM客户端
        self.llm_client = await self._init_llm_client()

        # 加载工具
        self.tools = await self._load_tools()

        self.state = AgentState.IDLE

    async def execute(self, task: Task) -> TaskResult:
        """执行任务"""
        self.state = AgentState.RUNNING

        try:
            # 1. 解析任务
            parsed_input = await self._parse_task(task)

            # 2. 构建提示
            prompt = await self._build_prompt(parsed_input)

            # 3. 调用LLM
            response = await self._call_llm(prompt)

            # 4. 处理输出
            output = await self._process_output(response)

            # 5. 返回结果
            return TaskResult(
                task_id=task.task_id,
                success=True,
                output=output,
                metrics=self._collect_metrics(),
                errors=[],
                completed_at=datetime.now()
            )

        except Exception as e:
            self.state = AgentState.ERROR
            return TaskResult(
                task_id=task.task_id,
                success=False,
                output=None,
                metrics={},
                errors=[str(e)],
                completed_at=datetime.now()
            )

        finally:
            if self.state != AgentState.ERROR:
                self.state = AgentState.IDLE

    @abstractmethod
    async def _parse_task(self, task: Task) -> Dict[str, Any]:
        """解析任务输入"""
        pass

    @abstractmethod
    async def _build_prompt(self, parsed_input: Dict[str, Any]) -> str:
        """构建LLM提示"""
        pass

    async def _call_llm(self, prompt: str) -> str:
        """调用LLM"""
        return await self.llm_client.generate(prompt)

    @abstractmethod
    async def _process_output(self, response: str) -> Any:
        """处理LLM输出"""
        pass
```

### 3.3 ReviewerAgent 设计

```python
@dataclass
class ReviewResult:
    """审核结果"""
    passed: bool
    score: float  # 0-1
    issues: List[Dict[str, Any]]
    suggestions: List[str]
    details: Dict[str, Any]

class ReviewerAgent(BaseAgent):
    """
    审核型Agent基类

    职责：审核其他Agent的输出质量
    """

    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, config)
        self.criteria: List[ReviewCriteria] = []

    async def initialize(self) -> None:
        """初始化审核标准"""
        self.criteria = await self._load_criteria()

    async def execute(self, task: Task) -> TaskResult:
        """执行审核任务"""
        # 获取待审核的内容
        content = task.payload.get("content")
        content_type = task.payload.get("content_type")

        # 执行审核
        review_result = await self._review(content, content_type)

        return TaskResult(
            task_id=task.task_id,
            success=True,
            output=review_result,
            metrics={"score": review_result.score},
            errors=[],
            completed_at=datetime.now()
        )

    @abstractmethod
    async def _review(self, content: Any, content_type: str) -> ReviewResult:
        """执行审核逻辑"""
        pass

    async def _load_criteria(self) -> List[ReviewCriteria]:
        """加载审核标准"""
        return []
```

### 3.4 PlannerAgent 设计

```python
@dataclass
class Plan:
    """计划定义"""
    plan_id: str
    goal: str
    steps: List[PlanStep]
    dependencies: Dict[str, List[str]]
    estimated_duration: int
    created_at: datetime

@dataclass
class PlanStep:
    """计划步骤"""
    step_id: str
    description: str
    agent_type: str
    input_requirements: Dict[str, Any]
    expected_output: Dict[str, Any]
    priority: int

class PlannerAgent(BaseAgent):
    """
    规划型Agent基类

    职责：将复杂目标分解为可执行的步骤
    """

    async def execute(self, task: Task) -> TaskResult:
        """执行规划任务"""
        goal = task.payload.get("goal")
        constraints = task.payload.get("constraints", {})

        # 生成计划
        plan = await self._create_plan(goal, constraints)

        # 优化计划
        optimized_plan = await self._optimize_plan(plan)

        return TaskResult(
            task_id=task.task_id,
            success=True,
            output=optimized_plan,
            metrics={"step_count": len(optimized_plan.steps)},
            errors=[],
            completed_at=datetime.now()
        )

    @abstractmethod
    async def _create_plan(self, goal: str, constraints: Dict) -> Plan:
        """创建执行计划"""
        pass

    async def _optimize_plan(self, plan: Plan) -> Plan:
        """优化执行计划"""
        # 默认实现：按优先级排序
        plan.steps.sort(key=lambda s: s.priority, reverse=True)
        return plan
```

### 3.5 CriticAgent 设计

```python
@dataclass
class Critique:
    """评估结果"""
    critique_id: str
    overall_score: float
    dimensions: Dict[str, float]
    feedback: List[str]
    improvement_suggestions: List[str]
    should_retry: bool

class CriticAgent(BaseAgent):
    """
    评估型Agent基类

    职责：评估整体输出质量，提供改进建议
    """

    async def execute(self, task: Task) -> TaskResult:
        """执行评估任务"""
        work_output = task.payload.get("work_output")
        original_task = task.payload.get("original_task")

        # 多维度评估
        critique = await self._critique(work_output, original_task)

        return TaskResult(
            task_id=task.task_id,
            success=True,
            output=critique,
            metrics={"overall_score": critique.overall_score},
            errors=[],
            completed_at=datetime.now()
        )

    @abstractmethod
    async def _critique(self, work_output: Any, original_task: Dict) -> Critique:
        """执行评估逻辑"""
        pass
```

## 4. Agent 生命周期管理

### 4.1 生命周期状态机

```
          ┌─────────────────────────────────────────┐
          │                                         │
          ▼                                         │
    ┌──────────┐                              ┌──────────┐
    │  IDLE    │◀─────────────────────────────│ RUNNING  │
    └────┬─────┘                              └────┬─────┘
         │                                         │
         │ initialize()                       pause│
         │                                         │
         ▼                                         ▼
    ┌──────────────┐                        ┌──────────┐
    │ INITIALIZING │                        │  PAUSED  │
    └──────────────┘                        └────┬─────┘
                                                │ resume()
                                                │
                                                ▼
                                           ┌──────────┐
                                           │ RUNNING  │
                                           └──────────┘
                                                │
                                                │ error
                                                ▼
                                           ┌──────────┐
                                           │  ERROR   │
                                           └────┬─────┘
                                                │
                                                │ shutdown()
                                                ▼
                                           ┌───────────┐
                                           │TERMINATED │
                                           └───────────┘
```

### 4.2 Agent Manager

```python
class AgentManager:
    """Agent生命周期管理器"""

    def __init__(self):
        self.agents: Dict[str, IAgent] = {}
        self.agent_registry: Dict[str, Type[BaseAgent]] = {}
        self.agent_pools: Dict[str, AgentPool] = {}

    def register_agent_type(self, agent_type: str, agent_class: Type[BaseAgent]) -> None:
        """注册Agent类型"""
        self.agent_registry[agent_type] = agent_class

    async def create_agent(
        self,
        agent_type: str,
        agent_id: str,
        config: Dict[str, Any]
    ) -> IAgent:
        """创建Agent实例"""
        if agent_type not in self.agent_registry:
            raise ValueError(f"Unknown agent type: {agent_type}")

        agent_class = self.agent_registry[agent_type]
        agent = agent_class(agent_id, config)

        await agent.initialize()
        self.agents[agent_id] = agent

        return agent

    async def destroy_agent(self, agent_id: str) -> None:
        """销毁Agent实例"""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            await agent.shutdown()
            del self.agents[agent_id]

    async def get_agent(self, agent_id: str) -> Optional[IAgent]:
        """获取Agent实例"""
        return self.agents.get(agent_id)

    async def get_agents_by_state(self, state: AgentState) -> List[IAgent]:
        """获取指定状态的Agent列表"""
        return [a for a in self.agents.values() if a.state == state]

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "total_agents": len(self.agents),
            "by_state": {
                state.value: len([a for a in self.agents.values() if a.state == state])
                for state in AgentState
            }
        }
```

### 4.3 Agent Pool

```python
class AgentPool:
    """Agent池，用于管理同类型Agent的多个实例"""

    def __init__(
        self,
        agent_type: str,
        min_size: int = 1,
        max_size: int = 10,
        auto_scale: bool = True
    ):
        self.agent_type = agent_type
        self.min_size = min_size
        self.max_size = max_size
        self.auto_scale = auto_scale
        self.agents: List[IAgent] = []
        self.available: asyncio.Queue[IAgent] = asyncio.Queue()

    async def initialize(self, agent_manager: AgentManager) -> None:
        """初始化Agent池"""
        for i in range(self.min_size):
            agent = await agent_manager.create_agent(
                self.agent_type,
                f"{self.agent_type}_{i}",
                {}
            )
            self.agents.append(agent)
            await self.available.put(agent)

    async def acquire(self, timeout: float = 30.0) -> IAgent:
        """获取一个可用的Agent"""
        try:
            agent = await asyncio.wait_for(
                self.available.get(),
                timeout=timeout
            )
            return agent
        except asyncio.TimeoutError:
            if self.auto_scale and len(self.agents) < self.max_size:
                # 自动扩展
                new_agent = await self._create_new_agent()
                return new_agent
            raise

    async def release(self, agent: IAgent) -> None:
        """释放Agent回池"""
        await self.available.put(agent)

    async def scale(self, target_size: int) -> None:
        """扩展/收缩池大小"""
        current_size = len(self.agents)
        if target_size > current_size:
            # 扩展
            for _ in range(target_size - current_size):
                agent = await self._create_new_agent()
                self.agents.append(agent)
        elif target_size < current_size:
            # 收缩
            for _ in range(current_size - target_size):
                agent = self.agents.pop()
                await agent.shutdown()
```

## 5. Agent 通信机制

### 5.1 消息定义

```python
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime

class MessageType(Enum):
    """消息类型"""
    TASK_ASSIGNMENT = "task_assignment"    # 任务分配
    TASK_RESULT = "task_result"            # 任务结果
    STATUS_UPDATE = "status_update"        # 状态更新
    QUERY = "query"                        # 查询
    RESPONSE = "response"                  # 响应
    BROADCAST = "broadcast"                # 广播
    ERROR = "error"                        # 错误

@dataclass
class AgentMessage:
    """Agent消息"""
    message_id: str
    message_type: MessageType
    sender_id: str
    receiver_id: Optional[str]  # None表示广播
    payload: Dict[str, Any]
    timestamp: datetime
    correlation_id: Optional[str] = None  # 关联消息ID
    priority: int = 0
    ttl: Optional[int] = None  # 消息过期时间(秒)
```

### 5.2 消息总线

```python
class MessageBus:
    """Agent间消息总线"""

    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.message_queue: asyncio.Queue[AgentMessage] = asyncio.Queue()
        self.running = False

    async def start(self) -> None:
        """启动消息总线"""
        self.running = True
        asyncio.create_task(self._process_messages())

    async def stop(self) -> None:
        """停止消息总线"""
        self.running = False

    async def publish(self, message: AgentMessage) -> None:
        """发布消息"""
        await self.message_queue.put(message)

    def subscribe(
        self,
        agent_id: str,
        callback: Callable[[AgentMessage], None]
    ) -> None:
        """订阅消息"""
        if agent_id not in self.subscribers:
            self.subscribers[agent_id] = []
        self.subscribers[agent_id].append(callback)

    def unsubscribe(self, agent_id: str) -> None:
        """取消订阅"""
        self.subscribers.pop(agent_id, None)

    async def _process_messages(self) -> None:
        """处理消息队列"""
        while self.running:
            try:
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )
                await self._deliver_message(message)
            except asyncio.TimeoutError:
                continue

    async def _deliver_message(self, message: AgentMessage) -> None:
        """投递消息"""
        if message.receiver_id:
            # 点对点消息
            callbacks = self.subscribers.get(message.receiver_id, [])
            for callback in callbacks:
                await callback(message)
        else:
            # 广播消息
            for callbacks in self.subscribers.values():
                for callback in callbacks:
                    await callback(message)
```

### 5.3 共享工作空间

```python
class SharedWorkspace:
    """Agent共享工作空间"""

    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        self.data: Dict[str, Any] = {}
        self.version = 0
        self.history: List[Dict[str, Any]] = []
        self.lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """获取数据"""
        return self.data.get(key)

    async def set(self, key: str, value: Any, agent_id: str) -> None:
        """设置数据"""
        async with self.lock:
            old_value = self.data.get(key)
            self.data[key] = value
            self.version += 1
            self.history.append({
                "version": self.version,
                "key": key,
                "old_value": old_value,
                "new_value": value,
                "agent_id": agent_id,
                "timestamp": datetime.now()
            })

    async def get_history(self, key: str) -> List[Dict[str, Any]]:
        """获取数据变更历史"""
        return [h for h in self.history if h["key"] == key]

    async def snapshot(self) -> Dict[str, Any]:
        """创建快照"""
        return {
            "workspace_id": self.workspace_id,
            "data": self.data.copy(),
            "version": self.version,
            "timestamp": datetime.now().isoformat()
        }
```

## 6. 错误处理与恢复

### 6.1 错误类型定义

```python
class AgentError(Exception):
    """Agent基础异常"""
    pass

class InitializationError(AgentError):
    """初始化错误"""
    pass

class ExecutionError(AgentError):
    """执行错误"""
    pass

class TimeoutError(AgentError):
    """超时错误"""
    pass

class ResourceExhaustedError(AgentError):
    """资源耗尽错误"""
    pass

class LLMError(AgentError):
    """LLM调用错误"""
    pass
```

### 6.2 错误处理策略

```python
class ErrorHandler:
    """错误处理器"""

    def __init__(self):
        self.strategies: Dict[Type[Exception], ErrorStrategy] = {}

    def register_strategy(
        self,
        error_type: Type[Exception],
        strategy: ErrorStrategy
    ) -> None:
        """注册错误处理策略"""
        self.strategies[error_type] = strategy

    async def handle(self, error: Exception, context: Dict[str, Any]) -> ErrorAction:
        """处理错误"""
        for error_type, strategy in self.strategies.items():
            if isinstance(error, error_type):
                return await strategy.handle(error, context)

        # 默认策略
        return ErrorAction.RAISE

class ErrorStrategy(ABC):
    """错误处理策略"""

    @abstractmethod
    async def handle(self, error: Exception, context: Dict[str, Any]) -> ErrorAction:
        pass

class RetryStrategy(ErrorStrategy):
    """重试策略"""

    def __init__(self, max_retries: int = 3, backoff: float = 1.0):
        self.max_retries = max_retries
        self.backoff = backoff

    async def handle(self, error: Exception, context: Dict[str, Any]) -> ErrorAction:
        retry_count = context.get("retry_count", 0)
        if retry_count < self.max_retries:
            await asyncio.sleep(self.backoff * (2 ** retry_count))
            return ErrorAction.RETRY
        return ErrorAction.RAISE

class ErrorAction(Enum):
    """错误处理动作"""
    RETRY = "retry"          # 重试
    SKIP = "skip"            # 跳过
    RAISE = "raise"          # 抛出异常
    FALLBACK = "fallback"    # 降级处理
    TERMINATE = "terminate"  # 终止
```

## 7. 配置管理

### 7.1 Agent 配置模式

```yaml
# agent_config.yaml
agent:
  id: "code_writer_001"
  type: "CodeWriterAgent"

  llm:
    provider: "openai"
    model: "gpt-4"
    temperature: 0.7
    max_tokens: 4000

  tools:
    - name: "file_reader"
      enabled: true
    - name: "code_executor"
      enabled: true
      config:
        timeout: 60
        sandbox: true

  limits:
    max_concurrent_tasks: 5
    task_timeout: 300
    daily_token_limit: 1000000

  persistence:
    checkpoint_interval: 60
    state_storage: "redis"

  logging:
    level: "INFO"
    format: "json"
```

### 7.2 配置加载器

```python
class AgentConfigLoader:
    """Agent配置加载器"""

    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.configs: Dict[str, Dict[str, Any]] = {}

    async def load(self, agent_id: str) -> Dict[str, Any]:
        """加载Agent配置"""
        config_path = os.path.join(self.config_dir, f"{agent_id}.yaml")

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config not found: {config_path}")

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # 验证配置
        self._validate_config(config)

        self.configs[agent_id] = config
        return config

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """验证配置格式"""
        required_fields = ["agent", "llm"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")
```

## 8. 监控与可观测性

### 8.1 Agent 指标

```python
@dataclass
class AgentMetrics:
    """Agent指标"""
    agent_id: str

    # 任务指标
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_in_progress: int = 0
    avg_task_duration: float = 0.0

    # LLM指标
    total_tokens_used: int = 0
    total_llm_calls: int = 0
    avg_llm_latency: float = 0.0

    # 错误指标
    error_count: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None

    # 资源指标
    memory_usage: float = 0.0
    cpu_usage: float = 0.0

    # 时间戳
    uptime: float = 0.0
    last_heartbeat: datetime = None
```

### 8.2 Metrics Collector

```python
class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self.metrics: Dict[str, AgentMetrics] = {}
        self.exporters: List[MetricsExporter] = []

    def record_task_completion(
        self,
        agent_id: str,
        duration: float,
        success: bool
    ) -> None:
        """记录任务完成"""
        metrics = self._get_or_create_metrics(agent_id)

        if success:
            metrics.tasks_completed += 1
        else:
            metrics.tasks_failed += 1

        # 更新平均时长
        total = metrics.tasks_completed + metrics.tasks_failed
        metrics.avg_task_duration = (
            (metrics.avg_task_duration * (total - 1) + duration) / total
        )

    def record_llm_call(
        self,
        agent_id: str,
        tokens: int,
        latency: float
    ) -> None:
        """记录LLM调用"""
        metrics = self._get_or_create_metrics(agent_id)
        metrics.total_tokens_used += tokens
        metrics.total_llm_calls += 1

        # 更新平均延迟
        metrics.avg_llm_latency = (
            (metrics.avg_llm_latency * (metrics.total_llm_calls - 1) + latency)
            / metrics.total_llm_calls
        )

    async def export(self) -> None:
        """导出指标"""
        for exporter in self.exporters:
            await exporter.export(self.metrics)
```
