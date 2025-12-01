from __future__ import annotations


class KimiCLIException(Exception):
    """Kimi CLI 的基础异常类。"""

    pass


class ConfigError(KimiCLIException):
    """配置错误。"""

    pass


class AgentSpecError(KimiCLIException):
    """代理规范错误。"""

    pass
