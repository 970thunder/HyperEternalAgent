"""
Self-evolution system for continuous improvement.

This module provides mechanisms for the system to analyze its own behavior,
learn from feedback, and evolve its strategies over time.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict

from ..core.types import Task, TaskResult
from ..infrastructure.logging import get_logger
from .quality import QualityDimension, QualityAssessment
from .correction import DetectedError, Correction, ErrorCategory
from .llm_evaluation import LLMEvaluator, DeepReflector, ReflectionInsight

logger = get_logger(__name__)


@dataclass
class PerformanceMetric:
    """A tracked performance metric."""
    name: str
    values: List[float] = field(default_factory=list)
    timestamps: List[datetime] = field(default_factory=list)
    target: float = 0.8
    weight: float = 1.0

    def add_value(self, value: float) -> None:
        """Add a new measurement."""
        self.values.append(value)
        self.timestamps.append(datetime.now())

    def get_average(self, window: Optional[int] = None) -> float:
        """Get average value."""
        if not self.values:
            return 0.0
        values = self.values[-window:] if window else self.values
        return sum(values) / len(values)

    def get_trend(self) -> str:
        """Get trend direction."""
        if len(self.values) < 3:
            return "insufficient_data"

        recent = self.get_average(window=3)
        earlier = self.get_average(window=len(self.values) - 3) if len(self.values) > 3 else self.get_average()

        if recent > earlier + 0.05:
            return "improving"
        elif recent < earlier - 0.05:
            return "declining"
        return "stable"

    def is_on_target(self) -> bool:
        """Check if metric is meeting target."""
        return self.get_average() >= self.target


@dataclass
class StrategyPerformance:
    """Performance tracking for a strategy."""
    strategy_id: str
    strategy_type: str
    success_count: int = 0
    failure_count: int = 0
    total_executions: int = 0
    avg_execution_time: float = 0.0
    quality_scores: List[float] = field(default_factory=list)
    last_used: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.success_count / self.total_executions

    def record_execution(self, success: bool, quality: float = 0.0, execution_time: float = 0.0) -> None:
        """Record an execution."""
        self.total_executions += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        if quality > 0:
            self.quality_scores.append(quality)

        if execution_time > 0:
            # Rolling average
            self.avg_execution_time = (
                (self.avg_execution_time * (self.total_executions - 1) + execution_time)
                / self.total_executions
            )

        self.last_used = datetime.now()

    def get_effectiveness_score(self) -> float:
        """Calculate overall effectiveness score."""
        if self.total_executions == 0:
            return 0.0

        # Weight success rate, quality, and recency
        success_weight = 0.4
        quality_weight = 0.4
        recency_weight = 0.2

        # Quality score
        avg_quality = sum(self.quality_scores) / len(self.quality_scores) if self.quality_scores else 0.5

        # Recency score (decay over time)
        if self.last_used:
            hours_since = (datetime.now() - self.last_used).total_seconds() / 3600
            recency_score = max(0, 1 - (hours_since / 168))  # Decay over a week
        else:
            recency_score = 0

        return (
            success_weight * self.success_rate +
            quality_weight * avg_quality +
            recency_weight * recency_score
        )


@dataclass
class EvolutionProposal:
    """A proposed evolution/change to the system."""
    proposal_id: str
    description: str
    rationale: str
    expected_impact: str
    risk_level: str  # "low", "medium", "high"
    affected_components: List[str]
    implementation_steps: List[str]
    rollback_plan: str
    status: str = "proposed"  # "proposed", "testing", "adopted", "rejected"
    created_at: datetime = field(default_factory=datetime.now)
    test_results: Optional[Dict[str, Any]] = None


class PerformanceTracker:
    """Tracks and analyzes system performance."""

    def __init__(self):
        self.metrics: Dict[str, PerformanceMetric] = {}
        self.strategy_performance: Dict[str, StrategyPerformance] = {}
        self._event_log: List[Dict[str, Any]] = []

        # Initialize default metrics
        self._init_default_metrics()

    def _init_default_metrics(self) -> None:
        """Initialize default performance metrics."""
        default_metrics = [
            ("task_success_rate", 0.9, 1.0),
            ("code_quality_score", 0.75, 1.0),
            ("execution_efficiency", 0.7, 0.8),
            ("error_resolution_rate", 0.85, 1.0),
            ("user_satisfaction", 0.8, 0.9),
            ("iteration_convergence", 0.7, 0.8),
        ]

        for name, target, weight in default_metrics:
            self.metrics[name] = PerformanceMetric(
                name=name,
                target=target,
                weight=weight,
            )

    def record_metric(self, metric_name: str, value: float) -> None:
        """Record a metric value."""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = PerformanceMetric(name=metric_name)

        self.metrics[metric_name].add_value(value)

        logger.debug(
            "metric_recorded",
            metric=metric_name,
            value=value,
            average=self.metrics[metric_name].get_average(),
        )

    def record_strategy_execution(
        self,
        strategy_id: str,
        strategy_type: str,
        success: bool,
        quality: float = 0.0,
        execution_time: float = 0.0,
    ) -> None:
        """Record a strategy execution."""
        if strategy_id not in self.strategy_performance:
            self.strategy_performance[strategy_id] = StrategyPerformance(
                strategy_id=strategy_id,
                strategy_type=strategy_type,
            )

        self.strategy_performance[strategy_id].record_execution(success, quality, execution_time)

    def log_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log a system event."""
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "details": details,
        }
        self._event_log.append(event)

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        metric_summaries = {}
        for name, metric in self.metrics.items():
            metric_summaries[name] = {
                "average": metric.get_average(),
                "trend": metric.get_trend(),
                "on_target": metric.is_on_target(),
                "target": metric.target,
            }

        strategy_summaries = {}
        for strategy_id, perf in self.strategy_performance.items():
            strategy_summaries[strategy_id] = {
                "success_rate": perf.success_rate,
                "effectiveness": perf.get_effectiveness_score(),
                "total_executions": perf.total_executions,
            }

        return {
            "metrics": metric_summaries,
            "strategies": strategy_summaries,
            "event_count": len(self._event_log),
            "overall_health": self._calculate_health_score(),
        }

    def _calculate_health_score(self) -> float:
        """Calculate overall system health score."""
        if not self.metrics:
            return 0.5

        total_weight = 0
        weighted_score = 0

        for metric in self.metrics.values():
            if metric.values:
                avg = metric.get_average()
                weighted_score += avg * metric.weight
                total_weight += metric.weight

        return weighted_score / total_weight if total_weight > 0 else 0.5

    def identify_weak_areas(self) -> List[Dict[str, Any]]:
        """Identify areas needing improvement."""
        weak_areas = []

        for name, metric in self.metrics.items():
            if not metric.is_on_target() or metric.get_trend() == "declining":
                weak_areas.append({
                    "area": name,
                    "current_value": metric.get_average(),
                    "target": metric.target,
                    "gap": metric.target - metric.get_average(),
                    "trend": metric.get_trend(),
                })

        # Sort by gap (largest first)
        weak_areas.sort(key=lambda x: x["gap"], reverse=True)

        return weak_areas

    def get_best_strategies(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top performing strategies."""
        strategies = [
            {
                "strategy_id": s.strategy_id,
                "strategy_type": s.strategy_type,
                "effectiveness": s.get_effectiveness_score(),
                "success_rate": s.success_rate,
            }
            for s in self.strategy_performance.values()
            if s.total_executions >= 3  # Minimum data points
        ]

        strategies.sort(key=lambda x: x["effectiveness"], reverse=True)

        return strategies[:limit]


class SelfEvolutionEngine:
    """
    Engine for system self-evolution and continuous improvement.

    This engine analyzes performance data, identifies improvement opportunities,
    proposes and tests changes, and evolves the system over time.
    """

    def __init__(
        self,
        performance_tracker: Optional[PerformanceTracker] = None,
        llm_evaluator: Optional[LLMEvaluator] = None,
        auto_apply_low_risk: bool = False,
    ):
        self.performance_tracker = performance_tracker or PerformanceTracker()
        self.llm_evaluator = llm_evaluator
        self.auto_apply_low_risk = auto_apply_low_risk

        self.proposals: Dict[str, EvolutionProposal] = {}
        self.applied_changes: List[Dict[str, Any]] = []
        self._evolution_history: List[Dict[str, Any]] = []

    async def analyze_and_propose(self) -> List[EvolutionProposal]:
        """
        Analyze current performance and propose improvements.

        Returns:
            List of new evolution proposals
        """
        # Identify weak areas
        weak_areas = self.performance_tracker.identify_weak_areas()

        # Get strategy insights
        best_strategies = self.performance_tracker.get_best_strategies()

        # Generate proposals
        proposals = []

        for area in weak_areas:
            proposal = await self._generate_proposal(area, best_strategies)
            if proposal:
                proposals.append(proposal)
                self.proposals[proposal.proposal_id] = proposal

        logger.info(
            "evolution_proposals_generated",
            count=len(proposals),
            areas_addressed=[p.affected_components for p in proposals],
        )

        return proposals

    async def _generate_proposal(
        self,
        weak_area: Dict[str, Any],
        best_strategies: List[Dict[str, Any]],
    ) -> Optional[EvolutionProposal]:
        """Generate an evolution proposal for a weak area."""
        area_name = weak_area["area"]
        gap = weak_area["gap"]

        # Skip if gap is too small
        if gap < 0.05:
            return None

        # Generate proposal based on area
        proposal_templates = {
            "task_success_rate": self._propose_success_improvement,
            "code_quality_score": self._propose_quality_improvement,
            "execution_efficiency": self._propose_efficiency_improvement,
            "error_resolution_rate": self._propose_error_improvement,
        }

        generator = proposal_templates.get(area_name, self._propose_generic_improvement)
        proposal = await generator(weak_area, best_strategies)

        return proposal

    async def _propose_success_improvement(
        self,
        area: Dict[str, Any],
        best_strategies: List[Dict[str, Any]],
    ) -> EvolutionProposal:
        """Propose improvement for task success rate."""
        return EvolutionProposal(
            proposal_id=f"prop_{datetime.now().strftime('%Y%m%d_%H%M%S')}_success",
            description="Enhance task validation and pre-execution checks",
            rationale=f"Current success rate ({area['current_value']:.2f}) below target ({area['target']:.2f})",
            expected_impact="Increase task success rate by 10-15%",
            risk_level="low",
            affected_components=["task_executor", "validator"],
            implementation_steps=[
                "Add pre-flight validation for common failure modes",
                "Implement circuit breaker pattern for external calls",
                "Add retry with exponential backoff",
                "Enhance error categorization",
            ],
            rollback_plan="Revert to previous validation logic",
        )

    async def _propose_quality_improvement(
        self,
        area: Dict[str, Any],
        best_strategies: List[Dict[str, Any]],
    ) -> EvolutionProposal:
        """Propose improvement for code quality."""
        return EvolutionProposal(
            proposal_id=f"prop_{datetime.now().strftime('%Y%m%d_%H%M%S')}_quality",
            description="Strengthen quality assurance pipeline",
            rationale=f"Quality score ({area['current_value']:.2f}) needs improvement",
            expected_impact="Improve code quality scores by 15-20%",
            risk_level="medium",
            affected_components=["quality_engine", "reviewer_agent"],
            implementation_steps=[
                "Add additional quality dimensions",
                "Implement stricter linting rules",
                "Add automated test coverage requirements",
                "Integrate security scanning",
            ],
            rollback_plan="Disable new quality checks",
        )

    async def _propose_efficiency_improvement(
        self,
        area: Dict[str, Any],
        best_strategies: List[Dict[str, Any]],
    ) -> EvolutionProposal:
        """Propose improvement for execution efficiency."""
        return EvolutionProposal(
            proposal_id=f"prop_{datetime.now().strftime('%Y%m%d_%H%M%S')}_efficiency",
            description="Optimize execution pipeline",
            rationale=f"Efficiency ({area['current_value']:.2f}) below target",
            expected_impact="Reduce execution time by 20-30%",
            risk_level="medium",
            affected_components=["task_router", "agent_pool"],
            implementation_steps=[
                "Implement task batching",
                "Add caching layer for repeated operations",
                "Optimize agent selection algorithm",
                "Parallelize independent operations",
            ],
            rollback_plan="Revert to sequential execution",
        )

    async def _propose_error_improvement(
        self,
        area: Dict[str, Any],
        best_strategies: List[Dict[str, Any]],
    ) -> EvolutionProposal:
        """Propose improvement for error resolution."""
        return EvolutionProposal(
            proposal_id=f"prop_{datetime.now().strftime('%Y%m%d_%H%M%S')}_error",
            description="Enhance error detection and correction",
            rationale=f"Error resolution rate ({area['current_value']:.2f}) needs improvement",
            expected_impact="Increase error resolution by 25%",
            risk_level="low",
            affected_components=["error_detector", "auto_corrector"],
            implementation_steps=[
                "Add more error patterns to detector",
                "Improve error categorization",
                "Add context-aware correction strategies",
                "Implement learning from corrections",
            ],
            rollback_plan="Revert to previous error handling",
        )

    async def _propose_generic_improvement(
        self,
        area: Dict[str, Any],
        best_strategies: List[Dict[str, Any]],
    ) -> EvolutionProposal:
        """Propose generic improvement."""
        return EvolutionProposal(
            proposal_id=f"prop_{datetime.now().strftime('%Y%m%d_%H%M%S')}_generic",
            description=f"Improve {area['area']}",
            rationale=f"Performance gap of {area['gap']:.2f}",
            expected_impact="Close performance gap",
            risk_level="medium",
            affected_components=["system"],
            implementation_steps=[
                "Analyze root cause",
                "Implement targeted fix",
                "Monitor results",
            ],
            rollback_plan="Revert changes",
        )

    async def test_proposal(self, proposal_id: str) -> Dict[str, Any]:
        """
        Test an evolution proposal in a controlled manner.

        Args:
            proposal_id: ID of the proposal to test

        Returns:
            Test results
        """
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return {"error": "Proposal not found"}

        proposal.status = "testing"

        # Simulate testing (in real implementation, would run A/B tests)
        test_results = {
            "proposal_id": proposal_id,
            "tested_at": datetime.now().isoformat(),
            "metrics_before": self.performance_tracker.get_performance_summary(),
            "simulated_improvement": self._simulate_improvement(proposal),
            "recommendation": "adopt" if proposal.risk_level == "low" else "review",
        }

        proposal.test_results = test_results

        logger.info(
            "proposal_tested",
            proposal_id=proposal_id,
            recommendation=test_results["recommendation"],
        )

        return test_results

    def _simulate_improvement(self, proposal: EvolutionProposal) -> Dict[str, float]:
        """Simulate expected improvement from a proposal."""
        # Simple heuristic based on proposal characteristics
        base_improvement = {
            "low": 0.10,
            "medium": 0.15,
            "high": 0.25,
        }

        improvement_factor = base_improvement.get(proposal.risk_level, 0.10)

        return {
            "expected_improvement": improvement_factor,
            "confidence": 0.7 if proposal.risk_level == "low" else 0.5,
        }

    async def apply_proposal(self, proposal_id: str) -> Dict[str, Any]:
        """
        Apply an evolution proposal.

        Args:
            proposal_id: ID of the proposal to apply

        Returns:
            Application result
        """
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return {"error": "Proposal not found"}

        if proposal.status not in ["proposed", "testing"]:
            return {"error": f"Cannot apply proposal in status: {proposal.status}"}

        # Record the change
        change_record = {
            "proposal_id": proposal_id,
            "description": proposal.description,
            "applied_at": datetime.now().isoformat(),
            "affected_components": proposal.affected_components,
            "implementation_steps": proposal.implementation_steps,
        }

        self.applied_changes.append(change_record)
        proposal.status = "adopted"

        # Log event
        self.performance_tracker.log_event(
            "evolution_applied",
            {"proposal_id": proposal_id, "description": proposal.description},
        )

        logger.info(
            "evolution_proposal_applied",
            proposal_id=proposal_id,
            components=proposal.affected_components,
        )

        return {
            "status": "applied",
            "proposal_id": proposal_id,
            "change_record": change_record,
        }

    async def rollback_proposal(self, proposal_id: str) -> Dict[str, Any]:
        """
        Rollback an applied proposal.

        Args:
            proposal_id: ID of the proposal to rollback

        Returns:
            Rollback result
        """
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return {"error": "Proposal not found"}

        if proposal.status != "adopted":
            return {"error": "Can only rollback adopted proposals"}

        # Execute rollback plan
        rollback_result = {
            "proposal_id": proposal_id,
            "rolled_back_at": datetime.now().isoformat(),
            "rollback_plan": proposal.rollback_plan,
        }

        proposal.status = "rejected"

        # Log event
        self.performance_tracker.log_event(
            "evolution_rolled_back",
            {"proposal_id": proposal_id, "reason": "Manual rollback"},
        )

        logger.info(
            "evolution_proposal_rolled_back",
            proposal_id=proposal_id,
        )

        return rollback_result

    def get_evolution_report(self) -> Dict[str, Any]:
        """Get comprehensive evolution report."""
        return {
            "performance_summary": self.performance_tracker.get_performance_summary(),
            "weak_areas": self.performance_tracker.identify_weak_areas(),
            "best_strategies": self.performance_tracker.get_best_strategies(),
            "proposals": {
                "total": len(self.proposals),
                "by_status": {
                    status: len([p for p in self.proposals.values() if p.status == status])
                    for status in ["proposed", "testing", "adopted", "rejected"]
                },
            },
            "applied_changes_count": len(self.applied_changes),
            "recent_changes": self.applied_changes[-5:] if self.applied_changes else [],
        }

    async def run_evolution_cycle(self) -> Dict[str, Any]:
        """
        Run a complete evolution cycle.

        This analyzes performance, generates proposals, tests them,
        and applies approved changes.

        Returns:
            Evolution cycle results
        """
        cycle_start = datetime.now()

        # Step 1: Analyze and propose
        proposals = await self.analyze_and_propose()

        # Step 2: Test proposals
        test_results = []
        for proposal in proposals:
            if proposal.risk_level == "low" or self.auto_apply_low_risk:
                result = await self.test_proposal(proposal.proposal_id)
                test_results.append(result)

        # Step 3: Apply approved proposals
        applied = []
        for proposal in proposals:
            if proposal.test_results and proposal.test_results.get("recommendation") == "adopt":
                if proposal.risk_level == "low" or not self.auto_apply_low_risk:
                    result = await self.apply_proposal(proposal.proposal_id)
                    if "error" not in result:
                        applied.append(result)

        cycle_result = {
            "cycle_started": cycle_start.isoformat(),
            "cycle_completed": datetime.now().isoformat(),
            "proposals_generated": len(proposals),
            "proposals_tested": len(test_results),
            "proposals_applied": len(applied),
            "applied_changes": applied,
        }

        self._evolution_history.append(cycle_result)

        logger.info(
            "evolution_cycle_complete",
            proposals=len(proposals),
            tested=len(test_results),
            applied=len(applied),
        )

        return cycle_result


class AdaptiveLearningSystem:
    """
    System for adaptive learning from feedback and experience.

    This system learns patterns from successful and failed operations
    and adapts its behavior accordingly.
    """

    def __init__(self):
        self._success_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._failure_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._learned_rules: Dict[str, Dict[str, Any]] = {}
        self._adaptation_history: List[Dict[str, Any]] = []

    def record_success(
        self,
        operation_type: str,
        context: Dict[str, Any],
        outcome: Dict[str, Any],
    ) -> None:
        """Record a successful operation."""
        pattern = {
            "context": context,
            "outcome": outcome,
            "timestamp": datetime.now().isoformat(),
        }
        self._success_patterns[operation_type].append(pattern)

        # Analyze for new rules
        self._analyze_patterns(operation_type)

    def record_failure(
        self,
        operation_type: str,
        context: Dict[str, Any],
        error: str,
    ) -> None:
        """Record a failed operation."""
        pattern = {
            "context": context,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }
        self._failure_patterns[operation_type].append(pattern)

        # Analyze for new rules
        self._analyze_patterns(operation_type)

    def _analyze_patterns(self, operation_type: str) -> None:
        """Analyze patterns to derive rules."""
        successes = self._success_patterns[operation_type]
        failures = self._failure_patterns[operation_type]

        if len(successes) < 3 or len(failures) < 2:
            return

        # Find common context in failures
        failure_contexts = [p["context"] for p in failures[-10:]]
        success_contexts = [p["context"] for p in successes[-10:]]

        # Simple rule extraction (in real system, would use ML)
        rules = {}

        # Check for common failure conditions
        for key in set(k for ctx in failure_contexts for k in ctx.keys()):
            failure_values = [ctx.get(key) for ctx in failure_contexts if key in ctx]
            success_values = [ctx.get(key) for ctx in success_contexts if key in ctx]

            if failure_values and success_values:
                # If certain values appear more in failures
                failure_set = set(str(v) for v in failure_values if v is not None)
                success_set = set(str(v) for v in success_values if v is not None)

                problematic = failure_set - success_set
                if problematic:
                    rules[f"avoid_{key}"] = {
                        "values_to_avoid": list(problematic),
                        "confidence": min(0.9, len(failure_values) / 10),
                    }

        if rules:
            self._learned_rules[operation_type] = rules
            self._adaptation_history.append({
                "operation_type": operation_type,
                "rules_added": list(rules.keys()),
                "timestamp": datetime.now().isoformat(),
            })

    def get_recommendations(self, operation_type: str, context: Dict[str, Any]) -> List[str]:
        """Get recommendations based on learned patterns."""
        recommendations = []

        rules = self._learned_rules.get(operation_type, {})
        for rule_name, rule_data in rules.items():
            if rule_name.startswith("avoid_"):
                key = rule_name[6:]  # Remove "avoid_" prefix
                current_value = str(context.get(key, ""))
                if current_value in rule_data.get("values_to_avoid", []):
                    recommendations.append(
                        f"Consider avoiding {key}={current_value} based on past failures"
                    )

        return recommendations

    def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of learned patterns."""
        return {
            "operation_types_tracked": len(set(list(self._success_patterns.keys()) + list(self._failure_patterns.keys()))),
            "total_successes": sum(len(v) for v in self._success_patterns.values()),
            "total_failures": sum(len(v) for v in self._failure_patterns.values()),
            "learned_rules_count": sum(len(rules) for rules in self._learned_rules.values()),
            "recent_adaptations": len(self._adaptation_history[-10:]),
        }
