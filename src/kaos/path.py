from __future__ import annotations

import ntpath
import os
import posixpath
from collections.abc import AsyncGenerator
from pathlib import Path, PurePath
from stat import S_ISDIR, S_ISREG
from typing import Any, Literal

import kaos


class KaosPath:
    """
    KAOS 文件系统的路径抽象。
    """

    def __init__(self, *args: str) -> None:
        self._path: PurePath = kaos.pathclass()(*args)

    @classmethod
    def unsafe_from_local_path(cls, path: Path) -> KaosPath:
        """
        从本地 `Path` 创建 `KaosPath`。
        仅在确定使用 `LocalKaos` 时才使用此方法。
        """
        return cls(str(path))

    def unsafe_to_local_path(self) -> Path:
        """
        将 `KaosPath` 转换为本地 `Path`。
        仅在确定使用 `LocalKaos` 时才使用此方法。
        """
        return Path(str(self._path))

    def __lt__(self, other: KaosPath) -> bool:
        return self._path.__lt__(other._path)

    def __le__(self, other: KaosPath) -> bool:
        return self._path.__le__(other._path)

    def __gt__(self, other: KaosPath) -> bool:
        return self._path.__gt__(other._path)

    def __ge__(self, other: KaosPath) -> bool:
        return self._path.__ge__(other._path)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, KaosPath):
            return NotImplemented
        return self._path.__eq__(other._path)

    def __repr__(self) -> str:
        return f"KaosPath({repr(str(self._path))})"

    def __str__(self) -> str:
        return str(self._path)

    @property
    def name(self) -> str:
        """返回路径的最后一个组件。"""
        return self._path.name

    @property
    def parent(self) -> KaosPath:
        """返回路径的父目录。"""
        return KaosPath(str(self._path.parent))

    def is_absolute(self) -> bool:
        """如果路径是绝对路径，则返回 True。"""
        return self._path.is_absolute()

    def joinpath(self, *other: str) -> KaosPath:
        """将此路径与其他路径组件连接。"""
        return KaosPath(str(self._path.joinpath(*other)))

    def __truediv__(self, other: str | KaosPath) -> KaosPath:
        """使用 `/` 运算符将此路径与另一个路径连接。"""
        p = other._path if isinstance(other, KaosPath) else other
        ret = KaosPath()
        ret._path = self._path.__truediv__(p)
        return ret

    def canonical(self) -> KaosPath:
        """
        使路径成为绝对路径，解析路径中的所有 `.` 和 `..`。
        与 `pathlib.Path.resolve` 不同，此方法不解析符号链接。
        """
        abs_path = self if self.is_absolute() else kaos.getcwd().joinpath(str(self._path))

        # Normalize the path (handle . and ..) but preserve the format
        path_parser = kaos.pathclass().parser
        assert path_parser in (posixpath, ntpath), (
            "Path class should be either PurePosixPath or PureWindowsPath"
        )
        normalized = path_parser.normpath(abs_path._path)
        assert isinstance(normalized, str)

        # `normpath` 可能会去除尾部斜杠，但我们希望为目录保留它
        # 但是，由于我们不访问文件系统，我们无法知道它是否是目录
        # 因此我们遵循 pathlib 的行为，即不保留尾部斜杠

        return KaosPath(normalized)

    def relative_to(self, other: KaosPath) -> KaosPath:
        """返回从 `other` 到此路径的相对路径。"""
        relative_path = self._path.relative_to(other._path)
        return KaosPath(str(relative_path))

    @classmethod
    def home(cls) -> KaosPath:
        """以 KaosPath 形式返回主目录。"""
        return kaos.gethome()

    @classmethod
    def cwd(cls) -> KaosPath:
        """以 KaosPath 形式返回当前工作目录。"""
        return kaos.getcwd()

    async def stat(self, follow_symlinks: bool = True) -> os.stat_result:
        """返回路径的 os.stat_result。"""
        return await kaos.stat(self, follow_symlinks=follow_symlinks)

    async def exists(self, *, follow_symlinks: bool = True) -> bool:
        """如果路径指向现有文件系统条目，则返回 True。"""
        try:
            await self.stat(follow_symlinks=follow_symlinks)
            return True
        except OSError:
            return False

    async def is_file(self, *, follow_symlinks: bool = True) -> bool:
        """如果路径指向常规文件，则返回 True。"""
        try:
            st = await self.stat(follow_symlinks=follow_symlinks)
            return S_ISREG(st.st_mode)
        except OSError:
            return False

    async def is_dir(self, *, follow_symlinks: bool = True) -> bool:
        """如果路径指向目录，则返回 True。"""
        try:
            st = await self.stat(follow_symlinks=follow_symlinks)
            return S_ISDIR(st.st_mode)
        except OSError:
            return False

    async def iterdir(self) -> AsyncGenerator[KaosPath]:
        """返回目录的直接子项。"""
        return await kaos.iterdir(self)

    async def glob(self, pattern: str, *, case_sensitive: bool = True) -> AsyncGenerator[KaosPath]:
        """返回此目录下所有匹配模式的路径。"""
        return await kaos.glob(self, pattern, case_sensitive=case_sensitive)

    async def read_bytes(self) -> bytes:
        """将整个文件内容作为字节读取。"""
        return await kaos.readbytes(self)

    async def read_text(
        self,
        *,
        encoding: str = "utf-8",
        errors: Literal["strict", "ignore", "replace"] = "strict",
    ) -> str:
        """将整个文件内容作为文本读取。"""
        return await kaos.readtext(self, encoding=encoding, errors=errors)

    async def read_lines(
        self,
        *,
        encoding: str = "utf-8",
        errors: Literal["strict", "ignore", "replace"] = "strict",
    ) -> AsyncGenerator[str]:
        """迭代文件的行。"""
        return await kaos.readlines(self, encoding=encoding, errors=errors)

    async def write_bytes(self, data: bytes) -> int:
        """将字节数据写入文件。"""
        return await kaos.writebytes(self, data)

    async def write_text(
        self,
        data: str,
        *,
        encoding: str = "utf-8",
        errors: Literal["strict", "ignore", "replace"] = "strict",
    ) -> int:
        """将文本数据写入文件，并返回写入的字符数。"""
        return await kaos.writetext(
            self,
            data,
            mode="w",
            encoding=encoding,
            errors=errors,
        )

    async def append_text(
        self,
        data: str,
        *,
        encoding: str = "utf-8",
        errors: Literal["strict", "ignore", "replace"] = "strict",
    ) -> int:
        """将文本数据追加到文件，并返回写入的字符数。"""
        return await kaos.writetext(
            self,
            data,
            mode="a",
            encoding=encoding,
            errors=errors,
        )

    async def mkdir(self, parents: bool = False, exist_ok: bool = False) -> None:
        """在此路径创建目录。"""
        return await kaos.mkdir(self, parents=parents, exist_ok=exist_ok)
