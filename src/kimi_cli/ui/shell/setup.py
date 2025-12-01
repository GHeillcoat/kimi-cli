from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, NamedTuple

import aiohttp
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts.choice_input import ChoiceInput
from pydantic import SecretStr
from urllib.parse import urljoin

from kimi_cli.config import (
    LLMModel,
    LLMProvider,
    MoonshotFetchConfig,
    MoonshotSearchConfig,
    load_config,
    save_config,
)
from kimi_cli.ui.shell.console import console
from kimi_cli.ui.shell.metacmd import meta_command
from kimi_cli.utils.aiohttp import new_client_session

if TYPE_CHECKING:
    from kimi_cli.ui.shell import Shell


class _Platform(NamedTuple):
    id: str
    name: str
    base_url: str
    search_url: str | None = None
    fetch_url: str | None = None
    allowed_prefixes: list[str] | None = None


_PLATFORMS = [
    _Platform(
        id="kimi-for-coding",
        name="Kimi 编程版",
        base_url="https://api.kimi.com/coding/v1",
        search_url="https://api.kimi.com/coding/v1/search",
        fetch_url="https://api.kimi.com/coding/v1/fetch",
    ),
    _Platform(
        id="moonshot-cn",
        name="月之暗面开放平台 (moonshot.cn)",
        base_url="https://api.moonshot.cn/v1",
        allowed_prefixes=["kimi-k2-"],
    ),
    _Platform(
        id="moonshot-ai",
        name="Moonshot AI 开放平台 (moonshot.ai)",
        base_url="https://api.moonshot.ai/v1",
        allowed_prefixes=["kimi-k2-"],
    ),
    _Platform(
        id="custom",
        name="自定义 (兼容OpenAI)",
        base_url="",  # 将会提示用户输入
    ),
]


@meta_command
async def setup(app: Shell, args: list[str]):
    """设置 Kimi 命令行工具"""
    result = await _setup()
    if not result:
        # 错误信息已经打印
        return

    config = load_config()

    # 根据所选名称确定提供商类型
    provider_type = (
        "openai_legacy" if result.platform.name == "自定义 (兼容OpenAI)" else "kimi"
    )

    config.providers[result.platform.id] = LLMProvider(
        type=provider_type,
        base_url=result.platform.base_url,
        api_key=result.api_key,
    )
    config.models[result.model_id] = LLMModel(
        provider=result.platform.id,
        model=result.model_id,
        max_context_size=result.max_context_size,
    )
    config.default_model = result.model_id

    # 仅为官方 kimi 平台设置服务
    if provider_type == "kimi":
        if result.platform.search_url:
            config.services.moonshot_search = MoonshotSearchConfig(
                base_url=result.platform.search_url,
                api_key=result.api_key,
            )

        if result.platform.fetch_url:
            config.services.moonshot_fetch = MoonshotFetchConfig(
                base_url=result.platform.fetch_url,
                api_key=result.api_key,
            )

    save_config(config)
    console.print("[green]✓[/green] Kimi CLI 设置完成！正在重新加载...")
    await asyncio.sleep(1)
    console.clear()

    from kimi_cli.cli import Reload

    raise Reload


class _SetupResult(NamedTuple):
    platform: _Platform
    api_key: SecretStr
    model_id: str
    max_context_size: int


async def _setup() -> _SetupResult | None:
    # 选择 API 平台
    platform_name = await _prompt_choice(
        header="选择 API 平台",
        choices=[platform.name for platform in _PLATFORMS],
    )
    if not platform_name:
        console.print("[red]未选择任何平台[/red]")
        return None

    platform = next(platform for platform in _PLATFORMS if platform.name == platform_name)

    # 如果是自定义，则提示输入更多详细信息并创建动态平台对象
    if platform.id == "custom":
        custom_id = await _prompt_text(
            "请输入此提供商的唯一名称 (例如, 'ollama', 'local_gpt')"
        )
        if not custom_id:
            console.print("[red]提供商名称不能为空。[/red]")
            return None

        custom_base_url = await _prompt_text(
            "请输入 API Base URL (例如, http://localhost:8080/v1)"
        )
        if not custom_base_url:
            console.print("[red]Base URL 不能为空。[/red]")
            return None

        platform = _Platform(id=custom_id, name=platform.name, base_url=custom_base_url)
        models_url = urljoin(custom_base_url, "models")

    # 输入 API 密钥
    api_key_str = await _prompt_text(
        "请输入您的 API 密钥 (部分本地模型可选)", is_password=True
    )
    api_key = api_key_str or "dummy-key"  # 如果为空则使用虚拟密钥

    # 列出模型


    model_list_fetched_successfully = False
    try:
        async with (
            new_client_session() as session,
            session.get(
                models_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                },
                raise_for_status=True,
            ) as response,
        ):
            resp_json = await response.json()
            temp_model_list = resp_json.get("data")
            if not temp_model_list or not isinstance(temp_model_list, list):
                console.print(f"[red]解析模型列表失败。响应格式不符合预期。[/red]")
                model_list = []
            else:
                model_list = temp_model_list
                model_list_fetched_successfully = True
    except aiohttp.ClientResponseError as e:
        if e.status == 401:
            console.print(
                f"[red]获取模型列表失败: 未授权 (401)。请检查您的 API 密钥。[/red]"
            )
        else:
            console.print(f"[red]获取模型列表失败: {e}[/red]")
        model_list = []
    except aiohttp.ClientError as e:
        console.print(
            f"[red]获取模型列表失败: {e}。请检查 Base URL 和您的网络连接。[/red]"
        )
        model_list = []

    model_dict = {model["id"]: model for model in model_list}
    
    if not model_list_fetched_successfully:
        choice = await _prompt_choice(
            header="获取模型列表失败。您想手动输入模型名称吗？",
            choices=["是", "否"],
        )
        if choice == "是":
            manual_model_ids_str = await _prompt_text(
                "请输入模型名称，多个模型请用逗号分隔 (例如, 'kimi-k2-nightly,gpt-4')"
            )
            if manual_model_ids_str:
                manual_model_ids = [mid.strip() for mid in manual_model_ids_str.split(",") if mid.strip()]
                for mid in manual_model_ids:
                    # 创建一个简化的模型字典，包含一个默认的 context_length
                    model_dict[mid] = {"id": mid, "context_length": 32768}
                model_ids = manual_model_ids
            else:
                console.print("[red]未输入模型名称。[/red]")
                return None
        else:
            return None
    else:
        model_ids: list[str] = [model["id"] for model in model_list]
        if platform.allowed_prefixes is not None:
            model_ids = [
                model_id
                for model_id in model_ids
                if model_id.startswith(tuple(platform.allowed_prefixes))
            ]

    if not model_ids:
        console.print("[red]所选平台下无可用模型[/red]")
        return None

    model_id = await _prompt_choice(
        header="选择模型",
        choices=model_ids,
    )
    if not model_id:
        console.print("[red]未选择任何模型[/red]")
        return None

    model = model_dict[model_id]

    # Kimi 特定的字段是 context_length，OpenAI 的模型通常缺少该字段或名称不同。
    max_context_size = model.get("context_length", 32768)  # 默认为 32k

    return _SetupResult(
        platform=platform,
        api_key=SecretStr(api_key),
        model_id=model_id,
        max_context_size=max_context_size,
    )


async def _prompt_choice(*, header: str, choices: list[str]) -> str | None:
    if not choices:
        return None

    try:
        return await ChoiceInput(
            message=header,
            options=[(choice, choice) for choice in choices],
            default=choices[0],
        ).prompt_async()
    except (EOFError, KeyboardInterrupt):
        return None


async def _prompt_text(prompt: str, *, is_password: bool = False) -> str | None:
    session = PromptSession()
    try:
        return str(
            await session.prompt_async(
                f" {prompt}: ",
                is_password=is_password,
            )
        ).strip()
    except (EOFError, KeyboardInterrupt):
        return None


@meta_command
def reload(app: Shell, args: list[str]):
    """重新加载配置"""
    from kimi_cli.cli import Reload

    raise Reload
