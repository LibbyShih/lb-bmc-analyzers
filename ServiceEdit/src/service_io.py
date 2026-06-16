"""systemd .service 檔案讀寫。"""

from configparser import RawConfigParser
from pathlib import Path

from schema import SECTIONS_ORDER, KEY_DEFS


def parse_service_file(path: Path) -> dict[str, dict[str, str]]:
    """Parse .service file into {[Section]: {key: value}}."""
    parser = RawConfigParser()
    parser.optionxform = str
    parser.read(str(path), encoding="utf-8")
    return {f"[{s}]": dict(parser.items(s)) for s in parser.sections()}


def render_service(data: dict[str, dict[str, str]]) -> str:
    """Render data dict to .service file string."""
    lines: list[str] = []
    extra_sections = [s for s in data if s not in SECTIONS_ORDER]
    for section in SECTIONS_ORDER + extra_sections:
        if section not in data or not data[section]:
            continue
        lines.append(section)
        known_order = list(KEY_DEFS.get(section, {}))
        keys = [k for k in known_order if k in data[section]]
        keys += sorted(k for k in data[section] if k not in known_order)
        for key in keys:
            value = data[section][key]
            if value:
                lines.append(f"{key}={value}")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def collect_form_data(
    vars_by_section: dict[str, dict[str, str]],
    extra_by_section: dict[str, dict[str, str]] | None = None,
) -> dict[str, dict[str, str]]:
    """Merge known fields and extra/unknown fields, dropping empties."""
    result: dict[str, dict[str, str]] = {}
    extra_by_section = extra_by_section or {}

    all_sections = set(vars_by_section) | set(extra_by_section)
    for section in SECTIONS_ORDER + [s for s in all_sections if s not in SECTIONS_ORDER]:
        merged: dict[str, str] = {}
        for src in (vars_by_section.get(section, {}), extra_by_section.get(section, {})):
            for key, value in src.items():
                if value and value.strip():
                    merged[key] = value.strip()
        if merged:
            result[section] = merged
    return result


def validate_service(data: dict[str, dict[str, str]]) -> list[str]:
    """Return list of validation warning messages."""
    warnings: list[str] = []
    unit = data.get("[Unit]", {})
    service = data.get("[Service]", {})
    install = data.get("[Install]", {})

    if not unit.get("Description"):
        warnings.append("[Unit] Description 為必填")
    if not service.get("ExecStart"):
        warnings.append("[Service] ExecStart 為必填")
    if not service.get("Type"):
        warnings.append("[Service] Type 為必填")
    if not install.get("WantedBy"):
        warnings.append("[Install] WantedBy 為必填（否則 systemctl enable 無法掛載）")

    if service.get("Type") == "dbus" and not service.get("BusName"):
        warnings.append("[Service] Type=dbus 時建議填寫 BusName")
    if service.get("Type") == "forking" and not service.get("PIDFile"):
        warnings.append("[Service] Type=forking 時建議填寫 PIDFile")

    exec_start = service.get("ExecStart", "")
    if exec_start and not exec_start.lstrip("-+!@").startswith("/"):
        warnings.append("[Service] ExecStart 建議使用絕對路徑")

    return warnings
