"""
Paper Writing System Example

This example demonstrates how to build a 24/7 academic paper writing system
using the HyperEternalAgent framework. The system can:
- Generate paper outlines from research topics
- Write sections with proper academic style
- Review and improve writing quality
- Check citations and references
- Continuously improve the paper through feedback
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

from hypereternal import HyperEternalAgent, SystemConfig
from hypereternal.core.types import Task, TaskResult, TaskPriority
from hypereternal.agents.base import BaseAgent, AgentCapabilities, AgentType
from hypereternal.orchestration.flow_engine import FlowDefinition, FlowStep, StepType


@dataclass
class PaperSection:
    """Represents a section of the paper."""
    section_id: str
    title: str
    content: str
    word_count: int
    citations: List[str]
    quality_score: float = 0.0
    revision: int = 0


@dataclass
class AcademicPaper:
    """Represents an academic paper being written."""
    paper_id: str
    title: str
    authors: List[str]
    abstract: str
    keywords: List[str]
    sections: Dict[str, PaperSection]
    references: List[Dict[str, str]]
    quality_scores: List[float]
    revision_history: List[Dict[str, Any]]
    status: str = "draft"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class OutlineGeneratorAgent(BaseAgent):
    """Agent that generates paper outlines from research topics."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.PLANNER

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="Outline Generator",
            description="Generates paper outlines from research topics",
            input_types=["topic", "requirements"],
            output_types=["outline"],
            tags=["planning", "academic"],
        )

    async def execute(self, task: Task) -> TaskResult:
        topic = task.payload.get("topic", "")
        paper_type = task.payload.get("paper_type", "research")
        target_length = task.payload.get("target_length", 5000)

        # Generate outline based on paper type
        outline = self._generate_outline(topic, paper_type, target_length)

        return TaskResult(
            task_id=task.task_id,
            success=True,
            output={
                "outline": outline,
                "estimated_sections": len(outline["sections"]),
                "estimated_words": target_length,
            },
        )

    def _generate_outline(self, topic: str, paper_type: str, target_length: int) -> Dict:
        """Generate paper outline."""
        base_sections = [
            {
                "id": "introduction",
                "title": "Introduction",
                "description": "Background, motivation, and research questions",
                "target_words": int(target_length * 0.15),
                "key_points": [
                    "Background and context",
                    "Problem statement",
                    "Research objectives",
                    "Paper structure overview",
                ],
            },
            {
                "id": "literature_review",
                "title": "Literature Review",
                "description": "Review of related work and theoretical background",
                "target_words": int(target_length * 0.20),
                "key_points": [
                    "Theoretical framework",
                    "Related research",
                    "Research gaps",
                    "Critical analysis",
                ],
            },
            {
                "id": "methodology",
                "title": "Methodology",
                "description": "Research design and methods",
                "target_words": int(target_length * 0.20),
                "key_points": [
                    "Research design",
                    "Data collection",
                    "Analysis methods",
                    "Validity and reliability",
                ],
            },
            {
                "id": "results",
                "title": "Results",
                "description": "Presentation of findings",
                "target_words": int(target_length * 0.20),
                "key_points": [
                    "Descriptive statistics",
                    "Main findings",
                    "Tables and figures",
                    "Statistical analysis",
                ],
            },
            {
                "id": "discussion",
                "title": "Discussion",
                "description": "Interpretation and implications",
                "target_words": int(target_length * 0.15),
                "key_points": [
                    "Interpretation of results",
                    "Theoretical implications",
                    "Practical implications",
                    "Limitations",
                ],
            },
            {
                "id": "conclusion",
                "title": "Conclusion",
                "description": "Summary and future work",
                "target_words": int(target_length * 0.10),
                "key_points": [
                    "Summary of contributions",
                    "Future research directions",
                    "Final remarks",
                ],
            },
        ]

        return {
            "topic": topic,
            "paper_type": paper_type,
            "sections": base_sections,
            "structure_notes": {
                "citation_style": "APA",
                "figure_format": "Numbered with captions",
                "table_format": "Numbered with titles",
            },
        }


class SectionWriterAgent(BaseAgent):
    """Agent that writes paper sections."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.WORKER

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="Section Writer",
            description="Writes academic paper sections",
            input_types=["section_info", "context"],
            output_types=["content"],
            tags=["writing", "academic"],
        )

    async def execute(self, task: Task) -> TaskResult:
        section_info = task.payload.get("section_info", {})
        context = task.payload.get("context", {})
        topic = context.get("topic", "")

        section_id = section_info.get("id", "unknown")
        title = section_info.get("title", "")
        key_points = section_info.get("key_points", [])
        target_words = section_info.get("target_words", 500)

        # Generate section content
        content = self._write_section(section_id, title, key_points, topic, target_words)

        # Extract citations
        citations = self._extract_citations(content)

        return TaskResult(
            task_id=task.task_id,
            success=True,
            output={
                "section_id": section_id,
                "title": title,
                "content": content,
                "word_count": len(content.split()),
                "citations": citations,
            },
        )

    def _write_section(self, section_id: str, title: str, key_points: List[str], topic: str, target_words: int) -> str:
        """Write section content."""
        # Template-based content generation
        templates = {
            "introduction": f'''## {title}

The field of {topic} has gained significant attention in recent years due to its potential impact on various domains. This paper presents a comprehensive study that addresses key challenges in this area.

### Background

Understanding the fundamental concepts of {topic} is essential for appreciating the contributions of this research. Previous studies have established the importance of systematic approaches to problems in this domain (Smith et al., 2023; Johnson, 2022).

### Problem Statement

Despite advances in the field, several challenges remain unaddressed. The primary problem this research addresses is the lack of comprehensive frameworks that can effectively handle the complexity of modern {topic} applications.

### Research Objectives

The main objectives of this research are:
1. To develop a novel framework for {topic}
2. To evaluate the effectiveness of the proposed approach
3. To provide practical guidelines for implementation

### Paper Structure

The remainder of this paper is organized as follows. Section 2 reviews the relevant literature. Section 3 describes the methodology. Section 4 presents the results. Section 5 discusses the findings, and Section 6 concludes the paper.
''',
            "literature_review": f'''## {title}

This section provides a comprehensive review of the existing literature on {topic}, identifying key themes, methodologies, and gaps that inform the current study.

### Theoretical Framework

The theoretical underpinnings of this research draw from multiple disciplines. Williams (2021) established the foundational principles that guide contemporary approaches to {topic}. Building on this work, Chen et al. (2022) proposed an integrated framework that combines multiple theoretical perspectives.

### Related Research

Numerous studies have explored various aspects of {topic}. Brown and Davis (2023) conducted a meta-analysis of 45 studies, identifying common patterns and best practices. Their findings suggest that systematic approaches yield superior outcomes compared to ad-hoc methods.

### Research Gaps

Despite the extensive body of research, several gaps remain:
1. Limited research on scalability issues
2. Lack of standardized evaluation metrics
3. Insufficient attention to practical implementation challenges

### Critical Analysis

A critical examination of the literature reveals both strengths and limitations in existing approaches. While many studies provide valuable insights, methodological inconsistencies make cross-study comparisons challenging (Thompson, 2023).
''',
            "methodology": f'''## {title}

This section describes the research design, data collection procedures, and analysis methods employed in this study.

### Research Design

This study employs a mixed-methods approach, combining quantitative and qualitative techniques to provide a comprehensive understanding of {topic}. The research design follows established guidelines (Anderson, 2022) and incorporates recent methodological advances.

### Data Collection

Data were collected through multiple channels:
1. **Primary Sources**: Surveys and interviews with practitioners
2. **Secondary Sources**: Academic databases and industry reports
3. **Experimental Data**: Controlled experiments to evaluate performance

The sample size was determined using power analysis, ensuring adequate statistical power for detecting meaningful effects (Cohen, 1988).

### Analysis Methods

The analysis employed multiple techniques:
- Descriptive statistics for summarizing data
- Regression analysis for identifying relationships
- Thematic analysis for qualitative data

### Validity and Reliability

Several measures were taken to ensure the validity and reliability of the findings:
- Triangulation of data sources
- Member checking for qualitative data
- Inter-rater reliability assessment
''',
            "results": f'''## {title}

This section presents the findings of the study, organized according to the research questions.

### Descriptive Statistics

The study included 150 participants from various backgrounds. Table 1 summarizes the demographic characteristics of the sample. The majority of participants (68%) had more than 5 years of experience in {topic}.

### Main Findings

**Finding 1: Performance Improvement**

The results demonstrate significant improvement in key metrics. Figure 1 illustrates the performance gains achieved through the proposed approach. Statistical analysis revealed a significant effect (p < 0.001) with a large effect size (d = 0.85).

**Finding 2: User Satisfaction**

Participants reported high levels of satisfaction with the proposed solution. On a 5-point scale, the mean satisfaction score was 4.2 (SD = 0.65), indicating generally positive perceptions.

**Finding 3: Efficiency Gains**

Efficiency metrics showed substantial improvements. The average time to completion decreased by 35% compared to baseline conditions.

### Statistical Analysis

Multiple regression analysis was conducted to examine the relationships between variables. The overall model was significant, F(3, 146) = 15.67, p < 0.001, R² = 0.24.
''',
            "discussion": f'''## {title}

This section interprets the findings, discusses their implications, and acknowledges the limitations of the study.

### Interpretation of Results

The findings of this study provide strong support for the proposed approach to {topic}. The significant improvements in performance metrics align with theoretical predictions and validate the underlying framework.

### Theoretical Implications

These results contribute to the theoretical understanding of {topic} in several ways. First, they demonstrate the viability of the proposed framework. Second, they identify key factors that influence outcomes. Third, they suggest directions for future theoretical development.

### Practical Implications

Practitioners can apply these findings in several ways:
1. **Implementation Guidelines**: The framework provides a structured approach
2. **Best Practices**: The study identifies effective strategies
3. **Resource Allocation**: The findings inform resource decisions

### Limitations

Several limitations should be acknowledged:
1. **Sample Size**: While adequate, a larger sample would strengthen conclusions
2. **Generalizability**: Results may not apply to all contexts
3. **Temporal Factors**: Long-term effects were not assessed

### Future Research Directions

Future research should address the identified limitations and explore:
- Longitudinal studies to assess long-term effects
- Cross-cultural comparisons
- Integration with emerging technologies
''',
            "conclusion": f'''## {title}

This paper has presented a comprehensive study on {topic}, contributing both theoretical insights and practical guidelines.

### Summary of Contributions

The main contributions of this research are:
1. A novel framework for addressing challenges in {topic}
2. Empirical evidence supporting the effectiveness of the approach
3. Practical guidelines for implementation

### Future Research Directions

While this study makes important contributions, several avenues for future research remain. These include exploring applications in different domains, investigating long-term effects, and developing automated tools to support implementation.

### Final Remarks

The findings of this study advance our understanding of {topic} and provide valuable guidance for practitioners. As the field continues to evolve, the principles and methods presented here will serve as a foundation for future developments.
''',
        }

        return templates.get(section_id, f"## {title}\n\nContent for {title} section.\n")

    def _extract_citations(self, content: str) -> List[str]:
        """Extract citations from content."""
        import re
        # Simple citation extraction (Author, Year) format
        pattern = r'\(([A-Z][a-z]+(?:\s+et\s+al\.)?(?:,\s+\d{4}(?:,\s*[a-z])?)*(?:;\s*[A-Z][a-z]+(?:\s+et\s+al\.)?,\s*\d{4}(?:,\s*[a-z])?)*)\)'
        matches = re.findall(pattern, content)
        return list(set(matches))


class AcademicReviewerAgent(BaseAgent):
    """Agent that reviews academic writing quality."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.REVIEWER

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="Academic Reviewer",
            description="Reviews academic writing quality and structure",
            input_types=["content", "section_type"],
            output_types=["review", "suggestions"],
            tags=["review", "academic"],
        )

    async def execute(self, task: Task) -> TaskResult:
        content = task.payload.get("content", "")
        section_type = task.payload.get("section_type", "general")
        requirements = task.payload.get("requirements", {})

        # Perform review
        review_result = self._review_content(content, section_type, requirements)

        return TaskResult(
            task_id=task.task_id,
            success=True,
            output=review_result,
        )

    def _review_content(self, content: str, section_type: str, requirements: Dict) -> Dict:
        """Review content and provide feedback."""
        issues = []
        suggestions = []

        # Check word count
        word_count = len(content.split())
        min_words = requirements.get("min_words", 100)

        if word_count < min_words:
            issues.append({
                "type": "length",
                "severity": "medium",
                "message": f"Section too short ({word_count} words, minimum {min_words})",
            })

        # Check for citations
        if "et al." not in content and "(" not in content:
            issues.append({
                "type": "citations",
                "severity": "high",
                "message": "No citations found in academic content",
            })
            suggestions.append("Add relevant citations to support claims")

        # Check for academic phrases
        academic_indicators = [
            "research", "study", "analysis", "findings", "results",
            "conclusion", "implications", "framework", "methodology"
        ]
        indicator_count = sum(1 for ind in academic_indicators if ind.lower() in content.lower())

        if indicator_count < 3:
            issues.append({
                "type": "style",
                "severity": "low",
                "message": "Content may lack academic tone",
            })
            suggestions.append("Consider using more academic language")

        # Check structure
        if "##" not in content and section_type not in ["abstract", "conclusion"]:
            suggestions.append("Consider adding subsections for better organization")

        # Calculate quality score
        base_score = 1.0
        for issue in issues:
            severity = issue.get("severity", "low")
            if severity == "high":
                base_score -= 0.25
            elif severity == "medium":
                base_score -= 0.15
            else:
                base_score -= 0.05

        quality_score = max(0.0, min(1.0, base_score))

        return {
            "word_count": word_count,
            "quality_score": quality_score,
            "approved": quality_score >= 0.7 and len([i for i in issues if i["severity"] == "high"]) == 0,
            "issues": issues,
            "suggestions": suggestions,
            "strengths": self._identify_strengths(content),
        }

    def _identify_strengths(self, content: str) -> List[str]:
        """Identify strengths in the content."""
        strengths = []

        if len(content.split()) > 200:
            strengths.append("Comprehensive coverage of the topic")

        if "et al." in content:
            strengths.append("Good use of academic citations")

        if any(word in content.lower() for word in ["however", "therefore", "furthermore"]):
            strengths.append("Good use of transitional phrases")

        return strengths


class CitationCheckerAgent(BaseAgent):
    """Agent that checks and validates citations."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.CRITIC

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="Citation Checker",
            description="Validates citations and reference formatting",
            input_types=["content", "references"],
            output_types=["validation_result"],
            tags=["citations", "validation"],
        )

    async def execute(self, task: Task) -> TaskResult:
        content = task.payload.get("content", "")
        references = task.payload.get("references", [])
        style = task.payload.get("style", "APA")

        # Check citations
        validation_result = self._validate_citations(content, references, style)

        return TaskResult(
            task_id=task.task_id,
            success=True,
            output=validation_result,
        )

    def _validate_citations(self, content: str, references: List, style: str) -> Dict:
        """Validate citations against references."""
        import re

        # Extract citations from content
        citation_pattern = r'\(([A-Z][a-z]+(?:\s+et\s+al\.)?),\s*(\d{4})\)'
        citations = re.findall(citation_pattern, content)

        # Check for unreferenced citations
        unreferenced = []
        for author, year in citations:
            found = any(
                author.split()[0].lower() in ref.get("author", "").lower()
                and str(year) in ref.get("year", "")
                for ref in references
            )
            if not found:
                unreferenced.append(f"{author}, {year}")

        # Check for unused references
        unused_refs = []
        for ref in references:
            author = ref.get("author", "").split(",")[0] if ref.get("author") else ""
            year = ref.get("year", "")
            citation_str = f"{author}, {year}"

            if author and citation_str not in content:
                unused_refs.append(ref.get("key", "Unknown"))

        return {
            "total_citations": len(citations),
            "unreferenced_citations": unreferenced,
            "unused_references": unused_refs,
            "is_valid": len(unreferenced) == 0,
            "style": style,
            "issues": unreferenced + [f"Unused reference: {r}" for r in unused_refs],
        }


class AbstractWriterAgent(BaseAgent):
    """Agent that writes paper abstracts."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.WORKER

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="Abstract Writer",
            description="Writes paper abstracts summarizing key points",
            input_types=["sections", "keywords"],
            output_types=["abstract"],
            tags=["writing", "abstract"],
        )

    async def execute(self, task: Task) -> TaskResult:
        sections = task.payload.get("sections", {})
        keywords = task.payload.get("keywords", [])
        max_words = task.payload.get("max_words", 250)

        # Generate abstract
        abstract = self._generate_abstract(sections, keywords, max_words)

        return TaskResult(
            task_id=task.task_id,
            success=True,
            output={
                "abstract": abstract,
                "word_count": len(abstract.split()),
            },
        )

    def _generate_abstract(self, sections: Dict, keywords: List[str], max_words: int) -> str:
        """Generate abstract from sections."""
        # Extract key information from sections
        intro = sections.get("introduction", {}).get("content", "")
        methods = sections.get("methodology", {}).get("content", "")
        results = sections.get("results", {}).get("content", "")
        conclusion = sections.get("conclusion", {}).get("content", "")

        # Construct abstract
        abstract_parts = []

        # Background/Context
        abstract_parts.append(
            "This paper presents a comprehensive study addressing key challenges "
            "in the field through a systematic approach combining theoretical "
            "framework with empirical validation."
        )

        # Methods
        abstract_parts.append(
            "A mixed-methods research design was employed, incorporating both "
            "quantitative and qualitative data collection techniques."
        )

        # Results
        abstract_parts.append(
            "The findings demonstrate significant improvements in key metrics, "
            "with statistical analysis revealing meaningful effects (p < 0.001)."
        )

        # Conclusion
        abstract_parts.append(
            "These results contribute to the theoretical understanding of the subject "
            "and provide practical guidelines for implementation."
        )

        # Keywords
        if keywords:
            abstract_parts.append(f"Keywords: {', '.join(keywords[:5])}")

        abstract = " ".join(abstract_parts)

        # Trim if too long
        words = abstract.split()
        if len(words) > max_words:
            abstract = " ".join(words[:max_words-1]) + "..."

        return abstract


class PaperWritingSystem:
    """
    Paper Writing System using HyperEternalAgent.

    This system can run 24/7 to continuously write, review, and improve
    academic papers through iterative feedback.
    """

    def __init__(self, config: Optional[SystemConfig] = None):
        self.config = config or SystemConfig(
            name="PaperWritingSystem",
            version="1.0.0",
        )
        self.system = HyperEternalAgent(config=self.config)
        self.papers: Dict[str, AcademicPaper] = {}
        self._running = False

    async def start(self) -> None:
        """Start the paper writing system."""
        # Register all agents
        self.system.register_agent_type("outline_generator", OutlineGeneratorAgent)
        self.system.register_agent_type("section_writer", SectionWriterAgent)
        self.system.register_agent_type("academic_reviewer", AcademicReviewerAgent)
        self.system.register_agent_type("citation_checker", CitationCheckerAgent)
        self.system.register_agent_type("abstract_writer", AbstractWriterAgent)

        await self.system.start()
        self._running = True
        print("Paper Writing System started")

    async def stop(self) -> None:
        """Stop the paper writing system."""
        self._running = False
        await self.system.stop()
        print("Paper Writing System stopped")

    async def create_paper(
        self,
        title: str,
        authors: List[str],
        keywords: List[str],
    ) -> str:
        """Create a new paper project."""
        paper_id = f"paper_{len(self.papers) + 1}"

        paper = AcademicPaper(
            paper_id=paper_id,
            title=title,
            authors=authors,
            abstract="",
            keywords=keywords,
            sections={},
            references=[],
            quality_scores=[],
            revision_history=[],
        )

        self.papers[paper_id] = paper
        print(f"Created paper: {title} ({paper_id})")

        return paper_id

    async def generate_outline(
        self,
        paper_id: str,
        topic: str,
        paper_type: str = "research",
        target_length: int = 5000,
    ) -> Dict[str, Any]:
        """Generate paper outline."""
        paper = self.papers.get(paper_id)
        if not paper:
            return {"error": "Paper not found"}

        # Generate outline
        outline_task = await self.system.submit_task(
            task_type="outline_generator",
            payload={
                "topic": topic,
                "paper_type": paper_type,
                "target_length": target_length,
            },
        )

        outline_result = await self.system.wait_for_completion(outline_task.task_id, timeout=60)

        if outline_result.success:
            # Store outline in paper
            for section_info in outline_result.output.get("outline", {}).get("sections", []):
                section = PaperSection(
                    section_id=section_info["id"],
                    title=section_info["title"],
                    content="",
                    word_count=0,
                    citations=[],
                )
                paper.sections[section.section_id] = section

        return outline_result.output if outline_result.success else {"error": "Outline generation failed"}

    async def write_section(
        self,
        paper_id: str,
        section_id: str,
        section_info: Dict,
        context: Dict,
    ) -> Dict[str, Any]:
        """Write a specific section."""
        paper = self.papers.get(paper_id)
        if not paper:
            return {"error": "Paper not found"}

        # Write section
        write_task = await self.system.submit_task(
            task_type="section_writer",
            payload={
                "section_info": section_info,
                "context": context,
            },
        )

        write_result = await self.system.wait_for_completion(write_task.task_id, timeout=120)

        if write_result.success:
            # Update paper section
            section = paper.sections.get(section_id)
            if section:
                section.content = write_result.output["content"]
                section.word_count = write_result.output["word_count"]
                section.citations = write_result.output["citations"]

        return write_result.output if write_result.success else {"error": "Section writing failed"}

    async def review_section(
        self,
        paper_id: str,
        section_id: str,
        requirements: Dict = None,
    ) -> Dict[str, Any]:
        """Review a section for quality."""
        paper = self.papers.get(paper_id)
        if not paper:
            return {"error": "Paper not found"}

        section = paper.sections.get(section_id)
        if not section:
            return {"error": "Section not found"}

        # Review section
        review_task = await self.system.submit_task(
            task_type="academic_reviewer",
            payload={
                "content": section.content,
                "section_type": section_id,
                "requirements": requirements or {},
            },
        )

        review_result = await self.system.wait_for_completion(review_task.task_id, timeout=60)

        if review_result.success:
            section.quality_score = review_result.output.get("quality_score", 0)

        return review_result.output if review_result.success else {"error": "Review failed"}

    async def generate_abstract(
        self,
        paper_id: str,
        max_words: int = 250,
    ) -> Dict[str, Any]:
        """Generate paper abstract."""
        paper = self.papers.get(paper_id)
        if not paper:
            return {"error": "Paper not found"}

        # Prepare section data
        sections_data = {
            section_id: {
                "content": section.content,
                "title": section.title,
            }
            for section_id, section in paper.sections.items()
        }

        # Generate abstract
        abstract_task = await self.system.submit_task(
            task_type="abstract_writer",
            payload={
                "sections": sections_data,
                "keywords": paper.keywords,
                "max_words": max_words,
            },
        )

        abstract_result = await self.system.wait_for_completion(abstract_task.task_id, timeout=60)

        if abstract_result.success:
            paper.abstract = abstract_result.output["abstract"]

        return abstract_result.output if abstract_result.success else {"error": "Abstract generation failed"}

    async def write_paper(
        self,
        paper_id: str,
        topic: str,
        max_revisions: int = 3,
        quality_threshold: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Write a complete paper with iterative improvement.

        This implements the feedback loop:
        1. Generate outline
        2. Write each section
        3. Review sections
        4. Revise if needed
        5. Generate abstract
        6. Final review
        """
        paper = self.papers.get(paper_id)
        if not paper:
            return {"error": "Paper not found"}

        results = {
            "paper_id": paper_id,
            "revisions": [],
            "final_status": "in_progress",
        }

        # Step 1: Generate outline
        print("Generating outline...")
        outline = await self.generate_outline(paper_id, topic)
        if "error" in outline:
            return outline

        outline_sections = outline.get("outline", {}).get("sections", [])

        # Step 2-4: Write and review each section iteratively
        for revision in range(max_revisions):
            print(f"\n--- Revision {revision + 1} ---")
            revision_result = {"revision": revision + 1, "sections": []}
            all_approved = True

            for section_info in outline_sections:
                section_id = section_info["id"]

                # Write section
                print(f"Writing section: {section_info['title']}...")
                write_result = await self.write_section(
                    paper_id,
                    section_id,
                    section_info,
                    {"topic": topic},
                )

                if "error" in write_result:
                    continue

                # Review section
                print(f"Reviewing section: {section_info['title']}...")
                review_result = await self.review_section(
                    paper_id,
                    section_id,
                    {"min_words": section_info.get("target_words", 100) // 2},
                )

                section = paper.sections.get(section_id)
                revision_result["sections"].append({
                    "section_id": section_id,
                    "word_count": section.word_count if section else 0,
                    "quality_score": section.quality_score if section else 0,
                    "approved": review_result.get("approved", False),
                })

                if not review_result.get("approved", False):
                    all_approved = False

            results["revisions"].append(revision_result)

            # Check if all sections approved
            if all_approved:
                print("All sections approved!")
                break

        # Step 5: Generate abstract
        print("\nGenerating abstract...")
        await self.generate_abstract(paper_id)

        # Calculate overall quality
        if paper.sections:
            avg_quality = sum(s.quality_score for s in paper.sections.values()) / len(paper.sections)
            paper.quality_scores.append(avg_quality)

            if avg_quality >= quality_threshold:
                paper.status = "completed"
                results["final_status"] = "completed"
            else:
                paper.status = "needs_revision"
                results["final_status"] = "needs_revision"

        results["final_quality"] = paper.quality_scores[-1] if paper.quality_scores else 0

        return results

    def export_paper(self, paper_id: str, format: str = "markdown") -> str:
        """Export paper to specified format."""
        paper = self.papers.get(paper_id)
        if not paper:
            return ""

        if format == "markdown":
            return self._export_markdown(paper)
        elif format == "latex":
            return self._export_latex(paper)
        else:
            return self._export_markdown(paper)

    def _export_markdown(self, paper: AcademicPaper) -> str:
        """Export paper as Markdown."""
        lines = [
            f"# {paper.title}",
            "",
            f"**Authors:** {', '.join(paper.authors)}",
            "",
            "## Abstract",
            paper.abstract,
            "",
            f"**Keywords:** {', '.join(paper.keywords)}",
            "",
        ]

        # Add sections in order
        section_order = ["introduction", "literature_review", "methodology", "results", "discussion", "conclusion"]
        for section_id in section_order:
            section = paper.sections.get(section_id)
            if section and section.content:
                lines.append(section.content)
                lines.append("")

        # Add references
        if paper.references:
            lines.append("## References")
            for ref in paper.references:
                lines.append(f"- {ref.get('full_citation', '')}")
            lines.append("")

        return "\n".join(lines)

    def _export_latex(self, paper: AcademicPaper) -> str:
        """Export paper as LaTeX."""
        lines = [
            r"\documentclass{article}",
            r"\usepackage[utf8]{inputenc}",
            r"\title{" + paper.title + "}",
            r"\author{" + r" \and ".join(paper.authors) + "}",
            r"\begin{document}",
            r"\maketitle",
            "",
            r"\begin{abstract}",
            paper.abstract,
            r"\end{abstract}",
            "",
            r"\section*{Keywords}",
            ", ".join(paper.keywords),
            "",
        ]

        # Add sections
        for section_id, section in paper.sections.items():
            if section.content:
                lines.append(f"\\section{{{section.title}}}")
                lines.append(section.content.replace("##", "\\subsection").replace("###", "\\subsubsection"))
                lines.append("")

        lines.append(r"\end{document}")

        return "\n".join(lines)

    def get_paper_status(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a paper."""
        paper = self.papers.get(paper_id)
        if not paper:
            return None

        total_words = sum(s.word_count for s in paper.sections.values())

        return {
            "paper_id": paper.paper_id,
            "title": paper.title,
            "status": paper.status,
            "sections_completed": len([s for s in paper.sections.values() if s.content]),
            "total_sections": len(paper.sections),
            "total_words": total_words,
            "quality_scores": paper.quality_scores,
            "latest_quality": paper.quality_scores[-1] if paper.quality_scores else None,
            "revisions": len(paper.revision_history),
        }


async def main():
    """Example usage of the Paper Writing System."""

    # Create and start the system
    system = PaperWritingSystem()
    await system.start()

    try:
        # Create a new paper
        paper_id = await system.create_paper(
            title="A Novel Approach to Multi-Agent Systems for Autonomous Code Generation",
            authors=["Alice Researcher", "Bob Scientist"],
            keywords=["multi-agent systems", "code generation", "artificial intelligence", "automation"],
        )

        # Write the paper
        result = await system.write_paper(
            paper_id=paper_id,
            topic="Multi-agent systems for code generation",
            max_revisions=2,
            quality_threshold=0.6,
        )

        # Print results
        print("\n=== Paper Writing Results ===")
        print(f"Final Status: {result['final_status']}")
        print(f"Final Quality: {result['final_quality']:.2f}")
        print(f"Total Revisions: {len(result['revisions'])}")

        # Get paper status
        status = system.get_paper_status(paper_id)
        if status:
            print(f"\nPaper Status:")
            print(f"  Title: {status['title']}")
            print(f"  Status: {status['status']}")
            print(f"  Sections: {status['sections_completed']}/{status['total_sections']}")
            print(f"  Total Words: {status['total_words']}")

        # Export paper
        print("\n=== Exported Paper (Markdown) ===")
        markdown = system.export_paper(paper_id, format="markdown")
        print(markdown[:2000] + "..." if len(markdown) > 2000 else markdown)

    finally:
        await system.stop()


if __name__ == "__main__":
    asyncio.run(main())
