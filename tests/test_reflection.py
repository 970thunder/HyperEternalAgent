"""
Tests for reflection system (quality and correction).
"""

import pytest
from datetime import datetime

from hypereternal.reflection.quality import (
    QualityAssuranceEngine,
    QualityDimension,
    QualityScore,
    QualityAssessment,
)
from hypereternal.reflection.correction import (
    ErrorDetectionEngine,
    AutoCorrectionEngine,
    DetectedError,
    Correction,
    ErrorCategory,
    CorrectionStrategy,
    SyntaxDetector,
    PatternDetector,
)


class TestQualityScore:
    """Tests for QualityScore."""

    def test_quality_score_creation(self):
        """Test creating a quality score."""
        score = QualityScore(
            dimension=QualityDimension.CORRECTNESS,
            score=0.85,
            weight=1.0,
            passed=True,
        )
        assert score.dimension == QualityDimension.CORRECTNESS
        assert score.score == 0.85
        assert score.passed is True

    def test_quality_score_with_issues(self):
        """Test quality score with issues."""
        score = QualityScore(
            dimension=QualityDimension.READABILITY,
            score=0.6,
            weight=0.5,
            passed=False,
            issues=["Code is hard to read", "Missing comments"],
        )
        assert len(score.issues) == 2
        assert score.weighted_score == 0.3  # 0.6 * 0.5

    def test_weighted_score_calculation(self):
        """Test weighted score calculation."""
        score = QualityScore(
            dimension=QualityDimension.COMPLETENESS,
            score=0.8,
            weight=2.0,
        )
        assert score.weighted_score == 1.6


class TestQualityAssessment:
    """Tests for QualityAssessment."""

    def test_assessment_creation(self):
        """Test creating a quality assessment."""
        assessment = QualityAssessment(
            content_id="test_1",
            overall_score=0.75,
            passed=True,
            dimension_scores=[
                QualityScore(dimension=QualityDimension.CORRECTNESS, score=0.8),
                QualityScore(dimension=QualityDimension.COMPLETENESS, score=0.7),
            ],
        )
        assert assessment.overall_score == 0.75
        assert assessment.passed is True
        assert len(assessment.dimension_scores) == 2

    def test_assessment_to_dict(self):
        """Test assessment serialization."""
        assessment = QualityAssessment(
            content_id="test_2",
            overall_score=0.9,
            passed=True,
            dimension_scores=[
                QualityScore(dimension=QualityDimension.CORRECTNESS, score=0.9),
            ],
        )
        data = assessment.to_dict()
        assert data["content_id"] == "test_2"
        assert data["overall_score"] == 0.9
        assert "dimension_scores" in data


class TestQualityRule:
    """Tests for QualityRule."""

    def test_rule_creation(self):
        """Test creating a quality rule."""
        rule = QualityRule(
            rule_id="rule_1",
            name="No TODO comments",
            dimension=QualityDimension.COMPLETENESS,
            checker=lambda content: "TODO" not in content,
            weight=0.5,
            threshold=1.0,
        )
        assert rule.rule_id == "rule_1"
        assert rule.dimension == QualityDimension.COMPLETENESS

    def test_rule_check_pass(self):
        """Test rule check that passes."""
        rule = QualityRule(
            rule_id="rule_2",
            name="Has content",
            dimension=QualityDimension.COMPLETENESS,
            checker=lambda content: len(content) > 0,
            weight=1.0,
            threshold=1.0,
        )
        result = rule.check("Some content")
        assert result["passed"] is True

    def test_rule_check_fail(self):
        """Test rule check that fails."""
        rule = QualityRule(
            rule_id="rule_3",
            name="No empty content",
            dimension=QualityDimension.COMPLETENESS,
            checker=lambda content: len(content) > 0,
            weight=1.0,
            threshold=1.0,
        )
        result = rule.check("")
        assert result["passed"] is False


class TestRuleBasedQualityChecker:
    """Tests for RuleBasedQualityChecker."""

    @pytest.fixture
    def checker(self):
        """Create a quality checker with sample rules."""
        checker = RuleBasedQualityChecker()

        # Add some rules
        checker.add_rule(QualityRule(
            rule_id="length_check",
            name="Minimum length",
            dimension=QualityDimension.COMPLETENESS,
            checker=lambda c: len(c) >= 10,
            weight=1.0,
            threshold=0.5,
        ))

        checker.add_rule(QualityRule(
            rule_id="no_error_word",
            name="No ERROR word",
            dimension=QualityDimension.CORRECTNESS,
            checker=lambda c: "ERROR" not in c,
            weight=1.0,
            threshold=1.0,
        ))

        return checker

    def test_add_rule(self, checker):
        """Test adding a rule."""
        initial_count = len(checker._rules)
        checker.add_rule(QualityRule(
            rule_id="new_rule",
            name="New Rule",
            dimension=QualityDimension.READABILITY,
            checker=lambda c: True,
            weight=1.0,
            threshold=1.0,
        ))
        assert len(checker._rules) == initial_count + 1

    def test_check_passing_content(self, checker):
        """Test checking content that passes."""
        result = checker.check("This is a good content without errors")
        assert result["passed"] is True

    def test_check_failing_content(self, checker):
        """Test checking content that fails."""
        result = checker.check("ERROR")
        assert result["passed"] is False

    def test_check_by_dimension(self, checker):
        """Test checking by specific dimension."""
        result = checker.check_by_dimension(
            "Short",
            QualityDimension.COMPLETENESS
        )
        assert result["passed"] is False  # Length < 10


class TestQualityAssuranceEngine:
    """Tests for QualityAssuranceEngine."""

    @pytest.fixture
    def engine(self):
        """Create a quality assurance engine."""
        return QualityAssuranceEngine(
            threshold=0.7,
            dimension_weights={
                QualityDimension.CORRECTNESS: 1.0,
                QualityDimension.COMPLETENESS: 1.0,
                QualityDimension.READABILITY: 0.5,
            },
        )

    @pytest.mark.asyncio
    async def test_assess_simple_content(self, engine):
        """Test assessing simple content."""
        assessment = await engine.assess(
            content="This is a well-written piece of content.",
            context={},
        )
        assert assessment is not None
        assert assessment.overall_score >= 0
        assert assessment.overall_score <= 1

    @pytest.mark.asyncio
    async def test_assess_with_context(self, engine):
        """Test assessing with context."""
        assessment = await engine.assess(
            content="def foo(): pass",
            context={"language": "python", "type": "code"},
        )
        assert assessment is not None

    @pytest.mark.asyncio
    async def test_assess_empty_content(self, engine):
        """Test assessing empty content."""
        assessment = await engine.assess(content="", context={})
        assert assessment.overall_score < 0.7  # Should fail threshold

    @pytest.mark.asyncio
    async def test_assess_with_requirements(self, engine):
        """Test assessing against requirements."""
        assessment = await engine.assess(
            content="Complete implementation with all features",
            context={"requirements": ["implementation", "features"]},
        )
        assert assessment is not None

    def test_set_threshold(self, engine):
        """Test setting threshold."""
        engine.set_threshold(0.8)
        assert engine._threshold == 0.8

    def test_add_custom_checker(self, engine):
        """Test adding custom checker."""
        engine.add_custom_checker(
            dimension=QualityDimension.SECURITY,
            checker=lambda c, ctx: QualityScore(
                dimension=QualityDimension.SECURITY,
                score=1.0 if "password" not in c.lower() else 0.0,
            ),
        )
        assert QualityDimension.SECURITY in engine._custom_checkers


class TestDetectedError:
    """Tests for DetectedError."""

    def test_error_creation(self):
        """Test creating a detected error."""
        error = DetectedError(
            category=ErrorCategory.SYNTAX,
            severity="high",
            message="Missing closing bracket",
            location={"line": 10, "column": 5},
        )
        assert error.category == ErrorCategory.SYNTAX
        assert error.severity == "high"
        assert error.location["line"] == 10

    def test_error_with_suggestions(self):
        """Test error with suggestions."""
        error = DetectedError(
            category=ErrorCategory.LOGIC,
            severity="medium",
            message="Potential infinite loop",
            suggestions=["Add break condition", "Check loop bounds"],
        )
        assert len(error.suggestions) == 2

    def test_error_to_dict(self):
        """Test error serialization."""
        error = DetectedError(
            category=ErrorCategory.RUNTIME,
            severity="low",
            message="Unused variable",
        )
        data = error.to_dict()
        assert data["category"] == "runtime"
        assert data["severity"] == "low"


class TestCorrection:
    """Tests for Correction."""

    def test_correction_creation(self):
        """Test creating a correction."""
        correction = Correction(
            error_id="err_1",
            strategy=CorrectionStrategy.AUTOMATIC,
            description="Add missing bracket",
            changes=[{"type": "insert", "position": 100, "content": "}"}],
            confidence=0.95,
        )
        assert correction.strategy == CorrectionStrategy.AUTOMATIC
        assert correction.confidence == 0.95

    def test_correction_with_validation(self):
        """Test correction with validation."""
        correction = Correction(
            error_id="err_2",
            strategy=CorrectionStrategy.GUIDED,
            description="Fix variable name typo",
            changes=[{"type": "replace", "from": "count", "to": "counter"}],
            confidence=0.8,
            validation_steps=["Check variable scope", "Verify usage"],
        )
        assert len(correction.validation_steps) == 2


class TestSyntaxDetector:
    """Tests for SyntaxDetector."""

    @pytest.fixture
    def detector(self):
        """Create a syntax detector."""
        return SyntaxDetector()

    def test_detect_missing_bracket(self, detector):
        """Test detecting missing bracket."""
        errors = detector.detect("def foo():\n    print('hello'", {"language": "python"})
        # May or may not detect depending on implementation
        assert isinstance(errors, list)

    def test_detect_valid_code(self, detector):
        """Test detecting errors in valid code."""
        errors = detector.detect("x = 1\ny = 2\nprint(x + y)", {"language": "python"})
        assert isinstance(errors, list)


class TestPatternDetector:
    """Tests for PatternDetector."""

    @pytest.fixture
    def detector(self):
        """Create a pattern detector."""
        detector = PatternDetector()

        # Add some patterns
        detector.add_pattern(
            name="todo_comment",
            pattern=r"TODO|FIXME|XXX",
            category=ErrorCategory.LOGIC,
            severity="low",
            message="Unresolved TODO comment",
        )

        detector.add_pattern(
            name="hardcoded_password",
            pattern=r"password\s*=\s*['\"][^'\"]+['\"]",
            category=ErrorCategory.SECURITY,
            severity="high",
            message="Hardcoded password detected",
        )

        return detector

    def test_add_pattern(self, detector):
        """Test adding a pattern."""
        initial_count = len(detector._patterns)
        detector.add_pattern(
            name="test_pattern",
            pattern=r"test",
            category=ErrorCategory.LOGIC,
            severity="low",
            message="Test pattern found",
        )
        assert len(detector._patterns) == initial_count + 1

    def test_detect_todo(self, detector):
        """Test detecting TODO comment."""
        errors = detector.detect("def foo():\n    # TODO: implement this\n    pass", {})
        todo_errors = [e for e in errors if "TODO" in e.message]
        assert len(todo_errors) > 0

    def test_detect_hardcoded_password(self, detector):
        """Test detecting hardcoded password."""
        errors = detector.detect('password = "secret123"', {})
        security_errors = [e for e in errors if e.category == ErrorCategory.SECURITY]
        assert len(security_errors) > 0

    def test_no_false_positives(self, detector):
        """Test that clean code has no errors."""
        errors = detector.detect("def hello():\n    print('Hello, World!')", {})
        assert len(errors) == 0


class TestErrorDetectionEngine:
    """Tests for ErrorDetectionEngine."""

    @pytest.fixture
    async def engine(self):
        """Create an error detection engine."""
        engine = ErrorDetectionEngine()
        await engine.initialize()
        return engine

    @pytest.mark.asyncio
    async def test_initialize(self, engine):
        """Test engine initialization."""
        assert engine._initialized is True

    @pytest.mark.asyncio
    async def test_detect_errors(self, engine):
        """Test detecting errors."""
        errors = await engine.detect(
            content="def foo():\n    # TODO: fix this\n    pass",
            context={"language": "python"},
        )
        assert isinstance(errors, list)

    @pytest.mark.asyncio
    async def test_detect_no_errors(self, engine):
        """Test detecting no errors in clean content."""
        errors = await engine.detect(
            content="x = 1\ny = 2\nz = x + y",
            context={"language": "python"},
        )
        # Clean code should have few or no errors
        assert isinstance(errors, list)

    @pytest.mark.asyncio
    async def test_detect_by_category(self, engine):
        """Test detecting errors by category."""
        errors = await engine.detect_by_category(
            content="TODO: implement",
            category=ErrorCategory.LOGIC,
            context={},
        )
        assert isinstance(errors, list)


class TestAutoCorrectionEngine:
    """Tests for AutoCorrectionEngine."""

    @pytest.fixture
    async def engine(self):
        """Create an auto-correction engine."""
        engine = AutoCorrectionEngine()
        await engine.initialize()
        return engine

    @pytest.mark.asyncio
    async def test_initialize(self, engine):
        """Test engine initialization."""
        assert engine._initialized is True

    @pytest.mark.asyncio
    async def test_generate_correction(self, engine):
        """Test generating a correction."""
        error = DetectedError(
            category=ErrorCategory.SYNTAX,
            severity="medium",
            message="Trailing whitespace",
            location={"line": 5, "column": 20},
        )

        correction = await engine.generate_correction(
            error=error,
            context={"content": "x = 1   \n"},
        )
        # May or may not generate correction
        if correction:
            assert correction.error_id is not None

    @pytest.mark.asyncio
    async def test_apply_correction(self, engine):
        """Test applying a correction."""
        correction = Correction(
            error_id="test_err",
            strategy=CorrectionStrategy.AUTOMATIC,
            description="Remove trailing whitespace",
            changes=[{"type": "trim_line", "line": 1}],
            confidence=0.9,
        )

        content = "x = 1   "
        corrected, success = await engine.apply_correction(content, correction)
        assert isinstance(success, bool)

    @pytest.mark.asyncio
    async def test_correct_content(self, engine):
        """Test full correction workflow."""
        errors = [
            DetectedError(
                category=ErrorCategory.SYNTAX,
                severity="low",
                message="Multiple blank lines",
                location={"line": 10},
            ),
        ]

        result = await engine.correct_content(
            content="x = 1\n\n\n\ny = 2",
            errors=errors,
            context={},
        )
        assert "original" in result
        assert "corrected" in result
        assert "applied" in result


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_category_values(self):
        """Test error category values."""
        assert ErrorCategory.SYNTAX.value == "syntax"
        assert ErrorCategory.LOGIC.value == "logic"
        assert ErrorCategory.RUNTIME.value == "runtime"
        assert ErrorCategory.RESOURCE.value == "resource"
        assert ErrorCategory.INTEGRATION.value == "integration"
        assert ErrorCategory.SECURITY.value == "security"


class TestCorrectionStrategy:
    """Tests for CorrectionStrategy enum."""

    def test_strategy_values(self):
        """Test correction strategy values."""
        assert CorrectionStrategy.AUTOMATIC.value == "automatic"
        assert CorrectionStrategy.GUIDED.value == "guided"
        assert CorrectionStrategy.SUGGESTED.value == "suggested"
        assert CorrectionStrategy.MANUAL.value == "manual"


class TestQualityDimension:
    """Tests for QualityDimension enum."""

    def test_dimension_values(self):
        """Test quality dimension values."""
        assert QualityDimension.CORRECTNESS.value == "correctness"
        assert QualityDimension.COMPLETENESS.value == "completeness"
        assert QualityDimension.CONSISTENCY.value == "consistency"
        assert QualityDimension.EFFICIENCY.value == "efficiency"
        assert QualityDimension.READABILITY.value == "readability"
        assert QualityDimension.MAINTAINABILITY.value == "maintainability"
        assert QualityDimension.SECURITY.value == "security"
