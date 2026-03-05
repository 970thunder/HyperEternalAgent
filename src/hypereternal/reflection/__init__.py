"""
Reflection system for HyperEternalAgent.

This package provides quality assurance, error detection, auto-correction,
and self-evolution capabilities.
"""

from .quality import (
    QualityAssuranceEngine,
    QualityDimension,
    QualityScore,
    QualityAssessment,
)
from .correction import (
    ErrorDetectionEngine,
    AutoCorrectionEngine,
    DetectedError,
    Correction,
    ErrorCategory,
    CorrectionStrategy,
)
from .llm_evaluation import (
    LLMEvaluator,
    LLMEvaluationResult,
    EvaluationCriteria,
    DeepReflector,
    ReflectionInsight,
    IterativeImprovementLoop,
)
from .self_evolution import (
    PerformanceTracker,
    PerformanceMetric,
    StrategyPerformance,
    EvolutionProposal,
    SelfEvolutionEngine,
    AdaptiveLearningSystem,
)

__all__ = [
    # Quality
    "QualityAssuranceEngine",
    "QualityDimension",
    "QualityScore",
    "QualityAssessment",
    # Correction
    "ErrorDetectionEngine",
    "AutoCorrectionEngine",
    "DetectedError",
    "Correction",
    "ErrorCategory",
    "CorrectionStrategy",
    # LLM Evaluation
    "LLMEvaluator",
    "LLMEvaluationResult",
    "EvaluationCriteria",
    "DeepReflector",
    "ReflectionInsight",
    "IterativeImprovementLoop",
    # Self Evolution
    "PerformanceTracker",
    "PerformanceMetric",
    "StrategyPerformance",
    "EvolutionProposal",
    "SelfEvolutionEngine",
    "AdaptiveLearningSystem",
]
