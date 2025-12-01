from __future__ import annotations

import json
from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field, SecretStr, ValidationError, field_serializer, model_validator

from kimi_cli.exception import ConfigError
from kimi_cli.llm import ModelCapability, ProviderType
from kimi_cli.share import get_share_dir
from kimi_cli.utils.logging import logger


class LLMProvider(BaseModel):
    """LLM 提供商配置。"""

    type: ProviderType
    """提供商类型"""
    base_url: str
    """API 基础 URL"""
    api_key: SecretStr
    """API 密钥"""
    custom_headers: dict[str, str] | None = None
    """API 请求中包含的自定义头部"""

    @field_serializer("api_key", when_used="json")
    def dump_secret(self, v: SecretStr):
        return v.get_secret_value()


class LLMModel(BaseModel):
    """LLM 模型配置。"""

    provider: str
    """提供商名称"""
    model: str
    """模型名称"""
    max_context_size: int
    """最大上下文大小（单位：token）"""
    capabilities: set[ModelCapability] | None = None
    """模型能力"""


class LoopControl(BaseModel):
    """智能体循环控制配置。"""

    max_steps_per_run: int = 100
    """单次运行的最大步数"""
    max_retries_per_step: int = 3
    """单步中的最大重试次数"""


class MoonshotSearchConfig(BaseModel):
    """Moonshot Search 配置。"""

    base_url: str
    """Moonshot Search 服务的基准 URL。"""
    api_key: SecretStr
    """Moonshot Search 服务的 API 密钥。"""
    custom_headers: dict[str, str] | None = None
    """API 请求中包含的自定义头部。"""

    @field_serializer("api_key", when_used="json")
    def dump_secret(self, v: SecretStr):
        return v.get_secret_value()


class MoonshotFetchConfig(BaseModel):
    """Moonshot Fetch 配置。"""

    base_url: str
    """Moonshot Fetch 服务的基准 URL。"""
    api_key: SecretStr
    """Moonshot Fetch 服务的 API 密钥。"""
    custom_headers: dict[str, str] | None = None
    """API 请求中包含的自定义头部。"""

    @field_serializer("api_key", when_used="json")
    def dump_secret(self, v: SecretStr):
        return v.get_secret_value()


class Services(BaseModel):
    """服务配置。"""

    moonshot_search: MoonshotSearchConfig | None = None
    """Moonshot 搜索配置。"""
    moonshot_fetch: MoonshotFetchConfig | None = None
    """Moonshot Fetch 配置。"""


class Config(BaseModel):
    """主配置结构。"""

    default_model: str = Field(default="", description="要使用的默认模型")
    models: dict[str, LLMModel] = Field(default_factory=dict, description="LLM 模型列表")
    providers: dict[str, LLMProvider] = Field(
        default_factory=dict, description="LLM 提供商列表"
    )
    loop_control: LoopControl = Field(default_factory=LoopControl, description="智能体循环控制")
    services: Services = Field(default_factory=Services, description="服务配置")

    @model_validator(mode="after")
    def validate_model(self) -> Self:
        if self.default_model and self.default_model not in self.models:
            raise ValueError(f"默认模型 {self.default_model} 在模型中未找到")
        for model in self.models.values():
            if model.provider not in self.providers:
                raise ValueError(f"提供商 {model.provider} 在提供商中未找到")
        return self


def get_config_file() -> Path:
    """获取配置文件路径。"""
    return get_share_dir() / "config.json"


def get_default_config() -> Config:
    """获取默认配置。"""
    return Config(
        default_model="",
        models={},
        providers={},
        services=Services(),
    )


def load_config(config_file: Path | None = None) -> Config:
    """
    从配置文件加载配置。
    如果配置文件不存在，则使用默认配置创建。

    Args:
        config_file (Path | None): 配置文件的路径。如果为 None，则使用默认路径。

    Returns:
        已验证的 Config 对象。

    Raises:
        ConfigError: 如果配置文件无效。
    """
    config_file = config_file or get_config_file()
    logger.debug("正在从文件加载配置: {file}", file=config_file)

    if not config_file.exists():
        config = get_default_config()
        logger.debug("未找到配置文件，正在创建默认配置: {config}", config=config)
        with open(config_file, "w", encoding="utf-8") as f:
            f.write(config.model_dump_json(indent=2, exclude_none=True))
        return config

    try:
        with open(config_file, encoding="utf-8") as f:
            data = json.load(f)
        return Config(**data)
    except json.JSONDecodeError as e:
        raise ConfigError(f"配置文件中的 JSON 无效: {e}") from e
    except ValidationError as e:
        raise ConfigError(f"配置文件无效: {e}") from e


def save_config(config: Config, config_file: Path | None = None):
    """
    将配置保存到配置文件。

    Args:
        config (Config): 要保存的 Config 对象。
        config_file (Path | None): 配置文件的路径。如果为 None，则使用默认路径。
    """
    config_file = config_file or get_config_file()
    logger.debug("正在将配置保存到文件: {file}", file=config_file)
    with open(config_file, "w", encoding="utf-8") as f:
        f.write(config.model_dump_json(indent=2, exclude_none=True))
