from typing import TYPE_CHECKING

from rich.console import Group, Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from kimi_cli.soul.kimisoul import KimiSoul
from kimi_cli.ui.shell.metacmd import meta_command

if TYPE_CHECKING:
    from kimi_cli.ui.shell import Shell

console = Console()


@meta_command(kimi_soul_only=True)
def mcp(app: "Shell", args: list[str]):
    """显示已加载的 MCP 服务器和工具信息"""
    assert isinstance(app.soul, KimiSoul)

    toolset = app.soul._agent.toolset
    mcp_tools = []
    
    # 收集所有 MCP 工具
    for tool in toolset.tools:
        if hasattr(tool, '_mcp_tool') and hasattr(tool, '_client'):
            mcp_tools.append(tool)
    
    if not mcp_tools:
        console.print(
            Panel(
                "[yellow]未加载任何 MCP 工具[/yellow]",
                title="MCP 服务器状态",
                border_style="blue",
                padding=(1, 2),
            )
        )
        return
    
    # 按 MCP 服务器分组工具
    server_groups = {}
    for tool in mcp_tools:
        client = tool._client
        # 尝试从客户端获取服务器信息
        server_info = "未知服务器"
        if hasattr(client, '_config'):
            config = client._config
            if isinstance(config, dict):
                if 'url' in config:
                    server_info = f"URL: {config['url']}"
                elif 'command' in config:
                    server_info = f"命令: {config['command']} {' '.join(config.get('args', []))}"
        
        if server_info not in server_groups:
            server_groups[server_info] = []
        server_groups[server_info].append(tool)
    
    # 创建输出内容
    content_parts = []
    
    for server_info, tools in server_groups.items():
        # 服务器信息面板
        server_panel = Panel(
            Text(f"已加载 {len(tools)} 个工具", style="bold"),
            title=server_info,
            border_style="green",
            padding=(0, 1),
        )
        content_parts.append(server_panel)
        
        # 工具列表表格
        tools_table = Table(show_header=True, header_style="bold blue", box=None)
        tools_table.add_column("工具名称", style="cyan")
        tools_table.add_column("描述", style="white")
        
        for tool in tools:
            tool_name = tool._mcp_tool.name
            tool_desc = tool._mcp_tool.description or "无描述"
            # 截断过长的描述
            if len(tool_desc) > 60:
                tool_desc = tool_desc[:57] + "..."
            
            tools_table.add_row(tool_name, tool_desc)
        
        content_parts.append(tools_table)
        content_parts.append("")  # 空行分隔
    
    # 总体统计信息
    summary_text = Text()
    summary_text.append("总计: ", style="bold")
    summary_text.append(f"{len(mcp_tools)} 个 MCP 工具", style="green")
    summary_text.append(f" 来自 {len(server_groups)} 个服务器", style="green")
    
    summary_panel = Panel(
        summary_text,
        title="统计信息",
        border_style="yellow",
        padding=(0, 1),
    )
    
    # 显示所有内容
    console.print(
        Panel(
            Group(
                *content_parts,
                summary_panel,
            ),
            title="MCP 服务器和工具",
            border_style="blue",
            padding=(1, 2),
        )
    )