# Kimi CLI - AI 编程智能体

## 项目概览

Kimi CLI 是一款交互式命令行界面智能体，专注于软件工程任务。它采用 Python 构建，提供模块化架构，用于人工智能驱动的开发协助。该项目使用先进的智能体系统，具有可定制的工具、多种用户界面模式和广泛的配置选项。

## 技术栈

- **语言**：Python 3.13+
- **包管理**：uv (现代 Python 包管理器)
- **构建系统**：uv_build
- **CLI 框架**：Typer
- **LLM 集成**：kosong (自定义 LLM 框架)
- **异步运行时**：asyncio
- **测试**：支持 asyncio 的 pytest
- **代码质量**：ruff (代码检查/格式化), pyright (类型检查)
- **分发**：用于独立可执行文件的 PyInstaller
## 架构

### 核心组件

1. **代理系统** (`src/kimi_cli/agent.py`)
   - 基于 YAML 的代理规范
   - 带有内置参数的系统提示模板
   - 工具加载和依赖注入
   - 用于任务委托的子代理支持

2. **灵魂架构** (`src/kimi_cli/soul/`)
   - `KimiSoul`：主代理执行引擎
   - `Context`：会话历史管理
   - `DenwaRenji`：工具通信枢纽
   - 带有重试机制的事件驱动架构

3. **用户界面模式** (`src/kimi_cli/ui/`)
   - **Shell**：交互式终端界面（默认）
   - **Print**：用于脚本编写的非交互模式
   - **ACP**：代理客户端协议服务器模式

4. **工具系统** (`src/kimi_cli/tools/`)
   - 模块化工具架构，支持依赖注入
   - 内置工具：bash、文件操作、网页搜索、任务管理
   - MCP (模型上下文协议) 集成，支持外部工具
   - 自定义工具开发支持
### 关键目录

```
src/kimi_cli/
├── agents/           # 默认代理配置
├── soul/            # 核心代理执行逻辑
├── tools/           # 工具实现
│   ├── bash/       # Shell 命令执行
│   ├── file/       # 文件操作（读取、写入、grep 等）
│   ├── web/        # 网页搜索和 URL 获取
│   ├── task/       # 子代理任务委托
│   └── dmail/      # 时空旅行消息系统
└── ui/              # 用户界面实现
```

## 构建与开发

### 安装

```bash
# 使用 uv 安装
uv sync

# 安装开发依赖
uv sync --group dev
```

### 构建命令

```bash
# 格式化代码
make format
# 或者：uv run ruff check --fix && uv run ruff format

# 运行 linting 和类型检查
make check
# 或者：uv run ruff check && uv run ruff format --check && uv run pyright

# 运行测试
make test
# 或者：uv run pytest tests -vv

# 构建独立可执行文件
uv run pyinstaller kimi.spec
```

### 配置

配置文件：`~/.kimi/config.json`

默认配置包括：

- LLM 提供商设置（默认为 Kimi API）
- 带有上下文大小限制的模型配置
- 循环控制参数（最大步数，重试次数）
- 服务配置（Moonshot 搜索 API）
## 测试策略

- **单元测试**：所有工具和核心组件的全面测试覆盖
- **集成测试**：代理工作流的端到端测试
- **模拟提供商**：模拟 LLM 交互以进行一致性测试
- **固定装置**：为代理组件和工具提供广泛的 pytest 固定装置
- **异步测试**：完整的异步/等待测试支持

测试文件遵循 `test_*.py` 模式，并按组件组织：

- `test_load_agent.py`：代理加载和配置
- `test_bash.py`：Shell 命令执行
- `test_*_file.py`：文件操作工具
- `test_task_subagents.py`：子代理功能
## 代码风格指南

- **行长度**：最大 100 个字符
- **格式化工具**：ruff，带有特定规则选择
- **类型提示**：由 pyright 强制执行
- **导入组织**：应用 isort 规则
- **错误处理**：带有正确链的特定异常类型
- **日志记录**：使用 loguru 进行结构化日志记录

选定的 ruff 规则：

- E: pycodestyle
- F: Pyflakes
- UP: pyupgrade
- B: flake8-bugbear
- SIM: flake8-simplify
- I: isort
## 安全注意事项

- **文件系统访问**：默认限制在工作目录
- **API 密钥**：作为 SecretStr 处理，并进行适当的序列化
- **Shell 命令**：谨慎执行，强调用户知情
- **网络请求**：具有可配置端点的 Web 工具
- **会话管理**：具有历史记录跟踪的持久会话
## 代理开发

### 自定义代理创建

1. 创建代理规范文件（YAML 格式）
2. 定义带有模板变量的系统提示
3. 选择并配置工具
4. 可选地扩展现有代理
### 可用工具

- **Shell**：执行 shell 命令
- **ReadFile**：读取文件内容并限制行数
- **WriteFile**：写入内容到文件
- **Glob**：文件模式匹配
- **Grep**：使用正则表达式搜索内容
- **StrReplaceFile**：文件中字符串替换
- **PatchFile**：对文件应用补丁
- **SearchWeb**：网页搜索功能
- **FetchURL**：下载网页内容
- **Task**：委托给子代理
- **SendDMail**：时空旅行消息
- **Think**：内部推理工具
- **SetTodoList**：任务管理
### 系统提示参数

系统提示中可用的内置变量：

- `${KIMI_NOW}`：当前时间戳
- `${KIMI_WORK_DIR}`：工作目录路径
- `${KIMI_WORK_DIR_LS}`：目录列表输出
- `${KIMI_AGENTS_MD}`：项目 AGENTS.md 内容
## 部署

- **PyPI 包**：以 `kimi-cli` 发布
- **独立二进制文件**：使用 PyInstaller 构建
- **入口点**：`kimi` 命令行工具
- **配置**：用户特定的配置位于 `~/.kimi/`
## 版本历史

本项目遵循语义化版本控制。有关详细的版本历史、发布说明以及所有版本中的更改，请参阅项目根目录中的 `CHANGELOG.md`。
