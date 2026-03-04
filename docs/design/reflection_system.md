# 自省更正机制设计文档

## 1. 概述

自省更正机制（Self-Reflection & Correction Mechanism）是 HyperEternalAgent 框架的核心特性，确保系统输出能够持续优化和改进。本文档详细描述自省层的设计理念、组件结构和实现策略。

## 2. 设计理念

### 2.1 核心原则

```
┌──────────────────────────────────────────────────────────────┐
│                    Self-Reflection Cycle                      │
│                                                               │
│    ┌─────────┐      ┌─────────┐      ┌─────────┐            │
│    │  Work   │ ───▶ │ Evaluate│ ───▶ │ Reflect │            │
│    │ Output  │      │         │      │         │            │
│    └─────────┘      └─────────┘      └────┬────┘            │
│         ▲                                 │                  │
│         │                                 ▼                  │
│    ┌────┴────┐                      ┌─────────┐              │
│    │ Improved│ ◀──── ────────── ─── │ Correct │              │
│    │ Output  │      (if needed)     │         │              │
│    └─────────┘                      └─────────┘              │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

1. **持续评估**：每个输出都经过质量评估
2. **深度反思**：分析问题根因，而非表面修复
3. **渐进改进**：每次迭代都在前一版本基础上优化
4. **收敛保证**：设置最大迭代次数，避免无限循环

### 2.2 自省层次

| 层次 | 描述 | 示例 |
|------|------|------|
| L1 - 格式检查 | 输出格式是否符合要求 | 语法检查、格式验证 |
| L2 - 内容检查 | 输出内容是否正确 | 逻辑验证、事实核查 |
| L3 - 质量评估 | 输出质量是否达标 | 代码质量、文档质量 |
| L4 - 目标对齐 | 输出是否达成目标 | 需求满足度、用户意图 |
| L5 - 创新优化 | 是否有更好的方案 | 创新性、效率优化 |

## 3. 组件架构

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Self-Reflection Layer                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    Quality Assurance Engine                         │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────────┐  │ │
│  │  │   Format     │ │   Content    │ │      Quality Scorer        │  │ │
│  │  │   Checker    │ │   Validator  │ │                            │  │ │
│  │  └──────────────┘ └──────────────┘ └────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      Error Detection Engine                         │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────────┐  │ │
│  │  │   Static     │ │   Runtime    │ │      Anomaly               │  │ │
│  │  │   Analyzer   │ │   Monitor    │ │      Detector              │  │ │
│  │  └──────────────┘ └──────────────┘ └────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                     Auto Correction Engine                          │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────────┐  │ │
│  │  │   Issue      │ │   Fix        │ │      Improvement           │  │ │
│  │  │   Analyzer   │ │   Generator  │ │      Optimizer             │  │ │
│  │  └──────────────┘ └──────────────┘ └────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      Reflection Orchestrator                        │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────────┐  │ │
│  │  │   Feedback   │ │   Iteration  │ │      Convergence           │  │ │
│  │  │   Loop       │ │   Manager    │ │      Checker               │  │ │
│  │  └──────────────┘ └──────────────┘ └────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 4. Quality Assurance Engine

### 4.1 质量评估模型

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime

class QualityDimension(Enum):
    """质量维度"""
    CORRECTNESS = "correctness"       # 正确性
    COMPLETENESS = "completeness"     # 完整性
    CONSISTENCY = "consistency"       # 一致性
    EFFICIENCY = "efficiency"         # 效率性
    READABILITY = "readability"       # 可读性
    MAINTAINABILITY = "maintainability"  # 可维护性
    SECURITY = "security"             # 安全性

@dataclass
class QualityScore:
    """质量评分"""
    dimension: QualityDimension
    score: float  # 0-1
    weight: float = 1.0
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QualityAssessment:
    """质量评估结果"""
    assessment_id: str
    overall_score: float
    dimension_scores: List[QualityScore]
    passed: bool
    issues: List[Dict[str, Any]]
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.now)

class QualityScorer(ABC):
    """质量评分器基类"""

    @abstractmethod
    async def score(self, content: Any, context: Dict[str, Any]) -> QualityScore:
        """评估内容质量"""
        pass

class CompositeQualityScorer:
    """组合质量评分器"""

    def __init__(self):
        self.scorers: Dict[QualityDimension, QualityScorer] = {}
        self.weights: Dict[QualityDimension, float] = {}

    def register_scorer(
        self,
        dimension: QualityDimension,
        scorer: QualityScorer,
        weight: float = 1.0
    ) -> None:
        """注册评分器"""
        self.scorers[dimension] = scorer
        self.weights[dimension] = weight

    async def assess(self, content: Any, context: Dict[str, Any]) -> QualityAssessment:
        """执行全面质量评估"""
        dimension_scores = []

        for dimension, scorer in self.scorers.items():
            score = await scorer.score(content, context)
            score.weight = self.weights.get(dimension, 1.0)
            dimension_scores.append(score)

        # 计算加权总分
        total_weight = sum(s.weight for s in dimension_scores)
        overall_score = sum(s.score * s.weight for s in dimension_scores) / total_weight

        # 收集问题
        issues = self._collect_issues(dimension_scores)

        # 生成建议
        recommendations = self._generate_recommendations(dimension_scores)

        return QualityAssessment(
            assessment_id=self._generate_id(),
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            passed=overall_score >= context.get("threshold", 0.7),
            issues=issues,
            recommendations=recommendations
        )

    def _collect_issues(self, scores: List[QualityScore]) -> List[Dict[str, Any]]:
        """收集问题"""
        issues = []
        for score in scores:
            if score.score < 0.7:
                issues.append({
                    "dimension": score.dimension.value,
                    "score": score.score,
                    "details": score.details
                })
        return issues

    def _generate_recommendations(self, scores: List[QualityScore]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        for score in sorted(scores, key=lambda s: s.score):
            if score.score < 0.8:
                recommendations.append(
                    f"改进 {score.dimension.value}: {score.details.get('suggestion', '需要改进')}"
                )
        return recommendations
```

### 4.2 领域特定评分器

```python
class CodeQualityScorer(QualityScorer):
    """代码质量评分器"""

    def __init__(self):
        self.metrics = {
            "complexity": ComplexityAnalyzer(),
            "duplication": DuplicationDetector(),
            "test_coverage": CoverageAnalyzer(),
            "style": StyleChecker()
        }

    async def score(self, content: str, context: Dict[str, Any]) -> QualityScore:
        """评估代码质量"""
        results = {}

        # 复杂度分析
        complexity = await self.metrics["complexity"].analyze(content)
        results["complexity"] = self._normalize_complexity(complexity)

        # 重复代码检测
        duplication = await self.metrics["duplication"].detect(content)
        results["duplication"] = 1.0 - duplication.ratio

        # 测试覆盖率
        if context.get("test_file"):
            coverage = await self.metrics["test_coverage"].analyze(
                content,
                context["test_file"]
            )
            results["test_coverage"] = coverage.percentage / 100
        else:
            results["test_coverage"] = 0.5  # 默认中等评分

        # 代码风格
        style = await self.metrics["style"].check(content)
        results["style"] = style.compliance_score

        # 综合评分
        overall = sum(results.values()) / len(results)

        return QualityScore(
            dimension=QualityDimension.MAINTAINABILITY,
            score=overall,
            details={
                "metrics": results,
                "suggestion": self._get_improvement_suggestion(results)
            }
        )

class DocumentQualityScorer(QualityScorer):
    """文档质量评分器"""

    async def score(self, content: str, context: Dict[str, Any]) -> QualityScore:
        """评估文档质量"""
        results = {}

        # 结构完整性
        results["structure"] = self._check_structure(content)

        # 语言质量
        results["language"] = await self._check_language_quality(content)

        # 逻辑连贯性
        results["coherence"] = await self._check_coherence(content)

        # 引用完整性
        results["citations"] = self._check_citations(content)

        overall = sum(results.values()) / len(results)

        return QualityScore(
            dimension=QualityDimension.READABILITY,
            score=overall,
            details={"metrics": results}
        )
```

### 4.3 Format Checker

```python
@dataclass
class FormatRule:
    """格式规则"""
    rule_id: str
    rule_type: str  # "regex", "schema", "custom"
    pattern: Optional[str] = None
    schema: Optional[Dict] = None
    validator: Optional[Callable] = None
    error_message: str = ""

class FormatChecker:
    """格式检查器"""

    def __init__(self):
        self.rules: Dict[str, List[FormatRule]] = {}

    def register_rules(self, content_type: str, rules: List[FormatRule]) -> None:
        """注册格式规则"""
        self.rules[content_type] = rules

    async def check(self, content: Any, content_type: str) -> FormatCheckResult:
        """执行格式检查"""
        violations = []

        if content_type not in self.rules:
            return FormatCheckResult(passed=True, violations=[])

        for rule in self.rules[content_type]:
            if not await self._check_rule(content, rule):
                violations.append(Violation(
                    rule_id=rule.rule_id,
                    message=rule.error_message,
                    severity="error"
                ))

        return FormatCheckResult(
            passed=len(violations) == 0,
            violations=violations
        )

    async def _check_rule(self, content: Any, rule: FormatRule) -> bool:
        """检查单条规则"""
        if rule.rule_type == "regex":
            return bool(re.match(rule.pattern, str(content)))
        elif rule.rule_type == "schema":
            return self._validate_schema(content, rule.schema)
        elif rule.rule_type == "custom":
            return await rule.validator(content)
        return True

@dataclass
class Violation:
    """违规项"""
    rule_id: str
    message: str
    severity: str  # "error", "warning", "info"
    location: Optional[Dict[str, int]] = None

@dataclass
class FormatCheckResult:
    """格式检查结果"""
    passed: bool
    violations: List[Violation]
```

## 5. Error Detection Engine

### 5.1 错误类型体系

```python
class ErrorCategory(Enum):
    """错误类别"""
    SYNTAX = "syntax"           # 语法错误
    LOGIC = "logic"             # 逻辑错误
    RUNTIME = "runtime"         # 运行时错误
    RESOURCE = "resource"       # 资源错误
    INTEGRATION = "integration" # 集成错误
    SECURITY = "security"       # 安全错误

@dataclass
class DetectedError:
    """检测到的错误"""
    error_id: str
    category: ErrorCategory
    severity: str  # "critical", "high", "medium", "low"
    message: str
    location: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

class ErrorDetector(ABC):
    """错误检测器基类"""

    @abstractmethod
    async def detect(self, content: Any, context: Dict[str, Any]) -> List[DetectedError]:
        """检测错误"""
        pass
```

### 5.2 Static Analyzer

```python
class StaticAnalyzer(ErrorDetector):
    """静态分析器"""

    def __init__(self):
        self.analyzers: Dict[str, StaticCodeAnalyzer] = {
            "python": PythonAnalyzer(),
            "javascript": JavaScriptAnalyzer(),
            "typescript": TypeScriptAnalyzer()
        }

    async def detect(self, code: str, context: Dict[str, Any]) -> List[DetectedError]:
        """静态代码分析"""
        language = context.get("language", "python")
        analyzer = self.analyzers.get(language)

        if not analyzer:
            return []

        errors = []

        # 语法检查
        syntax_errors = await analyzer.check_syntax(code)
        errors.extend(self._convert_errors(syntax_errors, ErrorCategory.SYNTAX))

        # 类型检查
        type_errors = await analyzer.check_types(code)
        errors.extend(self._convert_errors(type_errors, ErrorCategory.LOGIC))

        # 安全检查
        security_issues = await analyzer.check_security(code)
        errors.extend(self._convert_errors(security_issues, ErrorCategory.SECURITY))

        # 代码规范
        style_issues = await analyzer.check_style(code)
        errors.extend(self._convert_errors(style_issues, ErrorCategory.SYNTAX))

        return errors

    def _convert_errors(
        self,
        raw_errors: List[Dict],
        category: ErrorCategory
    ) -> List[DetectedError]:
        """转换错误格式"""
        return [
            DetectedError(
                error_id=self._generate_id(),
                category=category,
                severity=err.get("severity", "medium"),
                message=err.get("message", ""),
                location=err.get("location")
            )
            for err in raw_errors
        ]
```

### 5.3 Runtime Monitor

```python
class RuntimeMonitor:
    """运行时监控器"""

    def __init__(self):
        self.active_monitors: Dict[str, MonitorSession] = {}
        self.error_handlers: List[ErrorHandler] = []

    async def start_monitoring(
        self,
        execution_id: str,
        process: asyncio.subprocess.Process
    ) -> None:
        """开始监控执行"""
        session = MonitorSession(
            execution_id=execution_id,
            process=process,
            start_time=datetime.now()
        )
        self.active_monitors[execution_id] = session

        # 启动监控任务
        asyncio.create_task(self._monitor_process(session))

    async def _monitor_process(self, session: MonitorSession) -> None:
        """监控进程执行"""
        while session.is_active:
            try:
                # 检查进程状态
                if session.process.returncode is not None:
                    session.is_active = False
                    if session.process.returncode != 0:
                        await self._handle_error(session, "Process exited with error")
                    break

                # 检查超时
                elapsed = (datetime.now() - session.start_time).total_seconds()
                if elapsed > session.timeout:
                    session.process.kill()
                    await self._handle_error(session, "Execution timeout")

                # 检查资源使用
                resources = await self._check_resources(session.process.pid)
                if resources.exceeds_limits:
                    await self._handle_error(session, "Resource limit exceeded")

                await asyncio.sleep(1)

            except Exception as e:
                await self._handle_error(session, str(e))
                break

    async def _handle_error(self, session: MonitorSession, message: str) -> None:
        """处理运行时错误"""
        error = DetectedError(
            error_id=self._generate_id(),
            category=ErrorCategory.RUNTIME,
            severity="high",
            message=message,
            context={"execution_id": session.execution_id}
        )

        for handler in self.error_handlers:
            await handler.handle(error)

@dataclass
class MonitorSession:
    """监控会话"""
    execution_id: str
    process: asyncio.subprocess.Process
    start_time: datetime
    timeout: float = 300.0
    is_active: bool = True
```

### 5.4 Anomaly Detector

```python
class AnomalyDetector:
    """异常检测器 - 基于统计和ML的异常检测"""

    def __init__(self):
        self.baselines: Dict[str, Baseline] = {}
        self.detectors: Dict[str, AnomalyModel] = {}

    async def learn_baseline(
        self,
        metric_name: str,
        historical_data: List[float]
    ) -> None:
        """学习基线"""
        baseline = Baseline(
            mean=np.mean(historical_data),
            std=np.std(historical_data),
            percentiles={
                50: np.percentile(historical_data, 50),
                95: np.percentile(historical_data, 95),
                99: np.percentile(historical_data, 99)
            }
        )
        self.baselines[metric_name] = baseline

    async def detect_anomaly(
        self,
        metric_name: str,
        value: float
    ) -> Optional[Anomaly]:
        """检测异常"""
        if metric_name not in self.baselines:
            return None

        baseline = self.baselines[metric_name]

        # Z-score 检测
        z_score = abs(value - baseline.mean) / baseline.std if baseline.std > 0 else 0

        if z_score > 3.0:  # 3-sigma 规则
            return Anomaly(
                metric_name=metric_name,
                value=value,
                expected_range=(baseline.mean - 3 * baseline.std,
                               baseline.mean + 3 * baseline.std),
                z_score=z_score,
                severity="high" if z_score > 4 else "medium"
            )

        return None

@dataclass
class Baseline:
    """基线数据"""
    mean: float
    std: float
    percentiles: Dict[int, float]

@dataclass
class Anomaly:
    """异常"""
    metric_name: str
    value: float
    expected_range: Tuple[float, float]
    z_score: float
    severity: str
```

## 6. Auto Correction Engine

### 6.1 修复策略

```python
class CorrectionStrategy(Enum):
    """修复策略"""
    AUTOMATIC = "automatic"     # 自动修复
    GUIDED = "guided"           # 引导修复
    SUGGESTED = "suggested"     # 建议修复
    MANUAL = "manual"           # 手动修复

@dataclass
class Correction:
    """修复方案"""
    correction_id: str
    target_error: DetectedError
    strategy: CorrectionStrategy
    fix_description: str
    fix_code: Optional[str] = None
    confidence: float = 0.0
    requires_review: bool = True

class AutoCorrector(ABC):
    """自动修复器基类"""

    @abstractmethod
    async def can_fix(self, error: DetectedError) -> bool:
        """判断是否能修复该错误"""
        pass

    @abstractmethod
    async def generate_fix(self, error: DetectedError, context: Dict[str, Any]) -> Correction:
        """生成修复方案"""
        pass

    @abstractmethod
    async def apply_fix(self, content: Any, correction: Correction) -> Any:
        """应用修复"""
        pass
```

### 6.2 Issue Analyzer

```python
class IssueAnalyzer:
    """问题分析器 - 分析问题根因"""

    async def analyze(
        self,
        errors: List[DetectedError],
        context: Dict[str, Any]
    ) -> IssueAnalysis:
        """分析问题"""
        # 问题分类
        categorized = self._categorize_errors(errors)

        # 根因分析
        root_causes = await self._identify_root_causes(categorized, context)

        # 依赖关系分析
        dependencies = self._analyze_dependencies(errors)

        # 优先级排序
        prioritized = self._prioritize_issues(errors, root_causes)

        return IssueAnalysis(
            total_issues=len(errors),
            by_category=categorized,
            root_causes=root_causes,
            dependencies=dependencies,
            prioritized_issues=prioritized
        )

    def _categorize_errors(
        self,
        errors: List[DetectedError]
    ) -> Dict[ErrorCategory, List[DetectedError]]:
        """错误分类"""
        categorized = {}
        for error in errors:
            if error.category not in categorized:
                categorized[error.category] = []
            categorized[error.category].append(error)
        return categorized

    async def _identify_root_causes(
        self,
        categorized: Dict[ErrorCategory, List[DetectedError]],
        context: Dict[str, Any]
    ) -> List[RootCause]:
        """识别根因"""
        root_causes = []

        # 使用LLM进行深度分析
        for category, errors in categorized.items():
            if len(errors) > 3:  # 同类错误超过3个，可能存在根因
                analysis = await self._analyze_with_llm(errors, context)
                root_causes.append(RootCause(
                    category=category,
                    description=analysis.description,
                    affected_errors=[e.error_id for e in errors],
                    suggested_fix=analysis.suggested_fix
                ))

        return root_causes

@dataclass
class IssueAnalysis:
    """问题分析结果"""
    total_issues: int
    by_category: Dict[ErrorCategory, List[DetectedError]]
    root_causes: List[RootCause]
    dependencies: Dict[str, List[str]]
    prioritized_issues: List[DetectedError]

@dataclass
class RootCause:
    """根因"""
    category: ErrorCategory
    description: str
    affected_errors: List[str]
    suggested_fix: str
```

### 6.3 Fix Generator

```python
class FixGenerator:
    """修复生成器"""

    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.fix_templates = self._load_templates()
        self.correctors: Dict[ErrorCategory, AutoCorrector] = {}

    def register_corrector(self, category: ErrorCategory, corrector: AutoCorrector) -> None:
        """注册修复器"""
        self.correctors[category] = corrector

    async def generate_fix(
        self,
        error: DetectedError,
        content: Any,
        context: Dict[str, Any]
    ) -> Correction:
        """生成修复方案"""
        # 尝试使用注册的修复器
        if error.category in self.correctors:
            corrector = self.correctors[error.category]
            if await corrector.can_fix(error):
                return await corrector.generate_fix(error, context)

        # 使用模板修复
        template_fix = self._try_template_fix(error)
        if template_fix:
            return template_fix

        # 使用LLM生成修复
        return await self._generate_with_llm(error, content, context)

    async def _generate_with_llm(
        self,
        error: DetectedError,
        content: Any,
        context: Dict[str, Any]
    ) -> Correction:
        """使用LLM生成修复"""
        prompt = f"""
        分析以下错误并生成修复方案：

        错误信息：
        - 类别: {error.category.value}
        - 严重性: {error.severity}
        - 消息: {error.message}
        - 位置: {error.location}

        相关代码/内容：
        {content}

        请提供：
        1. 问题分析
        2. 修复方案
        3. 修复后的代码/内容
        4. 置信度 (0-1)
        """

        response = await self.llm_client.generate(prompt)

        # 解析响应
        fix_info = self._parse_llm_response(response)

        return Correction(
            correction_id=self._generate_id(),
            target_error=error,
            strategy=CorrectionStrategy.SUGGESTED,
            fix_description=fix_info["analysis"],
            fix_code=fix_info.get("fixed_code"),
            confidence=fix_info.get("confidence", 0.5),
            requires_review=True
        )
```

### 6.4 Improvement Optimizer

```python
class ImprovementOptimizer:
    """改进优化器 - 持续优化输出"""

    def __init__(self):
        self.optimization_history: Dict[str, List[OptimizationRecord]] = {}
        self.strategies: List[OptimizationStrategy] = []

    async def optimize(
        self,
        content: Any,
        assessment: QualityAssessment,
        context: Dict[str, Any]
    ) -> OptimizationResult:
        """执行优化"""
        content_id = context.get("content_id", "default")

        # 获取历史优化记录
        history = self.optimization_history.get(content_id, [])

        # 选择优化策略
        strategy = self._select_strategy(assessment, history)

        # 执行优化
        optimized_content = await strategy.optimize(content, assessment, context)

        # 记录优化
        record = OptimizationRecord(
            content_id=content_id,
            strategy=strategy.name,
            before_score=assessment.overall_score,
            changes=strategy.get_changes(),
            timestamp=datetime.now()
        )

        if content_id not in self.optimization_history:
            self.optimization_history[content_id] = []
        self.optimization_history[content_id].append(record)

        return OptimizationResult(
            original_content=content,
            optimized_content=optimized_content,
            strategy_used=strategy.name,
            expected_improvement=self._estimate_improvement(strategy, assessment)
        )

    def _select_strategy(
        self,
        assessment: QualityAssessment,
        history: List[OptimizationRecord]
    ) -> OptimizationStrategy:
        """选择优化策略"""
        # 基于评估结果选择策略
        for strategy in self.strategies:
            if strategy.can_apply(assessment):
                # 检查历史，避免重复无效策略
                if not self._is_ineffective(strategy, history):
                    return strategy

        return DefaultOptimizationStrategy()

class OptimizationStrategy(ABC):
    """优化策略基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def can_apply(self, assessment: QualityAssessment) -> bool:
        pass

    @abstractmethod
    async def optimize(
        self,
        content: Any,
        assessment: QualityAssessment,
        context: Dict[str, Any]
    ) -> Any:
        pass

    @abstractmethod
    def get_changes(self) -> List[str]:
        pass
```

## 7. Reflection Orchestrator

### 7.1 反馈循环

```python
class FeedbackLoop:
    """反馈循环 - 管理迭代改进过程"""

    def __init__(
        self,
        max_iterations: int = 5,
        convergence_threshold: float = 0.95,
        min_improvement: float = 0.01
    ):
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        self.min_improvement = min_improvement

    async def run(
        self,
        initial_content: Any,
        worker_agent: IAgent,
        reviewer_agent: IAgent,
        corrector: AutoCorrector,
        context: Dict[str, Any]
    ) -> FeedbackLoopResult:
        """运行反馈循环"""
        current_content = initial_content
        iterations = []
        converged = False

        for i in range(self.max_iterations):
            # 评估当前内容
            assessment = await self._assess(current_content, reviewer_agent, context)

            # 检查是否达标
            if assessment.overall_score >= self.convergence_threshold:
                converged = True
                break

            # 生成改进
            correction = await corrector.generate_fix(
                assessment.issues[0] if assessment.issues else None,
                current_content,
                context
            )

            # 应用改进
            improved_content = await corrector.apply_fix(current_content, correction)

            # 检查改进幅度
            improvement = await self._measure_improvement(
                current_content,
                improved_content,
                reviewer_agent
            )

            iterations.append(IterationRecord(
                iteration=i + 1,
                score=assessment.overall_score,
                improvement=improvement,
                changes=correction.fix_description
            ))

            # 检查收敛
            if improvement < self.min_improvement:
                break

            current_content = improved_content

        return FeedbackLoopResult(
            final_content=current_content,
            iterations=iterations,
            converged=converged,
            total_iterations=len(iterations)
        )

@dataclass
class FeedbackLoopResult:
    """反馈循环结果"""
    final_content: Any
    iterations: List[IterationRecord]
    converged: bool
    total_iterations: int

@dataclass
class IterationRecord:
    """迭代记录"""
    iteration: int
    score: float
    improvement: float
    changes: str
```

### 7.2 Iteration Manager

```python
class IterationManager:
    """迭代管理器"""

    def __init__(self):
        self.active_iterations: Dict[str, IterationContext] = {}
        self.iteration_history: Dict[str, List[IterationRecord]] = {}

    async def start_iteration(
        self,
        task_id: str,
        initial_content: Any
    ) -> str:
        """开始迭代"""
        iteration_id = self._generate_id()

        context = IterationContext(
            iteration_id=iteration_id,
            task_id=task_id,
            current_content=initial_content,
            iteration_count=0,
            status=IterationStatus.RUNNING
        )

        self.active_iterations[iteration_id] = context
        return iteration_id

    async def record_iteration(
        self,
        iteration_id: str,
        content: Any,
        score: float,
        changes: str
    ) -> None:
        """记录迭代"""
        context = self.active_iterations[iteration_id]
        context.iteration_count += 1
        context.current_content = content
        context.last_score = score

        record = IterationRecord(
            iteration=context.iteration_count,
            score=score,
            improvement=score - (context.last_score or 0),
            changes=changes
        )

        if iteration_id not in self.iteration_history:
            self.iteration_history[iteration_id] = []
        self.iteration_history[iteration_id].append(record)

    async def should_continue(self, iteration_id: str) -> bool:
        """判断是否继续迭代"""
        context = self.active_iterations[iteration_id]
        history = self.iteration_history.get(iteration_id, [])

        # 检查迭代次数
        if context.iteration_count >= self.max_iterations:
            return False

        # 检查分数
        if context.last_score >= self.convergence_threshold:
            return False

        # 检查改进幅度
        if len(history) >= 2:
            recent_improvement = history[-1].score - history[-2].score
            if recent_improvement < self.min_improvement:
                return False

        return True

@dataclass
class IterationContext:
    """迭代上下文"""
    iteration_id: str
    task_id: str
    current_content: Any
    iteration_count: int = 0
    last_score: float = 0.0
    status: IterationStatus = IterationStatus.RUNNING

class IterationStatus(Enum):
    RUNNING = "running"
    CONVERGED = "converged"
    MAX_ITERATIONS = "max_iterations"
    FAILED = "failed"
```

### 7.3 Convergence Checker

```python
class ConvergenceChecker:
    """收敛检查器"""

    def __init__(
        self,
        score_threshold: float = 0.95,
        improvement_threshold: float = 0.01,
        stability_window: int = 3
    ):
        self.score_threshold = score_threshold
        self.improvement_threshold = improvement_threshold
        self.stability_window = stability_window

    def check_convergence(self, history: List[IterationRecord]) -> ConvergenceStatus:
        """检查收敛状态"""
        if not history:
            return ConvergenceStatus.NOT_CONVERGED

        latest = history[-1]

        # 检查分数阈值
        if latest.score >= self.score_threshold:
            return ConvergenceStatus.SCURE_CONVERGED

        # 检查改进幅度
        if len(history) >= 2:
            improvement = latest.score - history[-2].score
            if improvement < self.improvement_threshold:
                # 检查稳定性
                if self._is_stable(history):
                    return ConvergenceStatus.PLATEAU_CONVERGED

        # 检查震荡
        if self._is_oscillating(history):
            return ConvergenceStatus.OSCILLATING

        return ConvergenceStatus.NOT_CONVERGED

    def _is_stable(self, history: List[IterationRecord]) -> bool:
        """检查是否稳定"""
        if len(history) < self.stability_window:
            return False

        recent = history[-self.stability_window:]
        variance = np.var([r.score for r in recent])
        return variance < 0.001

    def _is_oscillating(self, history: List[IterationRecord]) -> bool:
        """检查是否震荡"""
        if len(history) < 4:
            return False

        recent = history[-4:]
        signs = [
            1 if recent[i].score > recent[i-1].score else -1
            for i in range(1, len(recent))
        ]
        sign_changes = sum(1 for i in range(1, len(signs)) if signs[i] != signs[i-1])
        return sign_changes >= 2

class ConvergenceStatus(Enum):
    NOT_CONVERGED = "not_converged"
    SCORE_CONVERGED = "score_converged"
    PLATEAU_CONVERGED = "plateau_converged"
    OSCILLATING = "oscillating"
```

## 8. 配置示例

```yaml
# reflection_config.yaml
reflection:
  quality_assurance:
    enabled: true
    dimensions:
      - name: correctness
        weight: 1.0
        threshold: 0.8
      - name: completeness
        weight: 0.8
        threshold: 0.7
      - name: readability
        weight: 0.6
        threshold: 0.7

  error_detection:
    static_analysis:
      enabled: true
      languages: [python, javascript]
    runtime_monitoring:
      enabled: true
      timeout: 300
    anomaly_detection:
      enabled: true
      sensitivity: medium

  auto_correction:
    enabled: true
    strategy: guided  # automatic, guided, suggested, manual
    max_auto_fixes: 3
    require_review: true

  feedback_loop:
    max_iterations: 5
    convergence_threshold: 0.95
    min_improvement: 0.01
    cooldown_seconds: 60
```
