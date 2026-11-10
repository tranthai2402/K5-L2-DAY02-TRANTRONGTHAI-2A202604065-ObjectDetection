#!/usr/bin/env python3
"""Sao lưu Label Studio: copy database SQLite + ảnh media ra thư mục backup.

Dùng khi muốn chắc chắn không mất nhãn đã làm (đặc biệt trước khi làm thao tác
nguy hiểm, hoặc khi sắp nộp bài).

Usage:
    python tools/backup_ls.py
    python tools/backup_ls.py --out E:\\backups\\ls
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

LS_HOME = Path.home() / "AppData" / "Local" / "label-studio" / "label-studio"
DB = LS_HOME / "label_studio.sqlite3"
MEDIA = LS_HOME / "media"

REPO = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO.parent / "_backup"


def db_stats() -> tuple[int, int]:
    """(so task, so task da Submit) trong project 2."""
    if not DB.exists():
        return 0, 0
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        tasks = conn.execute("SELECT COUNT(*) FROM task").fetchone()[0]
        done = conn.execute(
            "SELECT COUNT(DISTINCT task_id) FROM task_completion WHERE was_cancelled = 0"
        ).fetchone()[0]
        drafts = conn.execute("SELECT COUNT(*) FROM tasks_annotationdraft").fetchone()[0]
        return tasks, done, drafts
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup database + media cua Label Studio.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="thu muc dich")
    args = parser.parse_args()

    if not DB.exists():
        print(f"Khong tim thay database: {DB}")
        return 1

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = args.out / f"labelstudio_{stamp}"
    dest.mkdir(parents=True, exist_ok=True)

    # 1. Copy database (dung file trong, khong copy thang file dang mo)
    db_dest = dest / "label_studio.sqlite3"
    src = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    out = sqlite3.connect(db_dest)
    with out:
        src.backup(out)
    src.close()
    out.close()

    # 2. Copy media (anh da upload)
    media_dest = dest / "media"
    if MEDIA.exists():
        shutil.copytree(MEDIA, media_dest, dirs_exist_ok=True)
        n_files = sum(1 for p in media_dest.rglob("*") if p.is_file())
    else:
        n_files = 0

    tasks, done, drafts = db_stats()
    print(f"Backup xong: {dest}")
    print(f"  - database : {db_dest.stat().st_size / 1e6:.1f} MB")
    print(f"  - media    : {n_files} file")
    print(f"  - hien trang: {tasks} task, {done} da Submit, {drafts} draft")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
