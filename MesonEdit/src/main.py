#!/usr/bin/env python3
"""MesonEdit — meson.build 編輯器

Usage:
  python src/main.py                  # GUI，空白檔案
  python src/main.py path/to/meson.build
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _detach_console_on_windows() -> None:
    """GUI 模式用 pythonw 重新啟動，避免留下 CMD 視窗。"""
    if sys.platform != "win32" or getattr(sys, "frozen", False):
        return
    exe = Path(sys.executable)
    if exe.stem.lower() != "python":
        return
    pythonw = exe.with_name("pythonw.exe")
    if not pythonw.is_file():
        return
    import subprocess

    subprocess.Popen([str(pythonw), str(Path(__file__).resolve()), *sys.argv[1:]])
    raise SystemExit(0)


def main():
    args = sys.argv[1:]
    initial_path = Path(args[0]) if args else None

    from gui.app import run_gui

    run_gui(initial_path if initial_path and initial_path.exists() else None)


if __name__ == "__main__":
    _detach_console_on_windows()
    main()
