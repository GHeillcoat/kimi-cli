from __future__ import annotations

import asyncio
import os
import platform
import re
import shutil
import stat
import tarfile
import tempfile
from enum import Enum, auto
from pathlib import Path

import aiohttp

from kimi_cli.share import get_share_dir
from kimi_cli.ui.shell.console import console
from kimi_cli.utils.aiohttp import new_client_session
from kimi_cli.utils.logging import logger

BASE_URL = "https://cdn.kimi.com/binaries/kimi-cli"
LATEST_VERSION_URL = f"{BASE_URL}/latest"
INSTALL_DIR = Path.home() / ".local" / "bin"


class UpdateResult(Enum):
    UPDATE_AVAILABLE = auto()
    UPDATED = auto()
    UP_TO_DATE = auto()
    FAILED = auto()
    UNSUPPORTED = auto()


_UPDATE_LOCK = asyncio.Lock()


def semver_tuple(version: str) -> tuple[int, int, int]:
    v = version.strip()
    if v.startswith("v"):
        v = v[1:]
    match = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?", v)
    if not match:
        return (0, 0, 0)
    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3) or 0)
    return (major, minor, patch)


def _detect_target() -> str | None:
    sys_name = platform.system()
    mach = platform.machine()
    if mach in ("x86_64", "amd64", "AMD64"):
        arch = "x86_64"
    elif mach in ("arm64", "aarch64"):
        arch = "aarch64"
    else:
        logger.error("不支持的架构: {mach}", mach=mach)
        return None
    if sys_name == "Darwin":
        os_name = "apple-darwin"
    elif sys_name == "Linux":
        os_name = "unknown-linux-gnu"
    else:
        logger.error("不支持的操作系统: {sys_name}", sys_name=sys_name)
        return None
    return f"{arch}-{os_name}"


async def _get_latest_version(session: aiohttp.ClientSession) -> str | None:
    try:
        async with session.get(LATEST_VERSION_URL) as resp:
            resp.raise_for_status()
            data = await resp.text()
            return data.strip()
    except aiohttp.ClientError:
        logger.exception("获取最新版本失败:")
        return None


async def do_update(*, print: bool = True, check_only: bool = False) -> UpdateResult:
    async with _UPDATE_LOCK:
        return await _do_update(print=print, check_only=check_only)


LATEST_VERSION_FILE = get_share_dir() / "latest_version.txt"


async def _do_update(*, print: bool, check_only: bool) -> UpdateResult:
    from kimi_cli.constant import VERSION as current_version

    def _print(message: str) -> None:
        if print:
            console.print(message)

    target = _detect_target()
    if not target:
        _print("[red]未能检测到目标平台。[/red]")
        return UpdateResult.UNSUPPORTED

    async with new_client_session() as session:
        logger.info("正在检查更新...")
        _print("正在检查更新...")
        latest_version = await _get_latest_version(session)
        if not latest_version:
            _print("[red]检查更新失败。[/red]")
            return UpdateResult.FAILED

        logger.debug("最新版本: {latest_version}", latest_version=latest_version)
        LATEST_VERSION_FILE.write_text(latest_version, encoding="utf-8")

        cur_t = semver_tuple(current_version)
        lat_t = semver_tuple(latest_version)

        if cur_t >= lat_t:
            logger.debug("已是最新版本: {current_version}", current_version=current_version)
            _print("[green]已是最新版本。[/green]")
            return UpdateResult.UP_TO_DATE

        if check_only:
            logger.info(
                "有可用更新: current={current_version}, latest={latest_version}",
                current_version=current_version,
                latest_version=latest_version,
            )
            _print(f"[yellow]有可用更新: {latest_version}[/yellow]")
            return UpdateResult.UPDATE_AVAILABLE

        logger.info(
            "正在从 {current_version} 更新到 {latest_version}...",
            current_version=current_version,
            latest_version=latest_version,
        )
        _print(f"正在从 {current_version} 更新到 {latest_version}...")

        filename = f"kimi-{latest_version}-{target}.tar.gz"
        download_url = f"{BASE_URL}/{latest_version}/{filename}"

        with tempfile.TemporaryDirectory(prefix="kimi-cli-") as tmpdir:
            tar_path = os.path.join(tmpdir, filename)

            logger.info("正在从 {download_url} 下载...", download_url=download_url)
            _print("[grey50]正在下载...[/grey50]")
            try:
                async with session.get(download_url) as resp:
                    resp.raise_for_status()
                    with open(tar_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(1024 * 64):
                            if chunk:
                                f.write(chunk)
            except aiohttp.ClientError:
                logger.exception(
                    "从 {download_url} 下载更新失败",
                    download_url=download_url,
                )
                _print("[red]下载失败。[/red]")
                return UpdateResult.FAILED
            except Exception:
                logger.exception("下载失败:")
                _print("[red]下载失败。[/red]")
                return UpdateResult.FAILED

            logger.info("正在解压压缩包 {tar_path}...", tar_path=tar_path)
            _print("[grey50]正在解压...[/grey50]")
            try:
                with tarfile.open(tar_path, "r:gz") as tar:
                    tar.extractall(tmpdir)
                binary_path = None
                for root, _, files in os.walk(tmpdir):
                    if "kimi" in files:
                        binary_path = os.path.join(root, "kimi")
                        break
                if not binary_path:
                    logger.error("在压缩包中未找到 'kimi' 执行文件。")
                    _print("[red]在压缩包中未找到 'kimi' 执行文件。[/red]")
                    return UpdateResult.FAILED
            except Exception:
                logger.exception("解压失败:")
                _print("[red]解压失败。[/red]")
                return UpdateResult.FAILED

            INSTALL_DIR.mkdir(parents=True, exist_ok=True)
            dest_path = INSTALL_DIR / "kimi"
            logger.info("正在安装到 {dest_path}...", dest_path=dest_path)
            _print("[grey50]正在安装...[/grey50]")

            try:
                shutil.copy2(binary_path, dest_path)
                os.chmod(
                    dest_path,
                    os.stat(dest_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
                )
            except Exception:
                logger.exception("安装失败:")
                _print("[red]安装失败。[/red]")
                return UpdateResult.FAILED

    _print("[green]更新成功！[/green]")
    _print("[yellow]请重启 Kimi CLI 以使用新版本。[/yellow]")
    return UpdateResult.UPDATED


# @meta_command
# async def update(app: "Shell", args: list[str]):
#     """检查更新"""
#     await do_update(print=True)


# @meta_command(name="check-update")
# async def check_update(app: "Shell", args: list[str]):
#     """检查更新"""
#     await do_update(print=True, check_only=True)
