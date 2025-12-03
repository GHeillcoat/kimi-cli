from __future__ import annotations

import json
from typing import TYPE_CHECKING

from kosong.message import (
    AudioURLPart,
    ContentPart,
    ImageURLPart,
    Message,
    TextPart,
    ThinkPart,
    ToolCall,
)
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.text import Text

from kimi_cli.soul.kimisoul import KimiSoul
from kimi_cli.ui.shell.console import console
from kimi_cli.ui.shell.metacmd import meta_command

if TYPE_CHECKING:
    from kimi_cli.ui.shell import Shell


def _format_content_part(part: ContentPart) -> Text | Panel | Group:
    """Format a single content part."""
    match part:
        case TextPart(text=text):
            # Check if it looks like a system tag
            if text.strip().startswith("<system>") and text.strip().endswith("</system>"):
                return Panel(
                    text.strip()[8:-9].strip(),
                    title="[dim]系统[/dim]",
                    border_style="dim yellow",
                    padding=(0, 1),
                )
            return Text(text, style="white")

        case ThinkPart(think=think):
            return Panel(
                think,
                title="[dim]思考中[/dim]",
                border_style="dim cyan",
                padding=(0, 1),
            )

        case ImageURLPart(image_url=img):
            url_display = img.url[:80] + "..." if len(img.url) > 80 else img.url
            id_text = f" (id: {img.id})" if img.id else ""
            return Text(f"[图像{id_text}] {url_display}", style="blue")

        case AudioURLPart(audio_url=audio):
            url_display = audio.url[:80] + "..." if len(audio.url) > 80 else audio.url
            id_text = f" (id: {audio.id})" if audio.id else ""
            return Text(f"[音频{id_text}] {url_display}", style="blue")

        case _:
            return Text(f"[未知内容类型: {type(part).__name__}]", style="red")


def _format_tool_call(tool_call: ToolCall) -> Panel:
    """Format a tool call."""
    args = tool_call.function.arguments or "{}"
    try:
        args_formatted = json.dumps(json.loads(args), indent=2)
        args_syntax = Syntax(args_formatted, "json", theme="monokai", padding=(0, 1))
    except json.JSONDecodeError:
        args_syntax = Text(args, style="red")

    content = Group(
        Text(f"函数: {tool_call.function.name}", style="bold cyan"),
        Text(f"调用ID: {tool_call.id}", style="dim"),
        Text("参数:", style="bold"),
        args_syntax,
    )

    return Panel(
        content,
        title="[bold yellow]工具调用[/bold yellow]",
        border_style="yellow",
        padding=(0, 1),
    )


def _format_message(msg: Message, index: int) -> Panel:
    """Format a single message."""
    # Role styling
    role_colors = {
        "system": "magenta",
        "developer": "magenta",
        "user": "green",
        "assistant": "blue",
        "tool": "yellow",
    }
    role_map = {
        "system": "系统",
        "developer": "开发者",
        "user": "用户",
        "assistant": "助手",
        "tool": "工具",
    }
    role_color = role_colors.get(msg.role, "white")
    role_name = role_map.get(msg.role, msg.role).upper()
    role_text = f"[bold {role_color}]{role_name}[/bold {role_color}]"

    # Add name if present
    if msg.name:
        role_text += f" [dim]({msg.name})[/dim]"

    # Add tool call ID for tool messages
    if msg.tool_call_id:
        role_text += f" [dim]→ {msg.tool_call_id}[/dim]"

    # Format content
    content_items: list = []

    for part in msg.content:
        formatted = _format_content_part(part)
        content_items.append(formatted)

    # Add tool calls if present
    if msg.tool_calls:
        if content_items:
            content_items.append(Text())  # Empty line
        for tool_call in msg.tool_calls:
            content_items.append(_format_tool_call(tool_call))

    # Combine all content
    if not content_items:
        content_items.append(Text("[空消息]", style="dim italic"))

    group = Group(*content_items)

    # Create panel
    title = f"#{index + 1} {role_text}"
    if msg.partial:
        title += " [dim italic](部分)[/dim italic]"

    return Panel(
        group,
        title=title,
        border_style=role_color,
        padding=(0, 1),
    )


@meta_command(kimi_soul_only=True)
def debug(app: Shell, args: list[str]):
    """调试上下文"""
    assert isinstance(app.soul, KimiSoul)

    context = app.soul._context
    history = context.history

    if not history:
        console.print(
            Panel(
                "上下文为空 - 尚无消息",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        return

    # Build the debug output
    output_items = [
        Panel(
            Group(
                Text(f"总消息数: {len(history)}", style="bold"),
                Text(f"Token 数量: {context.token_count:,}", style="bold"),
                Text(f"检查点数: {context.n_checkpoints}", style="bold"),
                Text(f"轨迹文件: {context._file_backend}", style="dim"),
            ),
            title="[bold]上下文信息[/bold]",
            border_style="cyan",
            padding=(0, 1),
        ),
        Rule(style="dim"),
    ]

    # Add all messages
    for idx, msg in enumerate(history):
        output_items.append(_format_message(msg, idx))

    # Display using rich pager
    display_group = Group(*output_items)

    # Use pager to display
    with console.pager(styles=True):
        console.print(display_group)
