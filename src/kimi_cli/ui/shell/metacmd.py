from __future__ import annotations

import tempfile
import webbrowser
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, overload

from kosong.message import Message
from rich.panel import Panel

import kimi_cli.prompts as prompts
from kimi_cli.cli import Reload
from kimi_cli.soul.agent import load_agents_md
from kimi_cli.soul.context import Context
from kimi_cli.soul.kimisoul import KimiSoul
from kimi_cli.soul.message import system
from kimi_cli.ui.shell.console import console
from kimi_cli.utils.changelog import CHANGELOG, format_release_notes
from kimi_cli.utils.logging import logger

if TYPE_CHECKING:
    from kimi_cli.ui.shell import Shell

type MetaCmdFunc = Callable[[Shell, list[str]], None | Awaitable[None]]
"""
一个作为元命令运行的函数。

Raises:
    LLMNotSet: 当未设置LLM时。
    ChatProviderError: 当LLM提供商返回错误时。
    Reload: 当应重新加载配置时。
    asyncio.CancelledError: 当用户中断命令时。

这与 `Soul.run` 方法非常相似。
"""


@dataclass(frozen=True, slots=True, kw_only=True)
class MetaCommand:
    name: str
    description: str
    func: MetaCmdFunc
    aliases: list[str]
    kimi_soul_only: bool
    # TODO: actually kimi_soul_only meta commands should be defined in KimiSoul

    def slash_name(self):
        """/name (aliases)"""
        if self.aliases:
            return f"/{self.name} ({', '.join(self.aliases)})"
        return f"/{self.name}"


# primary name -> MetaCommand
_meta_commands: dict[str, MetaCommand] = {}
# primary name or alias -> MetaCommand
_meta_command_aliases: dict[str, MetaCommand] = {}


def get_meta_command(name: str) -> MetaCommand | None:
    return _meta_command_aliases.get(name)


def get_meta_commands() -> list[MetaCommand]:
    """Get all unique primary meta commands (without duplicating aliases)."""
    return list(_meta_commands.values())


@overload
def meta_command(func: MetaCmdFunc, /) -> MetaCmdFunc: ...


@overload
def meta_command(
    *,
    name: str | None = None,
    aliases: Sequence[str] | None = None,
    kimi_soul_only: bool = False,
) -> Callable[[MetaCmdFunc], MetaCmdFunc]: ...


def meta_command(
    func: MetaCmdFunc | None = None,
    *,
    name: str | None = None,
    aliases: Sequence[str] | None = None,
    kimi_soul_only: bool = False,
) -> (
    MetaCmdFunc
    | Callable[
        [MetaCmdFunc],
        MetaCmdFunc,
    ]
):
    """Decorator to register a meta command with optional custom name and aliases.

    Usage examples:
      @meta_command
      def help(app: App, args: list[str]): ...

      @meta_command(name="run")
      def start(app: App, args: list[str]): ...

      @meta_command(aliases=["h", "?", "assist"])
      def help(app: App, args: list[str]): ...
    """

    def _register(f: MetaCmdFunc):
        primary = name or f.__name__
        alias_list = list(aliases) if aliases else []

        # Create the primary command with aliases
        cmd = MetaCommand(
            name=primary,
            description=(f.__doc__ or "").strip(),
            func=f,
            aliases=alias_list,
            kimi_soul_only=kimi_soul_only,
        )

        # Register primary command
        _meta_commands[primary] = cmd
        _meta_command_aliases[primary] = cmd

        # Register aliases pointing to the same command
        for alias in alias_list:
            _meta_command_aliases[alias] = cmd

        return f

    if func is not None:
        return _register(func)
    return _register


@meta_command(aliases=["quit"])
def exit(app: Shell, args: list[str]):
    """退出应用程序"""
    # should be handled by `Shell`
    raise NotImplementedError


_HELP_MESSAGE_FMT = """
[grey50]▌ 救命！我需要有个人来。救命！不是随便哪个人。[/grey50]
[grey50]▌ 救命！你知道我需要有个人。救命！[/grey50]
[grey50]▌ ― 披头士乐队, [italic]《救命！》[/italic][/grey50]

当然，Kimi CLI 随时准备提供帮助！
只需向我发送消息，我将帮助您完成任务！

此外还提供以下元命令：

[grey50]{meta_commands_md}[/grey50]
"""


@meta_command(aliases=["h", "?"])
def help(app: Shell, args: list[str]):
    """显示帮助信息"""
    console.print(
        Panel(
            _HELP_MESSAGE_FMT.format(
                meta_commands_md="\n".join(
                    f" • {command.slash_name()}: {command.description}"
                    for command in get_meta_commands()
                )
            ).strip(),
            title="Kimi CLI 帮助",
            border_style="wheat4",
            expand=False,
            padding=(1, 2),
        )
    )


@meta_command
def version(app: Shell, args: list[str]):
    """显示版本信息"""
    from kimi_cli.constant import VERSION

    console.print(f"kimi, version {VERSION}")


@meta_command(name="release-notes")
def release_notes(app: Shell, args: list[str]):
    """显示发行说明"""
    text = format_release_notes(CHANGELOG, include_lib_changes=False)
    with console.pager(styles=True):
        console.print(Panel.fit(text, border_style="wheat4", title="发行说明"))


@meta_command
def feedback(app: Shell, args: list[str]):
    """提交反馈以帮助 Kimi CLI 变得更好"""

    ISSUE_URL = "https://github.com/MoonshotAI/kimi-cli/issues"
    if webbrowser.open(ISSUE_URL):
        return
    console.print(f"请通过以下地址提交反馈: [underline]{ISSUE_URL}[/underline].")


@meta_command(kimi_soul_only=True)
async def init(app: Shell, args: list[str]):
    """分析代码库并生成一个 `AGENTS.md` 文件"""
    assert isinstance(app.soul, KimiSoul)

    soul_bak = app.soul
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info("正在运行 `/init`")
        console.print("正在分析代码库...")
        tmp_context = Context(file_backend=Path(temp_dir) / "context.jsonl")
        app.soul = KimiSoul(soul_bak._agent, context=tmp_context)
        ok = await app._run_soul_command(prompts.INIT, thinking=False)

        if ok:
            console.print(
                "代码库分析成功！"
                "已创建 [underline]AGENTS.md[/underline] 文件。"
            )
        else:
            console.print("[red]代码库分析失败。[/red]")

    app.soul = soul_bak
    agents_md = load_agents_md(soul_bak._runtime.builtin_args.KIMI_WORK_DIR)
    system_message = system(
        "用户刚刚运行了 /init 元命令。"
        "系统已经分析了代码库并生成了一个 `AGENTS.md` 文件。"
        f"最新的 AGENTS.md 文件内容如下：\n{agents_md}"
    )
    await app.soul._context.append_message(Message(role="user", content=[system_message]))


@meta_command(aliases=["reset"], kimi_soul_only=True)
async def clear(app: Shell, args: list[str]):
    """清空上下文"""
    assert isinstance(app.soul, KimiSoul)

    if app.soul._context.n_checkpoints == 0:
        raise Reload()

    await app.soul._context.clear()
    raise Reload()


@meta_command(kimi_soul_only=True)
async def compact(app: Shell, args: list[str]):
    """压缩上下文"""
    assert isinstance(app.soul, KimiSoul)

    if app.soul._context.n_checkpoints == 0:
        console.print("[yellow]上下文是空的。[/yellow]")
        return

    logger.info("正在运行 `/compact`")
    with console.status("[cyan]正在压缩...[/cyan]"):
        await app.soul.compact_context()
    console.print("[green]✓[/green] 上下文已压缩。")


@meta_command(kimi_soul_only=True)
async def yolo(app: Shell, args: list[str]):
    """启用 YOLO 模式（自动批准所有操作）"""
    assert isinstance(app.soul, KimiSoul)

    app.soul._runtime.approval.set_yolo(True)
    console.print("[green]✓[/green] 人生苦短，YOLO 当先！")


from . import (  # noqa: E402
    debug,  # noqa: F401
    mcp_info,  # noqa: F401
    setup,  # noqa: F401
    update,  # noqa: F401
)
