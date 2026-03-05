# HyperEternalAgent

> Multi-Agent Persistent Running Framework - Building 24/7 Autonomous Intelligent Systems

## Overview

HyperEternalAgent is a multi-agent persistent running framework designed to support the development of intelligent systems that can run continuously for extended periods (days, weeks, or even months). Key features include:

- **Persistent Operation**: 24/7 continuous operation with fault recovery and checkpoint support
- **Self-Evolution**: Continuous quality improvement through reflection mechanisms
- **Flexible Orchestration**: YAML-based agent orchestration and workflow definition
- **High Availability**: Comprehensive error handling, retry mechanisms, and circuit breaker protection
- **Web Dashboard**: Real-time visualization and management interface

## Core Applications

1. **Auto-Programming System**: Continuous development, code review, and refactoring
2. **Paper Writing System**: Literature review, paper drafting, and format verification
3. **Data Analysis System**: Continuous monitoring, report generation, trend analysis
4. **Content Creation System**: Article generation, quality review, iterative improvement

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HyperEternalAgent Framework                   │
├─────────────────────────────────────────────────────────────────┤
│  Application Layer   │  Auto-Programming  │  Paper Writing  │    │
├─────────────────────────────────────────────────────────────────┤
│  Web Interface       │  Dashboard  │  REST API  │  WebSocket    │
├─────────────────────────────────────────────────────────────────┤
│  Orchestration Layer │  Flow Engine  │  Task Router  │  Config  │
├─────────────────────────────────────────────────────────────────┤
│  Agent Layer         │  Worker  │  Reviewer  │  Planner  │ Critic│
├─────────────────────────────────────────────────────────────────┤
│  Reflection Layer    │  Quality  │  Error Detection  │  LLM Eval │
├─────────────────────────────────────────────────────────────────┤
│  Persistence Layer   │  State Manager  │  Task Queue  │  Checkpoint│
├─────────────────────────────────────────────────────────────────┤
│  Infrastructure Layer│  LLM Client  │  Monitoring  │  Logging   │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
HyperEternalAgent/
├── docs/                           # Documentation
│   ├── architecture/               # Architecture docs
│   ├── design/                     # Design docs
│   └── api/                        # API reference
├── src/                            # Source code
│   ├── core/                       # Core module (types, config, exceptions)
│   ├── agents/                     # Agent implementations
│   ├── orchestration/              # Orchestration (flow engine, task router)
│   ├── reflection/                 # Reflection system (quality, correction)
│   ├── persistence/                # Persistence (storage, state, queue)
│   ├── infrastructure/             # Infrastructure (LLM, logging)
│   └── web/                        # Web interface
├── examples/                       # Example applications
│   ├── auto_programming_system.py  # Auto-programming example
│   └── paper_writing_system.py     # Paper writing example
├── tests/                          # Test suite
├── config/                         # Configuration files
└── README.md                       # This file
```

## Quick Start

### Requirements

- Python 3.10+
- Redis 7.0+ (optional, for distributed operation)
- PostgreSQL 15+ (optional, for persistent storage)

### Installation

```bash
# Clone repository
git clone https://github.com/970thunder/HyperEternalAgent.git
cd HyperEternalAgent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

### Basic Usage

```python
import asyncio
from hypereternal import HyperEternalAgent, SystemConfig, Task

async def main():
    # Create and start system
    config = SystemConfig(name="MySystem", version="1.0.0")
    system = HyperEternalAgent(config=config)
    await system.start()

    # Submit a task
    submission = await system.submit_task(
        task_type="code_generation",
        payload={"prompt": "Write a function to sort a list"},
    )

    # Wait for result
    result = await system.wait_for_completion(submission.task_id)
    print(f"Result: {result.output}")

    # Stop system
    await system.stop()

asyncio.run(main())
```

### Run Web Dashboard

```bash
# Start web server
python -m hypereternal.web.api

# Or using uvicorn
uvicorn hypereternal.web.api:app --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000 in your browser.

### Run Examples

```bash
# Run auto-programming example
python examples/auto_programming_system.py

# Run paper writing example
python examples/paper_writing_system.py
```

## Core Concepts

### Agent Types

| Type | Responsibility | Example |
|------|---------------|---------|
| WorkerAgent | Execute tasks | CodeGeneratorAgent, ResearchAgent |
| ReviewerAgent | Review output quality | QualityReviewerAgent |
| PlannerAgent | Plan task workflows | TaskPlannerAgent |
| CriticAgent | Evaluate overall performance | PerformanceCriticAgent |
| CoordinatorAgent | Coordinate multiple agents | SupervisorAgent |

### Flow Types

Flow defines how agents collaborate:

- **Sequential**: Steps execute in order
- **Parallel**: Multiple steps execute simultaneously
- **Condition**: Branch based on conditions
- **Loop**: Repeat until condition met

### Reflection System

The reflection system ensures output quality:

1. **Quality Assessment**: Multi-dimensional quality scoring
2. **Error Detection**: Static analysis and runtime monitoring
3. **Auto-Correction**: Intelligent fix suggestions
4. **Iterative Improvement**: Continuous optimization until standards met

## API Reference

See [API Documentation](docs/api/README.md) for detailed API reference.

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/system/status` | GET | Get system status |
| `/api/tasks` | POST | Create a new task |
| `/api/tasks/{task_id}` | GET | Get task status |
| `/api/agents` | GET | List all agents |
| `/api/flows` | POST | Execute a flow |

## Configuration

Create a `config.yaml` file:

```yaml
name: MySystem
version: 1.0.0

runtime:
  max_workers: 10
  task_timeout: 3600
  heartbeat_interval: 30

persistence:
  backend: redis
  url: redis://localhost:6379/0

monitoring:
  enabled: true
  metrics_port: 9090
  log_level: INFO

llm:
  openai:
    provider: openai
    model: gpt-4
    api_key: ${OPENAI_API_KEY}
```

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_core_types.py
```

## Development Roadmap

### Phase 1: Core Framework ✅
- [x] Architecture design
- [x] Base agent system
- [x] Task queue
- [x] Basic persistence
- [x] Unit tests

### Phase 2: Reflection System ✅
- [x] Quality assessment engine
- [x] Error detection engine
- [x] Auto-correction engine
- [x] LLM-based evaluation
- [x] Deep reflection
- [x] Self-evolution

### Phase 3: Web Interface ✅
- [x] REST API
- [x] WebSocket support
- [x] Dashboard UI

### Phase 4: Applications ✅
- [x] Auto-programming system
- [x] Paper writing system

## Contributing

Contributions are welcome! Please read our contributing guidelines.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

- Issues: [GitHub Issues](https://github.com/970thunder/HyperEternalAgent/issues)
- Discussions: [GitHub Discussions](https://github.com/970thunder/HyperEternalAgent/discussions)
