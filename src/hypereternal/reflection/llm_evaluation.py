"""
LLM-based evaluation for the reflection system.

This module provides advanced evaluation capabilities using LLM integration
for deeper analysis and more nuanced quality assessment.
"""

import asyncio
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..core.types import Task, TaskResult
from ..infrastructure.llm_client import LLMClientWrapper as LLMClient
from ..core.config import LLMConfig
from ..infrastructure.logging import get_logger
from .quality import QualityDimension, QualityScore, QualityAssessment

logger = get_logger(__name__)


@dataclass
class EvaluationCriteria:
    """Criteria for LLM-based evaluation."""
    name: str
    description: str
    weight: float = 1.0
    scale_min: float = 0.0
    scale_max: float = 1.0
    passing_threshold: float = 0.7


@dataclass
class LLMEvaluationResult:
    """Result from LLM evaluation."""
    content_id: str
    overall_score: float
    criteria_scores: Dict[str, float]
    reasoning: str
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]
    passed: bool
    confidence: float
    evaluated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content_id": self.content_id,
            "overall_score": self.overall_score,
            "criteria_scores": self.criteria_scores,
            "reasoning": self.reasoning,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "suggestions": self.suggestions,
            "passed": self.passed,
            "confidence": self.confidence,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


class LLMEvaluator:
    """
    LLM-based evaluator for content quality assessment.

    Uses language models to provide nuanced, context-aware evaluation
    of generated content.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        model: str = "gpt-4",
        temperature: float = 0.3,
    ):
        self.llm_client = llm_client
        self.model = model
        self.temperature = temperature
        self._initialized = False

        # Default evaluation criteria
        self.criteria: Dict[str, EvaluationCriteria] = {
            "correctness": EvaluationCriteria(
                name="Correctness",
                description="Accuracy and correctness of the content",
                weight=1.5,
                passing_threshold=0.8,
            ),
            "completeness": EvaluationCriteria(
                name="Completeness",
                description="Coverage of required topics and requirements",
                weight=1.2,
                passing_threshold=0.7,
            ),
            "clarity": EvaluationCriteria(
                name="Clarity",
                description="Clear and understandable presentation",
                weight=1.0,
                passing_threshold=0.6,
            ),
            "coherence": EvaluationCriteria(
                name="Coherence",
                description="Logical flow and consistency",
                weight=1.0,
                passing_threshold=0.7,
            ),
            "relevance": EvaluationCriteria(
                name="Relevance",
                description="Relevance to the specified context and goals",
                weight=1.3,
                passing_threshold=0.7,
            ),
        }

    async def initialize(self) -> None:
        """Initialize the evaluator."""
        if self.llm_client is None:
            config = LLMConfig(
                provider="openai",
                model=self.model,
                temperature=self.temperature,
            )
            self.llm_client = LLMClient(config)

        await self.llm_client.connect()
        self._initialized = True
        logger.info("llm_evaluator_initialized", model=self.model)

    async def evaluate(
        self,
        content: str,
        context: Dict[str, Any],
        criteria: Optional[List[str]] = None,
    ) -> LLMEvaluationResult:
        """
        Evaluate content using LLM.

        Args:
            content: Content to evaluate
            context: Evaluation context (requirements, goals, etc.)
            criteria: Specific criteria to evaluate (optional)

        Returns:
            LLMEvaluationResult with detailed assessment
        """
        if not self._initialized:
            await self.initialize()

        # Determine criteria to use
        eval_criteria = criteria or list(self.criteria.keys())
        criteria_descriptions = [
            f"- {self.criteria[c].name}: {self.criteria[c].description} (weight: {self.criteria[c].weight})"
            for c in eval_criteria
            if c in self.criteria
        ]

        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(content, context, criteria_descriptions)

        try:
            # Get LLM response
            response = await self.llm_client.generate(prompt)

            # Parse response
            result = self._parse_evaluation_response(
                response.content,
                content_id=context.get("content_id", "unknown"),
                criteria=eval_criteria,
            )

            logger.info(
                "llm_evaluation_complete",
                content_id=result.content_id,
                score=result.overall_score,
                passed=result.passed,
            )

            return result

        except Exception as e:
            logger.error("llm_evaluation_failed", error=str(e))
            # Return a failed evaluation
            return LLMEvaluationResult(
                content_id=context.get("content_id", "unknown"),
                overall_score=0.0,
                criteria_scores={},
                reasoning=f"Evaluation failed: {str(e)}",
                strengths=[],
                weaknesses=["Evaluation system error"],
                suggestions=["Please retry evaluation"],
                passed=False,
                confidence=0.0,
            )

    def _build_evaluation_prompt(
        self,
        content: str,
        context: Dict[str, Any],
        criteria_descriptions: List[str],
    ) -> str:
        """Build the evaluation prompt for the LLM."""
        requirements = context.get("requirements", [])
        goal = context.get("goal", "General content evaluation")
        content_type = context.get("type", "general")

        prompt = f"""You are an expert evaluator. Please evaluate the following content based on the specified criteria.

## Goal
{goal}

## Content Type
{content_type}

## Requirements
{chr(10).join(f'- {r}' for r in requirements) if requirements else 'No specific requirements'}

## Evaluation Criteria
{chr(10).join(criteria_descriptions)}

## Content to Evaluate
```
{content[:4000]}  # Truncate for token limits
```

## Instructions
1. Evaluate the content against each criterion on a scale of 0.0 to 1.0
2. Provide overall reasoning for your evaluation
3. List specific strengths (at least 2)
4. List specific weaknesses or areas for improvement (at least 1)
5. Provide actionable suggestions for improvement

## Response Format
Please respond in the following JSON format:
{{
    "criteria_scores": {{
        "correctness": 0.85,
        "completeness": 0.75,
        ...
    }},
    "overall_reasoning": "Your detailed reasoning here...",
    "strengths": ["Strength 1", "Strength 2"],
    "weaknesses": ["Weakness 1"],
    "suggestions": ["Suggestion 1", "Suggestion 2"],
    "confidence": 0.85
}}

Provide your evaluation:"""

        return prompt

    def _parse_evaluation_response(
        self,
        response: str,
        content_id: str,
        criteria: List[str],
    ) -> LLMEvaluationResult:
        """Parse LLM response into evaluation result."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in response")

            # Extract criteria scores
            criteria_scores = data.get("criteria_scores", {})

            # Calculate weighted overall score
            total_weight = 0
            weighted_sum = 0
            for criterion, score in criteria_scores.items():
                if criterion in self.criteria:
                    weight = self.criteria[criterion].weight
                    weighted_sum += score * weight
                    total_weight += weight

            overall_score = weighted_sum / total_weight if total_weight > 0 else 0.5

            # Determine if passed
            passed = all(
                score >= self.criteria.get(c, EvaluationCriteria(c, "")).passing_threshold
                for c, score in criteria_scores.items()
                if c in self.criteria
            )

            return LLMEvaluationResult(
                content_id=content_id,
                overall_score=overall_score,
                criteria_scores=criteria_scores,
                reasoning=data.get("overall_reasoning", ""),
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                suggestions=data.get("suggestions", []),
                passed=passed,
                confidence=data.get("confidence", 0.5),
            )

        except json.JSONDecodeError as e:
            logger.warning("failed_to_parse_evaluation_json", error=str(e))
            return LLMEvaluationResult(
                content_id=content_id,
                overall_score=0.5,
                criteria_scores={},
                reasoning="Failed to parse LLM response",
                strengths=[],
                weaknesses=["Could not parse evaluation response"],
                suggestions=["Retry evaluation"],
                passed=False,
                confidence=0.0,
            )

    def add_criteria(self, criteria: EvaluationCriteria) -> None:
        """Add custom evaluation criteria."""
        key = criteria.name.lower().replace(" ", "_")
        self.criteria[key] = criteria
        logger.info("evaluation_criteria_added", name=criteria.name)

    def remove_criteria(self, name: str) -> bool:
        """Remove evaluation criteria."""
        key = name.lower().replace(" ", "_")
        if key in self.criteria:
            del self.criteria[key]
            return True
        return False


@dataclass
class ReflectionInsight:
    """Insight from deep reflection process."""
    insight_type: str  # "pattern", "issue", "improvement", "learning"
    description: str
    evidence: List[str]
    confidence: float
    actionable: bool
    suggested_actions: List[str]


class DeepReflector:
    """
    Deep reflection system for meta-analysis and learning.

    Analyzes patterns across multiple evaluations to derive insights
    and guide continuous improvement.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        reflection_depth: int = 3,
    ):
        self.llm_client = llm_client
        self.reflection_depth = reflection_depth
        self._evaluation_history: List[LLMEvaluationResult] = []
        self._insights: List[ReflectionInsight] = []
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the reflector."""
        if self.llm_client is None:
            config = LLMConfig(provider="openai", model="gpt-4", temperature=0.5)
            self.llm_client = LLMClient(config)

        await self.llm_client.connect()
        self._initialized = True
        logger.info("deep_reflector_initialized")

    async def reflect(
        self,
        evaluation: LLMEvaluationResult,
        context: Dict[str, Any],
    ) -> List[ReflectionInsight]:
        """
        Perform deep reflection on an evaluation.

        Args:
            evaluation: Recent evaluation result
            context: Additional context for reflection

        Returns:
            List of insights derived from reflection
        """
        if not self._initialized:
            await self.initialize()

        # Add to history
        self._evaluation_history.append(evaluation)

        # Generate insights
        insights = await self._generate_insights(evaluation, context)

        # Store insights
        self._insights.extend(insights)

        logger.info(
            "deep_reflection_complete",
            insights_count=len(insights),
            evaluation_score=evaluation.overall_score,
        )

        return insights

    async def _generate_insights(
        self,
        evaluation: LLMEvaluationResult,
        context: Dict[str, Any],
    ) -> List[ReflectionInsight]:
        """Generate insights using LLM."""
        # Build reflection prompt
        prompt = self._build_reflection_prompt(evaluation, context)

        try:
            response = await self.llm_client.generate(prompt)

            # Parse insights
            insights = self._parse_insights(response.content)

            return insights

        except Exception as e:
            logger.error("reflection_generation_failed", error=str(e))
            return []

    def _build_reflection_prompt(
        self,
        evaluation: LLMEvaluationResult,
        context: Dict[str, Any],
    ) -> str:
        """Build reflection prompt."""
        recent_history = self._evaluation_history[-5:]  # Last 5 evaluations

        prompt = f"""You are a reflective AI system analyzing evaluation results to derive insights.

## Current Evaluation
- Content ID: {evaluation.content_id}
- Overall Score: {evaluation.overall_score:.2f}
- Passed: {evaluation.passed}
- Criteria Scores: {json.dumps(evaluation.criteria_scores)}
- Strengths: {evaluation.strengths}
- Weaknesses: {evaluation.weaknesses}

## Recent Evaluation History
{self._format_history(recent_history)}

## Context
- Goal: {context.get('goal', 'General improvement')}
- Iteration: {context.get('iteration', 1)}

## Instructions
Analyze the evaluation and history to generate insights. For each insight, provide:
1. Type: "pattern", "issue", "improvement", or "learning"
2. Description: Clear explanation of the insight
3. Evidence: Specific examples or data points
4. Confidence: 0.0 to 1.0
5. Actionable: true/false
6. Suggested Actions: List of concrete steps

## Response Format (JSON array)
[
    {{
        "type": "pattern",
        "description": "Description of the pattern",
        "evidence": ["Evidence 1", "Evidence 2"],
        "confidence": 0.8,
        "actionable": true,
        "suggested_actions": ["Action 1", "Action 2"]
    }}
]

Provide your insights:"""

        return prompt

    def _format_history(self, history: List[LLMEvaluationResult]) -> str:
        """Format evaluation history for prompt."""
        lines = []
        for i, eval_result in enumerate(history):
            lines.append(
                f"{i+1}. Score: {eval_result.overall_score:.2f}, "
                f"Passed: {eval_result.passed}, "
                f"Main weakness: {eval_result.weaknesses[0] if eval_result.weaknesses else 'None'}"
            )
        return "\n".join(lines) if lines else "No previous evaluations"

    def _parse_insights(self, response: str) -> List[ReflectionInsight]:
        """Parse insights from LLM response."""
        insights = []

        try:
            # Extract JSON array
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                data_list = json.loads(json_match.group())

                for item in data_list:
                    insight = ReflectionInsight(
                        insight_type=item.get("type", "learning"),
                        description=item.get("description", ""),
                        evidence=item.get("evidence", []),
                        confidence=item.get("confidence", 0.5),
                        actionable=item.get("actionable", False),
                        suggested_actions=item.get("suggested_actions", []),
                    )
                    insights.append(insight)

        except json.JSONDecodeError as e:
            logger.warning("failed_to_parse_insights_json", error=str(e))

        return insights

    def get_improvement_priorities(self) -> List[Dict[str, Any]]:
        """Get prioritized improvement areas based on reflection history."""
        if not self._insights:
            return []

        # Group insights by type
        by_type: Dict[str, List[ReflectionInsight]] = {}
        for insight in self._insights:
            if insight.insight_type not in by_type:
                by_type[insight.insight_type] = []
            by_type[insight.insight_type].append(insight)

        # Calculate priorities
        priorities = []
        for insight_type, insights in by_type.items():
            avg_confidence = sum(i.confidence for i in insights) / len(insights)
            actionable_count = sum(1 for i in insights if i.actionable)

            priorities.append({
                "type": insight_type,
                "count": len(insights),
                "avg_confidence": avg_confidence,
                "actionable_count": actionable_count,
                "priority_score": avg_confidence * actionable_count,
                "insights": [i.description for i in insights[:3]],
            })

        # Sort by priority score
        priorities.sort(key=lambda x: x["priority_score"], reverse=True)

        return priorities

    def get_learning_summary(self) -> Dict[str, Any]:
        """Get a summary of learnings from reflection."""
        return {
            "total_evaluations": len(self._evaluation_history),
            "total_insights": len(self._insights),
            "insight_types": {
                t: len([i for i in self._insights if i.insight_type == t])
                for t in ["pattern", "issue", "improvement", "learning"]
            },
            "avg_evaluation_score": (
                sum(e.overall_score for e in self._evaluation_history) / len(self._evaluation_history)
                if self._evaluation_history else 0
            ),
            "improvement_trend": self._calculate_trend(),
        }

    def _calculate_trend(self) -> str:
        """Calculate improvement trend."""
        if len(self._evaluation_history) < 2:
            return "insufficient_data"

        recent = self._evaluation_history[-3:]
        earlier = self._evaluation_history[:-3] or self._evaluation_history[:1]

        recent_avg = sum(e.overall_score for e in recent) / len(recent)
        earlier_avg = sum(e.overall_score for e in earlier) / len(earlier)

        if recent_avg > earlier_avg + 0.05:
            return "improving"
        elif recent_avg < earlier_avg - 0.05:
            return "declining"
        else:
            return "stable"


class IterativeImprovementLoop:
    """
    Iterative improvement loop combining evaluation and reflection.

    This class orchestrates the continuous improvement cycle:
    Evaluate -> Reflect -> Improve -> Evaluate
    """

    def __init__(
        self,
        evaluator: Optional[LLMEvaluator] = None,
        reflector: Optional[DeepReflector] = None,
        max_iterations: int = 5,
        target_score: float = 0.8,
    ):
        self.evaluator = evaluator or LLMEvaluator()
        self.reflector = reflector or DeepReflector()
        self.max_iterations = max_iterations
        self.target_score = target_score

        self._iteration_history: List[Dict[str, Any]] = []
        self._current_iteration = 0

    async def initialize(self) -> None:
        """Initialize the improvement loop."""
        await self.evaluator.initialize()
        await self.reflector.initialize()
        logger.info("iterative_improvement_loop_initialized")

    async def run(
        self,
        content: str,
        context: Dict[str, Any],
        improvement_callback: Optional[Callable[[str, List[str]], str]] = None,
    ) -> Dict[str, Any]:
        """
        Run the iterative improvement loop.

        Args:
            content: Initial content to improve
            context: Evaluation context
            improvement_callback: Function to apply improvements

        Returns:
            Final result with improvement history
        """
        await self.initialize()

        current_content = content
        result = {
            "initial_content": content[:500],  # Truncated for storage
            "iterations": [],
            "final_score": 0.0,
            "target_achieved": False,
            "total_iterations": 0,
        }

        for iteration in range(self.max_iterations):
            self._current_iteration = iteration + 1
            iteration_result = {
                "iteration": iteration + 1,
                "content_length": len(current_content),
            }

            # Step 1: Evaluate
            evaluation = await self.evaluator.evaluate(
                content=current_content,
                context={**context, "iteration": iteration + 1},
            )
            iteration_result["evaluation"] = evaluation.to_dict()

            # Step 2: Reflect
            insights = await self.reflector.reflect(
                evaluation=evaluation,
                context={**context, "iteration": iteration + 1},
            )
            iteration_result["insights"] = [
                {
                    "type": i.insight_type,
                    "description": i.description,
                    "confidence": i.confidence,
                }
                for i in insights
            ]

            # Record iteration
            self._iteration_history.append(iteration_result)
            result["iterations"].append(iteration_result)

            # Check if target achieved
            if evaluation.overall_score >= self.target_score:
                result["target_achieved"] = True
                result["final_score"] = evaluation.overall_score
                result["total_iterations"] = iteration + 1
                logger.info(
                    "improvement_target_achieved",
                    iteration=iteration + 1,
                    score=evaluation.overall_score,
                )
                break

            # Step 3: Improve (if callback provided)
            if improvement_callback and iteration < self.max_iterations - 1:
                suggestions = evaluation.suggestions + [
                    action for insight in insights
                    for action in insight.suggested_actions
                ]
                current_content = await self._apply_improvement(
                    current_content,
                    suggestions,
                    improvement_callback,
                )
                iteration_result["improved"] = True
            else:
                iteration_result["improved"] = False

        # Set final results
        if result["iterations"]:
            result["final_score"] = result["iterations"][-1]["evaluation"]["overall_score"]
            result["total_iterations"] = len(result["iterations"])

        # Add learning summary
        result["learning_summary"] = self.reflector.get_learning_summary()

        return result

    async def _apply_improvement(
        self,
        content: str,
        suggestions: List[str],
        callback: Callable,
    ) -> str:
        """Apply improvements to content."""
        try:
            if asyncio.iscoroutinefunction(callback):
                improved = await callback(content, suggestions)
            else:
                improved = callback(content, suggestions)
            return improved
        except Exception as e:
            logger.error("improvement_callback_failed", error=str(e))
            return content

    def get_progress_report(self) -> Dict[str, Any]:
        """Get progress report of the improvement loop."""
        if not self._iteration_history:
            return {"status": "not_started"}

        scores = [
            it["evaluation"]["overall_score"]
            for it in self._iteration_history
        ]

        return {
            "status": "in_progress" if self._current_iteration < self.max_iterations else "completed",
            "current_iteration": self._current_iteration,
            "max_iterations": self.max_iterations,
            "score_history": scores,
            "best_score": max(scores) if scores else 0,
            "latest_score": scores[-1] if scores else 0,
            "improvement": scores[-1] - scores[0] if len(scores) > 1 else 0,
        }
