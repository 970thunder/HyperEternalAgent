"""
Error detection and auto-correction for HyperEternalAgent framework.
"""

import asyncio
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..core.types import ErrorCategory, generate_id
from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class DetectedError:
    """Detected error information."""

    error_id: str = field(default_factory=generate_id)
    category: ErrorCategory = ErrorCategory.RUNTIME
    severity: str = "medium"  # "critical", "high", "medium", "low"
    message: str = ""
    location: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "category": self.category.value,
            "severity": self.severity,
            "message": self.message,
            "location": self.location,
            "stack_trace": self.stack_trace,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "suggestions": self.suggestions,
        }


@dataclass
class Correction:
    """Correction for a detected error."""

    correction_id: str = field(default_factory=generate_id)
    target_error_id: str = ""
    strategy: str = "suggested"  # "automatic", "guided", "suggested", "manual"
    description: str = ""
    fix_code: Optional[str] = None
    confidence: float = 0.0
    requires_review: bool = True
    applied: bool = False
    applied_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "correction_id": self.correction_id,
            "target_error_id": self.target_error_id,
            "strategy": self.strategy,
            "description": self.description,
            "fix_code": self.fix_code,
            "confidence": self.confidence,
            "requires_review": self.requires_review,
            "applied": self.applied,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "metadata": self.metadata,
        }


class ErrorDetector(ABC):
    """Abstract base class for error detectors."""

    @property
    @abstractmethod
    def category(self) -> ErrorCategory:
        """Get the error category this detector handles."""
        pass

    @abstractmethod
    async def detect(
        self,
        content: Any,
        context: Dict[str, Any],
    ) -> List[DetectedError]:
        """
        Detect errors in content.

        Args:
            content: Content to analyze
            context: Detection context

        Returns:
            List of detected errors
        """
        pass


class SyntaxErrorDetector(ErrorDetector):
    """Detector for syntax errors."""

    @property
    def category(self) -> ErrorCategory:
        return ErrorCategory.SYNTAX

    async def detect(
        self,
        content: Any,
        context: Dict[str, Any],
    ) -> List[DetectedError]:
        """Detect syntax errors in code."""
        errors = []

        if not isinstance(content, str):
            return errors

        language = context.get("language", "python")

        if language == "python":
            errors.extend(await self._detect_python_syntax(content))
        elif language == "javascript":
            errors.extend(await self._detect_js_syntax(content))

        return errors

    async def _detect_python_syntax(self, code: str) -> List[DetectedError]:
        """Detect Python syntax errors."""
        errors = []

        try:
            compile(code, "<string>", "exec")
        except SyntaxError as e:
            error = DetectedError(
                category=ErrorCategory.SYNTAX,
                severity="high",
                message=str(e.msg),
                location={"line": e.lineno, "offset": e.offset},
                context={"code": code},
                suggestions=[self._suggest_python_fix(e)],
            )
            errors.append(error)

        return errors

    async def _detect_js_syntax(self, code: str) -> List[DetectedError]:
        """Detect JavaScript syntax errors (basic)."""
        errors = []

        # Basic bracket matching
        brackets = {"(": ")", "[": "]", "{": "}"}
        stack = []

        for i, char in enumerate(code):
            if char in brackets:
                stack.append((char, i))
            elif char in brackets.values():
                if not stack:
                    errors.append(
                        DetectedError(
                            category=ErrorCategory.SYNTAX,
                            severity="high",
                            message=f"Unmatched closing bracket '{char}'",
                            location={"position": i},
                            suggestions=["Add matching opening bracket"],
                        )
                    )
                else:
                    expected = brackets.get(stack[-1][0])
                    if char != expected:
                        errors.append(
                            DetectedError(
                                category=ErrorCategory.SYNTAX,
                                severity="high",
                                message=f"Mismatched brackets: expected '{expected}', got '{char}'",
                                location={"position": i},
                                suggestions=[f"Replace with '{expected}'"],
                            )
                        )
                    else:
                        stack.pop()

        for bracket, pos in stack:
            errors.append(
                DetectedError(
                    category=ErrorCategory.SYNTAX,
                    severity="high",
                    message=f"Unclosed bracket '{bracket}'",
                    location={"position": pos},
                    suggestions=[f"Add closing '{brackets[bracket]}'"],
                )
            )

        return errors

    def _suggest_python_fix(self, error: SyntaxError) -> str:
        """Suggest fix for Python syntax error."""
        msg = str(error.msg).lower()

        if "unexpected eof" in msg:
            return "Check for missing closing brackets or quotes"
        elif "invalid syntax" in msg:
            return "Check for typos or missing operators"
        elif "unindent" in msg:
            return "Check indentation consistency"
        else:
            return f"Review syntax at line {error.lineno}"


class PatternErrorDetector(ErrorDetector):
    """Detector for pattern-based errors."""

    def __init__(self):
        self.patterns: Dict[str, List[Dict[str, Any]]] = {
            "python": [
                {
                    "pattern": r"except\s*:",
                    "message": "Bare except clause",
                    "severity": "medium",
                    "suggestion": "Specify exception type: except Exception:",
                },
                {
                    "pattern": r"print\s*\(",
                    "message": "Print statement in production code",
                    "severity": "low",
                    "suggestion": "Use logging instead of print",
                },
                {
                    "pattern": r"eval\s*\(",
                    "message": "Use of eval() is potentially unsafe",
                    "severity": "high",
                    "suggestion": "Avoid eval() or use safer alternatives",
                },
            ],
        }

    @property
    def category(self) -> ErrorCategory:
        return ErrorCategory.LOGIC

    def add_pattern(
        self,
        language: str,
        pattern: str,
        message: str,
        severity: str = "medium",
        suggestion: str = "",
    ) -> None:
        """Add a pattern to detect."""
        if language not in self.patterns:
            self.patterns[language] = []

        self.patterns[language].append(
            {
                "pattern": pattern,
                "message": message,
                "severity": severity,
                "suggestion": suggestion,
            }
        )

    async def detect(
        self,
        content: Any,
        context: Dict[str, Any],
    ) -> List[DetectedError]:
        """Detect pattern-based errors."""
        errors = []

        if not isinstance(content, str):
            return errors

        language = context.get("language", "python")
        patterns = self.patterns.get(language, [])

        for pattern_info in patterns:
            matches = re.finditer(pattern_info["pattern"], content)

            for match in matches:
                # Calculate line number
                line_num = content[: match.start()].count("\n") + 1

                error = DetectedError(
                    category=ErrorCategory.LOGIC,
                    severity=pattern_info["severity"],
                    message=pattern_info["message"],
                    location={"line": line_num, "match": match.group()},
                    suggestions=[pattern_info["suggestion"]],
                )
                errors.append(error)

        return errors


class ErrorDetectionEngine:
    """
    Engine for detecting errors.

    Features:
    - Multiple detector types
    - Configurable detection rules
    - Error aggregation and deduplication
    """

    def __init__(self):
        self.detectors: List[ErrorDetector] = []
        self._error_cache: Dict[str, DetectedError] = {}

    def register_detector(self, detector: ErrorDetector) -> None:
        """Register an error detector."""
        self.detectors.append(detector)
        logger.info(
            "error_detector_registered",
            category=detector.category.value,
            detector_type=detector.__class__.__name__,
        )

    def unregister_detector(self, detector: ErrorDetector) -> None:
        """Unregister an error detector."""
        if detector in self.detectors:
            self.detectors.remove(detector)

    async def detect(
        self,
        content: Any,
        context: Optional[Dict[str, Any]] = None,
        categories: Optional[List[ErrorCategory]] = None,
    ) -> List[DetectedError]:
        """
        Detect errors in content.

        Args:
            content: Content to analyze
            context: Detection context
            categories: Specific categories to check (all if None)

        Returns:
            List of detected errors
        """
        context = context or {}
        all_errors: List[DetectedError] = []

        for detector in self.detectors:
            if categories and detector.category not in categories:
                continue

            try:
                errors = await detector.detect(content, context)
                all_errors.extend(errors)
            except Exception as e:
                logger.error(
                    "error_detection_failed",
                    detector=detector.__class__.__name__,
                    error=str(e),
                )

        # Deduplicate errors
        unique_errors = self._deduplicate_errors(all_errors)

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        unique_errors.sort(key=lambda e: severity_order.get(e.severity, 4))

        return unique_errors

    def _deduplicate_errors(self, errors: List[DetectedError]) -> List[DetectedError]:
        """Remove duplicate errors."""
        seen = set()
        unique = []

        for error in errors:
            key = (error.category, error.message, str(error.location))
            if key not in seen:
                seen.add(key)
                unique.append(error)

        return unique


# =============================================================================
# Auto-Correction System
# =============================================================================


class CorrectionStrategy(Enum):
    """Correction strategy types."""

    AUTOMATIC = "automatic"
    GUIDED = "guided"
    SUGGESTED = "suggested"
    MANUAL = "manual"


class AutoCorrector(ABC):
    """Abstract base class for auto-correctors."""

    @property
    @abstractmethod
    def supported_categories(self) -> List[ErrorCategory]:
        """Get supported error categories."""
        pass

    @abstractmethod
    async def can_fix(self, error: DetectedError) -> bool:
        """Check if this corrector can fix the error."""
        pass

    @abstractmethod
    async def generate_fix(
        self,
        error: DetectedError,
        context: Dict[str, Any],
    ) -> Correction:
        """Generate a correction for the error."""
        pass

    @abstractmethod
    async def apply_fix(
        self,
        content: Any,
        correction: Correction,
    ) -> Any:
        """Apply the correction to content."""
        pass


class SyntaxCorrector(AutoCorrector):
    """Auto-corrector for syntax errors."""

    @property
    def supported_categories(self) -> List[ErrorCategory]:
        return [ErrorCategory.SYNTAX]

    async def can_fix(self, error: DetectedError) -> bool:
        """Check if error can be auto-fixed."""
        # Simple syntax errors can often be auto-fixed
        if error.category != ErrorCategory.SYNTAX:
            return False

        message = error.message.lower()

        # These can be auto-fixed
        fixable = [
            "missing",
            "unclosed",
            "unmatched",
        ]

        return any(f in message for f in fixable)

    async def generate_fix(
        self,
        error: DetectedError,
        context: Dict[str, Any],
    ) -> Correction:
        """Generate a syntax correction."""
        description = "Manual review required"
        fix_code = None
        confidence = 0.0

        message = error.message.lower()

        if "unclosed" in message or "missing" in message:
            if error.suggestions:
                description = error.suggestions[0]
                confidence = 0.7

        return Correction(
            target_error_id=error.error_id,
            strategy=CorrectionStrategy.SUGGESTED.value,
            description=description,
            fix_code=fix_code,
            confidence=confidence,
            requires_review=True,
        )

    async def apply_fix(
        self,
        content: Any,
        correction: Correction,
    ) -> Any:
        """Apply syntax fix."""
        # For suggested fixes, return original content
        # Actual fix requires human review
        return content


class AutoCorrectionEngine:
    """
    Engine for automatic error correction.

    Features:
    - Multiple corrector types
    - Strategy-based correction
    - Review workflow
    """

    def __init__(self):
        self.correctors: List[AutoCorrector] = []
        self._correction_history: Dict[str, List[Correction]] = {}

    def register_corrector(self, corrector: AutoCorrector) -> None:
        """Register an auto-corrector."""
        self.correctors.append(corrector)
        logger.info(
            "auto_corrector_registered",
            categories=[c.value for c in corrector.supported_categories],
        )

    async def generate_correction(
        self,
        error: DetectedError,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Correction]:
        """
        Generate a correction for an error.

        Args:
            error: Error to correct
            context: Correction context

        Returns:
            Correction or None if no corrector available
        """
        context = context or {}

        for corrector in self.correctors:
            if error.category not in corrector.supported_categories:
                continue

            if await corrector.can_fix(error):
                correction = await corrector.generate_fix(error, context)

                # Record in history
                if error.error_id not in self._correction_history:
                    self._correction_history[error.error_id] = []
                self._correction_history[error.error_id].append(correction)

                return correction

        return None

    async def apply_correction(
        self,
        content: Any,
        correction: Correction,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, bool]:
        """
        Apply a correction to content.

        Args:
            content: Content to correct
            correction: Correction to apply
            context: Application context

        Returns:
            Tuple of (corrected_content, success)
        """
        context = context or {}

        # Find appropriate corrector
        for corrector in self.correctors:
            try:
                corrected = await corrector.apply_fix(content, correction)
                correction.applied = True
                correction.applied_at = datetime.now()

                logger.info(
                    "correction_applied",
                    correction_id=correction.correction_id,
                    strategy=correction.strategy,
                )

                return corrected, True
            except Exception as e:
                logger.error(
                    "correction_apply_failed",
                    correction_id=correction.correction_id,
                    error=str(e),
                )

        return content, False

    def get_correction_history(
        self,
        error_id: str,
    ) -> List[Correction]:
        """Get correction history for an error."""
        return self._correction_history.get(error_id, [])


# =============================================================================
# Feedback Loop
# =============================================================================


@dataclass
class FeedbackLoopResult:
    """Result of a feedback loop iteration."""

    final_content: Any
    iterations: int
    converged: bool
    final_score: float
    corrections_applied: int
    history: List[Dict[str, Any]] = field(default_factory=list)


class FeedbackLoop:
    """
    Feedback loop for iterative improvement.

    Features:
    - Iterative correction
    - Convergence detection
    - Maximum iteration limit
    """

    def __init__(
        self,
        max_iterations: int = 5,
        convergence_threshold: float = 0.95,
        min_improvement: float = 0.01,
    ):
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        self.min_improvement = min_improvement

    async def run(
        self,
        content: Any,
        assess_func: Callable[[Any], float],
        correct_func: Callable[[Any, float], Tuple[Any, List[Correction]]],
    ) -> FeedbackLoopResult:
        """
        Run the feedback loop.

        Args:
            content: Initial content
            assess_func: Function to assess content quality (returns score 0-1)
            correct_func: Function to correct content (returns corrected content and corrections)

        Returns:
            Feedback loop result
        """
        current_content = content
        history: List[Dict[str, Any]] = []
        total_corrections = 0
        converged = False
        prev_score = 0.0

        for iteration in range(self.max_iterations):
            # Assess current content
            score = await assess_func(current_content)

            # Record history
            history.append(
                {
                    "iteration": iteration + 1,
                    "score": score,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # Check convergence
            if score >= self.convergence_threshold:
                converged = True
                break

            # Check improvement
            improvement = score - prev_score
            if iteration > 0 and improvement < self.min_improvement:
                # Not improving enough
                break

            # Apply corrections
            corrected_content, corrections = await correct_func(current_content, score)
            total_corrections += len(corrections)

            current_content = corrected_content
            prev_score = score

        # Final assessment
        final_score = await assess_func(current_content)

        return FeedbackLoopResult(
            final_content=current_content,
            iterations=len(history),
            converged=converged,
            final_score=final_score,
            corrections_applied=total_corrections,
            history=history,
        )
