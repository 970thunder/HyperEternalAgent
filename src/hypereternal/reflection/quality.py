"""
Quality assurance engine for HyperEternalAgent framework.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..core.types import QualityDimension, generate_id
from ..infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class QualityScore:
    """Score for a quality dimension."""

    dimension: QualityDimension
    score: float  # 0.0 to 1.0
    weight: float = 1.0
    details: Dict[str, Any] = field(default_factory=dict)
    passed: bool = True
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "score": self.score,
            "weight": self.weight,
            "details": self.details,
            "passed": self.passed,
            "issues": self.issues,
        }


@dataclass
class QualityAssessment:
    """Complete quality assessment result."""

    assessment_id: str = field(default_factory=generate_id)
    overall_score: float = 0.0
    dimension_scores: List[QualityScore] = field(default_factory=list)
    passed: bool = False
    issues: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "overall_score": self.overall_score,
            "dimension_scores": [s.to_dict() for s in self.dimension_scores],
            "passed": self.passed,
            "issues": self.issues,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class QualityScorer(ABC):
    """Abstract base class for quality scorers."""

    @property
    @abstractmethod
    def dimension(self) -> QualityDimension:
        """Get the quality dimension this scorer evaluates."""
        pass

    @abstractmethod
    async def score(
        self,
        content: Any,
        context: Dict[str, Any],
    ) -> QualityScore:
        """
        Score content quality.

        Args:
            content: Content to evaluate
            context: Evaluation context

        Returns:
            Quality score
        """
        pass


class QualityAssuranceEngine:
    """
    Engine for quality assessment.

    Features:
    - Multi-dimensional quality scoring
    - Configurable thresholds
    - Issue detection and recommendations
    """

    def __init__(self):
        self.scorers: Dict[QualityDimension, QualityScorer] = {}
        self.weights: Dict[QualityDimension, float] = {}
        self.thresholds: Dict[QualityDimension, float] = {}

    def register_scorer(
        self,
        scorer: QualityScorer,
        weight: float = 1.0,
        threshold: float = 0.7,
    ) -> None:
        """Register a quality scorer."""
        dimension = scorer.dimension
        self.scorers[dimension] = scorer
        self.weights[dimension] = weight
        self.thresholds[dimension] = threshold

        logger.info(
            "quality_scorer_registered",
            dimension=dimension.value,
            weight=weight,
            threshold=threshold,
        )

    def unregister_scorer(self, dimension: QualityDimension) -> None:
        """Unregister a quality scorer."""
        self.scorers.pop(dimension, None)
        self.weights.pop(dimension, None)
        self.thresholds.pop(dimension, None)

    async def assess(
        self,
        content: Any,
        context: Optional[Dict[str, Any]] = None,
        dimensions: Optional[List[QualityDimension]] = None,
    ) -> QualityAssessment:
        """
        Perform quality assessment.

        Args:
            content: Content to assess
            context: Assessment context
            dimensions: Specific dimensions to assess (all if None)

        Returns:
            Quality assessment result
        """
        context = context or {}
        dimensions = dimensions or list(self.scorers.keys())

        dimension_scores: List[QualityScore] = []
        issues: List[Dict[str, Any]] = []
        recommendations: List[str] = []

        # Score each dimension
        for dimension in dimensions:
            scorer = self.scorers.get(dimension)
            if not scorer:
                continue

            try:
                score = await scorer.score(content, context)
                score.weight = self.weights.get(dimension, 1.0)
                score.passed = score.score >= self.thresholds.get(dimension, 0.7)
                dimension_scores.append(score)

                if not score.passed:
                    issues.append(
                        {
                            "dimension": dimension.value,
                            "score": score.score,
                            "threshold": self.thresholds.get(dimension, 0.7),
                            "details": score.issues,
                        }
                    )
                    recommendations.extend(score.issues)

            except Exception as e:
                logger.error(
                    "quality_scoring_error",
                    dimension=dimension.value,
                    error=str(e),
                )

        # Calculate overall score
        if dimension_scores:
            total_weight = sum(s.weight for s in dimension_scores)
            overall_score = sum(s.score * s.weight for s in dimension_scores) / total_weight
        else:
            overall_score = 0.0

        # Determine if passed
        passed = len(issues) == 0 and overall_score >= context.get("threshold", 0.7)

        return QualityAssessment(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            passed=passed,
            issues=issues,
            recommendations=recommendations,
            metadata={"content_type": context.get("content_type", "unknown")},
        )


# =============================================================================
# Built-in Quality Scorers
# =============================================================================


class FormatQualityScorer(QualityScorer):
    """Scorer for format/structure quality."""

    @property
    def dimension(self) -> QualityDimension:
        return QualityDimension.CONSISTENCY

    async def score(
        self,
        content: Any,
        context: Dict[str, Any],
    ) -> QualityScore:
        """Score format quality."""
        issues = []
        score = 1.0

        content_type = context.get("content_type", "text")

        if content_type == "code":
            # Check code format
            if isinstance(content, str):
                # Basic checks
                if not content.strip():
                    score = 0.0
                    issues.append("Empty content")

                # Check for common format issues
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if len(line) > 120:
                        issues.append(f"Line {i+1} exceeds 120 characters")

                if issues:
                    score = max(0.0, 1.0 - len(issues) * 0.1)

        elif content_type == "text":
            # Check text format
            if isinstance(content, str):
                if not content.strip():
                    score = 0.0
                    issues.append("Empty content")
                elif len(content) < 10:
                    score = 0.5
                    issues.append("Content too short")

        return QualityScore(
            dimension=self.dimension,
            score=score,
            issues=issues,
            details={"content_type": content_type},
        )


class CompletenessQualityScorer(QualityScorer):
    """Scorer for completeness quality."""

    @property
    def dimension(self) -> QualityDimension:
        return QualityDimension.COMPLETENESS

    async def score(
        self,
        content: Any,
        context: Dict[str, Any],
    ) -> QualityScore:
        """Score completeness quality."""
        issues = []
        score = 1.0

        required_elements = context.get("required_elements", [])

        if required_elements:
            missing = []
            content_str = str(content) if not isinstance(content, str) else content

            for element in required_elements:
                if element not in content_str:
                    missing.append(element)

            if missing:
                score = 1.0 - (len(missing) / len(required_elements))
                issues = [f"Missing: {elem}" for elem in missing]

        return QualityScore(
            dimension=self.dimension,
            score=score,
            issues=issues,
            details={"required_elements": required_elements},
        )


class ReadabilityQualityScorer(QualityScorer):
    """Scorer for readability quality."""

    @property
    def dimension(self) -> QualityDimension:
        return QualityDimension.READABILITY

    async def score(
        self,
        content: Any,
        context: Dict[str, Any],
    ) -> QualityScore:
        """Score readability quality."""
        issues = []
        score = 1.0

        if isinstance(content, str):
            # Simple readability checks
            words = content.split()
            sentences = content.split(".")
            sentences = [s for s in sentences if s.strip()]

            if words and sentences:
                # Average words per sentence
                avg_words = len(words) / len(sentences)

                if avg_words > 25:
                    issues.append("Sentences are too long on average")
                    score -= 0.2

                if avg_words < 5:
                    issues.append("Sentences are too short on average")
                    score -= 0.1

            # Check for very long paragraphs
            paragraphs = content.split("\n\n")
            for i, para in enumerate(paragraphs):
                if len(para.split()) > 200:
                    issues.append(f"Paragraph {i+1} is too long")
                    score -= 0.1

        score = max(0.0, min(1.0, score))

        return QualityScore(
            dimension=self.dimension,
            score=score,
            issues=issues,
        )


class CorrectnessQualityScorer(QualityScorer):
    """Scorer for correctness quality."""

    @property
    def dimension(self) -> QualityDimension:
        return QualityDimension.CORRECTNESS

    def __init__(self, validators: Optional[List[Callable]] = None):
        self.validators = validators or []

    def add_validator(self, validator: Callable) -> None:
        """Add a validation function."""
        self.validators.append(validator)

    async def score(
        self,
        content: Any,
        context: Dict[str, Any],
    ) -> QualityScore:
        """Score correctness quality."""
        issues = []
        score = 1.0

        for validator in self.validators:
            try:
                result = validator(content)
                if not result.get("valid", True):
                    issues.append(result.get("message", "Validation failed"))
                    score -= 0.2
            except Exception as e:
                issues.append(f"Validator error: {str(e)}")
                score -= 0.1

        score = max(0.0, score)

        return QualityScore(
            dimension=self.dimension,
            score=score,
            issues=issues,
        )
