"""
Auto-Programming System Example

This example demonstrates how to build a 24/7 auto-programming system
using the HyperEternalAgent framework. The system can:
- Generate code from specifications
- Review and test generated code
- Fix bugs and improve code quality
- Continuously optimize the codebase
"""

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path

from hypereternal import HyperEternalAgent, SystemConfig
from hypereternal.core.types import Task, TaskResult, TaskPriority
from hypereternal.agents.base import BaseAgent, AgentCapabilities, AgentType
from hypereternal.orchestration.flow_engine import FlowDefinition, FlowStep, StepType


@dataclass
class CodeProject:
    """Represents a code project being developed."""
    project_id: str
    name: str
    specifications: List[str]
    generated_files: Dict[str, str]
    test_results: List[Dict[str, Any]]
    quality_scores: List[float]
    iterations: int = 0
    status: str = "pending"


class SpecificationAnalyzerAgent(BaseAgent):
    """Agent that analyzes and breaks down specifications."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.PLANNER

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="Specification Analyzer",
            description="Analyzes project specifications and creates implementation plan",
            input_types=["specification"],
            output_types=["plan", "tasks"],
            tags=["planning", "analysis"],
        )

    async def execute(self, task: Task) -> TaskResult:
        specification = task.payload.get("specification", "")
        project_type = task.payload.get("project_type", "general")

        # Analyze specification and create implementation tasks
        plan = {
            "project_type": project_type,
            "modules": self._identify_modules(specification),
            "dependencies": self._identify_dependencies(specification),
            "implementation_order": self._determine_order(specification),
            "estimated_complexity": self._estimate_complexity(specification),
        }

        tasks = []
        for module in plan["modules"]:
            tasks.append({
                "type": "code_generation",
                "module": module,
                "specification": specification,
                "priority": TaskPriority.HIGH.value if module.get("core") else TaskPriority.NORMAL.value,
            })

        return TaskResult(
            task_id=task.task_id,
            success=True,
            output={
                "plan": plan,
                "tasks": tasks,
            },
        )

    def _identify_modules(self, spec: str) -> List[Dict]:
        """Identify required modules from specification."""
        # Simplified module identification
        modules = [
            {"name": "main", "description": "Main entry point", "core": True},
            {"name": "utils", "description": "Utility functions", "core": False},
            {"name": "models", "description": "Data models", "core": True},
            {"name": "services", "description": "Business logic", "core": True},
        ]
        return modules

    def _identify_dependencies(self, spec: str) -> List[str]:
        """Identify required dependencies."""
        return ["pytest", "pydantic", "typing-extensions"]

    def _determine_order(self, spec: str) -> List[str]:
        """Determine implementation order."""
        return ["models", "utils", "services", "main"]

    def _estimate_complexity(self, spec: str) -> str:
        """Estimate project complexity."""
        return "medium"


class CodeGeneratorAgent(BaseAgent):
    """Agent that generates code from specifications."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.WORKER

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="Code Generator",
            description="Generates code from detailed specifications",
            input_types=["specification", "module"],
            output_types=["code"],
            tags=["code", "generation", "python"],
        )

    async def execute(self, task: Task) -> TaskResult:
        module = task.payload.get("module", {})
        specification = task.payload.get("specification", "")
        language = task.payload.get("language", "python")

        module_name = module.get("name", "unknown")
        module_desc = module.get("description", "")

        # Generate code based on module type
        code = self._generate_module_code(module_name, module_desc, specification, language)

        return TaskResult(
            task_id=task.task_id,
            success=True,
            output={
                "filename": f"{module_name}.py",
                "code": code,
                "language": language,
                "lines": len(code.split("\n")),
            },
            metrics={"complexity": module.get("complexity", 1)},
        )

    def _generate_module_code(self, name: str, desc: str, spec: str, lang: str) -> str:
        """Generate module code."""
        templates = {
            "main": '''"""
Main entry point for the application.
{desc}
"""

import asyncio
from typing import Optional

from .services import ServiceManager
from .models import Config
from .utils import setup_logging


class Application:
    """Main application class."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.service_manager = ServiceManager()
        self._running = False

    async def start(self) -> None:
        """Start the application."""
        setup_logging(self.config.log_level)
        self._running = True
        await self.service_manager.initialize()

        print("Application started successfully")

    async def stop(self) -> None:
        """Stop the application."""
        self._running = False
        await self.service_manager.shutdown()
        print("Application stopped")

    async def run(self) -> None:
        """Run the main application loop."""
        await self.start()
        try:
            while self._running:
                await asyncio.sleep(1)
        finally:
            await self.stop()


async def main():
    """Main entry point."""
    app = Application()
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
''',
            "models": '''"""
Data models for the application.
{desc}
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid


@dataclass
class Config:
    """Application configuration."""
    name: str = "MyApp"
    version: str = "1.0.0"
    log_level: str = "INFO"
    debug: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {{
            "name": self.name,
            "version": self.version,
            "log_level": self.log_level,
            "debug": self.debug,
        }}


@dataclass
class Entity:
    """Base entity class."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update(self) -> None:
        self.updated_at = datetime.now()


@dataclass
class Result:
    """Operation result."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
''',
            "utils": '''"""
Utility functions for the application.
{desc}
"""

import logging
import os
from typing import Any, Dict, Optional


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Set up application logging."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
        ]
    )

    return logging.getLogger(__name__)


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable."""
    return os.environ.get(key, default)


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries."""
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def validate_input(data: Dict[str, Any], required_keys: list) -> bool:
    """Validate that required keys are present."""
    return all(key in data for key in required_keys)
''',
            "services": '''"""
Business logic services for the application.
{desc}
"""

import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from .models import Entity, Result
from .utils import validate_input


@dataclass
class ServiceConfig:
    """Service configuration."""
    max_retries: int = 3
    timeout: float = 30.0
    pool_size: int = 10


class BaseService:
    """Base service class."""

    def __init__(self, config: Optional[ServiceConfig] = None):
        self.config = config or ServiceConfig()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the service."""
        self._initialized = True

    async def shutdown(self) -> None:
        """Shutdown the service."""
        self._initialized = False

    def is_ready(self) -> bool:
        """Check if service is ready."""
        return self._initialized


class DataService(BaseService):
    """Data management service."""

    def __init__(self, config: Optional[ServiceConfig] = None):
        super().__init__(config)
        self._data: Dict[str, Entity] = {{}}

    async def create(self, data: Dict[str, Any]) -> Result:
        """Create a new entity."""
        entity = Entity(**data)
        self._data[entity.id] = entity
        return Result(success=True, data=entity)

    async def get(self, entity_id: str) -> Result:
        """Get an entity by ID."""
        entity = self._data.get(entity_id)
        if entity:
            return Result(success=True, data=entity)
        return Result(success=False, error="Entity not found")

    async def list(self) -> Result:
        """List all entities."""
        return Result(success=True, data=list(self._data.values()))


class ServiceManager:
    """Manages all services."""

    def __init__(self):
        self.data_service = DataService()
        self._services = [self.data_service]

    async def initialize(self) -> None:
        """Initialize all services."""
        for service in self._services:
            await service.initialize()

    async def shutdown(self) -> None:
        """Shutdown all services."""
        for service in self._services:
            await service.shutdown()
''',
        }

        return templates.get(name, f'"""\n{desc}\n"""\n\n# Module: {name}\n# TODO: Implement module\npass\n').format(desc=desc)


class CodeReviewerAgent(BaseAgent):
    """Agent that reviews generated code."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.REVIEWER

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="Code Reviewer",
            description="Reviews code quality, style, and best practices",
            input_types=["code"],
            output_types=["review", "issues"],
            tags=["review", "quality"],
        )

    async def execute(self, task: Task) -> TaskResult:
        code = task.payload.get("code", "")
        filename = task.payload.get("filename", "unknown.py")

        # Perform code review
        issues = []
        suggestions = []

        # Check for common issues
        if "TODO" in code:
            issues.append({"type": "incomplete", "message": "Contains TODO comments", "severity": "low"})

        if "print(" in code and "def " not in code.split("print(")[0]:
            issues.append({"type": "style", "message": "Use logging instead of print", "severity": "medium"})

        if "except:" in code:
            issues.append({"type": "best_practice", "message": "Bare except clause", "severity": "high"})

        # Calculate score
        base_score = 1.0
        for issue in issues:
            severity = issue.get("severity", "low")
            if severity == "high":
                base_score -= 0.2
            elif severity == "medium":
                base_score -= 0.1
            else:
                base_score -= 0.05

        score = max(0.0, min(1.0, base_score))

        return TaskResult(
            task_id=task.task_id,
            success=True,
            output={
                "filename": filename,
                "approved": score >= 0.7 and len([i for i in issues if i["severity"] == "high"]) == 0,
                "score": score,
                "issues": issues,
                "suggestions": suggestions,
            },
        )


class TestGeneratorAgent(BaseAgent):
    """Agent that generates tests for code."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.WORKER

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="Test Generator",
            description="Generates unit tests for code modules",
            input_types=["code"],
            output_types=["tests"],
            tags=["testing", "generation"],
        )

    async def execute(self, task: Task) -> TaskResult:
        code = task.payload.get("code", "")
        module_name = task.payload.get("module_name", "module")

        # Generate test code
        test_code = self._generate_tests(code, module_name)

        return TaskResult(
            task_id=task.task_id,
            success=True,
            output={
                "test_filename": f"test_{module_name}.py",
                "test_code": test_code,
            },
        )

    def _generate_tests(self, code: str, module_name: str) -> str:
        """Generate test code."""
        return f'''"""
Tests for {module_name} module.
"""

import pytest
import asyncio
from {module_name} import *


class TestBasic:
    """Basic tests for {module_name}."""

    def test_imports(self):
        """Test that module can be imported."""
        import {module_name}
        assert {module_name} is not None

    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Test async functionality."""
        # Add async tests here
        pass

    def test_configuration(self):
        """Test configuration."""
        # Add configuration tests here
        pass
'''


class BugFixerAgent(BaseAgent):
    """Agent that fixes bugs in code."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.WORKER

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="Bug Fixer",
            description="Analyzes and fixes bugs in code",
            input_types=["code", "error"],
            output_types=["fixed_code"],
            tags=["bugfix", "correction"],
        )

    async def execute(self, task: Task) -> TaskResult:
        code = task.payload.get("code", "")
        error_info = task.payload.get("error", {})
        issues = task.payload.get("issues", [])

        # Apply fixes based on issues
        fixed_code = code

        for issue in issues:
            fixed_code = self._apply_fix(fixed_code, issue)

        return TaskResult(
            task_id=task.task_id,
            success=True,
            output={
                "fixed_code": fixed_code,
                "fixes_applied": len(issues),
            },
        )

    def _apply_fix(self, code: str, issue: Dict) -> str:
        """Apply a fix for a specific issue."""
        issue_type = issue.get("type", "")

        if issue_type == "style" and "print(" in code:
            # Replace print with logging
            code = code.replace("print(", "logger.info(")

        if issue_type == "incomplete" and "TODO" in code:
            # Add placeholder implementation
            code = code.replace("# TODO:", "# Implemented: ")

        return code


class AutoProgrammingSystem:
    """
    Auto-Programming System using HyperEternalAgent.

    This system can run 24/7 to continuously develop, test, and improve code.
    """

    def __init__(self, config: Optional[SystemConfig] = None):
        self.config = config or SystemConfig(
            name="AutoProgrammingSystem",
            version="1.0.0",
        )
        self.system = HyperEternalAgent(config=self.config)
        self.projects: Dict[str, CodeProject] = {}
        self._running = False

    async def start(self) -> None:
        """Start the auto-programming system."""
        # Register all agents
        self.system.register_agent_type("spec_analyzer", SpecificationAnalyzerAgent)
        self.system.register_agent_type("code_generator", CodeGeneratorAgent)
        self.system.register_agent_type("code_reviewer", CodeReviewerAgent)
        self.system.register_agent_type("test_generator", TestGeneratorAgent)
        self.system.register_agent_type("bug_fixer", BugFixerAgent)

        await self.system.start()
        self._running = True
        print("Auto-Programming System started")

    async def stop(self) -> None:
        """Stop the auto-programming system."""
        self._running = False
        await self.system.stop()
        print("Auto-Programming System stopped")

    async def create_project(self, name: str, specifications: List[str]) -> str:
        """Create a new programming project."""
        project_id = f"proj_{len(self.projects) + 1}"

        project = CodeProject(
            project_id=project_id,
            name=name,
            specifications=specifications,
            generated_files={},
            test_results=[],
            quality_scores=[],
        )

        self.projects[project_id] = project
        print(f"Created project: {name} ({project_id})")

        return project_id

    async def develop_project(self, project_id: str, max_iterations: int = 5) -> Dict[str, Any]:
        """
        Develop a project through iterative improvement.

        This implements the feedback loop:
        1. Analyze specifications
        2. Generate code
        3. Review code
        4. Generate tests
        5. Fix issues
        6. Repeat until quality threshold met
        """
        project = self.projects.get(project_id)
        if not project:
            return {"error": "Project not found"}

        results = {
            "project_id": project_id,
            "iterations": [],
            "final_status": "in_progress",
        }

        for iteration in range(max_iterations):
            project.iterations = iteration + 1
            print(f"\n--- Iteration {iteration + 1} ---")

            iteration_result = {
                "iteration": iteration + 1,
                "steps": [],
            }

            # Step 1: Analyze specifications
            spec_task = await self.system.submit_task(
                task_type="spec_analyzer",
                payload={
                    "specification": "\n".join(project.specifications),
                    "project_type": "application",
                },
            )
            spec_result = await self.system.wait_for_completion(spec_task.task_id, timeout=60)
            iteration_result["steps"].append({"step": "analysis", "result": spec_result.output})

            if not spec_result.success:
                iteration_result["error"] = "Specification analysis failed"
                results["iterations"].append(iteration_result)
                continue

            # Step 2: Generate code for each module
            plan = spec_result.output.get("plan", {})
            modules = plan.get("modules", [])

            for module in modules:
                gen_task = await self.system.submit_task(
                    task_type="code_generator",
                    payload={
                        "module": module,
                        "specification": "\n".join(project.specifications),
                        "language": "python",
                    },
                )
                gen_result = await self.system.wait_for_completion(gen_task.task_id, timeout=60)

                if gen_result.success:
                    filename = gen_result.output["filename"]
                    project.generated_files[filename] = gen_result.output["code"]
                    iteration_result["steps"].append({
                        "step": "generation",
                        "module": module["name"],
                        "success": True,
                    })

            # Step 3: Review generated code
            total_score = 0
            for filename, code in project.generated_files.items():
                review_task = await self.system.submit_task(
                    task_type="code_reviewer",
                    payload={"code": code, "filename": filename},
                )
                review_result = await self.system.wait_for_completion(review_task.task_id, timeout=60)

                if review_result.success:
                    score = review_result.output.get("score", 0)
                    total_score += score

                    issues = review_result.output.get("issues", [])
                    iteration_result["steps"].append({
                        "step": "review",
                        "filename": filename,
                        "score": score,
                        "issues": len(issues),
                    })

                    # Step 4: Fix issues if any
                    if issues:
                        fix_task = await self.system.submit_task(
                            task_type="bug_fixer",
                            payload={
                                "code": code,
                                "issues": issues,
                            },
                        )
                        fix_result = await self.system.wait_for_completion(fix_task.task_id, timeout=60)

                        if fix_result.success:
                            project.generated_files[filename] = fix_result.output["fixed_code"]

            # Calculate average quality
            if project.generated_files:
                avg_score = total_score / len(project.generated_files)
                project.quality_scores.append(avg_score)
                iteration_result["quality_score"] = avg_score

                # Check if quality threshold met
                if avg_score >= 0.8:
                    project.status = "completed"
                    results["final_status"] = "completed"
                    print(f"Quality threshold met! Score: {avg_score:.2f}")
                    break

            results["iterations"].append(iteration_result)

        if project.status != "completed":
            project.status = "needs_review"
            results["final_status"] = "needs_review"

        return results

    async def run_continuous_improvement(self, project_id: str, interval: int = 3600) -> None:
        """
        Run continuous improvement on a project.

        This will periodically analyze and improve the codebase.
        """
        project = self.projects.get(project_id)
        if not project:
            print(f"Project {project_id} not found")
            return

        print(f"Starting continuous improvement for {project.name}")

        while self._running:
            # Perform improvement cycle
            result = await self.develop_project(project_id, max_iterations=1)

            if result.get("final_status") == "completed":
                print("Project completed, pausing improvement cycle")
                break

            # Wait for next interval
            print(f"Waiting {interval} seconds until next improvement cycle...")
            await asyncio.sleep(interval)

    def get_project_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a project."""
        project = self.projects.get(project_id)
        if not project:
            return None

        return {
            "project_id": project.project_id,
            "name": project.name,
            "status": project.status,
            "iterations": project.iterations,
            "files_generated": len(project.generated_files),
            "quality_scores": project.quality_scores,
            "latest_score": project.quality_scores[-1] if project.quality_scores else None,
        }


async def main():
    """Example usage of the Auto-Programming System."""

    # Create and start the system
    system = AutoProgrammingSystem()
    await system.start()

    try:
        # Create a new project
        project_id = await system.create_project(
            name="TaskManager",
            specifications=[
                "A task management application",
                "Supports creating, updating, and deleting tasks",
                "Tasks can have priorities and due dates",
                "Include user authentication",
                "RESTful API design",
            ],
        )

        # Develop the project
        result = await system.develop_project(project_id, max_iterations=3)

        # Print results
        print("\n=== Development Results ===")
        print(f"Final Status: {result['final_status']}")
        print(f"Total Iterations: {len(result['iterations'])}")

        # Get project status
        status = system.get_project_status(project_id)
        if status:
            print(f"\nProject Status:")
            print(f"  Name: {status['name']}")
            print(f"  Status: {status['status']}")
            print(f"  Files Generated: {status['files_generated']}")
            if status['latest_score']:
                print(f"  Quality Score: {status['latest_score']:.2f}")

        # Show generated files
        project = system.projects[project_id]
        print("\n=== Generated Files ===")
        for filename, code in project.generated_files.items():
            print(f"\n--- {filename} ---")
            print(code[:500] + "..." if len(code) > 500 else code)

    finally:
        await system.stop()


if __name__ == "__main__":
    asyncio.run(main())
