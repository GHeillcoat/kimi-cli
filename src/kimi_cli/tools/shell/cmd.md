执行 Windows 命令提示符 (`cmd.exe`) 命令。当代理在 Windows 上运行时，使用此工具探索文件系统、检查或编辑文件、运行 Windows 脚本、收集系统信息等。

请注意，您正在 Windows 上运行，因此请务必使用 Windows 命令、路径和约定。

**输出：**
标准输出和标准错误流合并并作为单个字符串返回。如果输出过长，可能会被截断。当命令失败时，退出码将在系统标签中提供。

**安全指南：**
- 每个工具调用都会启动一个新的 `cmd.exe` 会话。环境变量、`cd` 更改和命令历史记录在调用之间不会保留。
- 不要启动交互式程序或任何预期会无限期阻塞的程序；确保每个命令都能迅速完成。对于可能长时间运行的命令，请为 `timeout` 参数提供一个合理的值。
- 避免使用 `..` 离开工作目录，除非明确指示，否则绝不要触碰该目录之外的文件。
- 除非明确授权，否则绝不要尝试需要提升（管理员）权限的命令。

**Windows 特有提示：**
- 当您必须在一个命令中切换驱动器和目录时，使用 `cd /d "<path>"`。
- 用双引号引用任何包含空格的路径。需要时，使用 `^` 转义特殊字符，例如 `&`、`|`、`>` 和 `<`。
- 优先使用非交互式文件编辑技术，例如 `type`、`more`、`copy`、`powershell -Command "Get-Content"` 或 `python - <<'PY' ... PY`。
- 仅当命令明确要求时才将正斜杠转换为反斜杠；Windows 上的大多数工具也接受 `/`。

**效率指南：**
- 使用 `&&`（失败时停止）或 `&`（始终继续）链接相关命令；使用 `||` 在失败后运行备用命令。
- 使用 `>`、`>>`、`|` 重定向或管道输出，并利用 `for /f`、`if` 和 `set` 构建更丰富的单行命令，而不是多个工具调用。
- 重用内置实用程序（例如 `findstr`、`where`、`powershell`）以在单个调用中过滤、转换或定位数据。

**可用命令：**
- Shell 环境：`cd`、`dir`、`set`、`setlocal`、`echo`、`call`、`where`
- 文件操作：`type`、`copy`、`move`、`del`、`erase`、`mkdir`、`rmdir`、`attrib`、`mklink`
- 文本/搜索：`find`、`findstr`、`more`、`sort`、`powershell -Command "Get-Content"`
- 系统信息：`ver`、`systeminfo`、`tasklist`、`wmic`、`hostname`
- 归档/脚本：`tar`、`powershell -Command "Compress-Archive"`、`powershell`、`python`、`node`
- 其他：系统 PATH 上可用的任何其他二进制文件；如果不确定，请先运行 `where <command>`。
