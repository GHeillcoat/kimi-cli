from __future__ import annotations

import json
from hashlib import md5
from pathlib import Path

from kaos import get_current_kaos
from kaos.local import local_kaos
from kaos.path import KaosPath
from pydantic import BaseModel, Field

from kimi_cli.share import get_share_dir
from kimi_cli.utils.logging import logger


def get_metadata_file() -> Path:
    return get_share_dir() / "kimi.json"


class WorkDirMeta(BaseModel):
    """工作目录的元数据。"""

    path: str
    """工作目录的完整路径。"""

    kaos: str = local_kaos.name
    """工作目录所在的 KAOS 名称。"""

    last_session_id: str | None = None
    """此工作目录的最后一个会话 ID。"""

    @property
    def sessions_dir(self) -> Path:
        """此工作目录存储会话的目录。"""
        path_md5 = md5(self.path.encode(encoding="utf-8")).hexdigest()
        dir_basename = path_md5 if self.kaos == local_kaos.name else f"{self.kaos}_{path_md5}"
        session_dir = get_share_dir() / "sessions" / dir_basename
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir


class Metadata(BaseModel):
    """Kimi 元数据结构。"""

    work_dirs: list[WorkDirMeta] = Field(default_factory=list[WorkDirMeta])
    """工作目录列表。"""

    thinking: bool = False
    """上次会话是否处于思考模式。"""

    def get_work_dir_meta(self, path: KaosPath) -> WorkDirMeta | None:
        """获取工作目录的元数据。"""
        for wd in self.work_dirs:
            if wd.path == str(path) and wd.kaos == get_current_kaos().name:
                return wd
        return None

    def new_work_dir_meta(self, path: KaosPath) -> WorkDirMeta:
        """创建一个新的工作目录元数据。"""
        wd_meta = WorkDirMeta(path=str(path), kaos=get_current_kaos().name)
        self.work_dirs.append(wd_meta)
        return wd_meta


def load_metadata() -> Metadata:
    metadata_file = get_metadata_file()
    logger.debug("正在从文件加载元数据: {file}", file=metadata_file)
    if not metadata_file.exists():
        logger.debug("未找到元数据文件，正在创建空元数据")
        return Metadata()
    with open(metadata_file, encoding="utf-8") as f:
        data = json.load(f)
        return Metadata(**data)


def save_metadata(metadata: Metadata):
    metadata_file = get_metadata_file()
    logger.debug("正在将元数据保存到文件: {file}", file=metadata_file)
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata.model_dump(), f, indent=2, ensure_ascii=False)
