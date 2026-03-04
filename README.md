# HyperEternalAgent

> 多Agent持久运行框架 - 支持构建24/7不间断运行的智能系统

## 项目简介

HyperEternalAgent 是一个多Agent持久运行框架，旨在支持构建能够长时间（数天、数周甚至数月）不间断运行的智能系统。该框架的核心特性包括：

- **持久运行**：支持24/7不间断运行，具备故障恢复和断点续传能力
- **自我进化**：通过自省机制不断优化输出质量
- **灵活编排**：支持YAML配置化的Agent编排和流程定义
- **高可用性**：完善的错误处理、重试机制和熔断保护

## 核心应用场景

1. **自动编程系统**：持续开发、代码审查、重构优化
2. **论文编写系统**：文献综述、论文撰写、格式校对
3. **数据分析系统**：持续监控、报告生成、趋势分析
4. **内容创作系统**：文章生成、质量审核、迭代改进

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                    HyperEternalAgent Framework                   │
├─────────────────────────────────────────────────────────────────┤
│  Application Layer   │  自动编程  │  论文编写  │  自定义应用     │
├─────────────────────────────────────────────────────────────────┤
│  Orchestration Layer │  流程引擎  │  任务路由  │  配置管理       │
├─────────────────────────────────────────────────────────────────┤
│  Agent Layer         │  Worker   │  Reviewer │  Planner  │ Critic│
├─────────────────────────────────────────────────────────────────┤
│  Reflection Layer    │  质量保证  │  错误检测  │  自动更正       │
├─────────────────────────────────────────────────────────────────┤
│  Persistence Layer   │  状态管理  │  任务队列  │  检查点系统     │
├─────────────────────────────────────────────────────────────────┤
│  Infrastructure Layer│  LLM客户端 │  监控系统  │  日志系统       │
└─────────────────────────────────────────────────────────────────┘
```

## 项目结构

```
HyperEternalAgent/
├── docs/                           # 文档目录
│   ├── architecture/               # 架构文档
│   │   └── README.md               # 核心架构设计
│   ├── design/                     # 设计文档
│   │   ├── agent_system.md         # Agent系统设计
│   │   ├── reflection_system.md    # 自省机制设计
│   │   ├── orchestration_system.md # 编排系统设计
│   │   └── persistence_system.md   # 持久层设计
│   └── api/                        # API文档
├── src/                            # 源代码目录
│   ├── core/                       # 核心模块
│   ├── agents/                     # Agent实现
│   ├── orchestration/              # 编排系统
│   ├── reflection/                 # 自省系统
│   ├── persistence/                # 持久层
│   ├── infrastructure/             # 基础设施
│   └── applications/               # 应用实现
│       ├── coding/                 # 自动编程应用
│       └── paper/                  # 论文编写应用
├── examples/                       # 示例代码
├── tests/                          # 测试代码
├── config/                         # 配置文件
│   ├── flows/                      # 流程定义
│   └── agents/                     # Agent配置
└── README.md                       # 项目说明
```

## 快速开始

### 环境要求

- Python 3.10+
- Redis 7.0+
- PostgreSQL 15+ (可选)

### 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/HyperEternalAgent.git
cd HyperEternalAgent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 配置

```bash
# 复制配置模板
cp config/config.example.yaml config/config.yaml

# 编辑配置
vim config/config.yaml
```

### 运行示例

```bash
# 运行自动编程示例
python -m src.applications.coding --project my_project

# 运行论文编写示例
python -m src.applications.paper --topic "AI Research"
```

## 文档索引

### 架构文档
- [核心架构设计](docs/architecture/README.md) - 整体架构和设计原则

### 设计文档
- [Agent系统设计](docs/design/agent_system.md) - Agent模型、生命周期和通信机制
- [自省机制设计](docs/design/reflection_system.md) - 质量保证、错误检测和自动更正
- [编排系统设计](docs/design/orchestration_system.md) - 流程引擎、任务路由和配置管理
- [持久层设计](docs/design/persistence_system.md) - 状态管理、任务队列和检查点系统

## 核心概念

### Agent (智能体)

Agent是框架的基本执行单元，分为以下类型：

| 类型 | 职责 | 示例 |
|------|------|------|
| WorkerAgent | 执行具体任务 | CodeWriterAgent, ResearchAgent |
| ReviewerAgent | 审核输出质量 | QualityReviewerAgent, SecurityReviewerAgent |
| PlannerAgent | 规划任务流程 | TaskPlannerAgent, ResourcePlannerAgent |
| CriticAgent | 评估整体表现 | PerformanceCriticAgent, QualityCriticAgent |
| CoordinatorAgent | 协调多个Agent | MasterAgent, SupervisorAgent |

### Flow (流程)

Flow定义了Agent之间的协作方式，支持：

- **顺序执行**：步骤按顺序依次执行
- **并行执行**：多个步骤同时执行
- **条件分支**：根据条件选择执行路径
- **循环迭代**：重复执行直到满足条件

### Self-Reflection (自省)

自省机制确保输出质量：

1. **质量评估**：多维度评估输出质量
2. **错误检测**：静态分析和运行时监控
3. **自动更正**：智能修复和优化建议
4. **迭代改进**：持续优化直到满足标准

## 开发路线图

### Phase 1: 核心框架 (当前)
- [x] 架构设计
- [ ] 基础Agent系统
- [ ] 简单任务队列
- [ ] 基本持久化

### Phase 2: 自省系统
- [ ] 质量评估引擎
- [ ] 错误检测引擎
- [ ] 自动更正引擎
- [ ] 反馈循环

### Phase 3: 编排系统
- [ ] Flow DSL解析器
- [ ] Flow执行引擎
- [ ] 任务路由器
- [ ] 调度器

### Phase 4: 应用生态
- [ ] 自动编程应用
- [ ] 论文编写应用
- [ ] 插件系统

## 贡献指南

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 联系方式

- 问题反馈：[GitHub Issues](https://github.com/yourusername/HyperEternalAgent/issues)
- 讨论交流：[GitHub Discussions](https://github.com/yourusername/HyperEternalAgent/discussions)
