from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

import yaml
from pydantic import BaseModel, Field

from kimi_cli.exception import AgentSpecError


def get_agents_dir() -> Path:
    return Path(__file__).parent / "agents"


DEFAULT_AGENT_FILE = get_agents_dir() / "default" / "agent.yaml"


class Inherit(NamedTuple):
    """代理规范中用于继承的标记类。"""


inherit = Inherit()


class AgentSpec(BaseModel):
    """代理规范。"""

    extend: str | None = Field(default=None, description="要扩展的代理文件")
    name: str | Inherit = Field(default=inherit, description="代理名称")  # 必需
    system_prompt_path: Path | Inherit = Field(
        default=inherit, description="系统提示路径"
    )  # 必需
    system_prompt_args: dict[str, str] = Field(
        default_factory=dict, description="系统提示参数"
    )
    tools: list[str] | None | Inherit = Field(default=inherit, description="工具")  # 必需
    exclude_tools: list[str] | None | Inherit = Field(
        default=inherit, description="要排除的工具"
    )
    subagents: dict[str, SubagentSpec] | None | Inherit = Field(
        default=inherit, description="子代理"
    )


class SubagentSpec(BaseModel):
    """子代理规范。"""

    path: Path = Field(description="子代理文件路径")
    description: str = Field(description="子代理描述")


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedAgentSpec:
    """已解析的代理规范。"""

    name: str
    system_prompt_path: Path
    system_prompt_args: dict[str, str]
    tools: list[str]
    exclude_tools: list[str]
    subagents: dict[str, SubagentSpec]


def load_agent_spec(agent_file: Path) -> ResolvedAgentSpec:
    """
    从文件加载代理规范。

    Raises:
        FileNotFoundError: 如果未找到代理规范文件。
        AgentSpecError: 如果代理规范无效。
    """
    agent_spec = _load_agent_spec(agent_file)
    assert agent_spec.extend is None, "代理扩展应递归解析"
    if isinstance(agent_spec.name, Inherit):
        raise AgentSpecError("需要代理名称")
    if isinstance(agent_spec.system_prompt_path, Inherit):
        raise AgentSpecError("需要系统提示路径")
    if isinstance(agent_spec.tools, Inherit):
        raise AgentSpecError("需要工具")
    if isinstance(agent_spec.exclude_tools, Inherit):
        agent_spec.exclude_tools = []
    if isinstance(agent_spec.subagents, Inherit):
        agent_spec.subagents = {}
    return ResolvedAgentSpec(
        name=agent_spec.name,
        system_prompt_path=agent_spec.system_prompt_path,
        system_prompt_args=agent_spec.system_prompt_args,
        tools=agent_spec.tools or [],
        exclude_tools=agent_spec.exclude_tools or [],
        subagents=agent_spec.subagents or {},
    )


def _load_agent_spec(agent_file: Path) -> AgentSpec:
    if not agent_file.exists():
        raise AgentSpecError(f"未找到代理规范文件: {agent_file}")
    if not agent_file.is_file():
        raise AgentSpecError(f"代理规范路径不是文件: {agent_file}")
    try:
        with open(agent_file, encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise AgentSpecError(f"代理规范文件中 YAML 无效: {e}") from e

    version = data.get("version", 1)
    if version != 1:
        raise AgentSpecError(f"不支持的代理规范版本: {version}")

    agent_spec = AgentSpec(**data.get("agent", {}))
    if isinstance(agent_spec.system_prompt_path, Path):
        agent_spec.system_prompt_path = (
            agent_file.parent / agent_spec.system_prompt_path
        ).absolute()
    if isinstance(agent_spec.subagents, dict):
        for v in agent_spec.subagents.values():
            v.path = (agent_file.parent / v.path).absolute()
    if agent_spec.extend:
        if agent_spec.extend == "default":
            base_agent_file = DEFAULT_AGENT_FILE
        else:
            base_agent_file = (agent_file.parent / agent_spec.extend).absolute()
        base_agent_spec = _load_agent_spec(base_agent_file)
        if not isinstance(agent_spec.name, Inherit):
            base_agent_spec.name = agent_spec.name
        if not isinstance(agent_spec.system_prompt_path, Inherit):
            base_agent_spec.system_prompt_path = agent_spec.system_prompt_path
        for k, v in agent_spec.system_prompt_args.items():
            # 系统提示参数应该合并而不是覆盖
            base_agent_spec.system_prompt_args[k] = v
        if not isinstance(agent_spec.tools, Inherit):
            base_agent_spec.tools = agent_spec.tools
        if not isinstance(agent_spec.exclude_tools, Inherit):
            base_agent_spec.exclude_tools = agent_spec.exclude_tools
        if not isinstance(agent_spec.subagents, Inherit):
            base_agent_spec.subagents = agent_spec.subagents
        agent_spec = base_agent_spec
    return agent_spec
