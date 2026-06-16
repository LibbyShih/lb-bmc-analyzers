#!/usr/bin/env python3
"""ServiceEdit CLI — Rich 終端機互動編輯器。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.rule import Rule

from schema import KEY_DEFS, SECTIONS_ORDER
from service_io import parse_service_file, render_service

console = Console()


def print_key_info(key: str, meta: dict):
    desc = meta.get("desc", "")
    example = meta.get("example", "")
    choices = meta.get("choices", [])
    default = meta.get("default", "")
    required = meta.get("required", False)

    req_tag = " [red]*必填[/]" if required else ""
    console.print(f"\n  [bold cyan]{key}[/]{req_tag}")
    for line in desc.splitlines():
        console.print(f"  [dim]{line}[/]")

    if choices and "\n" not in desc:
        console.print(f"  [dim]可選: {' | '.join(choices)}[/]")

    if example:
        console.print(f"  [dim]範例: {example}[/]")
    if default:
        console.print(f"  [dim]預設: {default}[/]")


def prompt_key(key: str, meta: dict, current: str = "") -> str:
    if current:
        hint = f"[dim](目前: {current} | Enter 保留)[/]"
    else:
        hint = "[dim](Enter 跳過)[/]"

    return Prompt.ask(
        f"  [bold]{key}[/] {hint}",
        default=current or "",
        show_default=False,
    )


def edit_sections(existing: dict | None = None) -> dict[str, dict[str, str]]:
    existing = existing or {}
    result: dict[str, dict[str, str]] = {}

    for section in SECTIONS_ORDER:
        key_defs = KEY_DEFS.get(section, {})
        existing_section = existing.get(section, {})

        console.print()
        console.rule(f"[bold cyan]{section}[/]", style="cyan dim")

        section_data: dict[str, str] = {}

        for key, meta in key_defs.items():
            current = existing_section.get(key, "")
            print_key_info(key, meta)
            value = prompt_key(key, meta, current)
            if value:
                section_data[key] = value

        unknown = {k: v for k, v in existing_section.items() if k not in key_defs}
        if unknown:
            console.print("\n  [yellow]⚠ 檔案中有未定義欄位:[/]")
            for k, v in unknown.items():
                if Confirm.ask(f"  保留 [bold]{k}[/]=[dim]{v}[/]?", default=True):
                    section_data[k] = v

        if section_data:
            result[section] = section_data

    return result


def show_preview(content: str):
    console.print()
    console.rule("[bold]預覽[/]")
    console.print(Syntax(content, "ini", theme="monokai", line_numbers=True))


def save_file(content: str, default_path: str = "output.service") -> Path | None:
    save_path_str = Prompt.ask("[bold]儲存路徑[/]", default=default_path)
    path = Path(save_path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    console.print(f"\n[green]✓ 已儲存到 {path.resolve()}[/]")
    return path


def run_create():
    console.print(Panel(
        "[dim]逐一填寫各欄位，必填欄位標記 [red]*[/]，選填直接 Enter 跳過[/]",
        title="[bold]建立新 .service 檔案[/]",
        border_style="cyan",
    ))
    data = edit_sections()
    if not data:
        console.print("[yellow]未填任何欄位，已取消。[/]")
        return

    content = render_service(data)
    show_preview(content)

    if Confirm.ask("\n[bold]儲存?[/]", default=True):
        save_file(content)


def run_edit(initial_path: Path | None = None):
    if initial_path is None:
        path_str = Prompt.ask("[bold]載入 .service 檔案路徑[/]")
        initial_path = Path(path_str)

    if not initial_path.exists():
        console.print(f"[red]找不到檔案: {initial_path}[/]")
        return

    console.print(f"[green]✓ 載入 {initial_path.resolve()}[/]")
    existing = parse_service_file(initial_path)

    data = edit_sections(existing)
    content = render_service(data)
    show_preview(content)

    console.print()
    if Confirm.ask("[bold]覆寫原始檔案?[/]", default=False):
        initial_path.write_text(content, encoding="utf-8")
        console.print(f"[green]✓ 已更新 {initial_path.resolve()}[/]")
    elif Confirm.ask("[bold]儲存到新路徑?[/]", default=True):
        default_name = initial_path.stem + ".new" + initial_path.suffix
        save_file(content, str(initial_path.parent / default_name))


def main():
    console.print(Panel(
        "[bold]ServiceEdit[/] — systemd .service 互動式編輯器 (CLI)\n"
        "[dim]每個欄位附說明與範例，支援建立新檔 / 載入現有檔編輯[/]",
        border_style="cyan",
    ))

    if len(sys.argv) > 1:
        run_edit(Path(sys.argv[1]))
        return

    console.print("\n  [bold][1][/] 建立新的 .service 檔案")
    console.print("  [bold][2][/] 載入並編輯現有 .service 檔案")
    console.print("  [bold][3][/] 離開\n")

    choice = Prompt.ask("[bold]選擇[/]", choices=["1", "2", "3"], default="1")
    if choice == "1":
        run_create()
    elif choice == "2":
        run_edit()
    else:
        console.print("[dim]Bye.[/]")


if __name__ == "__main__":
    main()
