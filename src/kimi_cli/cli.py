from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Annotated, Literal

import typer

from kimi_cli.config import load_config
from kimi_cli.constant import VERSION


class Reload(Exception):
    """重新加载配置。"""

    pass


cli = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Kimi，你的下一代命令行智能体。",
    invoke_without_command=True,
)

UIMode = Literal["shell", "print", "acp", "wire"]
InputFormat = Literal["text", "stream-json"]
OutputFormat = Literal["text", "stream-json"]


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"Kimi，版本 {VERSION}")
        raise typer.Exit()


@cli.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="显示版本信息并退出。",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            help="打印详细信息。默认：否。",
        ),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help="记录调试信息。默认：否。",
        ),
    ] = False,
    agent_file: Annotated[
        Path | None,
        typer.Option(
            "--agent-file",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="自定义智能体规约文件。默认：使用内置的默认智能体。",
        ),
    ] = None,
    model_name: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            help="要使用的LLM模型。默认：配置文件中设置的默认模型。",
        ),
    ] = None,
    local_work_dir: Annotated[
        Path | None,
        typer.Option(
            "--work-dir",
            "-w",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            writable=True,
            help="智能体的工作目录。默认：当前目录。",
        ),
    ] = None,
    continue_: Annotated[
        bool,
        typer.Option(
            "--continue",
            "-C",
            help="继续此工作目录的上一个会话。默认：否。",
        ),
    ] = False,
    command: Annotated[
        str | None,
        typer.Option(
            "--command",
            "-c",
            "--query",
            "-q",
            help="向智能体提出的用户查询。默认：交互式提示。",
        ),
    ] = None,
    print_mode: Annotated[
        bool,
        typer.Option(
            "--print",
            help="以打印模式（非交互式）运行。注意：打印模式会隐式启用 --yolo。",
        ),
    ] = False,
    acp_mode: Annotated[
        bool,
        typer.Option(
            "--acp",
            help="作为 ACP 服务器运行。",
        ),
    ] = False,
    wire_mode: Annotated[
        bool,
        typer.Option(
            "--wire",
            help="作为 Wire 服务器运行 (实验性功能)。",
        ),
    ] = False,
    input_format: Annotated[
        InputFormat | None,
        typer.Option(
            "--input-format",
            help="要使用的输入格式。必须与 --print 一起使用，且输入必须通过 stdin 管道传入。默认：text。",
        ),
    ] = None,
    output_format: Annotated[
        OutputFormat | None,
        typer.Option(
            "--output-format",
            help="要使用的输出格式。必须与 --print 一起使用。默认：text。",
        ),
    ] = None,
    mcp_config_file: Annotated[
        list[Path] | None,
        typer.Option(
            "--mcp-config-file",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="要加载的 MCP 配置文件。可多次使用此选项以指定多个 MCP 配置。默认：无。",
        ),
    ] = None,
    mcp_config: Annotated[
        list[str] | None,
        typer.Option(
            "--mcp-config",
            help="要加载的 MCP 配置 JSON。可多次使用此选项以指定多个 MCP 配置。默认：无。",
        ),
    ] = None,
    yolo: Annotated[
        bool,
        typer.Option(
            "--yolo",
            "--yes",
            "-y",
            "--auto-approve",
            help="自动批准所有操作。默认：否。",
        ),
    ] = False,
    thinking: Annotated[
        bool | None,
        typer.Option(
            "--thinking",
            help="如果支持，则启用思考模式。默认：与上次设置相同。",
        ),
    ] = None,
):
    """Kimi，你的下一代命令行智能体。"""
    del version  # 已在回调中处理

    # 如果没有指定子命令，则运行主功能
    if ctx.invoked_subcommand is None:
        from kaos.path import KaosPath
        from kimi_cli.app import KimiCLI, enable_logging
        from kimi_cli.metadata import load_metadata, save_metadata
        from kimi_cli.session import Session
        from kimi_cli.utils.logging import logger

        enable_logging(debug)

        special_flags = {
            "--print": print_mode,
            "--acp": acp_mode,
            "--wire": wire_mode,
        }
        active_specials = [flag for flag, active in special_flags.items() if active]
        if len(active_specials) > 1:
            raise typer.BadParameter(
                f"无法合并使用 {', '.join(active_specials)}。",
                param_hint=active_specials[0],
            )

        ui: UIMode = "shell"
        if print_mode:
            ui = "print"
        elif acp_mode:
            ui = "acp"
        elif wire_mode:
            ui = "wire"

        if command is not None:
            command = command.strip()
            if not command:
                raise typer.BadParameter("命令不能为空", param_hint="--command")

        if input_format is not None and ui != "print":
            raise typer.BadParameter(
                "输入格式仅在打印用户界面（print UI）中受支持",
                param_hint="--input-format",
            )
        if output_format is not None and ui != "print":
            raise typer.BadParameter(
                "输出格式仅在打印用户界面（print UI）中受支持",
                param_hint="--output-format",
            )

        # 从配置文件加载永久 MCP 配置
        config = load_config()
        mcp_configs = list(config.mcp_configs)

        # 添加命令行指定的临时 MCP 配置
        file_configs = list(mcp_config_file or [])
        raw_mcp_config = list(mcp_config or [])

        try:
            mcp_configs.extend([json.loads(conf.read_text(encoding="utf-8")) for conf in file_configs])
        except json.JSONDecodeError as e:
            raise typer.BadParameter(f"无效的 JSON: {e}", param_hint="--mcp-config-file") from e

        try:
            mcp_configs.extend([json.loads(conf) for conf in raw_mcp_config])
        except json.JSONDecodeError as e:
            raise typer.BadParameter(f"无效的 JSON: {e}", param_hint="--mcp-config") from e

        async def _run() -> bool:
            work_dir = (
                KaosPath.unsafe_from_local_path(local_work_dir) if local_work_dir else KaosPath.cwd()
            )

            if continue_:
                session = await Session.continue_(work_dir)
                if session is None:
                    raise typer.BadParameter(
                        "在当前工作目录中未找到先前的会话",
                        param_hint="--continue",
                    )
                logger.info("继续上一个会话: {session_id}", session_id=session.id)
            else:
                session = await Session.create(work_dir)
                logger.info("已创建新会话: {session_id}", session_id=session.id)
            logger.debug("上下文文件: {context_file}", context_file=session.context_file)

            if thinking is None:
                metadata = load_metadata()
                thinking_mode = metadata.thinking
            else:
                thinking_mode = thinking

            instance = await KimiCLI.create(
                session,
                yolo=yolo or (ui == "print"),  # 打印模式意味着自动批准（yolo）
                mcp_configs=mcp_configs,
                model_name=model_name,
                thinking=thinking_mode,
                agent_file=agent_file,
            )
            match ui:
                case "shell":
                    succeeded = await instance.run_shell(command)
                case "print":
                    succeeded = await instance.run_print(
                        input_format or "text",
                        output_format or "text",
                        command,
                    )
                case "acp":
                    if command is not None:
                        logger.warning("ACP 服务器忽略 command 参数")
                    await instance.run_acp()
                    succeeded = True
                case "wire":
                    if command is not None:
                        logger.warning("Wire 服务器忽略 command 参数")
                    await instance.run_wire_stdio()
                    succeeded = True

            if succeeded:
                metadata = load_metadata()

                # 使用上一个会话更新 work_dir 元数据
                work_dir_meta = metadata.get_work_dir_meta(session.work_dir)

                if work_dir_meta is None:
                    logger.warning(
                        "标记上一个会话时缺少工作目录元数据，正在重新创建: {work_dir}",
                        work_dir=session.work_dir,
                    )
                    work_dir_meta = metadata.new_work_dir_meta(session.work_dir)

                work_dir_meta.last_session_id = session.id

                # 更新思考模式
                metadata.thinking = instance.soul.thinking

                save_metadata(metadata)

            return succeeded

        while True:
            try:
                succeeded = asyncio.run(_run())
                if succeeded:
                    break
                raise typer.Exit(code=1)
            except Reload:
                continue


@cli.command()
def kimi(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="显示版本信息并退出。",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            help="打印详细信息。默认：否。",
        ),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help="记录调试信息。默认：否。",
        ),
    ] = False,
    agent_file: Annotated[
        Path | None,
        typer.Option(
            "--agent-file",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="自定义智能体规约文件。默认：使用内置的默认智能体。",
        ),
    ] = None,
    model_name: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            help="要使用的LLM模型。默认：配置文件中设置的默认模型。",
        ),
    ] = None,
    local_work_dir: Annotated[
        Path | None,
        typer.Option(
            "--work-dir",
            "-w",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            writable=True,
            help="智能体的工作目录。默认：当前目录。",
        ),
    ] = None,
    continue_: Annotated[
        bool,
        typer.Option(
            "--continue",
            "-C",
            help="继续此工作目录的上一个会话。默认：否。",
        ),
    ] = False,
    command: Annotated[
        str | None,
        typer.Option(
            "--command",
            "-c",
            "--query",
            "-q",
            help="向智能体提出的用户查询。默认：交互式提示。",
        ),
    ] = None,
    print_mode: Annotated[
        bool,
        typer.Option(
            "--print",
            help="以打印模式（非交互式）运行。注意：打印模式会隐式启用 --yolo。",
        ),
    ] = False,
    acp_mode: Annotated[
        bool,
        typer.Option(
            "--acp",
            help="作为 ACP 服务器运行。",
        ),
    ] = False,
    wire_mode: Annotated[
        bool,
        typer.Option(
            "--wire",
            help="作为 Wire 服务器运行 (实验性功能)。",
        ),
    ] = False,
    input_format: Annotated[
        InputFormat | None,
        typer.Option(
            "--input-format",
            help="要使用的输入格式。必须与 --print 一起使用，且输入必须通过 stdin 管道传入。默认：text。",
        ),
    ] = None,
    output_format: Annotated[
        OutputFormat | None,
        typer.Option(
            "--output-format",
            help="要使用的输出格式。必须与 --print 一起使用。默认：text。",
        ),
    ] = None,
    mcp_config_file: Annotated[
        list[Path] | None,
        typer.Option(
            "--mcp-config-file",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="要加载的 MCP 配置文件。可多次使用此选项以指定多个 MCP 配置。默认：无。",
        ),
    ] = None,
    mcp_config: Annotated[
        list[str] | None,
        typer.Option(
            "--mcp-config",
            help="要加载的 MCP 配置 JSON。可多次使用此选项以指定多个 MCP 配置。默认：无。",
        ),
    ] = None,
    yolo: Annotated[
        bool,
        typer.Option(
            "--yolo",
            "--yes",
            "-y",
            "--auto-approve",
            help="自动批准所有操作。默认：否。",
        ),
    ] = False,
    thinking: Annotated[
        bool | None,
        typer.Option(
            "--thinking",
            help="如果支持，则启用思考模式。默认：与上次设置相同。",
        ),
    ] = None,
):
    """Kimi，你的下一代命令行智能体。"""
    del version  # 已在回调中处理

    from kaos.path import KaosPath
    from kimi_cli.app import KimiCLI, enable_logging
    from kimi_cli.metadata import load_metadata, save_metadata
    from kimi_cli.session import Session
    from kimi_cli.utils.logging import logger

    enable_logging(debug)

    special_flags = {
        "--print": print_mode,
        "--acp": acp_mode,
        "--wire": wire_mode,
    }
    active_specials = [flag for flag, active in special_flags.items() if active]
    if len(active_specials) > 1:
        raise typer.BadParameter(
            f"无法合并使用 {', '.join(active_specials)}。",
            param_hint=active_specials[0],
        )

    ui: UIMode = "shell"
    if print_mode:
        ui = "print"
    elif acp_mode:
        ui = "acp"
    elif wire_mode:
        ui = "wire"

    if command is not None:
        command = command.strip()
        if not command:
            raise typer.BadParameter("命令不能为空", param_hint="--command")

    if input_format is not None and ui != "print":
        raise typer.BadParameter(
            "输入格式仅在打印用户界面（print UI）中受支持",
            param_hint="--input-format",
        )
    if output_format is not None and ui != "print":
        raise typer.BadParameter(
            "输出格式仅在打印用户界面（print UI）中受支持",
            param_hint="--output-format",
        )

    # 从配置文件加载永久 MCP 配置
    config = load_config()
    mcp_configs = list(config.mcp_configs)

    # 添加命令行指定的临时 MCP 配置
    file_configs = list(mcp_config_file or [])
    raw_mcp_config = list(mcp_config or [])

    try:
        mcp_configs.extend([json.loads(conf.read_text(encoding="utf-8")) for conf in file_configs])
    except json.JSONDecodeError as e:
        raise typer.BadParameter(f"无效的 JSON: {e}", param_hint="--mcp-config-file") from e

    try:
        mcp_configs.extend([json.loads(conf) for conf in raw_mcp_config])
    except json.JSONDecodeError as e:
        raise typer.BadParameter(f"无效的 JSON: {e}", param_hint="--mcp-config") from e

    async def _run() -> bool:
        work_dir = (
            KaosPath.unsafe_from_local_path(local_work_dir) if local_work_dir else KaosPath.cwd()
        )

        if continue_:
            session = await Session.continue_(work_dir)
            if session is None:
                raise typer.BadParameter(
                    "在当前工作目录中未找到先前的会话",
                    param_hint="--continue",
                )
            logger.info("继续上一个会话: {session_id}", session_id=session.id)
        else:
            session = await Session.create(work_dir)
            logger.info("已创建新会话: {session_id}", session_id=session.id)
        logger.debug("上下文文件: {context_file}", context_file=session.context_file)

        if thinking is None:
            metadata = load_metadata()
            thinking_mode = metadata.thinking
        else:
            thinking_mode = thinking

        instance = await KimiCLI.create(
            session,
            yolo=yolo or (ui == "print"),  # 打印模式意味着自动批准（yolo）
            mcp_configs=mcp_configs,
            model_name=model_name,
            thinking=thinking_mode,
            agent_file=agent_file,
        )
        match ui:
            case "shell":
                succeeded = await instance.run_shell(command)
            case "print":
                succeeded = await instance.run_print(
                    input_format or "text",
                    output_format or "text",
                    command,
                )
            case "acp":
                if command is not None:
                    logger.warning("ACP 服务器忽略 command 参数")
                await instance.run_acp()
                succeeded = True
            case "wire":
                if command is not None:
                    logger.warning("Wire 服务器忽略 command 参数")
                await instance.run_wire_stdio()
                succeeded = True

        if succeeded:
            metadata = load_metadata()

            # 使用上一个会话更新 work_dir 元数据
            work_dir_meta = metadata.get_work_dir_meta(session.work_dir)

            if work_dir_meta is None:
                logger.warning(
                    "标记上一个会话时缺少工作目录元数据，正在重新创建: {work_dir}",
                    work_dir=session.work_dir,
                )
                work_dir_meta = metadata.new_work_dir_meta(session.work_dir)

            work_dir_meta.last_session_id = session.id

            # 更新思考模式
            metadata.thinking = instance.soul.thinking

            save_metadata(metadata)

        return succeeded

    while True:
        try:
            succeeded = asyncio.run(_run())
            if succeeded:
                break
            raise typer.Exit(code=1)
        except Reload:
            continue


@cli.command()
def config_mcp(
    action: Annotated[
        Literal["add", "remove", "list", "clear"],
        typer.Argument(help="MCP 配置操作：add（添加）、remove（移除）、list（列出）、clear（清空）"),
    ],
    config_file: Annotated[
        Path | None,
        typer.Option(
            "--config-file",
            help="MCP 配置文件路径（仅用于 add 操作）",
        ),
    ] = None,
    config_json: Annotated[
        str | None,
        typer.Option(
            "--config-json",
            help="MCP 配置 JSON 字符串（仅用于 add 操作）",
        ),
    ] = None,
    index: Annotated[
        int | None,
        typer.Option(
            "--index",
            help="要移除的 MCP 配置索引（仅用于 remove 操作）",
        ),
    ] = None,
):
    """管理永久 MCP 配置。"""
    from kimi_cli.config import Config, load_config, save_config

    config = load_config()

    if action == "list":
        if not config.mcp_configs:
            typer.echo("未配置任何 MCP 服务器")
            return
        
        # 统计实际的 MCP 服务器数量
        total_servers = 0
        for mcp_config in config.mcp_configs:
            if "mcpServers" in mcp_config:
                total_servers += len(mcp_config["mcpServers"])
            else:
                total_servers += 1  # 对于不包含 mcpServers 的配置，计为 1 个
        
        typer.echo(f"当前配置的 MCP 服务器（共 {total_servers} 个）：")
        for i, mcp_config in enumerate(config.mcp_configs):
            if "mcpServers" in mcp_config:
                # 对于包含 mcpServers 的配置，列出每个服务器
                for server_name, server_config in mcp_config["mcpServers"].items():
                    typer.echo(f"  - {server_name}: {json.dumps(server_config, ensure_ascii=False)}")
            else:
                # 对于其他配置，直接显示
                typer.echo(f"  [{i}] {json.dumps(mcp_config, ensure_ascii=False, indent=2)}")
    
    elif action == "add":
        if not config_file and not config_json:
            typer.echo("错误：必须指定 --config-file 或 --config-json", err=True)
            raise typer.Exit(1)
        
        new_config = None
        if config_file:
            try:
                new_config = json.loads(config_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                typer.echo(f"错误：配置文件中的 JSON 无效: {e}", err=True)
                raise typer.Exit(1)
        elif config_json:
            try:
                new_config = json.loads(config_json)
            except json.JSONDecodeError as e:
                typer.echo(f"错误：配置 JSON 无效: {e}", err=True)
                raise typer.Exit(1)
        
        # 如果新配置包含 mcpServers，则合并到现有配置中
        if "mcpServers" in new_config:
            # 查找现有的 mcpServers 配置
            merged_config = {"mcpServers": {}}
            
            # 合并所有现有的 mcpServers
            for existing in config.mcp_configs:
                if "mcpServers" in existing:
                    merged_config["mcpServers"].update(existing["mcpServers"])
            
            # 添加新的 mcpServers
            merged_config["mcpServers"].update(new_config["mcpServers"])
            
            # 清空现有配置并设置合并后的配置
            config.mcp_configs.clear()
            config.mcp_configs.append(merged_config)
        else:
            # 如果不包含 mcpServers，则直接添加
            config.mcp_configs.append(new_config)
        
        save_config(config)
        typer.echo("MCP 配置已添加")
    
    elif action == "remove":
        if index is None:
            typer.echo("错误：必须指定 --index", err=True)
            raise typer.Exit(1)
        
        if not config.mcp_configs:
            typer.echo("错误：未配置任何 MCP 服务器", err=True)
            raise typer.Exit(1)
        
        if index < 0 or index >= len(config.mcp_configs):
            typer.echo(f"错误：索引 {index} 超出范围", err=True)
            raise typer.Exit(1)
        
        removed_config = config.mcp_configs.pop(index)
        save_config(config)
        typer.echo(f"已移除 MCP 配置: {json.dumps(removed_config, ensure_ascii=False)}")
    
    elif action == "clear":
        config.mcp_configs.clear()
        save_config(config)
        typer.echo("已清空所有 MCP 配置")


if __name__ == "__main__":
    if "kimi_cli.cli" not in sys.modules:
        sys.modules["kimi_cli.cli"] = sys.modules[__name__]

    sys.exit(cli())
