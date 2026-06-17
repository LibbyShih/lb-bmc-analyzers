"""meson.build 讀寫：限定 project/dependency/files/executable/library/
static_library/shared_library/install_data/install_headers（外加 link_with/var_name
最小擴充）的表單式 parser 與 serializer。無法辨識的語句整段保留在
model["unrecognized"]，存檔時原樣附加在檔案最後。
"""

from __future__ import annotations

import re

TARGET_KINDS = ("executable", "library", "static_library", "shared_library")


def empty_model() -> dict:
    return {
        "project": {
            "name": "",
            "languages": [],
            "version": "",
            "meson_version": "",
            "default_options": [],
        },
        "dependencies": [],
        "file_groups": [],
        "targets": [],
        "install_data": [],
        "install_headers": [],
        "unrecognized": "",
    }


def _strip_comments(text: str) -> str:
    out: list[str] = []
    quote = None
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if quote:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in ("'", '"'):
            quote = c
            out.append(c)
            i += 1
            continue
        if c == "#":
            while i < n and text[i] != "\n":
                i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _split_statements(text: str) -> list[str]:
    statements: list[str] = []
    buf: list[str] = []
    depth = 0
    quote = None
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if quote:
            buf.append(c)
            if c == "\\" and i + 1 < n:
                buf.append(text[i + 1])
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in ("'", '"'):
            quote = c
            buf.append(c)
            i += 1
            continue
        if c in "([":
            depth += 1
            buf.append(c)
            i += 1
            continue
        if c in ")]":
            depth -= 1
            buf.append(c)
            i += 1
            continue
        if c == "\n" and depth == 0:
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def _split_top_level(s: str, sep: str = ",") -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    quote = None
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if quote:
            buf.append(c)
            if c == "\\" and i + 1 < n:
                buf.append(s[i + 1])
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in ("'", '"'):
            quote = c
            buf.append(c)
            i += 1
            continue
        if c in "([":
            depth += 1
            buf.append(c)
            i += 1
            continue
        if c in ")]":
            depth -= 1
            buf.append(c)
            i += 1
            continue
        if c == sep and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return [p for p in parts if p]


_CALL_RE = re.compile(
    r"^(?:(?P<assign>[A-Za-z_]\w*)\s*=\s*)?(?P<func>[A-Za-z_]\w*)\s*\((?P<args>.*)\)\s*$",
    re.DOTALL,
)
_KWARG_RE = re.compile(r"^(?P<key>[A-Za-z_]\w*)\s*:\s*(?P<value>.+)$", re.DOTALL)
_IDENT_RE = re.compile(r"^[A-Za-z_]\w*$")


def _parse_call(stmt: str):
    m = _CALL_RE.match(stmt)
    if not m:
        return None
    args_raw = _split_top_level(m.group("args"), ",")
    positional: list[str] = []
    kwargs: dict[str, str] = {}
    for arg in args_raw:
        km = _KWARG_RE.match(arg)
        if km:
            kwargs[km.group("key")] = km.group("value").strip()
        else:
            positional.append(arg.strip())
    return m.group("assign"), m.group("func"), positional, kwargs


def _unwrap_str(token: str) -> str:
    token = token.strip()
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ("'", '"'):
        return token[1:-1]
    return token


def _unwrap_str_list(token) -> list[str]:
    if token is None:
        return []
    token = token.strip()
    if token.startswith("[") and token.endswith("]"):
        return [_unwrap_str(t) for t in _split_top_level(token[1:-1], ",")]
    return [_unwrap_str(token)]


def _unwrap_bool(token, default: bool = False) -> bool:
    if token is None:
        return default
    return token.strip() == "true"


def _is_ident(token: str) -> bool:
    return bool(_IDENT_RE.match(token.strip()))


def parse_meson_build(text: str) -> dict:
    model = empty_model()
    statements = _split_statements(_strip_comments(text))
    dep_index_by_var: dict[str, int] = {}
    file_index_by_var: dict[str, int] = {}
    target_index_by_var: dict[str, int] = {}
    leftover: list[str] = []

    def add_dependency(var_name, positional, kwargs) -> int:
        entry = {
            "var_name": var_name,
            "name": _unwrap_str(positional[0]) if positional else "",
            "modules": _unwrap_str_list(kwargs.get("modules")),
            "method": _unwrap_str(kwargs.get("method", "")),
            "version": _unwrap_str(kwargs.get("version", "")),
            "required": _unwrap_bool(kwargs.get("required"), default=True),
        }
        model["dependencies"].append(entry)
        idx = len(model["dependencies"]) - 1
        if var_name:
            dep_index_by_var[var_name] = idx
        return idx

    def add_file_group(var_name, positional) -> int:
        entry = {
            "var_name": var_name or "",
            "paths": [_unwrap_str(p) for p in positional],
        }
        model["file_groups"].append(entry)
        idx = len(model["file_groups"]) - 1
        if var_name:
            file_index_by_var[var_name] = idx
        return idx

    def resolve_dep_refs(token) -> list[int]:
        if token is None:
            return []
        token = token.strip()
        if token.startswith("[") and token.endswith("]"):
            items = _split_top_level(token[1:-1], ",")
        else:
            items = [token]
        refs: list[int] = []
        for item in items:
            item = item.strip()
            sub = _parse_call(item)
            if sub and sub[1] == "dependency":
                refs.append(add_dependency(None, sub[2], sub[3]))
            elif item in dep_index_by_var:
                refs.append(dep_index_by_var[item])
        return refs

    def resolve_target_refs(token) -> list[int]:
        if token is None:
            return []
        token = token.strip()
        if token.startswith("[") and token.endswith("]"):
            items = _split_top_level(token[1:-1], ",")
        else:
            items = [token]
        return [target_index_by_var[i.strip()] for i in items if i.strip() in target_index_by_var]

    def split_sources(positional_tokens: list[str], kwargs) -> tuple[list[str], list[int]]:
        sources: list[str] = []
        file_refs: list[int] = []
        tokens = positional_tokens[1:] if positional_tokens else []
        if not tokens and kwargs.get("sources"):
            tokens = _split_top_level(kwargs["sources"], ",")
        for t in tokens:
            t = t.strip()
            if _is_ident(t) and t in file_index_by_var:
                file_refs.append(file_index_by_var[t])
            else:
                sources.extend(_unwrap_str_list(t))
        return sources, file_refs

    for stmt in statements:
        parsed = _parse_call(stmt)
        if not parsed:
            leftover.append(stmt)
            continue
        assign, func, positional, kwargs = parsed

        if func == "project" and not assign:
            names = [_unwrap_str(p) for p in positional]
            model["project"] = {
                "name": names[0] if names else "",
                "languages": names[1:],
                "version": _unwrap_str(kwargs.get("version", "")),
                "meson_version": _unwrap_str(kwargs.get("meson_version", "")),
                "default_options": _unwrap_str_list(kwargs.get("default_options")),
            }
        elif func == "dependency":
            add_dependency(assign, positional, kwargs)
        elif func == "files" and assign:
            add_file_group(assign, positional)
        elif func in TARGET_KINDS:
            sources, file_refs = split_sources(positional, kwargs)
            model["targets"].append({
                "kind": func,
                "var_name": assign,
                "name": _unwrap_str(positional[0]) if positional else "",
                "sources": sources,
                "file_refs": file_refs,
                "dep_refs": resolve_dep_refs(kwargs.get("dependencies")),
                "link_with_refs": resolve_target_refs(kwargs.get("link_with")),
                "install": _unwrap_bool(kwargs.get("install")),
            })
            if assign:
                target_index_by_var[assign] = len(model["targets"]) - 1
        elif func == "install_data" and not assign:
            model["install_data"].append({
                "paths": [_unwrap_str(p) for p in positional],
                "install_dir": _unwrap_str(kwargs.get("install_dir", "")),
            })
        elif func == "install_headers" and not assign:
            model["install_headers"].append({
                "paths": [_unwrap_str(p) for p in positional],
                "subdir": _unwrap_str(kwargs.get("subdir", "")),
                "install_dir": _unwrap_str(kwargs.get("install_dir", "")),
                "preserve_path": _unwrap_bool(kwargs.get("preserve_path")),
            })
        else:
            leftover.append(stmt)

    model["unrecognized"] = "\n".join(leftover)
    return model


def _quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _render_str_list(values: list[str]) -> str:
    return "[" + ", ".join(_quote(v) for v in values) + "]"


def _render_dependency_call(dep: dict) -> str:
    args = [_quote(dep.get("name", ""))]
    if dep.get("modules"):
        args.append(f"modules : {_render_str_list(dep['modules'])}")
    method = dep.get("method", "")
    if method and method != "auto":
        args.append(f"method : {_quote(method)}")
    if dep.get("version"):
        args.append(f"version : {_quote(dep['version'])}")
    if dep.get("required") is False:
        args.append("required : false")
    return f"dependency({', '.join(args)})"


def render_meson_build(model: dict) -> str:
    lines: list[str] = []
    project = model.get("project", {})

    proj_args = [_quote(project.get("name", ""))]
    proj_args += [_quote(lang) for lang in project.get("languages", [])]
    if project.get("version"):
        proj_args.append(f"version : {_quote(project['version'])}")
    if project.get("meson_version"):
        proj_args.append(f"meson_version : {_quote(project['meson_version'])}")
    if project.get("default_options"):
        proj_args.append(f"default_options : {_render_str_list(project['default_options'])}")
    lines.append(f"project({', '.join(proj_args)})")
    lines.append("")

    deps = model.get("dependencies", [])
    named_dep_lines = [
        f"{dep['var_name']} = {_render_dependency_call(dep)}" for dep in deps if dep.get("var_name")
    ]
    if named_dep_lines:
        lines.extend(named_dep_lines)
        lines.append("")

    file_groups = model.get("file_groups", [])
    file_lines = [
        f"{fg['var_name']} = files({', '.join(_quote(p) for p in fg['paths'])})"
        for fg in file_groups
        if fg.get("var_name") and fg.get("paths")
    ]
    if file_lines:
        lines.extend(file_lines)
        lines.append("")

    targets = model.get("targets", [])
    referenced = {idx for t in targets for idx in t.get("link_with_refs", [])}
    target_var_names: dict[int, str] = {}
    for idx, t in enumerate(targets):
        if t.get("var_name"):
            target_var_names[idx] = t["var_name"]
        elif idx in referenced:
            target_var_names[idx] = f"{t['name'].replace('-', '_')}_target"

    for idx, target in enumerate(targets):
        args = [_quote(target.get("name", ""))]
        for fidx in target.get("file_refs", []):
            if 0 <= fidx < len(file_groups) and file_groups[fidx].get("var_name"):
                args.append(file_groups[fidx]["var_name"])
        args += [_quote(s) for s in target.get("sources", [])]

        dep_refs = target.get("dep_refs", [])
        if dep_refs:
            items = [
                deps[i]["var_name"] if deps[i].get("var_name") else _render_dependency_call(deps[i])
                for i in dep_refs
            ]
            args.append("dependencies : [" + ", ".join(items) + "]")

        link_refs = target.get("link_with_refs", [])
        if link_refs:
            items = [target_var_names[i] for i in link_refs]
            args.append("link_with : [" + ", ".join(items) + "]")

        if target.get("install"):
            args.append("install : true")

        kind = target.get("kind", "executable")
        call = f"{kind}({', '.join(args)})"
        if idx in target_var_names:
            lines.append(f"{target_var_names[idx]} = {call}")
        else:
            lines.append(call)
        lines.append("")

    for item in model.get("install_data", []):
        args = [_quote(p) for p in item["paths"]]
        if item.get("install_dir"):
            args.append(f"install_dir : {_quote(item['install_dir'])}")
        lines.append(f"install_data({', '.join(args)})")

    for item in model.get("install_headers", []):
        args = [_quote(p) for p in item["paths"]]
        if item.get("install_dir"):
            args.append(f"install_dir : {_quote(item['install_dir'])}")
        if item.get("subdir"):
            args.append(f"subdir : {_quote(item['subdir'])}")
        if item.get("preserve_path"):
            args.append("preserve_path : true")
        lines.append(f"install_headers({', '.join(args)})")

    if model.get("install_data") or model.get("install_headers"):
        lines.append("")

    unrecognized = model.get("unrecognized", "").strip()
    if unrecognized:
        lines.append("# 以下內容未被 MesonEdit 解析，原樣保留")
        lines.append(unrecognized)
        lines.append("")

    text = "\n".join(lines)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip() + "\n"
