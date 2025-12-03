from __future__ import annotations

import asyncio
import importlib
import inspect
import string
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from kaos.path import KaosPath
from kosong.tooling import Toolset

from kimi_cli.agentspec import load_agent_spec
from kimi_cli.config import Config
from kimi_cli.llm import LLM
from kimi_cli.session import Session
from kimi_cli.soul.approval import Approval
from kimi_cli.soul.denwarenji import DenwaRenji
from kimi_cli.soul.toolset import KimiToolset, ToolType
from kimi_cli.tools import SkipThisTool
from kimi_cli.utils.logging import logger
from kimi_cli.utils.path import list_directory


@dataclass(frozen=True, slots=True, kw_only=True)
class BuiltinSystemPromptArgs:
    """内置系统提示参数。"""

    KIMI_NOW: str
    """当前日期时间。"""
    KIMI_WORK_DIR: KaosPath
    """当前工作目录的绝对路径。"""
    KIMI_WORK_DIR_LS: str
    """当前工作目录的目录列表。"""
    KIMI_AGENTS_MD: str  # TODO: move to first message from system prompt
    """AGENTS.md 的内容。"""


async def load_agents_md(work_dir: KaosPath) -> str | None:
    paths = [
        work_dir / "AGENTS.md",
        work_dir / "agents.md",
    ]
    for path in paths:
        if await path.is_file():
            logger.info("已加载 agents.md: {path}", path=path)
            return (await path.read_text()).strip()
    logger.info("在 {work_dir} 中未找到 AGENTS.md", work_dir=work_dir)
    return None


@dataclass(frozen=True, slots=True, kw_only=True)
class Runtime:
    """代理运行时。"""

    config: Config
    llm: LLM | None
    session: Session
    builtin_args: BuiltinSystemPromptArgs
    denwa_renji: DenwaRenji
    approval: Approval
    labor_market: LaborMarket

    @staticmethod
    async def create(
        config: Config,
        llm: LLM | None,
        session: Session,
        yolo: bool,
    ) -> Runtime:
        ls_output, agents_md = await asyncio.gather(
            list_directory(session.work_dir),
            load_agents_md(session.work_dir),
        )

        return Runtime(
            config=config,
            llm=llm,
            session=session,
            builtin_args=BuiltinSystemPromptArgs(
                KIMI_NOW=datetime.now().astimezone().isoformat(),
                KIMI_WORK_DIR=session.work_dir,
                KIMI_WORK_DIR_LS=ls_output,
                KIMI_AGENTS_MD=agents_md or "",
            ),
            denwa_renji=DenwaRenji(),
            approval=Approval(yolo=yolo),
            labor_market=LaborMarket(),
        )

    def copy_for_fixed_subagent(self) -> Runtime:
        """为固定子代理克隆运行时。"""
        return Runtime(
            config=self.config,
            llm=self.llm,
            session=self.session,
            builtin_args=self.builtin_args,
            denwa_renji=DenwaRenji(),  # 子代理必须有自己的 DenwaRenji
            approval=self.approval,
            labor_market=LaborMarket(),  # 固定子代理有自己的 LaborMarket
        )

    def copy_for_dynamic_subagent(self) -> Runtime:
        """为动态子代理克隆运行时。"""
        return Runtime(
            config=self.config,
            llm=self.llm,
            session=self.session,
            builtin_args=self.builtin_args,
            denwa_renji=DenwaRenji(),  # 子代理必须有自己的 DenwaRenji
            approval=self.approval,
            labor_market=self.labor_market,  # 动态子代理与主代理共享 LaborMarket
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class Agent:
    """已加载的代理。"""

    name: str
    system_prompt: str
    toolset: Toolset
    runtime: Runtime
    """每个代理都有自己的运行时，应从其主代理派生。"""


class LaborMarket:
    def __init__(self):
        self.fixed_subagents: dict[str, Agent] = {}
        self.fixed_subagent_descs: dict[str, str] = {}
        self.dynamic_subagents: dict[str, Agent] = {}

    @property
    def subagents(self) -> Mapping[str, Agent]:
        """获取劳务市场中的所有子代理。"""
        return {**self.fixed_subagents, **self.dynamic_subagents}

    def add_fixed_subagent(self, name: str, agent: Agent, description: str):
        """添加一个固定子代理。"""
        self.fixed_subagents[name] = agent
        self.fixed_subagent_descs[name] = description

    def add_dynamic_subagent(self, name: str, agent: Agent):
        """添加一个动态子代理。"""
        self.dynamic_subagents[name] = agent


async def load_agent(
    agent_file: Path,
    runtime: Runtime,
    *,
    mcp_configs: list[dict[str, Any]],
) -> Agent:
    """
    从规范文件加载代理。

    Raises:
        FileNotFoundError: 如果代理规范文件不存在。
        AgentSpecError: 如果代理规范无效。
    """
    logger.info("正在加载代理: {agent_file}", agent_file=agent_file)
    agent_spec = load_agent_spec(agent_file)

    system_prompt = _load_system_prompt(
        agent_spec.system_prompt_path,
        agent_spec.system_prompt_args,
        runtime.builtin_args,
    )

    # load subagents before loading tools because Task tool depends on LaborMarket on initialization
    for subagent_name, subagent_spec in agent_spec.subagents.items():
        logger.debug("正在加载子代理: {subagent_name}", subagent_name=subagent_name)
        subagent = await load_agent(
            subagent_spec.path,
            runtime.copy_for_fixed_subagent(),
            mcp_configs=mcp_configs,
        )
        runtime.labor_market.add_fixed_subagent(subagent_name, subagent, subagent_spec.description)

    toolset = KimiToolset()
    tool_deps = {
        KimiToolset: toolset,
        Runtime: runtime,
        Config: runtime.config,
        BuiltinSystemPromptArgs: runtime.builtin_args,
        Session: runtime.session,
        DenwaRenji: runtime.denwa_renji,
        Approval: runtime.approval,
        LaborMarket: runtime.labor_market,
    }
    tools = agent_spec.tools
    if agent_spec.exclude_tools:
        logger.debug("正在排除工具: {tools}", tools=agent_spec.exclude_tools)
        tools = [tool for tool in tools if tool not in agent_spec.exclude_tools]
    bad_tools = _load_tools(toolset, tools, tool_deps)
    if bad_tools:
        raise ValueError(f"无效的工具: {bad_tools}")

    if mcp_configs:
        await _load_mcp_tools(toolset, mcp_configs, runtime)

    return Agent(
        name=agent_spec.name,
        system_prompt=system_prompt,
        toolset=toolset,
        runtime=runtime,
    )


def _load_system_prompt(
    path: Path, args: dict[str, str], builtin_args: BuiltinSystemPromptArgs
) -> str:
    logger.info("正在加载系统提示: {path}", path=path)
    system_prompt = path.read_text(encoding="utf-8").strip()
    logger.debug(
        "正在用内置参数替换系统提示: {builtin_args}, 规范参数: {spec_args}",
        builtin_args=builtin_args,
        spec_args=args,
    )
    return string.Template(system_prompt).substitute(asdict(builtin_args), **args)


# TODO: maybe move to `KimiToolset`
def _load_tools(
    toolset: KimiToolset,
    tool_paths: list[str],
    dependencies: dict[type[Any], Any],
) -> list[str]:
    bad_tools: list[str] = []
    for tool_path in tool_paths:
        try:
            tool = _load_tool(tool_path, dependencies)
        except SkipThisTool:
            logger.info("跳过工具: {tool_path}", tool_path=tool_path)
            continue
        if tool:
            toolset.add(tool)
        else:
            bad_tools.append(tool_path)
    logger.info("已加载工具: {tools}", tools=[tool.name for tool in toolset.tools])
    if bad_tools:
        logger.error("不良工具: {bad_tools}", bad_tools=bad_tools)
    return bad_tools


def _load_tool(tool_path: str, dependencies: dict[type[Any], Any]) -> ToolType | None:
    logger.debug("正在加载工具: {tool_path}", tool_path=tool_path)
    module_name, class_name = tool_path.rsplit(":", 1)
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return None
    cls = getattr(module, class_name, None)
    if cls is None:
        return None
    args: list[type[Any]] = []
    if "__init__" in cls.__dict__:
        # the tool class overrides the `__init__` of base class
        for param in inspect.signature(cls).parameters.values():
            if param.kind == inspect.Parameter.KEYWORD_ONLY:
                # once we encounter a keyword-only parameter, we stop injecting dependencies
                break
            # all positional parameters should be dependencies to be injected
            if param.annotation not in dependencies:
                raise ValueError(f"未找到工具依赖项: {param.annotation}")
            args.append(dependencies[param.annotation])
    return cls(*args)


async def _load_mcp_tools(
    toolset: KimiToolset,
    mcp_configs: list[dict[str, Any]],
    runtime: Runtime,
):
    """
    Raises:
        ValueError: 如果 MCP 配置无效。
        RuntimeError: 如果无法连接 MCP 服务器。
    """
    import fastmcp

    from kimi_cli.tools.mcp import MCPTool

    for mcp_config in mcp_configs:
        logger.info("正在从以下位置加载 MCP 工具: {mcp_config}", mcp_config=mcp_config)
        client = fastmcp.Client(mcp_config)
        async with client:
            for tool in await client.list_tools():
                toolset.add(MCPTool(tool, client, runtime=runtime))
    return toolset
