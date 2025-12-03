# Changelog

<!--
发布说明将被解析并作为 /release-notes 提供
解析器为每个版本提取：
  - 简短描述（版本标题后的第一段）
  - 该版本下的以 "- " 开头的项目（跨任何子部分）
内部构建可能会在“未发布”部分追加内容。
只写入值得向用户提及的条目。
-->

## [0.60] - 2025-12-01

- LLM: Fix interleaved thinking for Kimi and OpenAI-compatible providers

## [0.59] - 2025-11-28

- 核心：将上下文文件位置移至 `.kimi/sessions/{workdir_md5}/{session_id}/context.jsonl`
- 库：将 `WireMessage` 类型别名移至 `kimi_cli.wire.message`
- 库：添加 `kimi_cli.wire.message.Request` 类型别名请求消息（目前仅包含 `ApprovalRequest`）
- 库：添加 `kimi_cli.wire.message.is_event`、`is_request` 和 `is_wire_message` 实用函数以检查线消息的类型
- 库：添加 `kimi_cli.wire.serde` 模块用于线消息的序列化和反序列化
- 库：更改 `StatusUpdate` 线消息，使其不使用 `kimi_cli.soul.StatusSnapshot`
- 核心：将线消息记录到会话目录中的 JSONL 文件
- 核心：引入 `TurnBegin` 线消息以标记每个智能体回合的开始
- UI：在 shell 模式下使用面板再次打印用户输入
- 库：添加 `Session.dir` 属性以获取会话目录路径
- UI：改进存在多个并行子智能体时的“批准会话”体验
- 线：重新实现线服务器模式（通过 `--wire` 选项启用）
- 库：为更好的一致性，将 `ShellApp` 重命名为 `Shell`，`PrintApp` 重命名为 `Print`，`ACPServer` 重命名为 `ACP`，`WireServer` 重命名为 `WireOverStdio`
- 库：为更好的一致性，将 `KimiCLI.run_shell_mode` 重命名为 `run_shell`，`run_print_mode` 重命名为 `run_print`，`run_acp_server` 重命名为 `run_acp`，`run_wire_server` 重命名为 `run_wire_stdio`
- 库：添加 `KimiCLI.run` 方法以使用给定的用户输入运行一个回合并生成线消息
- 打印：修复 stream-json 打印模式未正确刷新输出的问题
- LLM：提高与某些 OpenAI 和 Anthropic API 提供商的兼容性
- 核心：修复使用 Anthropic API 时，压缩后聊天提供商的错误

## [0.58] - 2025-11-21

- 核心：修复使用 `extend` 时代理规范文件的字段继承问题
- 核心：支持在子代理中使用 MCP 工具
- 工具：添加 `CreateSubagent` 工具以动态创建子代理（未在默认代理中启用）
- 工具：在 `FetchURL` 工具中为 Kimi for Coding 计划使用 MoonshotFetch 服务
- 工具：截断 Grep 工具输出以避免超出令牌限制

## [0.57] - 2025-11-20

- LLM：修复思考开关未打开时 Google GenAI 提供商的问题
- UI：改进审批请求措辞
- 工具：移除 `PatchFile` 工具
- 工具：将 `Bash`/`CMD` 工具重命名为 `Shell` 工具
- 工具：将 `Task` 工具移至 `kimi_cli.tools.multiagent` 模块

## [0.56] - 2025-11-19

- LLM：添加对 Google GenAI 提供商的支持

## [0.55] - 2025-11-18

- 库：添加 `kimi_cli.app.enable_logging` 函数，以便在使用 `KimiCLI` 类时启用日志记录
- 核心：修复代理规范文件中的相对路径解析问题
- 核心：防止 LLM API 连接失败时出现恐慌
- 工具：优化 `FetchURL` 工具以更好地提取内容
- 工具：将 MCP 工具调用超时增加到 60 秒
- 工具：当模式为 `**` 时，在 `Glob` 工具中提供更好的错误消息
- ACP：修复思考内容显示不正确的问题
- UI：shell 模式下的一些 UI 改进

## [0.54] - 2025-11-13

- 库：将 `WireMessage` 从 `kimi_cli.wire.message` 移动到 `kimi_cli.wire`
- 打印：修复 `stream-json` 输出格式缺少最后一个助手消息的问题
- UI：当 API 密钥被 `KIMI_API_KEY` 环境变量覆盖时添加警告
- UI：当有审批请求时发出蜂鸣声
- 核心：修复 Windows 上下文压缩和清除问题

## [0.53] - 2025-11-12

- UI：移除控制台输出中不必要的尾随空格
- 核心：当存在不支持的消息部分时抛出错误
- 元命令：添加 `/yolo` 元命令以在启动后启用 YOLO 模式
- 工具：为 MCP 工具添加审批请求
- 工具：在默认代理中禁用 `Think` 工具
- CLI：当未指定 `--thinking` 时，从上次恢复思考模式
- CLI：修复 PyInstaller 打包的二进制文件中 `/reload` 不工作的问题

## [0.52] - 2025-11-10

- CLI：移除 `--ui` 选项，改为使用 `--print`、`--acp` 和 `--wire` 标志（shell 仍然是默认选项）
- CLI：更直观的会话继续行为
- 核心：为 LLM 空响应添加重试
- 工具：在 Windows 上将 `Bash` 工具更改为 `CMD` 工具
- UI：修复退格键后的完成问题
- UI：修复浅色背景颜色下代码块渲染问题

## [0.51] - 2025-11-8

- 库：将 `Soul.model` 重命名为 `Soul.model_name`
- 库：将 `LLMModelCapability` 重命名为 `ModelCapability` 并移至 `kimi_cli.llm`
- 库：将 `"thinking"` 添加到 `ModelCapability`
- 库：移除 `LLM.supports_image_in` 属性
- 库：添加必需的 `Soul.model_capabilities` 属性
- 库：将 `KimiSoul.set_thinking_mode` 重命名为 `KimiSoul.set_thinking`
- 库：添加 `KimiSoul.thinking` 属性
- UI：改进 LLM 模型能力的检查和通知
- UI：为 `/clear` 元命令清除屏幕
- 工具：支持在 Windows 上自动下载 ripgrep
- CLI：添加 `--thinking` 选项以在思考模式下启动
- ACP：支持 ACP 模式下的思考内容

## [0.50] - 2025-11-07

### 变更

- 改进 UI 外观和感觉
- 改进任务工具的可观察性

## [0.49] - 2025-11-06

### 修复

- 细微的 UX 改进
## [0.48] - 2025-11-06

### 新增

- 支持 Kimi K2 思考模式
## [0.47] - 2025-11-05

### 修复

- 修复 Ctrl-W 在某些环境中不起作用的问题
- 当搜索服务未配置时，不加载 SearchWeb 工具
## [0.46] - 2025-11-03

### 新增

- 引入 Wire over stdio 用于本地 IPC（实验性功能，可能变更）
- 支持 Anthropic 提供商类型

### 修复

- 修复 PyInstaller 打包的二进制文件由于错误的入口点而无法工作的问题
## [0.45] - 2025-10-31

### 新增

- 允许 `KIMI_MODEL_CAPABILITIES` 环境变量覆盖模型能力
- 添加 `--no-markdown` 选项以禁用 markdown 渲染
- 支持 `openai_responses` LLM 提供商类型

### 修复

- 修复继续会话时崩溃的问题
## [0.44] - 2025-10-30

### 变更

- 改进启动时间

### 修复

- 修复用户输入中潜在的无效字节
## [0.43] - 2025-10-30

### 新增

- 基本 Windows 支持（实验性）
- 当基本 URL 或 API 密钥在环境变量中被覆盖时显示警告
- 如果 LLM 模型支持，则支持图像输入
- 继续会话时重播最近的上下文历史

### 修复

- 确保执行 shell 命令后有新行
## [0.42] - 2025-10-28

### 新增

- 支持 Ctrl-J 或 Alt-Enter 插入新行

### 变更

- 将模式切换快捷键从 Ctrl-K 更改为 Ctrl-X
- 提高整体健壮性

### 修复

- 修复 ACP 服务器 `no attribute` 错误
## [0.41] - 2025-10-26

### 修复

- 修复 Glob 工具在没有找到匹配文件时的 bug
- 确保以 UTF-8 编码读取文件

### 变更

- 在 shell 模式下禁用从 stdin 读取命令/查询
- 澄清 `/setup` 元命令中的 API 平台选择
## [0.40] - 2025-10-24

### 新增

- 支持 `ESC` 键中断代理循环

### 修复

- 修复在某些罕见情况下 SSL 证书验证错误
- 修复 Bash 工具中可能出现的解码错误
## [0.39] - 2025-10-24

### 修复

- 修复上下文压缩阈值检查
- 修复在 shell 会话中设置 SOCKS 代理时发生的恐慌
## [0.38] - 2025-10-24

- 细微的 UX 改进
## [0.37] - 2025-10-24

### 修复

- 修复更新检查
## [0.36] - 2025-10-24

### 新增

- 添加 `/debug` 元命令以调试上下文
- 添加自动上下文压缩
- 添加审批请求机制
- 添加 `--yolo` 选项以自动批准所有操作
- 渲染 markdown 内容以提高可读性

### 修复

- 修复中断元命令时出现的“未知错误”消息
## [0.35] - 2025-10-22

### 变更

- 细微的 UI 改进
- 如果系统中未找到 ripgrep，则自动下载
- 在 `--print` 模式下始终批准工具调用
- 添加 `/feedback` 元命令
## [0.34] - 2025-10-21

### 新增

- 添加 `/update` 元命令以检查更新并在后台自动更新
- 支持在原始 shell 模式下运行交互式 shell 命令
- 添加 `/setup` 元命令以设置 LLM 提供商和模型
- 添加 `/reload` 元命令以重新加载配置
## [0.33] - 2025-10-18

### 新增

- 添加 `/version` 元命令
- 添加原始 shell 模式，可通过 Ctrl-K 切换
- 在底部状态栏显示快捷方式

### 修复

- 修复日志重定向
- 合并重复的输入历史
## [0.32] - 2025-10-16

### 新增

- 添加底部状态栏
- 支持文件路径自动补全（`@filepath`）

### 修复

- 不在用户输入中间自动补全元命令
## [0.31] - 2025-10-14

### 修复

- 真正修复 Ctrl-C 中断步骤的问题
## [0.30] - 2025-10-14

### 新增

- 添加 `/compact` 元命令以允许手动压缩上下文

### 修复

- 修复上下文为空时 `/clear` 元命令的问题
## [0.29] - 2025-10-14

### 新增

- 支持在 shell 模式下按 Enter 键接受补全
- 在 shell 模式下跨会话记住用户输入历史
- 添加 `/reset` 元命令作为 `/clear` 的别名

### 修复

- 修复 Ctrl-C 中断步骤的问题

### 变更

- 在 Kimi Koder 代理中禁用 `SendDMail` 工具
## [0.28] - 2025-10-13

### 新增

- 添加 `/init` 元命令以分析代码库并生成 `AGENTS.md` 文件
- 添加 `/clear` 元命令以清除上下文

### 修复

- 修复 `ReadFile` 输出
## [0.27] - 2025-10-11

### 新增

- 添加 `--mcp-config-file` 和 `--mcp-config` 选项以加载 MCP 配置

### 变更

- 将 `--agent` 选项重命名为 `--agent-file`
## [0.26] - 2025-10-11

### 修复

- 修复 `--output-format stream-json` 模式下可能出现的编码错误
## [0.25] - 2025-10-11

### 变更

- 将包名 `ensoul` 重命名为 `kimi-cli`
- 将 `ENSOUL_*` 内置系统提示参数重命名为 `KIMI_*`
- 进一步解耦 `App` 和 `Soul`
- 分离 `Soul` 协议和 `KimiSoul` 实现以提高模块化
## [0.24] - 2025-10-10

### 修复

- 修复 ACP `cancel` 方法
## [0.23] - 2025-10-09

### 新增

- 向代理文件添加 `extend` 字段以支持代理文件扩展
- 向代理文件添加 `exclude_tools` 字段以支持排除工具
- 向代理文件添加 `subagents` 字段以支持定义子代理
## [0.22] - 2025-10-09

### 变更

- 改进 `SearchWeb` 和 `FetchURL` 工具调用可视化
- 改进搜索结果输出格式
## [0.21] - 2025-10-09

### 新增

- 添加 `--print` 选项作为 `--ui print` 的快捷方式，`--acp` 选项作为 `--ui acp` 的快捷方式
- 支持 `--output-format stream-json` 以 JSON 格式打印输出
- 添加 `SearchWeb` 工具，并配置 `services.moonshot_search`。您需要在配置文件中将其配置为 `"services": {"moonshot_search": {"api_key": "your-search-api-key"}}`。
- 添加 `FetchURL` 工具
- 添加 `Think` 工具
- 添加 `PatchFile` 工具，未在 Kimi Koder 代理中启用
- 在 Kimi Koder 代理中启用 `SendDMail` 和 `Task` 工具，并提供更好的工具提示
- 添加 `ENSOUL_NOW` 内置系统提示参数

### 变更

- 更好看的 `/release-notes`
- 改进工具描述
- 改进工具输出截断
## [0.20] - 2025-09-30

### 新增

- 添加 `--ui acp` 选项以启动 Agent Client Protocol (ACP) 服务器
## [0.19] - 2025-09-29

### 新增

- 支持管道输入用于打印 UI
- 支持 `--input-format=stream-json` 用于管道 JSON 输入

### 修复

- 当 `SendDMail` 未启用时，不在上下文中包含 `CHECKPOINT` 消息
## [0.18] - 2025-09-29

### 新增

- 支持在 LLM 模型配置中使用 `max_context_size` 来配置最大上下文大小（以 token 为单位）

### 改进

- 改进 `ReadFile` 工具描述
## [0.17] - 2025-09-29

### 修复

- 修复超出最大步数时错误消息中的步数计数问题
- 修复 `kimi_run` 中的历史文件断言错误
- 修复打印模式和单命令 shell 模式下的错误处理
- 为 LLM API 连接错误和超时错误添加重试

### 变更

- 将默认的最大每运行步数增加到 100
## [0.16.0] - 2025-09-26

### 工具

- 添加 `SendDMail` 工具（在 Kimi Koder 中禁用，可在自定义代理中启用）

### SDK

- 创建新会话时，可通过 `_history_file` 参数指定会话历史文件
## [0.15.0] - 2025-09-26

- 提高工具健壮性
## [0.14.0] - 2025-09-25

### 新增

- 添加 `StrReplaceFile` 工具

### 改进

- 强调使用与用户相同的语言
## [0.13.0] - 2025-09-25

### 新增

- 添加 `SetTodoList` 工具
- 在 LLM API 调用中添加 `User-Agent`

### 改进

- 更好的系统提示和工具描述
- 更好的 LLM 错误消息
## [0.12.0] - 2025-09-24

### 新增

- 添加 `print` UI 模式，可通过 `--ui print` 选项使用
- 添加日志记录和 `--debug` 选项

### 变更

- 捕获 EOF 错误以获得更好的体验
## [0.11.1] - 2025-09-22

### 变更

- 将 `max_retry_per_step` 重命名为 `max_retries_per_step`
## [0.11.0] - 2025-09-22

### 新增

- 添加 `/release-notes` 命令
- 为 LLM API 错误添加重试
- 添加循环控制配置，例如 `{"loop_control": {"max_steps_per_run": 50, "max_retry_per_step": 3}}`

### 变更

- 改进 `read_file` 工具在极端情况下的处理
- 防止 Ctrl-C 退出 CLI，强制使用 Ctrl-D 或 `exit` 代替
## [0.10.1] - 2025-09-18

- 让斜杠命令看起来更好一些
- 改进 `glob` 工具
## [0.10.0] - 2025-09-17

### 新增

- 添加 `read_file` 工具
- 添加 `write_file` 工具
- 添加 `glob` 工具
- 添加 `task` 工具

### 变更

- 改进工具调用可视化
- 改进会话管理
- 在 `--continue` 会话时恢复上下文使用
## [0.9.0] - 2025-09-15

- 移除 `--session` 和 `--continue` 选项
## [0.8.1] - 2025-09-14

- 修复配置模型转储
## [0.8.0] - 2025-09-14

- 添加 `shell` 工具和基本系统提示
- 添加工具调用可视化
- 添加上下文使用计数
- 支持中断代理循环
- 支持项目级 `AGENTS.md`
- 支持用 YAML 定义自定义代理
- 通过 `kimi -c` 支持一次性任务
