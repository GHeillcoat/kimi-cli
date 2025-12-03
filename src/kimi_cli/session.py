from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from kaos.path import KaosPath

from kimi_cli.metadata import WorkDirMeta, load_metadata, save_metadata
from kimi_cli.utils.logging import logger


@dataclass(frozen=True, slots=True, kw_only=True)
class Session:
    """工作目录的一个会话。"""

    id: str
    """会话 ID。"""
    work_dir: KaosPath
    """工作目录的绝对路径。"""
    work_dir_meta: WorkDirMeta
    """工作目录的元数据。"""
    context_file: Path
    """存储消息历史的文件的绝对路径。"""

    @property
    def dir(self) -> Path:
        """会话目录的绝对路径。"""
        path = self.work_dir_meta.sessions_dir / self.id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    async def create(work_dir: KaosPath, _context_file: Path | None = None) -> Session:
        """为工作目录创建一个新会话。"""
        work_dir = work_dir.canonical()
        logger.debug("正在为工作目录创建新会话: {work_dir}", work_dir=work_dir)

        metadata = load_metadata()
        work_dir_meta = metadata.get_work_dir_meta(work_dir)
        if work_dir_meta is None:
            work_dir_meta = metadata.new_work_dir_meta(work_dir)

        session_id = str(uuid.uuid4())
        session_dir = work_dir_meta.sessions_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        if _context_file is None:
            context_file = session_dir / "context.jsonl"
        else:
            logger.warning(
                "正在使用提供的上下文文件: {context_file}", context_file=_context_file
            )
            _context_file.parent.mkdir(parents=True, exist_ok=True)
            if _context_file.exists():
                assert _context_file.is_file()
            context_file = _context_file

        if context_file.exists():
            # truncate if exists
            logger.warning(
                "上下文文件已存在，正在截断: {context_file}", context_file=context_file
            )
            context_file.unlink()
            context_file.touch()

        save_metadata(metadata)

        return Session(
            id=session_id,
            work_dir=work_dir,
            work_dir_meta=work_dir_meta,
            context_file=context_file,
        )

    @staticmethod
    async def continue_(work_dir: KaosPath) -> Session | None:
        """获取工作目录的最后一个会话。"""
        work_dir = work_dir.canonical()
        logger.debug("正在继续工作目录的会话: {work_dir}", work_dir=work_dir)

        metadata = load_metadata()
        work_dir_meta = metadata.get_work_dir_meta(work_dir)
        if work_dir_meta is None:
            logger.debug("工作目录从未被使用过")
            return None
        if work_dir_meta.last_session_id is None:
            logger.debug("工作目录从未有过会话")
            return None

        logger.debug(
            "找到工作目录的最后一个会话: {session_id}",
            session_id=work_dir_meta.last_session_id,
        )
        session_id = work_dir_meta.last_session_id
        _migrate_session_context_file(work_dir_meta, session_id)

        session_dir = work_dir_meta.sessions_dir / session_id
        context_file = session_dir / "context.jsonl"

        return Session(
            id=session_id,
            work_dir=work_dir,
            work_dir_meta=work_dir_meta,
            context_file=context_file,
        )


def _migrate_session_context_file(work_dir_meta: WorkDirMeta, session_id: str) -> None:
    old_context_file = work_dir_meta.sessions_dir / f"{session_id}.jsonl"
    new_context_file = work_dir_meta.sessions_dir / session_id / "context.jsonl"
    if old_context_file.exists() and not new_context_file.exists():
        new_context_file.parent.mkdir(parents=True, exist_ok=True)
        old_context_file.rename(new_context_file)
        logger.info(
            "已将会话上下文文件从 {old} 迁移到 {new}",
            old=old_context_file,
            new=new_context_file,
        )
