from __future__ import annotations

import asyncio
import contextlib
import warnings
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from kosong.message import ContentPart
from pydantic import SecretStr

import kaos
from kaos.path import KaosPath
from kimi_cli.agentspec import DEFAULT_AGENT_FILE
from kimi_cli.cli import InputFormat, OutputFormat
from kimi_cli.config import LLMModel, LLMProvider, load_config
from kimi_cli.llm import augment_provider_with_env_vars, create_llm
from kimi_cli.session import Session
from kimi_cli.share import get_share_dir
from kimi_cli.soul import LLMNotSet, LLMNotSupported, run_soul
from kimi_cli.soul.agent import Runtime, load_agent
from kimi_cli.soul.context import Context
from kimi_cli.soul.kimisoul import KimiSoul
from kimi_cli.utils.logging import StreamToLogger, logger
from kimi_cli.utils.path import shorten_home
from kimi_cli.wire import Wire, WireUISide
from kimi_cli.wire.message import WireMessage


def enable_logging(debug: bool = False) -> None:
    if debug:
        logger.enable("kosong")
    logger.add(
        get_share_dir() / "logs" / "kimi.log",
        # FIXME: 为不同模块配置级别
        level="TRACE" if debug else "INFO",
        rotation="06:00",
        retention="10 days",
    )


class KimiCLI:
    @staticmethod
    async def create(
        session: Session,
        *,
        yolo: bool = False,
        mcp_configs: list[dict[str, Any]] | None = None,
        config_file: Path | None = None,
        model_name: str | None = None,
        thinking: bool = False,
        agent_file: Path | None = None,
    ) -> KimiCLI:
        """
        创建一个 KimiCLI 实例。

        Args:
            session (Session): 由 `Session.create` 或 `Session.continue_` 创建的会话。
            yolo (bool, optional): 无需确认即可批准所有操作。默认为 False。
            config_file (Path | None, optional): 配置文件的路径。默认为 None。
            model_name (str | None, optional): 要使用的模型的名称。默认为 None。
            agent_file (Path | None, optional): 智能体文件的路径。默认为 None。

        Raises:
            FileNotFoundError: 当找不到智能体文件时。
            ConfigError(KimiCLIException): 当配置无效时。
            AgentSpecError(KimiCLIException): 当智能体规约无效时。
        """
        config = load_config(config_file)
        logger.info("已加载配置: {config}", config=config)

        model: LLMModel | None = None
        provider: LLMProvider | None = None

        # 尝试使用配置文件
        if not model_name and config.default_model:
            # 未指定 --model && 在配置中设置了默认模型
            model = config.models[config.default_model]
            provider = config.providers[model.provider]
        if model_name and model_name in config.models:
            # 指定了 --model && 在配置中设置了模型
            model = config.models[model_name]
            provider = config.providers[model.provider]

        if not model or not provider:
            model = LLMModel(provider="", model="", max_context_size=100_000)
            provider = LLMProvider(type="kimi", base_url="", api_key=SecretStr(""))

        # 尝试用环境变量覆盖
        assert provider is not None
        assert model is not None
        env_overrides = augment_provider_with_env_vars(provider, model)

        if not provider.base_url or not model.model:
            llm = None
        else:
            logger.info("正在使用 LLM 提供商: {provider}", provider=provider)
            logger.info("正在使用 LLM 模型: {model}", model=model)
            llm = create_llm(provider, model, session_id=session.id)

        runtime = await Runtime.create(config, llm, session, yolo)

        if agent_file is None:
            agent_file = DEFAULT_AGENT_FILE
        agent = await load_agent(agent_file, runtime, mcp_configs=mcp_configs or [])

        context = Context(session.context_file)
        await context.restore()

        soul = KimiSoul(agent, context=context)
        try:
            soul.set_thinking(thinking)
        except (LLMNotSet, LLMNotSupported) as e:
            logger.warning("启用思考模式失败: {error}", error=e)
        return KimiCLI(soul, runtime, env_overrides)

    def __init__(
        self,
        _soul: KimiSoul,
        _runtime: Runtime,
        _env_overrides: dict[str, str],
    ) -> None:
        self._soul = _soul
        self._runtime = _runtime
        self._env_overrides = _env_overrides

    @property
    def soul(self) -> KimiSoul:
        """获取 KimiSoul 实例。"""
        return self._soul

    @property
    def session(self) -> Session:
        """获取 Session 实例。"""
        return self._runtime.session

    @contextlib.asynccontextmanager
    async def _env(self) -> AsyncGenerator[None]:
        original_cwd = KaosPath.cwd()
        await kaos.chdir(self._runtime.session.work_dir)
        try:
            # 忽略 dateparser 可能产生的警告
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            with contextlib.redirect_stderr(StreamToLogger()):
                yield
        finally:
            await kaos.chdir(original_cwd)

    async def run(
        self,
        user_input: str | list[ContentPart],
        cancel_event: asyncio.Event,
        merge_wire_messages: bool = False,
    ) -> AsyncGenerator[WireMessage]:
        """
        在没有任何UI的情况下运行Kimi CLI实例，并直接产生Wire消息。

        Args:
            user_input (str | list[ContentPart]): 对智能体的用户输入。
            cancel_event (asyncio.Event): 用于取消运行的事件。
            merge_wire_messages (bool): 是否尽可能合并Wire消息。

        Yields:
            WireMessage: 来自 `KimiSoul` 的Wire消息。

        Raises:
            LLMNotSet: 当未设置LLM时。
            LLMNotSupported: 当LLM不具备所需功能时。
            ChatProviderError: 当LLM提供商返回错误时。
            MaxStepsReached: 当达到最大步数时。
            RunCancelled: 当运行被取消事件取消时。
        """
        async with self._env():
            wire_future = asyncio.Future[WireUISide]()
            stop_ui_loop = asyncio.Event()

            async def _ui_loop_fn(wire: Wire) -> None:
                wire_future.set_result(wire.ui_side(merge=merge_wire_messages))
                await stop_ui_loop.wait()

            soul_task = asyncio.create_task(
                run_soul(self.soul, user_input, _ui_loop_fn, cancel_event)
            )

            try:
                wire_ui = await wire_future
                while True:
                    msg = await wire_ui.receive()
                    yield msg
            except asyncio.QueueShutDown:
                pass
            finally:
                # 停止消费 Wire 消息
                stop_ui_loop.set()
                # 等待 soul 任务完成，或抛出异常
                await soul_task

    async def run_shell(self, command: str | None = None) -> bool:
        """使用 shell UI 运行 Kimi CLI 实例。"""
        from kimi_cli.ui.shell import Shell, WelcomeInfoItem

        welcome_info = [
            WelcomeInfoItem(
                name="目录", value=str(shorten_home(self._runtime.session.work_dir))
            ),
            WelcomeInfoItem(name="会话", value=self._runtime.session.id),
        ]
        if base_url := self._env_overrides.get("KIMI_BASE_URL"):
            welcome_info.append(
                WelcomeInfoItem(
                    name="API 地址",
                    value=f"{base_url} (来自 KIMI_BASE_URL)",
                    level=WelcomeInfoItem.Level.WARN,
                )
            )
        if self._env_overrides.get("KIMI_API_KEY"):
            welcome_info.append(
                WelcomeInfoItem(
                    name="API 密钥",
                    value="****** (来自 KIMI_API_KEY)",
                    level=WelcomeInfoItem.Level.WARN,
                )
            )
        if not self._runtime.llm:
            welcome_info.append(
                WelcomeInfoItem(
                    name="模型",
                    value="未设置, 请使用 /setup 命令进行配置",
                    level=WelcomeInfoItem.Level.WARN,
                )
            )
        elif "KIMI_MODEL_NAME" in self._env_overrides:
            welcome_info.append(
                WelcomeInfoItem(
                    name="模型",
                    value=f"{self._soul.model_name} (来自 KIMI_MODEL_NAME)",
                    level=WelcomeInfoItem.Level.WARN,
                )
            )
        else:
            welcome_info.append(
                WelcomeInfoItem(
                    name="模型",
                    value=self._soul.model_name,
                    level=WelcomeInfoItem.Level.INFO,
                )
            )
        async with self._env():
            shell = Shell(self._soul, welcome_info=welcome_info)
            return await shell.run(command)

    async def run_print(
        self,
        input_format: InputFormat,
        output_format: OutputFormat,
        command: str | None = None,
    ) -> bool:
        """使用 print UI 运行 Kimi CLI 实例。"""
        from kimi_cli.ui.print import Print

        async with self._env():
            print_ = Print(
                self._soul,
                input_format,
                output_format,
                self._runtime.session.context_file,
            )
            return await print_.run(command)

    async def run_acp(self) -> None:
        """作为 ACP 服务器运行 Kimi CLI 实例。"""
        from kimi_cli.ui.acp import ACP

        async with self._env():
            acp = ACP(self._soul)
            await acp.run()

    async def run_wire_stdio(self) -> None:
        """通过 stdio 作为 Wire 服务器运行 Kimi CLI 实例。"""
        from kimi_cli.ui.wire import WireOverStdio

        async with self._env():
            server = WireOverStdio(self._soul)
            await server.serve()
