from __future__ import annotations

import asyncio
import os
import shlex
from collections.abc import Awaitable, Coroutine
from dataclasses import dataclass
from enum import Enum
from typing import Any

from kosong.chat_provider import APIStatusError, ChatProviderError
from kosong.message import ContentPart
from rich import box
from rich.console import Group, RenderableType
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from kimi_cli.soul import LLMNotSet, LLMNotSupported, MaxStepsReached, RunCancelled, Soul, run_soul
from kimi_cli.soul.kimisoul import KimiSoul
from kimi_cli.ui.shell.console import console
from kimi_cli.ui.shell.metacmd import get_meta_command
from kimi_cli.ui.shell.prompt import CustomPromptSession, PromptMode, toast
from kimi_cli.ui.shell.replay import replay_recent_history
from kimi_cli.ui.shell.update import LATEST_VERSION_FILE, UpdateResult, do_update, semver_tuple
from kimi_cli.ui.shell.visualize import visualize
from kimi_cli.utils.logging import logger
from kimi_cli.utils.signals import install_sigint_handler
from kimi_cli.utils.term import ensure_new_line
from kimi_cli.wire.message import StatusUpdate

# --- 赛博科技风配色方案 (优化护眼版) ---
_C_MAIN = "cyan1"  # 主色调 (青色) - 用于Logo
_C_ACCENT = "medium_orchid1"  # 强调色 (淡紫) - 用于更新/高亮
_C_TEXT = "white"  # 正文
_C_DIM = "grey50"  # 暗淡/标签 - 降低对比度
_C_BORDER = "grey35"  # 边框色 - 改为深灰，不再刺眼
_C_WARN = "gold1"  # 警告
_C_ERR = "red1"  # 错误
_C_SUCCESS = "green3"  # 在线状态 - 稍微调暗一点的绿


class Shell:
    """命令行交互式 Shell 主类"""

    def __init__(self, soul: Soul, welcome_info: list[WelcomeInfoItem] | None = None):
        self.soul = soul
        self._welcome_info = list(welcome_info or [])
        self._background_tasks: set[asyncio.Task[Any]] = set()

    async def run(self, command: str | None = None) -> bool:
        """运行交互式 Shell"""
        if command is not None:
            logger.info("执行命令: {command}", command=command)
            return await self._run_soul_command(command)

        self._start_background_task(self._auto_update())

        _print_welcome_info(self.soul.name or "Kimi CLI", self._welcome_info, self.soul)

        if isinstance(self.soul, KimiSoul):
            await replay_recent_history(self.soul.context.history)

        with CustomPromptSession(
            status_provider=lambda: self.soul.status,
            model_capabilities=self.soul.model_capabilities or set(),
            initial_thinking=isinstance(self.soul, KimiSoul) and self.soul.thinking,
        ) as prompt_session:
            while True:
                try:
                    ensure_new_line()
                    user_input = await prompt_session.prompt()
                except KeyboardInterrupt:
                    continue
                except EOFError:
                    self._print_goodbye()
                    break

                if not user_input:
                    continue

                if user_input.command in ["exit", "quit", "/exit", "/quit"]:
                    self._print_goodbye()
                    break

                if user_input.mode == PromptMode.SHELL:
                    await self._run_shell_command(user_input.command)
                    continue

                if user_input.command.startswith("/"):
                    await self._run_meta_command(user_input.command[1:])
                    continue

                await self._run_soul_command(user_input.content, user_input.thinking)

        return True

    def _print_goodbye(self) -> None:
        """打印退出信息"""
        grid = Table.grid(expand=False, padding=(0, 1))
        grid.add_column(justify="center")

        grid.add_row(Text.assemble(("⏻ ", _C_ERR), ("系统连接已断开", f"bold {_C_TEXT}")))
        grid.add_row(Text("SESSION TERMINATED", style=f"italic {_C_DIM}"))

        console.print()
        console.print(Padding(grid, (0, 1)))
        console.print()

    async def _run_shell_command(self, command: str) -> None:
        """在前台运行 Shell 命令"""
        if not command.strip():
            return

        stripped_cmd = command.strip()
        split_cmd = shlex.split(stripped_cmd)

        if len(split_cmd) == 2 and split_cmd[0] == "cd":
            console.print(f"[{_C_WARN}]⚠ 警告: Shell 目录变更不会在会话中保留[/{_C_WARN}]")
            return

        proc: asyncio.subprocess.Process | None = None

        def _handler():
            if proc:
                proc.terminate()

        loop = asyncio.get_running_loop()
        remove_sigint = install_sigint_handler(loop, _handler)
        try:
            proc = await asyncio.create_subprocess_shell(command)
            await proc.wait()
        except Exception as e:
            console.print(f"[{_C_ERR}]✖ 执行失败: {e}[/{_C_ERR}]")
        finally:
            remove_sigint()

    async def _run_meta_command(self, command_str: str):
        """执行元命令"""
        from kimi_cli.cli import Reload

        parts = command_str.split(" ")
        command_name = parts[0]
        command_args = parts[1:]
        command = get_meta_command(command_name)

        if command is None:
            console.print(f"[{_C_ERR}]✖ 未知指令: /{command_name}[/{_C_ERR}]")
            return

        if command.kimi_soul_only and not isinstance(self.soul, KimiSoul):
            console.print(f"[{_C_ERR}]✖ 当前系统模式不支持此指令[/{_C_ERR}]")
            return

        try:
            ret = command.func(self, command_args)
            if isinstance(ret, Awaitable):
                await ret
        except (LLMNotSet, ChatProviderError) as e:
            console.print(f"[{_C_ERR}]✖ 系统错误: {e}[/{_C_ERR}]")
        except asyncio.CancelledError:
            console.print(f"[{_C_DIM}]◈ 操作已取消[/{_C_DIM}]")
        except Reload:
            raise
        except BaseException as e:
            logger.exception("Command error")
            console.print(f"[{_C_ERR}]✖ 严重错误: {e}[/{_C_ERR}]")

    async def _run_soul_command(
        self,
        user_input: str | list[ContentPart],
        thinking: bool | None = None,
    ) -> bool:
        """运行 Soul 命令"""
        cancel_event = asyncio.Event()

        def _handler():
            cancel_event.set()

        loop = asyncio.get_running_loop()
        remove_sigint = install_sigint_handler(loop, _handler)

        try:
            if isinstance(self.soul, KimiSoul) and thinking is not None:
                self.soul.set_thinking(thinking)

            await run_soul(
                self.soul,
                user_input,
                lambda wire: visualize(
                    wire.ui_side(merge=False),
                    initial_status=StatusUpdate(context_usage=self.soul.status.context_usage),
                    cancel_event=cancel_event,
                ),
                cancel_event,
                self.soul.wire_file_backend if isinstance(self.soul, KimiSoul) else None,
            )
            return True
        except Exception as e:
            if isinstance(e, (LLMNotSet, LLMNotSupported, ChatProviderError)):
                console.print(f"[{_C_ERR}]✖ 服务异常: {e}[/{_C_ERR}]")
            elif isinstance(e, MaxStepsReached):
                console.print(f"[{_C_WARN}]⚡ 已达最大处理步数[/{_C_WARN}]")
            elif isinstance(e, RunCancelled):
                console.print(f"[{_C_DIM}]◈ 用户中断操作[/{_C_DIM}]")
            else:
                logger.exception("Runtime error")
                console.print(f"[{_C_ERR}]✖ 系统内核错误: {e}[/{_C_ERR}]")
        finally:
            remove_sigint()
        return False

    async def _auto_update(self) -> None:
        """后台更新检查"""
        try:
            result = await do_update(print=False, check_only=True)
            if result == UpdateResult.UPDATE_AVAILABLE:
                toast("系统发现新版本", topic="update", duration=10.0)
        except Exception:
            pass

    def _start_background_task(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(lambda t: self._background_tasks.discard(t))
        return task


@dataclass(slots=True)
class WelcomeInfoItem:
    class Level(Enum):
        INFO = _C_DIM
        WARN = _C_WARN
        ERROR = _C_ERR

    name: str
    value: str
    level: Level = Level.INFO


def _get_mcp_stats(soul: Soul | None = None) -> tuple[int, int]:
    """安全获取 MCP 统计 - 返回 (工具数量, 服务器数量)"""
    try:
        if not soul or not isinstance(soul, KimiSoul):
            return 0, 0

        if not hasattr(soul, "_agent") or not soul._agent:
            return 0, 0

        toolset = getattr(soul._agent, "toolset", None)
        if not toolset or not hasattr(toolset, "tools"):
            return 0, 0

        mcp_tools = [t for t in toolset.tools if hasattr(t, "_mcp_tool")]
        
        # 简化统计：如果有 MCP 工具，则认为有 MCP 服务器
        # 这里暂时无法准确统计服务器数量，因为工具对象中没有服务器信息
        # 所以我们返回工具数量作为主要指标
        return len(mcp_tools), 1 if mcp_tools else 0
    except Exception:
        return 0, 0


def _print_welcome_info(
    name: str, info_items: list[WelcomeInfoItem], soul: Soul | None = None
) -> None:
    """打印科技风格仪表盘欢迎信息"""
    from kimi_cli.constant import VERSION as current_version

    mcp_tool_count, mcp_server_count = _get_mcp_stats(soul)

    # 1. 构建主布局
    layout = Table.grid(expand=True)

    # 2. 顶部 Header
    header_table = Table.grid(expand=True)
    header_table.add_column(justify="left", ratio=1)
    header_table.add_column(justify="right", ratio=1)

    logo_text = Text("KIMI CLI", style=f"bold {_C_MAIN}")
    status_text = Text.assemble(
        ("● ", _C_SUCCESS), ("系统在线 ", f"{_C_SUCCESS} bold"), (f"v{current_version}", _C_DIM)
    )
    header_table.add_row(logo_text, status_text)

    layout.add_row(header_table)

    # 装饰线 - 使用更低调的颜色
    layout.add_row(Text("─" * 40, style=f"dim {_C_BORDER}"))
    layout.add_row(Text(""))  # Spacer

    # 3. 信息概览区
    info_grid = Table.grid(padding=(0, 2))
    info_grid.add_column(style=f"{_C_DIM}", justify="left", width=4)  # Icon 列
    info_grid.add_column(style=f"{_C_TEXT}", justify="left", width=12)  # Label 列
    info_grid.add_column(style=_C_DIM, justify="left")  # Value 列

    # MCP 状态
    if mcp_tool_count > 0:
        if mcp_server_count > 1:
            info_grid.add_row("⚡", "MCP 扩展", Text(f"已加载 {mcp_tool_count} 个工具", style=_C_TEXT))
        else:
            info_grid.add_row("⚡", "MCP 扩展", Text(f"已加载 {mcp_tool_count} 个工具", style=_C_TEXT))

    # 更新检查
    if LATEST_VERSION_FILE.exists():
        try:
            latest = LATEST_VERSION_FILE.read_text(encoding="utf-8").strip()
            if semver_tuple(latest) > semver_tuple(current_version):
                info_grid.add_row(
                    "↑", "系统更新", Text(f"新版本 {latest} 准备就绪", style=_C_ACCENT)
                )
        except Exception:
            pass

    # 其他信息 (Model, Path, etc.)
    # 这里根据传入的 info_items 显示
    for item in info_items:
        icon = "ℹ"
        if item.level == WelcomeInfoItem.Level.WARN:
            icon = "⚠"
        if item.level == WelcomeInfoItem.Level.ERROR:
            icon = "✖"

        info_grid.add_row(
            icon,
            item.name,
            Text(item.value, style=item.level.value),
        )

    if mcp_tool_count == 0 and not info_items:
        info_grid.add_row("◈", "系统就绪", "等待指令输入...")

    layout.add_row(Padding(info_grid, (0, 0, 0, 1)))
    layout.add_row(Text(""))  # Spacer

    # 4. 底部操作栏 - 使用 Text.assemble 避免 markup 解析问题
    footer_text = Text.assemble(
        ("指令集 ", _C_DIM),
        ("/help", f"bold {_C_TEXT}"),
        (" • ", _C_DIM),
        ("工具箱 ", _C_DIM),
        ("/mcp", f"bold {_C_TEXT}"),
        (" • ", _C_DIM),
        ("退出 ", _C_DIM),
        ("Ctrl+D", f"bold {_C_TEXT}"),
    )

    panel = Panel(
        layout,
        border_style=_C_BORDER,
        box=box.ROUNDED,
        padding=(0, 2),
        subtitle=footer_text,
        subtitle_align="right",
    )

    console.print()
    console.print(panel)
    console.print()
