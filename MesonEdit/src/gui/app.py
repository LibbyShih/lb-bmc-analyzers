"""MesonEdit GUI — tkinter 視窗編輯器，視覺風格沿用 ServiceEdit。"""

from __future__ import annotations

import copy
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from schema import (
    LANGUAGE_CHOICES,
    TARGET_KIND_CHOICES,
    DEPENDENCY_METHOD_CHOICES,
    DEFAULT_OPTION_PRESETS,
    PROJECT_FIELDS,
    DEPENDENCY_FIELDS,
    FILE_GROUP_FIELDS,
    TARGET_FIELDS,
    INSTALL_DATA_FIELDS,
    INSTALL_HEADERS_FIELDS,
    DEFAULT_HELP,
    TEMPLATES,
)
from meson_io import empty_model, parse_meson_build, render_meson_build


def _file_group_label(fg: dict, idx: int) -> str:
    name = fg.get("var_name") or f"group_{idx}"
    n = len(fg.get("paths", []))
    return f"{name} ({n} 檔)"


def _dep_label(dep: dict, idx: int) -> str:
    return dep.get("var_name") or f"{dep.get('name') or '(unnamed)'} (匿名 #{idx})"


def _target_label(target: dict) -> str:
    return f"[{target.get('kind')}] {target.get('name') or '(unnamed)'}"


class MesonEditApp(tk.Tk):
    def __init__(self, initial_path: Path | None = None):
        super().__init__()
        self.title("MesonEdit")
        self.minsize(880, 580)
        self.geometry("1000x660")

        self._current_path: Path | None = None
        self._model: dict = empty_model()
        self._dirty = False
        self._last_template = "空白"
        self._selected_dep_idx: int | None = None
        self._selected_file_idx: int | None = None
        self._selected_target_idx: int | None = None
        self._suppress_dep_trace = False
        self._suppress_file_trace = False
        self._suppress_target_trace = False
        self._master_detail_paneds: list[ttk.Panedwindow] = []

        _f = "Microsoft JhengHei UI"
        _s = 10
        self._font_ui = (_f, _s)
        self._font_title = (_f, _s + 2, "bold")
        self._font_mono = ("Consolas", _s)
        self._font_small = (_f, max(_s - 1, 9))
        self._label_w = 11
        self._list_w = 18
        self._list_h = 7
        self._row_pady = 4
        self._form_pad = (8, 6)

        self._setup_style()
        self._build_header()
        self._build_body()
        self._build_status()

        if initial_path and initial_path.exists():
            self._load_file(initial_path)
        else:
            self._refresh_all()

        self.after(120, self._init_paned_sashes)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind_all("<Control-n>", lambda _e: self._new_file())
        self.bind_all("<Control-o>", lambda _e: self._open_file())
        self.bind_all("<Control-s>", lambda _e: self._save_file())

    # ---------- style ----------

    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        self._c = {
            "bg": "#eef1f6",
            "surface": "#ffffff",
            "border": "#d0d7de",
            "accent": "#2563eb",
            "header_bg": "#ffffff",
            "header_text": "#1e293b",
            "header_sub": "#64748b",
            "text": "#1e293b",
            "muted": "#64748b",
            "required": "#dc2626",
            "ok": "#15803d",
            "warn": "#b45309",
            "preview_bg": "#1e293b",
            "preview_fg": "#e2e8f0",
            "preview_section": "#7dd3fc",
            "help_bg": "#f8fafc",
            "status_bg": "#e2e8f0",
        }
        c = self._c
        self.configure(bg=c["bg"])

        style.configure(".", font=self._font_ui)
        style.configure("TFrame", background=c["bg"])
        style.configure("Surface.TFrame", background=c["surface"])
        style.configure("Header.TFrame", background=c["header_bg"])
        style.configure("TLabel", background=c["bg"], foreground=c["text"], font=self._font_ui)
        style.configure("Header.TLabel", background=c["header_bg"], foreground=c["header_sub"], font=self._font_ui)
        style.configure("Title.TLabel", font=self._font_title, background=c["header_bg"], foreground=c["header_text"])
        style.configure("TLabelframe", background=c["surface"], bordercolor=c["border"], relief=tk.GROOVE)
        style.configure(
            "TLabelframe.Label",
            background=c["surface"],
            foreground=c["accent"],
            font=(self._font_ui[0], self._font_ui[1], "bold"),
        )
        style.configure("TNotebook", background=c["bg"], borderwidth=0, tabmargins=(4, 4, 0, 0))
        style.configure("TNotebook.Tab", padding=(10, 6), font=self._font_ui)
        style.map(
            "TNotebook.Tab",
            background=[("selected", c["surface"]), ("!selected", c["bg"])],
            foreground=[("selected", c["accent"]), ("!selected", c["text"])],
        )
        style.configure("TButton", padding=(8, 4), font=self._font_ui)
        style.configure("TEntry", padding=(4, 3), fieldbackground=c["surface"], font=self._font_ui)
        style.configure("TCombobox", padding=(4, 3), fieldbackground=c["surface"], font=self._font_ui)
        style.configure("Header.TCheckbutton", background=c["header_bg"], foreground=c["text"], font=self._font_ui)
        style.configure("TCheckbutton", background=c["surface"], font=self._font_ui)
        style.configure("TSeparator", background=c["border"])
        style.configure("Status.TLabel", background=c["status_bg"], foreground=c["text"], padding=(10, 5), font=self._font_ui)

    def _grid_label(self, parent, text: str, row: int, *, sticky: str = tk.E) -> None:
        ttk.Label(parent, text=text, width=self._label_w, anchor=tk.E).grid(
            row=row, column=0, sticky=sticky, padx=(0, 8), pady=self._row_pady,
        )

    def _grid_entry(self, parent, widget, row: int, **grid_kw) -> None:
        opts = {"row": row, "column": 1, "sticky": tk.EW, "pady": self._row_pady, "padx": (0, 2)}
        opts.update(grid_kw)
        widget.grid(**opts)

    def _listbox(self, parent, **kwargs) -> tk.Listbox:
        opts = {
            "width": self._list_w,
            "height": self._list_h,
            "font": self._font_ui,
            "exportselection": False,
            "relief": tk.FLAT,
            "borderwidth": 1,
            "highlightthickness": 1,
            "highlightbackground": self._c["border"],
            "highlightcolor": self._c["accent"],
            "selectbackground": self._c["accent"],
            "selectforeground": "#ffffff",
            "activestyle": "none",
        }
        opts.update(kwargs)
        return tk.Listbox(parent, **opts)

    def _multiline(self, parent, height: int = 4, **kwargs) -> tk.Text:
        opts = {
            "height": height,
            "font": self._font_ui,
            "relief": tk.FLAT,
            "wrap": tk.WORD,
            "padx": 6,
            "pady": 4,
            "borderwidth": 1,
            "highlightthickness": 1,
            "highlightbackground": self._c["border"],
            "highlightcolor": self._c["accent"],
        }
        opts.update(kwargs)
        return tk.Text(parent, **opts)

    def _multiselect_listbox(self, parent, height: int = 4, **kwargs) -> tk.Listbox:
        return self._listbox(parent, height=height, selectmode=tk.MULTIPLE, **kwargs)

    def _configure_left_panes(self):
        try:
            self._left_paned.paneconfig(self._help_host, minsize=self._help_min)
            self._left_paned.paneconfig(self._form_host, minsize=200)
        except tk.TclError:
            pass

    def _init_master_detail_sashes(self):
        for pw in self._master_detail_paneds:
            try:
                pw.update_idletasks()
                w = pw.winfo_width()
                if w > 40:
                    pw.sashpos(0, w // 2)
            except tk.TclError:
                pass

    def _init_paned_sashes(self):
        try:
            self.update_idletasks()
            w = max(self._main_paned.winfo_width(), 400)
            self._main_paned.sashpos(0, int(w * 0.52))

            h = max(self._left_paned.winfo_height(), self._help_min + 200)
            sash = max(200, h - self._help_min)
            self._left_paned.sashpos(0, sash)
        except tk.TclError:
            pass
        self._init_master_detail_sashes()

    # ---------- header ----------

    def _build_header(self):
        header = ttk.Frame(self, style="Header.TFrame", padding=(10, 6))
        header.pack(fill=tk.X)

        title_box = ttk.Frame(header, style="Header.TFrame")
        title_box.pack(side=tk.LEFT)
        ttk.Label(title_box, text="MesonEdit", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(title_box, text="meson.build 編輯器", style="Header.TLabel").pack(anchor=tk.W)

        actions = ttk.Frame(header, style="Header.TFrame")
        actions.pack(side=tk.RIGHT)

        ttk.Button(actions, text="新建", command=self._new_file, width=8).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="開啟", command=self._open_file, width=8).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="儲存", command=self._save_file, width=8).pack(side=tk.LEFT, padx=(0, 16))

        ttk.Separator(actions, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 16), pady=2)

        ttk.Label(actions, text="範本", style="Header.TLabel").pack(side=tk.LEFT)
        self._template_var = tk.StringVar(value="空白")
        tpl = ttk.Combobox(
            actions,
            textvariable=self._template_var,
            values=list(TEMPLATES.keys()),
            state="readonly",
            width=18,
        )
        tpl.pack(side=tk.LEFT, padx=(8, 0))
        tpl.bind("<<ComboboxSelected>>", self._on_template_selected)

        tk.Frame(self, bg=self._c["border"], height=1).pack(fill=tk.X)

    # ---------- body ----------

    def _build_body(self):
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self._main_paned = paned

        left = ttk.Frame(paned, style="Surface.TFrame", padding=2)
        right = ttk.Frame(paned, style="Surface.TFrame", padding=2)
        paned.add(left, weight=3)
        paned.add(right, weight=2)

        left_paned = ttk.Panedwindow(left, orient=tk.VERTICAL)
        left_paned.pack(fill=tk.BOTH, expand=True)
        self._left_paned = left_paned

        form_host = ttk.Frame(left_paned, style="Surface.TFrame")
        help_host = ttk.Frame(left_paned, style="Surface.TFrame")
        self._form_host = form_host
        self._help_host = help_host
        left_paned.add(form_host, weight=5)
        left_paned.add(help_host, weight=2)
        self._help_min = 130
        self.after_idle(lambda: self._configure_left_panes())

        form_card = ttk.LabelFrame(form_host, text=" 欄位設定 ", padding=(4, 4))
        form_card.pack(fill=tk.BOTH, expand=True)

        self._notebook = ttk.Notebook(form_card)
        self._notebook.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self._build_project_tab()
        self._build_dependencies_tab()
        self._build_files_tab()
        self._build_targets_tab()
        self._build_install_tab()
        self._notebook.bind("<<NotebookTabChanged>>", lambda _e: self.after_idle(self._init_master_detail_sashes))

        help_frame = ttk.LabelFrame(help_host, text=" 欄位說明 ", padding=(4, 4))
        help_frame.pack(fill=tk.BOTH, expand=True)
        self._help_text = self._multiline(
            help_frame, bg=self._c["help_bg"], fg=self._c["text"], wrap=tk.WORD,
        )
        help_scroll = ttk.Scrollbar(help_frame, command=self._help_text.yview)
        self._help_text.configure(yscrollcommand=help_scroll.set)
        self._help_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        help_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._help_text.tag_configure("title", font=(self._font_ui[0], self._font_ui[1], "bold"), foreground=self._c["accent"])
        self._help_text.tag_configure("ref", foreground=self._c["muted"], font=self._font_small)
        self._help_text.configure(state=tk.DISABLED)
        self._set_help_text(DEFAULT_HELP)

        preview_frame = ttk.LabelFrame(right, text=" 即時預覽 ", padding=(4, 4))
        preview_frame.pack(fill=tk.BOTH, expand=True)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        self._preview = tk.Text(
            preview_frame, wrap=tk.NONE, font=self._font_mono,
            bg=self._c["preview_bg"], fg=self._c["preview_fg"], relief=tk.FLAT,
            padx=8, pady=6, borderwidth=0, insertbackground=self._c["preview_fg"],
            spacing1=1, spacing3=1,
        )
        yscroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self._preview.yview)
        xscroll = ttk.Scrollbar(preview_frame, orient=tk.HORIZONTAL, command=self._preview.xview)
        self._preview.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self._preview.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        self._bind_preview_mousewheel(self._preview)
        self._preview.configure(state=tk.DISABLED)
        self._preview.tag_configure("func", foreground=self._c["preview_section"])
        self._preview.tag_configure("str", foreground="#86efac")
        self._preview.tag_configure("kw", foreground="#fcd34d")
        self._preview.tag_configure("comment", foreground="#94a3b8")

    def _bind_preview_mousewheel(self, text: tk.Text):
        def _on_wheel(event):
            delta = int(-1 * (event.delta / 120))
            if event.state & 0x1:
                text.xview_scroll(delta, "units")
            else:
                text.yview_scroll(delta, "units")
            return "break"

        text.bind("<MouseWheel>", _on_wheel)
        text.bind("<Shift-MouseWheel>", _on_wheel)

    def _set_help_text(self, text: str, title: str | None = None, ref: str | None = None):
        self._help_text.configure(state=tk.NORMAL)
        self._help_text.delete("1.0", tk.END)
        if title:
            self._help_text.insert("1.0", f"{title}\n", "title")
            self._help_text.insert(tk.END, text)
        else:
            self._help_text.insert("1.0", text)
        if ref:
            self._help_text.insert(tk.END, f"\n\n文件：{ref}", "ref")
        self._help_text.configure(state=tk.DISABLED)

    def _show_field_help(self, key: str, meta: dict):
        lines = []
        if meta.get("desc"):
            lines.append(meta["desc"])
        if meta.get("default"):
            lines.append(f"預設：{meta['default']}")
        if meta.get("example"):
            lines.append(f"範例：{meta['example']}")
        self._set_help_text("\n".join(lines), title=f"【{key}】", ref=meta.get("ref"))

    # ---------- project tab ----------

    def _build_project_tab(self):
        outer = ttk.Frame(self._notebook, style="Surface.TFrame", padding=self._form_pad)
        self._notebook.add(outer, text=" Project ")
        outer.columnconfigure(1, weight=1)

        self._proj_name = tk.StringVar()
        self._proj_version = tk.StringVar()
        self._proj_meson_version = tk.StringVar()
        self._proj_langs: dict[str, tk.BooleanVar] = {lang: tk.BooleanVar() for lang in LANGUAGE_CHOICES}
        self._lang_cols = 4

        row = 0
        self._grid_label(outer, "name *", row)
        e = ttk.Entry(outer, textvariable=self._proj_name)
        self._grid_entry(outer, e, row)
        e.bind("<FocusIn>", lambda _e: self._show_field_help("name", PROJECT_FIELDS["name"]))
        self._proj_name.trace_add("write", lambda *_: self._on_change())
        row += 1

        self._grid_label(outer, "languages *", row, sticky=tk.NE)
        self._lang_box = ttk.Frame(outer, style="Surface.TFrame")
        self._lang_box.grid(row=row, column=1, sticky=tk.EW, pady=self._row_pady, padx=(0, 2))
        for col in range(self._lang_cols):
            self._lang_box.columnconfigure(col, weight=1, uniform="lang")
        for idx, lang in enumerate(LANGUAGE_CHOICES):
            r, c = divmod(idx, self._lang_cols)
            cb = ttk.Checkbutton(
                self._lang_box, text=lang, variable=self._proj_langs[lang], command=self._on_change,
            )
            cb.grid(row=r, column=c, sticky=tk.W, padx=(0, 6), pady=1)
            cb.bind("<FocusIn>", lambda _e: self._show_field_help("languages", PROJECT_FIELDS["languages"]))
        row += 1

        self._grid_label(outer, "version", row)
        e = ttk.Entry(outer, textvariable=self._proj_version)
        self._grid_entry(outer, e, row)
        e.bind("<FocusIn>", lambda _e: self._show_field_help("version", PROJECT_FIELDS["version"]))
        self._proj_version.trace_add("write", lambda *_: self._on_change())
        row += 1

        self._grid_label(outer, "meson_ver", row)
        e = ttk.Entry(outer, textvariable=self._proj_meson_version)
        self._grid_entry(outer, e, row)
        e.bind("<FocusIn>", lambda _e: self._show_field_help("meson_version", PROJECT_FIELDS["meson_version"]))
        self._proj_meson_version.trace_add("write", lambda *_: self._on_change())
        row += 1

        self._grid_label(outer, "options", row, sticky=tk.NE)
        opt_col = ttk.Frame(outer, style="Surface.TFrame")
        opt_col.grid(row=row, column=1, sticky=tk.NSEW, pady=self._row_pady, padx=(0, 2))
        opt_col.columnconfigure(0, weight=1)

        opt_row = ttk.Frame(opt_col, style="Surface.TFrame")
        opt_row.pack(fill=tk.X)
        self._opt_preset_var = tk.StringVar()
        ttk.Combobox(
            opt_row,
            textvariable=self._opt_preset_var,
            values=DEFAULT_OPTION_PRESETS,
            width=24,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(opt_row, text="加入", command=self._add_default_option_preset, width=6).pack(
            side=tk.LEFT, padx=(6, 0),
        )

        self._proj_options_text = self._multiline(opt_col, height=4)
        self._proj_options_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self._proj_options_text.bind("<FocusIn>", lambda _e: self._show_field_help("default_options", PROJECT_FIELDS["default_options"]))
        self._proj_options_text.bind("<KeyRelease>", lambda _e: self._on_change())
        outer.rowconfigure(row, weight=1)

    def _add_default_option_preset(self):
        preset = self._opt_preset_var.get().strip()
        if not preset:
            return
        lines = [l.strip() for l in self._proj_options_text.get("1.0", tk.END).splitlines() if l.strip()]
        if preset not in lines:
            lines.append(preset)
            self._proj_options_text.delete("1.0", tk.END)
            self._proj_options_text.insert("1.0", "\n".join(lines))
            self._on_change()

    def _read_project_form(self):
        self._model["project"] = {
            "name": self._proj_name.get().strip(),
            "languages": [lang for lang, var in self._proj_langs.items() if var.get()],
            "version": self._proj_version.get().strip(),
            "meson_version": self._proj_meson_version.get().strip(),
            "default_options": [
                line.strip() for line in self._proj_options_text.get("1.0", tk.END).splitlines() if line.strip()
            ],
        }

    def _write_project_form(self):
        project = self._model.get("project", {})
        self._proj_name.set(project.get("name", ""))
        self._proj_version.set(project.get("version", ""))
        self._proj_meson_version.set(project.get("meson_version", ""))
        selected = set(project.get("languages", []))
        for lang, var in self._proj_langs.items():
            var.set(lang in selected)
        self._proj_options_text.delete("1.0", tk.END)
        self._proj_options_text.insert("1.0", "\n".join(project.get("default_options", [])))

    # ---------- dependencies tab ----------

    def _build_master_detail_tab(self, notebook: ttk.Notebook, tab_text: str):
        outer = ttk.Frame(notebook, style="Surface.TFrame", padding=self._form_pad)
        notebook.add(outer, text=tab_text)
        pw = ttk.Panedwindow(outer, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True)
        list_box = ttk.Frame(pw, style="Surface.TFrame", padding=(0, 0, 4, 0))
        detail = ttk.Frame(pw, style="Surface.TFrame", padding=(4, 0, 0, 0))
        pw.add(list_box, weight=1)
        pw.add(detail, weight=1)
        self._master_detail_paneds.append(pw)
        self.after_idle(lambda p=pw: self._configure_master_detail_pane(p))
        return outer, list_box, detail

    def _configure_master_detail_pane(self, pw: ttk.Panedwindow):
        try:
            panes = pw.panes()
            if len(panes) >= 2:
                pw.paneconfig(panes[0], minsize=140)
                pw.paneconfig(panes[1], minsize=140)
        except tk.TclError:
            pass

    def _build_dependencies_tab(self):
        outer, list_box, self._dep_detail = self._build_master_detail_tab(self._notebook, " Deps ")

        self._dep_listbox = self._listbox(list_box)
        self._dep_listbox.pack(fill=tk.BOTH, expand=True)
        self._dep_listbox.bind("<<ListboxSelect>>", self._on_dep_select)

        btns = ttk.Frame(list_box, style="Surface.TFrame")
        btns.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(btns, text="新增", command=self._add_dependency, width=8).pack(side=tk.LEFT)
        ttk.Button(btns, text="刪除", command=self._remove_dependency, width=8).pack(side=tk.LEFT, padx=(8, 0))

        self._dep_var_name = tk.StringVar()
        self._dep_name = tk.StringVar()
        self._dep_method = tk.StringVar()
        self._dep_version = tk.StringVar()
        self._dep_required = tk.BooleanVar(value=True)

        def row(label_text, var, key):
            f = ttk.Frame(self._dep_detail, style="Surface.TFrame")
            f.pack(fill=tk.X, pady=self._row_pady)
            ttk.Label(f, text=label_text, width=self._label_w, anchor=tk.E).pack(side=tk.LEFT, padx=(0, 8))
            e = ttk.Entry(f, textvariable=var)
            e.pack(side=tk.LEFT, fill=tk.X, expand=True)
            e.bind("<FocusIn>", lambda _ev, k=key: self._show_field_help(k, DEPENDENCY_FIELDS[k]))
            var.trace_add("write", lambda *_: self._on_dep_detail_change())

        row("var_name", self._dep_var_name, "var_name")
        row("name *", self._dep_name, "name")

        f = ttk.Frame(self._dep_detail, style="Surface.TFrame")
        f.pack(fill=tk.X, pady=self._row_pady)
        ttk.Label(f, text="modules", width=self._label_w, anchor=tk.E).pack(side=tk.LEFT, anchor=tk.N, padx=(0, 8))
        self._dep_modules_text = self._multiline(f, height=3)
        self._dep_modules_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._dep_modules_text.bind("<FocusIn>", lambda _e: self._show_field_help("modules", DEPENDENCY_FIELDS["modules"]))
        self._dep_modules_text.bind("<KeyRelease>", lambda _e: self._on_dep_detail_change())

        f = ttk.Frame(self._dep_detail, style="Surface.TFrame")
        f.pack(fill=tk.X, pady=self._row_pady)
        ttk.Label(f, text="method", width=self._label_w, anchor=tk.E).pack(side=tk.LEFT, padx=(0, 8))
        method_cb = ttk.Combobox(
            f, textvariable=self._dep_method, values=DEPENDENCY_METHOD_CHOICES,
        )
        method_cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        method_cb.bind("<FocusIn>", lambda _e: self._show_field_help("method", DEPENDENCY_FIELDS["method"]))
        method_cb.bind("<<ComboboxSelected>>", lambda _e: self._on_dep_detail_change())
        self._dep_method.trace_add("write", lambda *_: self._on_dep_detail_change())

        row("version", self._dep_version, "version")

        f = ttk.Frame(self._dep_detail, style="Surface.TFrame")
        f.pack(fill=tk.X, pady=self._row_pady)
        ttk.Label(f, text="", width=self._label_w).pack(side=tk.LEFT)
        cb = ttk.Checkbutton(f, text="required", variable=self._dep_required, command=self._on_dep_detail_change)
        cb.pack(side=tk.LEFT)
        cb.bind("<FocusIn>", lambda _e: self._show_field_help("required", DEPENDENCY_FIELDS["required"]))

    def _refresh_dep_listbox(self):
        self._dep_listbox.delete(0, tk.END)
        for idx, dep in enumerate(self._model["dependencies"]):
            self._dep_listbox.insert(tk.END, _dep_label(dep, idx))

    def _add_dependency(self):
        self._model["dependencies"].append(
            {"var_name": "", "name": "", "modules": [], "method": "", "version": "", "required": True}
        )
        self._refresh_dep_listbox()
        self._dep_listbox.selection_clear(0, tk.END)
        self._dep_listbox.selection_set(tk.END)
        self._on_dep_select()
        self._on_change()

    def _remove_dependency(self):
        if self._selected_dep_idx is None:
            return
        del self._model["dependencies"][self._selected_dep_idx]
        for target in self._model["targets"]:
            target["dep_refs"] = [i for i in target["dep_refs"] if i != self._selected_dep_idx]
            target["dep_refs"] = [i - 1 if i > self._selected_dep_idx else i for i in target["dep_refs"]]
        self._selected_dep_idx = None
        self._refresh_dep_listbox()
        self._on_change()

    def _on_dep_select(self, _event=None):
        sel = self._dep_listbox.curselection()
        self._selected_dep_idx = sel[0] if sel else None
        if self._selected_dep_idx is None:
            return
        dep = self._model["dependencies"][self._selected_dep_idx]
        self._suppress_dep_trace = True
        self._dep_var_name.set(dep.get("var_name") or "")
        self._dep_name.set(dep.get("name", ""))
        self._dep_modules_text.delete("1.0", tk.END)
        self._dep_modules_text.insert("1.0", "\n".join(dep.get("modules", [])))
        self._dep_method.set(dep.get("method", ""))
        self._dep_version.set(dep.get("version", ""))
        self._dep_required.set(dep.get("required", True))
        self._suppress_dep_trace = False

    def _on_dep_detail_change(self):
        if self._selected_dep_idx is None or self._suppress_dep_trace:
            return
        dep = self._model["dependencies"][self._selected_dep_idx]
        dep["var_name"] = self._dep_var_name.get().strip() or None
        dep["name"] = self._dep_name.get().strip()
        dep["modules"] = [l.strip() for l in self._dep_modules_text.get("1.0", tk.END).splitlines() if l.strip()]
        dep["method"] = self._dep_method.get().strip()
        dep["version"] = self._dep_version.get().strip()
        dep["required"] = self._dep_required.get()
        self._refresh_dep_listbox()
        self._dep_listbox.selection_set(self._selected_dep_idx)
        self._on_change()

    # ---------- files tab ----------

    def _build_files_tab(self):
        outer, list_box, detail = self._build_master_detail_tab(self._notebook, " Files ")

        self._file_listbox = self._listbox(list_box)
        self._file_listbox.pack(fill=tk.BOTH, expand=True)
        self._file_listbox.bind("<<ListboxSelect>>", self._on_file_select)

        btns = ttk.Frame(list_box, style="Surface.TFrame")
        btns.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(btns, text="新增", command=self._add_file_group, width=8).pack(side=tk.LEFT)
        ttk.Button(btns, text="刪除", command=self._remove_file_group, width=8).pack(side=tk.LEFT, padx=(8, 0))

        self._file_var_name = tk.StringVar()

        f = ttk.Frame(detail, style="Surface.TFrame")
        f.pack(fill=tk.X, pady=self._row_pady)
        ttk.Label(f, text="var_name *", width=self._label_w, anchor=tk.E).pack(side=tk.LEFT, padx=(0, 8))
        e = ttk.Entry(f, textvariable=self._file_var_name)
        e.pack(side=tk.LEFT, fill=tk.X, expand=True)
        e.bind("<FocusIn>", lambda _e: self._show_field_help("var_name", FILE_GROUP_FIELDS["var_name"]))
        self._file_var_name.trace_add("write", lambda *_: self._on_file_detail_change())

        f = ttk.Frame(detail, style="Surface.TFrame")
        f.pack(fill=tk.BOTH, expand=True, pady=self._row_pady)
        ttk.Label(f, text="paths *", width=self._label_w, anchor=tk.E).pack(side=tk.LEFT, anchor=tk.N, padx=(0, 8))
        self._file_paths_text = self._multiline(f, height=7)
        self._file_paths_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._file_paths_text.bind("<FocusIn>", lambda _e: self._show_field_help("paths", FILE_GROUP_FIELDS["paths"]))
        self._file_paths_text.bind("<KeyRelease>", lambda _e: self._on_file_detail_change())

    def _refresh_file_listbox(self):
        self._file_listbox.delete(0, tk.END)
        for idx, fg in enumerate(self._model.get("file_groups", [])):
            self._file_listbox.insert(tk.END, _file_group_label(fg, idx))

    def _add_file_group(self):
        self._model.setdefault("file_groups", []).append({"var_name": "", "paths": []})
        self._refresh_file_listbox()
        self._file_listbox.selection_clear(0, tk.END)
        self._file_listbox.selection_set(tk.END)
        self._on_file_select()
        self._on_change()

    def _remove_file_group(self):
        if self._selected_file_idx is None:
            return
        removed = self._selected_file_idx
        del self._model["file_groups"][removed]
        for target in self._model["targets"]:
            target["file_refs"] = [i for i in target.get("file_refs", []) if i != removed]
            target["file_refs"] = [i - 1 if i > removed else i for i in target.get("file_refs", [])]
        self._selected_file_idx = None
        self._refresh_file_listbox()
        self._on_change()

    def _on_file_select(self, _event=None):
        sel = self._file_listbox.curselection()
        self._selected_file_idx = sel[0] if sel else None
        if self._selected_file_idx is None:
            return
        fg = self._model["file_groups"][self._selected_file_idx]
        self._suppress_file_trace = True
        self._file_var_name.set(fg.get("var_name", ""))
        self._file_paths_text.delete("1.0", tk.END)
        self._file_paths_text.insert("1.0", "\n".join(fg.get("paths", [])))
        self._suppress_file_trace = False

    def _on_file_detail_change(self):
        if self._selected_file_idx is None or getattr(self, "_suppress_file_trace", False):
            return
        fg = self._model["file_groups"][self._selected_file_idx]
        fg["var_name"] = self._file_var_name.get().strip()
        fg["paths"] = [l.strip() for l in self._file_paths_text.get("1.0", tk.END).splitlines() if l.strip()]
        self._refresh_file_listbox()
        self._file_listbox.selection_set(self._selected_file_idx)
        if self._selected_target_idx is not None:
            self._refresh_target_ref_lists()
        self._on_change()

    # ---------- targets tab ----------

    def _build_targets_tab(self):
        outer, list_box, self._target_detail = self._build_master_detail_tab(self._notebook, " Targets ")

        self._target_listbox = self._listbox(list_box)
        self._target_listbox.pack(fill=tk.BOTH, expand=True)
        self._target_listbox.bind("<<ListboxSelect>>", self._on_target_select)

        btns = ttk.Frame(list_box, style="Surface.TFrame")
        btns.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(btns, text="新增", command=self._add_target, width=8).pack(side=tk.LEFT)
        ttk.Button(btns, text="刪除", command=self._remove_target, width=8).pack(side=tk.LEFT, padx=(8, 0))

        self._target_kind = tk.StringVar(value="executable")
        self._target_var_name = tk.StringVar()
        self._target_name = tk.StringVar()
        self._target_install = tk.BooleanVar()

        f = ttk.Frame(self._target_detail, style="Surface.TFrame")
        f.pack(fill=tk.X, pady=self._row_pady)
        ttk.Label(f, text="kind", width=self._label_w, anchor=tk.E).pack(side=tk.LEFT, padx=(0, 8))
        kind_cb = ttk.Combobox(f, textvariable=self._target_kind, values=TARGET_KIND_CHOICES, state="readonly")
        kind_cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        kind_cb.bind("<<ComboboxSelected>>", lambda _e: self._on_target_detail_change())
        kind_cb.bind("<FocusIn>", lambda _e: self._show_field_help("kind", TARGET_FIELDS["kind"]))

        f = ttk.Frame(self._target_detail, style="Surface.TFrame")
        f.pack(fill=tk.X, pady=self._row_pady)
        ttk.Label(f, text="var_name", width=self._label_w, anchor=tk.E).pack(side=tk.LEFT, padx=(0, 8))
        e = ttk.Entry(f, textvariable=self._target_var_name)
        e.pack(side=tk.LEFT, fill=tk.X, expand=True)
        e.bind("<FocusIn>", lambda _e: self._show_field_help("var_name", TARGET_FIELDS["var_name"]))
        self._target_var_name.trace_add("write", lambda *_: self._on_target_detail_change())

        f = ttk.Frame(self._target_detail, style="Surface.TFrame")
        f.pack(fill=tk.X, pady=self._row_pady)
        ttk.Label(f, text="name *", width=self._label_w, anchor=tk.E).pack(side=tk.LEFT, padx=(0, 8))
        e = ttk.Entry(f, textvariable=self._target_name)
        e.pack(side=tk.LEFT, fill=tk.X, expand=True)
        e.bind("<FocusIn>", lambda _e: self._show_field_help("name", TARGET_FIELDS["name"]))
        self._target_name.trace_add("write", lambda *_: self._on_target_detail_change())

        f = ttk.Frame(self._target_detail, style="Surface.TFrame")
        f.pack(fill=tk.X, pady=self._row_pady)
        ttk.Label(f, text="sources *", width=self._label_w, anchor=tk.E).pack(side=tk.LEFT, anchor=tk.N, padx=(0, 8))
        self._target_sources_text = self._multiline(f, height=4)
        self._target_sources_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._target_sources_text.bind("<FocusIn>", lambda _e: self._show_field_help("sources", TARGET_FIELDS["sources"]))
        self._target_sources_text.bind("<KeyRelease>", lambda _e: self._on_target_detail_change())

        refs = ttk.LabelFrame(self._target_detail, text=" 引用 ", padding=(6, 4))
        refs.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

        f = ttk.Frame(refs, style="Surface.TFrame")
        f.pack(fill=tk.BOTH, expand=True, pady=2)
        ttk.Label(f, text="files()", width=self._label_w, anchor=tk.E).pack(side=tk.LEFT, anchor=tk.N, padx=(0, 8))
        self._target_file_listbox = self._multiselect_listbox(f, height=2)
        self._target_file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._target_file_listbox.bind("<<ListboxSelect>>", lambda _e: self._on_target_detail_change())
        self._target_file_listbox.bind("<FocusIn>", lambda _e: self._show_field_help("sources", TARGET_FIELDS["sources"]))

        f = ttk.Frame(refs, style="Surface.TFrame")
        f.pack(fill=tk.BOTH, expand=True, pady=2)
        ttk.Label(f, text="deps", width=self._label_w, anchor=tk.E).pack(side=tk.LEFT, anchor=tk.N, padx=(0, 8))
        self._target_dep_listbox = self._multiselect_listbox(f, height=2)
        self._target_dep_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._target_dep_listbox.bind("<<ListboxSelect>>", lambda _e: self._on_target_detail_change())
        self._target_dep_listbox.bind("<FocusIn>", lambda _e: self._show_field_help("dependencies", TARGET_FIELDS["dependencies"]))

        f = ttk.Frame(refs, style="Surface.TFrame")
        f.pack(fill=tk.BOTH, expand=True, pady=2)
        ttk.Label(f, text="link", width=self._label_w, anchor=tk.E).pack(side=tk.LEFT, anchor=tk.N, padx=(0, 8))
        self._target_link_listbox = self._multiselect_listbox(f, height=2)
        self._target_link_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._target_link_listbox.bind("<<ListboxSelect>>", lambda _e: self._on_target_detail_change())
        self._target_link_listbox.bind("<FocusIn>", lambda _e: self._show_field_help("link_with", TARGET_FIELDS["link_with"]))

        f = ttk.Frame(self._target_detail, style="Surface.TFrame")
        f.pack(fill=tk.X, pady=self._row_pady)
        ttk.Label(f, text="", width=self._label_w).pack(side=tk.LEFT)
        cb = ttk.Checkbutton(f, text="install", variable=self._target_install, command=self._on_target_detail_change)
        cb.pack(side=tk.LEFT)
        cb.bind("<FocusIn>", lambda _e: self._show_field_help("install", TARGET_FIELDS["install"]))

    def _refresh_target_listbox(self):
        self._target_listbox.delete(0, tk.END)
        for target in self._model["targets"]:
            self._target_listbox.insert(tk.END, _target_label(target))

    def _refresh_target_ref_lists(self):
        self._target_file_listbox.delete(0, tk.END)
        for idx, fg in enumerate(self._model.get("file_groups", [])):
            self._target_file_listbox.insert(tk.END, _file_group_label(fg, idx))
        self._target_dep_listbox.delete(0, tk.END)
        for idx, dep in enumerate(self._model["dependencies"]):
            self._target_dep_listbox.insert(tk.END, _dep_label(dep, idx))
        self._target_link_listbox.delete(0, tk.END)
        for idx, target in enumerate(self._model["targets"]):
            if self._selected_target_idx is not None and idx == self._selected_target_idx:
                continue
            self._target_link_listbox.insert(tk.END, _target_label(target))

    def _add_target(self):
        self._model["targets"].append(
            {
                "kind": "executable",
                "var_name": None,
                "name": "",
                "sources": [],
                "file_refs": [],
                "dep_refs": [],
                "link_with_refs": [],
                "install": False,
            }
        )
        self._refresh_target_listbox()
        self._target_listbox.selection_clear(0, tk.END)
        self._target_listbox.selection_set(tk.END)
        self._on_target_select()
        self._on_change()

    def _remove_target(self):
        if self._selected_target_idx is None:
            return
        removed = self._selected_target_idx
        del self._model["targets"][removed]
        for target in self._model["targets"]:
            target["link_with_refs"] = [i for i in target["link_with_refs"] if i != removed]
            target["link_with_refs"] = [i - 1 if i > removed else i for i in target["link_with_refs"]]
        self._selected_target_idx = None
        self._refresh_target_listbox()
        self._on_change()

    def _on_target_select(self, _event=None):
        sel = self._target_listbox.curselection()
        self._selected_target_idx = sel[0] if sel else None
        self._refresh_target_ref_lists()
        if self._selected_target_idx is None:
            return
        target = self._model["targets"][self._selected_target_idx]
        self._suppress_target_trace = True
        self._target_kind.set(target.get("kind", "executable"))
        self._target_var_name.set(target.get("var_name") or "")
        self._target_name.set(target.get("name", ""))
        self._target_sources_text.delete("1.0", tk.END)
        self._target_sources_text.insert("1.0", "\n".join(target.get("sources", [])))
        self._target_file_listbox.selection_clear(0, tk.END)
        for idx in target.get("file_refs", []):
            self._target_file_listbox.selection_set(idx)
        self._target_dep_listbox.selection_clear(0, tk.END)
        for idx in target.get("dep_refs", []):
            self._target_dep_listbox.selection_set(idx)
        link_listbox_idx = 0
        self._target_link_listbox.selection_clear(0, tk.END)
        for idx, other in enumerate(self._model["targets"]):
            if idx == self._selected_target_idx:
                continue
            if idx in target.get("link_with_refs", []):
                self._target_link_listbox.selection_set(link_listbox_idx)
            link_listbox_idx += 1
        self._target_install.set(target.get("install", False))
        self._suppress_target_trace = False

    def _on_target_detail_change(self):
        if self._selected_target_idx is None or self._suppress_target_trace:
            return
        target = self._model["targets"][self._selected_target_idx]
        target["kind"] = self._target_kind.get()
        target["var_name"] = self._target_var_name.get().strip() or None
        target["name"] = self._target_name.get().strip()
        target["sources"] = [l.strip() for l in self._target_sources_text.get("1.0", tk.END).splitlines() if l.strip()]
        target["file_refs"] = list(self._target_file_listbox.curselection())
        target["dep_refs"] = list(self._target_dep_listbox.curselection())

        other_indices = [i for i in range(len(self._model["targets"])) if i != self._selected_target_idx]
        selected_positions = self._target_link_listbox.curselection()
        target["link_with_refs"] = [other_indices[p] for p in selected_positions]

        target["install"] = self._target_install.get()
        self._refresh_target_listbox()
        self._target_listbox.selection_set(self._selected_target_idx)
        self._on_change()

    # ---------- install tab ----------

    def _build_install_tab(self):
        outer = ttk.Frame(self._notebook, style="Surface.TFrame", padding=self._form_pad)
        self._notebook.add(outer, text=" Install ")

        data_frame = ttk.LabelFrame(outer, text=" install_data ", padding=(8, 6))
        data_frame.pack(fill=tk.X, pady=(0, 8))
        data_frame.columnconfigure(1, weight=1)

        self._grid_label(data_frame, "paths", 0, sticky=tk.NE)
        self._install_data_paths_text = self._multiline(data_frame, height=3)
        self._install_data_paths_text.grid(row=0, column=1, sticky=tk.EW, pady=self._row_pady, padx=(0, 2))
        self._install_data_paths_text.bind("<FocusIn>", lambda _e: self._show_field_help("paths", INSTALL_DATA_FIELDS["paths"]))
        self._install_data_paths_text.bind("<KeyRelease>", lambda _e: self._on_change())

        self._grid_label(data_frame, "inst_dir", 1)
        self._install_data_dir = tk.StringVar()
        e = ttk.Entry(data_frame, textvariable=self._install_data_dir)
        self._grid_entry(data_frame, e, 1)
        e.bind("<FocusIn>", lambda _e: self._show_field_help("install_dir", INSTALL_DATA_FIELDS["install_dir"]))
        self._install_data_dir.trace_add("write", lambda *_: self._on_change())

        headers_frame = ttk.LabelFrame(outer, text=" install_headers ", padding=(8, 6))
        headers_frame.pack(fill=tk.X, pady=(0, 8))
        headers_frame.columnconfigure(1, weight=1)

        self._grid_label(headers_frame, "paths", 0, sticky=tk.NE)
        self._install_headers_paths_text = self._multiline(headers_frame, height=3)
        self._install_headers_paths_text.grid(row=0, column=1, sticky=tk.EW, pady=self._row_pady, padx=(0, 2))
        self._install_headers_paths_text.bind("<FocusIn>", lambda _e: self._show_field_help("paths", INSTALL_HEADERS_FIELDS["paths"]))
        self._install_headers_paths_text.bind("<KeyRelease>", lambda _e: self._on_change())

        self._grid_label(headers_frame, "subdir", 1)
        self._install_headers_subdir = tk.StringVar()
        e = ttk.Entry(headers_frame, textvariable=self._install_headers_subdir)
        self._grid_entry(headers_frame, e, 1)
        e.bind("<FocusIn>", lambda _e: self._show_field_help("subdir", INSTALL_HEADERS_FIELDS["subdir"]))
        self._install_headers_subdir.trace_add("write", lambda *_: self._on_change())

        self._grid_label(headers_frame, "inst_dir", 2)
        self._install_headers_dir = tk.StringVar()
        e = ttk.Entry(headers_frame, textvariable=self._install_headers_dir)
        self._grid_entry(headers_frame, e, 2)
        e.bind("<FocusIn>", lambda _e: self._show_field_help("install_dir", INSTALL_HEADERS_FIELDS["install_dir"]))
        self._install_headers_dir.trace_add("write", lambda *_: self._on_change())

        self._install_headers_preserve = tk.BooleanVar()
        cb_row = ttk.Frame(headers_frame, style="Surface.TFrame")
        cb_row.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(2, 0))
        ttk.Label(cb_row, text="", width=self._label_w).pack(side=tk.LEFT)
        cb = ttk.Checkbutton(
            cb_row, text="preserve_path", variable=self._install_headers_preserve, command=self._on_change,
        )
        cb.pack(side=tk.LEFT)
        cb.bind("<FocusIn>", lambda _e: self._show_field_help("preserve_path", INSTALL_HEADERS_FIELDS["preserve_path"]))

        unrec_frame = ttk.LabelFrame(outer, text=" 未解析（唯讀） ", padding=(8, 6))
        unrec_frame.pack(fill=tk.BOTH, expand=True)
        self._unrecognized_text = self._multiline(
            unrec_frame, height=3, font=self._font_mono, bg=self._c["help_bg"], fg=self._c["muted"], state=tk.DISABLED,
        )
        self._unrecognized_text.pack(fill=tk.BOTH, expand=True)

    def _read_install_form(self):
        data_paths = [l.strip() for l in self._install_data_paths_text.get("1.0", tk.END).splitlines() if l.strip()]
        self._model["install_data"] = (
            [{"paths": data_paths, "install_dir": self._install_data_dir.get().strip()}] if data_paths else []
        )
        header_paths = [l.strip() for l in self._install_headers_paths_text.get("1.0", tk.END).splitlines() if l.strip()]
        self._model["install_headers"] = (
            [{
                "paths": header_paths,
                "subdir": self._install_headers_subdir.get().strip(),
                "install_dir": self._install_headers_dir.get().strip(),
                "preserve_path": self._install_headers_preserve.get(),
            }]
            if header_paths
            else []
        )

    def _write_install_form(self):
        data_items = self._model.get("install_data", [])
        self._install_data_paths_text.delete("1.0", tk.END)
        self._install_data_dir.set("")
        if data_items:
            self._install_data_paths_text.insert("1.0", "\n".join(data_items[0]["paths"]))
            self._install_data_dir.set(data_items[0].get("install_dir", ""))

        header_items = self._model.get("install_headers", [])
        self._install_headers_paths_text.delete("1.0", tk.END)
        self._install_headers_subdir.set("")
        self._install_headers_dir.set("")
        self._install_headers_preserve.set(False)
        if header_items:
            self._install_headers_paths_text.insert("1.0", "\n".join(header_items[0]["paths"]))
            self._install_headers_subdir.set(header_items[0].get("subdir", ""))
            self._install_headers_dir.set(header_items[0].get("install_dir", ""))
            self._install_headers_preserve.set(header_items[0].get("preserve_path", False))

        self._unrecognized_text.configure(state=tk.NORMAL)
        self._unrecognized_text.delete("1.0", tk.END)
        unrec = self._model.get("unrecognized", "").strip()
        if unrec:
            self._unrecognized_text.insert("1.0", unrec)
        else:
            self._unrecognized_text.insert("1.0", "（無）")
        self._unrecognized_text.configure(state=tk.DISABLED)

    # ---------- status / preview ----------

    def _build_status(self):
        status_bar = tk.Frame(self, bg=self._c["status_bg"], height=28)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self._status = ttk.Label(status_bar, text="就緒", style="Status.TLabel", anchor=tk.W)
        self._status.pack(fill=tk.X)

    def _validate(self) -> list[str]:
        warnings = []
        if not self._model["project"].get("name"):
            warnings.append("project name 為必填")
        if not self._model["project"].get("languages"):
            warnings.append("project languages 至少選一個")
        for idx, dep in enumerate(self._model["dependencies"]):
            if not dep.get("name"):
                warnings.append(f"依賴 #{idx} 的 name 為必填")
        for idx, fg in enumerate(self._model.get("file_groups", [])):
            if not fg.get("var_name"):
                warnings.append(f"files 群組 #{idx} 的 var_name 為必填")
            if not fg.get("paths"):
                warnings.append(f"files 群組 #{idx} 的 paths 至少需要一筆")
        for idx, target in enumerate(self._model["targets"]):
            if not target.get("name"):
                warnings.append(f"target #{idx} 的 name 為必填")
            has_sources = bool(target.get("sources")) or bool(target.get("file_refs"))
            if not has_sources:
                warnings.append(f"target #{idx} 的 sources 或 files() 引用至少需要一筆")
        return warnings

    def _highlight_preview(self, text: str):
        self._preview.delete("1.0", tk.END)
        if not text:
            return
        patterns = [
            ("comment", r"^#.*$"),
            ("str", r"'[^'\\]*(?:\\.[^'\\]*)*'"),
            ("kw", r"\b(?:version|meson_version|default_options|modules|method|required|dependencies|link_with|install|install_dir|subdir|preserve_path)\s*:"),
            ("func", r"\b(?:project|dependency|files|executable|library|static_library|shared_library|install_data|install_headers)\b"),
        ]
        pos = 0
        while pos < len(text):
            best = None
            for tag, pat in patterns:
                m = re.match(pat, text[pos:], re.MULTILINE if tag == "comment" else 0)
                if m and (best is None or m.start() < best[2]):
                    best = (tag, m.group(0), m.start(), m.end())
            if best is None:
                next_special = len(text)
                for tag, pat in patterns:
                    m = re.search(pat, text[pos:])
                    if m and m.start() < next_special - pos:
                        next_special = pos + m.start()
                chunk = text[pos:next_special]
                if chunk:
                    self._preview.insert(tk.END, chunk)
                pos = next_special if next_special > pos else pos + 1
                continue
            tag, chunk, start, end = best
            if start > 0:
                self._preview.insert(tk.END, text[pos : pos + start])
            self._preview.insert(tk.END, chunk, tag)
            pos = pos + end

    def _on_change(self):
        self._read_project_form()
        self._read_install_form()
        self._dirty = True
        self._update_title()
        self._refresh_preview()

    def _refresh_preview(self):
        text = render_meson_build(self._model)
        self._preview.configure(state=tk.NORMAL)
        self._highlight_preview(text)
        self._preview.configure(state=tk.DISABLED)

        warnings = self._validate()
        if warnings:
            self._status.configure(text="⚠  " + "  ·  ".join(warnings), foreground=self._c["warn"])
        elif self._current_path:
            self._status.configure(text=f"就緒  —  {self._current_path.name}", foreground=self._c["text"])
        else:
            self._status.configure(text="就緒", foreground=self._c["text"])

    def _update_title(self):
        title = "MesonEdit"
        if self._current_path:
            title += f" — {self._current_path.name}"
        if self._dirty:
            title += " *"
        self.title(title)

    def _refresh_all(self):
        self._write_project_form()
        self._refresh_dep_listbox()
        self._refresh_file_listbox()
        self._refresh_target_listbox()
        self._refresh_target_ref_lists()
        self._write_install_form()
        self._refresh_preview()
        self._update_title()

    # ---------- file ops ----------

    def _apply_template(self, name: str):
        template = TEMPLATES.get(name)
        if self._dirty and not messagebox.askyesno("套用範本", "尚未儲存，套用範本會覆蓋內容。繼續？", parent=self):
            self._template_var.set(self._last_template)
            return
        self._last_template = name
        self._template_var.set(name)
        self._model = empty_model() if template is None else copy.deepcopy(template)
        self._current_path = None
        self._selected_dep_idx = None
        self._selected_file_idx = None
        self._selected_target_idx = None
        self._refresh_all()
        self._dirty = name != "空白"
        self._update_title()

    def _on_template_selected(self, _event=None):
        self._apply_template(self._template_var.get())

    def _new_file(self):
        if self._dirty and not messagebox.askyesno("新建", "捨棄未儲存的變更？", parent=self):
            return
        self._model = empty_model()
        self._current_path = None
        self._selected_dep_idx = None
        self._selected_file_idx = None
        self._selected_target_idx = None
        self._template_var.set("空白")
        self._last_template = "空白"
        self._refresh_all()
        self._dirty = False
        self._update_title()
        self._set_help_text(DEFAULT_HELP)

    def _open_file(self):
        path = filedialog.askopenfilename(
            title="開啟 meson.build", filetypes=[("meson.build", "meson.build"), ("所有檔案", "*.*")]
        )
        if path:
            self._load_file(Path(path))

    def _load_file(self, path: Path):
        try:
            text = path.read_text(encoding="utf-8")
            self._model = parse_meson_build(text)
        except Exception as exc:
            messagebox.showerror("載入失敗", str(exc), parent=self)
            return
        self._current_path = path
        self._selected_dep_idx = None
        self._selected_file_idx = None
        self._selected_target_idx = None
        self._dirty = False
        self._template_var.set("空白")
        self._last_template = "空白"
        self._refresh_all()
        self._update_title()

    def _save_file(self):
        if self._current_path:
            self._write_path(self._current_path)
        else:
            self._save_file_as()

    def _save_file_as(self):
        path = filedialog.asksaveasfilename(
            title="儲存 meson.build", defaultextension="", initialfile="meson.build",
            filetypes=[("meson.build", "meson.build"), ("所有檔案", "*.*")],
        )
        if path:
            self._write_path(Path(path))

    def _write_path(self, path: Path):
        warnings = self._validate()
        if warnings:
            msg = "下列項目需要注意：\n\n" + "\n".join(f"• {w}" for w in warnings) + "\n\n仍要儲存？"
            if not messagebox.askyesno("儲存確認", msg, parent=self):
                return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(render_meson_build(self._model), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("儲存失敗", str(exc), parent=self)
            return
        self._current_path = path
        self._dirty = False
        self._update_title()
        self._status.configure(text=f"已儲存  —  {path.name}", foreground=self._c["ok"])

    def _on_close(self):
        if self._dirty:
            ans = messagebox.askyesnocancel("離開", "是否儲存變更後離開？", parent=self)
            if ans is None:
                return
            if ans:
                self._save_file()
                if self._dirty:
                    return
        self.destroy()


def run_gui(initial_path: Path | None = None):
    app = MesonEditApp(initial_path=initial_path)
    app.mainloop()
