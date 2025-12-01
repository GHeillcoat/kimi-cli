# CLI 加载时间

## `src/kimi_cli/__init__.py` 必须为空

**范围**

`src/kimi_cli/__init__.py`

**要求**

`src/kimi_cli/__init__.py` 文件必须为空，不包含任何代码或导入。

## `src/kimi_cli/cli.py` 中没有不必要的导入

**范围**

`src/kimi_cli/cli.py`

**要求**

`src/kimi_cli/cli.py` 文件在顶层不得导入 `kimi_cli` 或 `kosong` 中的任何模块，除了 `kimi_cli.constant`。

## `src/kimi_cli/app.py` 中按需导入

**范围**

`src/kimi_cli/app.py`

**要求**

`src/kimi_cli/app.py` 文件在顶层不得导入任何以 `kimi_cli.ui` 为前缀的模块；相反，UI 特定的模块应按需在函数内部导入。

<examples>

```python
# 顶层
from kimi_cli.ui.shell import ShellApp  # 不正确：UI 模块的顶层导入

# 函数内部
async def run_shell_app(...):
    from kimi_cli.ui.shell import ShellApp  # 正确：按需导入
    app = ShellApp(...)
    await app.run()
```

</examples>

## `--help` 应该运行快速

**范围**

无特定源文件。

**要求**

`uv run kimi --help` 在 3 次热身运行后，5 次运行的平均时间必须小于 150 毫秒。
