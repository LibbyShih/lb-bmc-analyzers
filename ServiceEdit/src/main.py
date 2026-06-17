#!/usr/bin/env python3
"""ServiceEdit — systemd .service 編輯器

預設啟動圖形介面；加 --cli 使用終端機互動模式。

Usage:
  python src/main.py                  # GUI
  python src/main.py path/to/foo.service
  python src/main.py --cli            # Rich CLI
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _detach_console_on_windows() -> None:
    """GUI 模式用 pythonw 重新啟動，避免留下 CMD 視窗。"""
    if sys.platform != "win32" or getattr(sys, "frozen", False):
        return
    if "--cli" in sys.argv[1:]:
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
    args = [a for a in sys.argv[1:] if a != "--cli"]
    use_cli = "--cli" in sys.argv[1:]

    initial_path = Path(args[0]) if args else None

    if use_cli:
        from cli import main as cli_main

        sys.argv = [sys.argv[0], *args]
        cli_main()
        return

    from gui.app import run_gui

    run_gui(initial_path if initial_path and initial_path.exists() else None)


if __name__ == "__main__":
    _detach_console_on_windows()
    main()
