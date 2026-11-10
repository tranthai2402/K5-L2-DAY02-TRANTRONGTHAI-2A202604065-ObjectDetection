#!/usr/bin/env python3
"""Launcher cho Windows: chạy auto-label bằng 1 lệnh ngắn.

    python tools/auto_label.py                 # project mặc định (đọc trong config)
    python tools/auto_label.py 5               # project id 5
    python tools/auto_label.py "Bài mới"        # theo tên project
    python tools/auto_label.py --new "Bài mới" --import-dir dataset/images/train
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "auto_label_ls.py"
CONFIG = HERE / "auto_label_config.json"


def main() -> int:
    argv = sys.argv[1:]

    # chế độ tạo project mới: --new <ten> --import-dir <thu muc>
    if argv and argv[0] == "--new":
        argv = ["--project", argv[1]] + argv[2:]

    if not argv:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
        argv = ["--project", str(cfg.get("default_project", 2))]
    elif "--project" not in argv:
        # chỉ truyền cờ khác -> lấy project mặc định từ config
        cfg = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
        argv = ["--project", str(cfg.get("default_project", 2))] + argv

    cmd = [sys.executable, str(SCRIPT)] + argv
    print("[auto-label]", " ".join(cmd[2:]))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
