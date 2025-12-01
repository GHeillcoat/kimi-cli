from __future__ import annotations

import contextvars
import os
from collections.abc import AsyncGenerator
from pathlib import PurePath
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from kaos.path import KaosPath


type StrOrKaosPath = str | KaosPath


@runtime_checkable
class Kaos(Protocol):
    """Kimi 代理操作系统 (KAOS) 接口。"""

    name: str
    """KAOS 实现的名称。"""

    def pathclass(self) -> type[PurePath]:
        """获取 `KaosPath` 下使用的路径类。"""
        ...

    def gethome(self) -> KaosPath:
        """获取主目录路径。"""
        ...

    def getcwd(self) -> KaosPath:
        """获取当前工作目录路径。"""
        ...

    async def chdir(self, path: StrOrKaosPath) -> None:
        """更改当前工作目录。"""
        ...

    async def stat(self, path: StrOrKaosPath, *, follow_symlinks: bool = True) -> os.stat_result:
        """获取路径的 stat 结果。"""
        ...

    def iterdir(self, path: StrOrKaosPath) -> AsyncGenerator[KaosPath]:
        """遍历目录中的条目。"""
        ...

    def glob(
        self, path: StrOrKaosPath, pattern: str, *, case_sensitive: bool = True
    ) -> AsyncGenerator[KaosPath]:
        """在给定路径中搜索匹配模式的文件/目录。"""
        ...

    async def readbytes(self, path: StrOrKaosPath) -> bytes:
        """将整个文件内容作为字节读取。"""
        ...

    async def readtext(
        self,
        path: StrOrKaosPath,
        *,
        encoding: str = "utf-8",
        errors: Literal["strict", "ignore", "replace"] = "strict",
    ) -> str:
        """将整个文件内容作为文本读取。"""
        ...

    def readlines(
        self,
        path: StrOrKaosPath,
        *,
        encoding: str = "utf-8",
        errors: Literal["strict", "ignore", "replace"] = "strict",
    ) -> AsyncGenerator[str]:
        """迭代文件的行。"""
        ...

    async def writebytes(self, path: StrOrKaosPath, data: bytes) -> int:
        """将字节数据写入文件。"""
        ...

    async def writetext(
        self,
        path: StrOrKaosPath,
        data: str,
        *,
        mode: Literal["w", "a"] = "w",
        encoding: str = "utf-8",
        errors: Literal["strict", "ignore", "replace"] = "strict",
    ) -> int:
        """将文本数据写入文件，并返回写入的字符数。"""
        ...

    async def mkdir(
        self, path: StrOrKaosPath, parents: bool = False, exist_ok: bool = False
    ) -> None:
        """在给定路径创建目录。"""
        ...


def get_current_kaos() -> Kaos:
    """获取当前 KAOS 实例。"""
    from kaos._current import current_kaos

    return current_kaos.get()


def set_current_kaos(kaos: Kaos) -> contextvars.Token[Kaos]:
    """设置当前 KAOS 实例。"""
    from kaos._current import current_kaos

    return current_kaos.set(kaos)


def reset_current_kaos(token: contextvars.Token[Kaos]) -> None:
    """重置当前 KAOS 实例。"""
    from kaos._current import current_kaos

    current_kaos.reset(token)


def pathclass() -> type[PurePath]:
    return get_current_kaos().pathclass()


def gethome() -> KaosPath:
    return get_current_kaos().gethome()


def getcwd() -> KaosPath:
    return get_current_kaos().getcwd()


async def chdir(path: StrOrKaosPath) -> None:
    await get_current_kaos().chdir(path)


async def stat(path: StrOrKaosPath, *, follow_symlinks: bool = True) -> os.stat_result:
    return await get_current_kaos().stat(path, follow_symlinks=follow_symlinks)


async def iterdir(path: StrOrKaosPath) -> AsyncGenerator[KaosPath]:
    return get_current_kaos().iterdir(path)


async def glob(
    path: StrOrKaosPath, pattern: str, *, case_sensitive: bool = True
) -> AsyncGenerator[KaosPath]:
    return get_current_kaos().glob(path, pattern, case_sensitive=case_sensitive)


async def readbytes(path: StrOrKaosPath) -> bytes:
    return await get_current_kaos().readbytes(path)


async def readtext(
    path: StrOrKaosPath,
    *,
    encoding: str = "utf-8",
    errors: Literal["strict", "ignore", "replace"] = "strict",
) -> str:
    return await get_current_kaos().readtext(path, encoding=encoding, errors=errors)


async def readlines(
    path: StrOrKaosPath,
    *,
    encoding: str = "utf-8",
    errors: Literal["strict", "ignore", "replace"] = "strict",
) -> AsyncGenerator[str]:
    return get_current_kaos().readlines(path, encoding=encoding, errors=errors)


async def writebytes(path: StrOrKaosPath, data: bytes) -> int:
    return await get_current_kaos().writebytes(path, data)


async def writetext(
    path: StrOrKaosPath,
    data: str,
    *,
    mode: Literal["w", "a"] = "w",
    encoding: str = "utf-8",
    errors: Literal["strict", "ignore", "replace"] = "strict",
) -> int:
    return await get_current_kaos().writetext(
        path, data, mode=mode, encoding=encoding, errors=errors
    )


async def mkdir(path: StrOrKaosPath, parents: bool = False, exist_ok: bool = False) -> None:
    return await get_current_kaos().mkdir(path, parents=parents, exist_ok=exist_ok)
