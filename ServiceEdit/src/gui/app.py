"""ServiceEdit GUI — tkinter 視窗編輯器。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from schema import (
    KEY_DEFS,
    SECTIONS_ORDER,
    SECTION_LABELS,
    TIER_LABELS,
    TIER_ORDER,
    TEMPLATES,
    DEFAULT_HELP,
)
from service_io import (
    parse_service_file,
    render_service,
    collect_form_data,
    validate_service,
)


class ServiceEditApp(tk.Tk):
    def __init__(self, initial_path: Path | None = None):
        super().__init__()
        self.title("ServiceEdit")
        self.minsize(980, 680)
        self.geometry("1120x760")

        self._current_path: Path | None = None
        self._vars: dict[str, dict[str, tk.StringVar]] = {}
        self._extra_vars: dict[str, dict[str, tk.StringVar]] = {}
        self._field_blocks: list[tuple[str, str, tk.Frame, dict]] = []
        self._tier_frames: dict[str, dict[str, ttk.LabelFrame]] = {}
        self._extra_containers: dict[str, ttk.LabelFrame] = {}
        self._section_canvas: dict[str, tk.Canvas] = {}
        self._show_advanced = tk.BooleanVar(value=False)
        self._dirty = False
        self._suppress_dirty = False
        self._last_template = "空白"

        # 統一字級（11pt）；標題略大
        _f = "Microsoft JhengHei UI"
        _s = 11
        self._font_ui = (_f, _s)
        self._font_title = (_f, _s + 3, "bold")
        self._font_mono = ("Consolas", _s)

        self._setup_style()
        self._init_vars()
        self._build_header()
        self._build_body()
        self._build_status()
        self._bind_dirty()

        if initial_path and initial_path.exists():
            self._load_file(initial_path)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind_all("<Control-n>", lambda _e: self._new_file())
        self.bind_all("<Control-o>", lambda _e: self._open_file())
        self.bind_all("<Control-s>", lambda _e: self._save_file())
        self.after(50, self._refresh_preview)

    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # 中性藍灰（通用工具風）
        self._c = {
            "bg": "#eef1f6",
            "surface": "#ffffff",
            "stripe": "#f6f8fb",
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
            "preview_key": "#93c5fd",
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
        style.configure("TNotebook.Tab", padding=(18, 8), font=self._font_ui)
        style.map(
            "TNotebook.Tab",
            background=[("selected", c["surface"]), ("!selected", c["bg"])],
            foreground=[("selected", c["accent"]), ("!selected", c["text"])],
        )
        style.configure("TButton", padding=(14, 7), font=self._font_ui)
        style.configure("Clear.TButton", padding=(2, 2), width=2, font=self._font_ui)
        style.configure("TEntry", padding=6, fieldbackground=c["surface"], font=self._font_ui)
        style.configure("TCombobox", padding=6, fieldbackground=c["surface"], font=self._font_ui)
        style.configure("Header.TCheckbutton", background=c["header_bg"], foreground=c["text"], font=self._font_ui)
        style.configure("TCheckbutton", background=c["surface"], font=self._font_ui)
        style.configure("TSeparator", background=c["border"])
        style.configure("Status.TLabel", background=c["status_bg"], foreground=c["text"], padding=(12, 7), font=self._font_ui)

    def _build_header(self):
        header = ttk.Frame(self, style="Header.TFrame", padding=(18, 12))
        header.pack(fill=tk.X)

        title_box = ttk.Frame(header, style="Header.TFrame")
        title_box.pack(side=tk.LEFT)
        ttk.Label(title_box, text="ServiceEdit", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(title_box, text="systemd .service 編輯器", style="Header.TLabel").pack(anchor=tk.W)

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
            width=20,
        )
        tpl.pack(side=tk.LEFT, padx=(8, 16))
        tpl.bind("<<ComboboxSelected>>", self._on_template_selected)

        ttk.Checkbutton(
            actions,
            text="進階欄位",
            style="Header.TCheckbutton",
            variable=self._show_advanced,
            command=self._update_field_visibility,
        ).pack(side=tk.LEFT)

        tk.Frame(self, bg=self._c["border"], height=1).pack(fill=tk.X)

    def _build_body(self):
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        left = ttk.Frame(paned, style="Surface.TFrame", padding=2)
        right = ttk.Frame(paned, style="Surface.TFrame", padding=2)
        paned.add(left, weight=3)
        paned.add(right, weight=2)

        form_card = ttk.LabelFrame(left, text="  欄位設定  ", padding=(4, 6))
        form_card.pack(fill=tk.BOTH, expand=True)

        self._notebook = ttk.Notebook(form_card)
        self._notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._tab_frames: dict[str, ttk.Frame] = {}
        for section in SECTIONS_ORDER:
            outer = ttk.Frame(self._notebook, style="Surface.TFrame")
            self._notebook.add(outer, text=f"  {SECTION_LABELS.get(section, section)}  ")

            canvas = tk.Canvas(
                outer,
                highlightthickness=0,
                borderwidth=0,
                bg=self._c["surface"],
            )
            scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
            inner = ttk.Frame(canvas, style="Surface.TFrame", padding=(8, 6))
            window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

            def _on_inner_configure(_event, c=canvas):
                c.configure(scrollregion=c.bbox("all"))

            def _on_canvas_configure(event, c=canvas, wid=window_id):
                c.itemconfigure(wid, width=event.width)

            inner.bind("<Configure>", _on_inner_configure)
            canvas.bind("<Configure>", _on_canvas_configure)
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            self._tab_frames[section] = inner
            self._build_section_form(section, inner)
            self._bind_canvas_mousewheel(canvas, inner)
            self._section_canvas[section] = canvas

        help_frame = ttk.LabelFrame(left, text="  欄位說明  ", padding=(8, 6))
        help_frame.pack(fill=tk.X, pady=(10, 0))

        self._help_text = tk.Text(
            help_frame,
            height=10,
            wrap=tk.WORD,
            font=self._font_ui,
            relief=tk.FLAT,
            bg=self._c["help_bg"],
            fg=self._c["text"],
            padx=10,
            pady=8,
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=self._c["border"],
            highlightcolor=self._c["accent"],
        )
        help_scroll = ttk.Scrollbar(help_frame, command=self._help_text.yview)
        self._help_text.configure(yscrollcommand=help_scroll.set)
        self._help_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        help_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._help_text.tag_configure(
            "title",
            font=(self._font_ui[0], self._font_ui[1], "bold"),
            foreground=self._c["accent"],
        )
        self._help_text.tag_configure("muted", foreground=self._c["muted"])
        self._help_text.configure(state=tk.DISABLED)
        self._set_help_text(DEFAULT_HELP)
        self._bind_text_mousewheel(self._help_text)

        preview_frame = ttk.LabelFrame(right, text="  即時預覽  ", padding=(6, 6))
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self._preview = tk.Text(
            preview_frame,
            wrap=tk.NONE,
            font=self._font_mono,
            bg=self._c["preview_bg"],
            fg=self._c["preview_fg"],
            relief=tk.FLAT,
            padx=10,
            pady=8,
            borderwidth=0,
            insertbackground=self._c["preview_fg"],
        )
        yscroll = ttk.Scrollbar(preview_frame, command=self._preview.yview)
        self._preview.configure(yscrollcommand=yscroll.set)
        self._preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._preview.tag_configure(
            "section",
            foreground=self._c["preview_section"],
            font=(self._font_mono[0], self._font_mono[1], "bold"),
        )
        self._preview.tag_configure("key", foreground=self._c["preview_key"])
        self._preview.configure(state=tk.DISABLED)
        self._bind_text_mousewheel(self._preview)

    def _wheel_scroll_canvas(self, canvas: tk.Canvas, event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _bind_canvas_mousewheel(self, canvas: tk.Canvas, root: tk.Widget):
        def _on_wheel(event, c=canvas):
            return self._wheel_scroll_canvas(c, event)

        def _bind_tree(widget: tk.Widget):
            widget.bind("<MouseWheel>", _on_wheel, add="+")
            for child in widget.winfo_children():
                _bind_tree(child)

        canvas.bind("<MouseWheel>", _on_wheel)
        _bind_tree(root)

    def _bind_text_mousewheel(self, text: tk.Text):
        def _on_wheel(event):
            text.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        text.bind("<MouseWheel>", _on_wheel)

    def _build_section_form(self, section: str, parent: ttk.Frame):
        self._tier_frames[section] = {}

        for tier in TIER_ORDER:
            items = [
                (key, meta)
                for key, meta in KEY_DEFS.get(section, {}).items()
                if meta.get("tier", "common") == tier
            ]
            if not items:
                continue

            lf = ttk.LabelFrame(parent, text=f"  {TIER_LABELS[tier]}  ", padding=(8, 6))
            lf.pack(fill=tk.X, pady=(0, 8))
            lf.columnconfigure(1, weight=1)
            self._tier_frames[section][tier] = lf

            for row_idx, (key, meta) in enumerate(items):
                self._add_field_row(lf, section, key, meta, row_idx)

        extra_box = ttk.LabelFrame(parent, text="  其他欄位  ", padding=(8, 6))
        extra_box.pack(fill=tk.X, pady=(0, 4))
        extra_box.pack_forget()
        extra_box.columnconfigure(1, weight=1)
        self._extra_containers[section] = extra_box

    def _add_field_row(
        self,
        parent: ttk.LabelFrame,
        section: str,
        key: str,
        meta: dict,
        row: int,
    ) -> None:
        required = meta.get("required", False)
        stripe = self._c["surface"] if row % 2 == 0 else self._c["stripe"]

        block = tk.Frame(parent, bg=stripe, padx=6, pady=6)
        block.grid(row=row, column=0, sticky=tk.EW)
        parent.columnconfigure(0, weight=1)

        label_text = f"{key}  *" if required else key
        fg = self._c["required"] if required else self._c["text"]
        tk.Label(
            block,
            text=label_text,
            bg=stripe,
            fg=fg,
            font=self._font_ui,
            width=22,
            anchor=tk.W,
        ).grid(row=0, column=0, sticky=tk.W, padx=(4, 0))

        var = self._vars[section][key]
        choices = meta.get("choices")
        if choices:
            cb_state = "readonly" if required else "normal"
            widget = ttk.Combobox(block, textvariable=var, values=choices, state=cb_state)
        else:
            widget = ttk.Entry(block, textvariable=var)

        widget.grid(row=0, column=1, sticky=tk.EW, padx=(10, 0))
        block.columnconfigure(1, weight=1)

        if not required:
            ttk.Button(
                block,
                text="×",
                style="Clear.TButton",
                command=lambda v=var: v.set(""),
            ).grid(row=0, column=2, padx=(6, 4))

        widget.bind("<FocusIn>", lambda _e, m=meta, k=key: self._show_field_help(k, m))
        if choices:
            widget.bind("<<ComboboxSelected>>", lambda _e, m=meta, k=key: self._show_field_help(k, m))

        self._field_blocks.append((section, key, block, meta))

    def _set_help_text(self, text: str, title: str | None = None):
        self._help_text.configure(state=tk.NORMAL)
        self._help_text.delete("1.0", tk.END)
        if title:
            self._help_text.insert("1.0", f"{title}\n", "title")
            self._help_text.insert(tk.END, text)
        else:
            self._help_text.insert("1.0", text, "muted")
        self._help_text.configure(state=tk.DISABLED)

    def _show_field_help(self, key: str, meta: dict):
        lines: list[str] = []
        if meta.get("desc"):
            lines.append(meta["desc"])
        if meta.get("choices"):
            lines.append(f"\n可選值：{' | '.join(meta['choices'])}")
        if meta.get("default"):
            lines.append(f"預設：{meta['default']}")
        if meta.get("example"):
            lines.append(f"範例：{meta['example']}")
        if not meta.get("required"):
            lines.append("\n選填欄位，可刪除內容或按 × 清空。")
        self._set_help_text("\n".join(lines), title=f"【{key}】")

    def _build_status(self):
        status_bar = tk.Frame(self, bg=self._c["status_bg"], height=28)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self._status = ttk.Label(status_bar, text="就緒", style="Status.TLabel", anchor=tk.W)
        self._status.pack(fill=tk.X)

    def _init_vars(self):
        for section in SECTIONS_ORDER:
            self._vars[section] = {key: tk.StringVar() for key in KEY_DEFS.get(section, {})}
            self._extra_vars[section] = {}

    def _bind_dirty(self):
        for section_vars in self._vars.values():
            for var in section_vars.values():
                var.trace_add("write", lambda *_: self._on_var_change())

    def _on_var_change(self):
        self._mark_dirty()
        self._update_field_visibility()
        self._refresh_preview()

    def _mark_dirty(self):
        if self._suppress_dirty:
            return
        self._dirty = True
        title = "ServiceEdit"
        if self._current_path:
            title += f" — {self._current_path.name}"
        if self._dirty:
            title += " *"
        self.title(title)

    def _get_service_type(self) -> str:
        return self._vars["[Service]"]["Type"].get().strip() or "simple"

    def _update_field_visibility(self):
        svc_type = self._get_service_type()
        show_adv = self._show_advanced.get()

        for section in SECTIONS_ORDER:
            tiers = self._tier_frames.get(section, {})
            for lf in tiers.values():
                lf.pack_forget()
            for tier in TIER_ORDER:
                lf = tiers.get(tier)
                if not lf:
                    continue
                if tier == "advanced" and not show_adv:
                    continue
                lf.pack(fill=tk.X, pady=(0, 8))

        for section, _key, block, meta in self._field_blocks:
            tier = meta.get("tier", "common")
            show_when = meta.get("show_when_type")
            visible = True
            if tier == "advanced" and not show_adv:
                visible = False
            if show_when and svc_type not in show_when:
                visible = False
            if visible:
                block.grid()
            else:
                block.grid_remove()

        for section in SECTIONS_ORDER:
            box = self._extra_containers[section]
            if self._extra_vars.get(section):
                box.pack(fill=tk.X, pady=(0, 4))
            else:
                box.pack_forget()

    def _gather_data(self) -> dict[str, dict[str, str]]:
        known = {s: {k: v.get() for k, v in keys.items()} for s, keys in self._vars.items()}
        extra = {s: {k: v.get() for k, v in keys.items()} for s, keys in self._extra_vars.items()}
        return collect_form_data(known, extra)

    def _refresh_preview(self):
        data = self._gather_data()
        content = render_service(data)
        warnings = validate_service(data)

        self._preview.configure(state=tk.NORMAL)
        self._preview.delete("1.0", tk.END)
        for line in content.splitlines():
            if line.startswith("[") and line.endswith("]"):
                self._preview.insert(tk.END, line + "\n", "section")
            elif "=" in line:
                key, _, val = line.partition("=")
                self._preview.insert(tk.END, key, "key")
                self._preview.insert(tk.END, "=" + val + "\n")
            else:
                self._preview.insert(tk.END, line + "\n")
        self._preview.configure(state=tk.DISABLED)

        if warnings:
            self._status.configure(text="⚠  " + "  ·  ".join(warnings), foreground=self._c["warn"])
        elif self._current_path:
            self._status.configure(text=f"就緒  —  {self._current_path.name}", foreground=self._c["text"])
        else:
            self._status.configure(text="就緒", foreground=self._c["text"])

    def _clear_extra_ui(self):
        for section in SECTIONS_ORDER:
            box = self._extra_containers[section]
            for child in list(box.winfo_children()):
                child.destroy()
            self._extra_vars[section] = {}

    def _render_extra_field(self, section: str, key: str, var: tk.StringVar, row: int):
        box = self._extra_containers[section]
        stripe = self._c["surface"] if row % 2 == 0 else self._c["stripe"]
        row_frame = tk.Frame(box, bg=stripe, padx=4, pady=4)
        row_frame.pack(fill=tk.X)

        tk.Label(
            row_frame,
            text=key,
            bg=stripe,
            fg=self._c["text"],
            font=self._font_ui,
            width=22,
            anchor=tk.W,
        ).grid(row=0, column=0, sticky=tk.W, padx=(4, 0))
        entry = ttk.Entry(row_frame, textvariable=var)
        entry.grid(row=0, column=1, sticky=tk.EW, padx=(10, 0))
        row_frame.columnconfigure(1, weight=1)
        ttk.Button(row_frame, text="×", style="Clear.TButton", command=lambda v=var: v.set("")).grid(
            row=0, column=2, padx=(6, 4)
        )
        canvas = self._section_canvas.get(section)
        if canvas:
            def _on_wheel(event, c=canvas):
                return self._wheel_scroll_canvas(c, event)
            for w in (row_frame, entry):
                w.bind("<MouseWheel>", _on_wheel)

    def _set_form_data(self, data: dict[str, dict[str, str]]):
        self._suppress_dirty = True
        try:
            for section in SECTIONS_ORDER:
                for key, var in self._vars[section].items():
                    var.set(data.get(section, {}).get(key, ""))

            self._clear_extra_ui()
            for section in SECTIONS_ORDER:
                known = set(KEY_DEFS.get(section, {}))
                extra_row = 0
                for key, value in data.get(section, {}).items():
                    if key in known:
                        continue
                    var = tk.StringVar(value=value)
                    self._extra_vars[section][key] = var
                    self._render_extra_field(section, key, var, extra_row)
                    var.trace_add("write", lambda *_: self._on_var_change())
                    extra_row += 1
        finally:
            self._suppress_dirty = False

        self._update_field_visibility()
        self._refresh_preview()

    def _apply_template(self, name: str):
        if name not in TEMPLATES:
            return
        if self._dirty and not messagebox.askyesno(
            "套用範本", "尚未儲存，套用範本會覆蓋內容。繼續？", parent=self
        ):
            self._template_var.set(self._last_template)
            return

        self._last_template = name
        self._template_var.set(name)
        merged: dict[str, dict[str, str]] = {s: {} for s in SECTIONS_ORDER}
        for section, fields in TEMPLATES[name].items():
            merged.setdefault(section, {}).update(fields)
        self._set_form_data(merged)
        self._dirty = name != "空白"
        self._mark_dirty()

    def _on_template_selected(self, _event=None):
        self._apply_template(self._template_var.get())

    def _new_file(self):
        if self._dirty and not messagebox.askyesno("新建", "捨棄未儲存的變更？", parent=self):
            return
        self._current_path = None
        for section in SECTIONS_ORDER:
            for var in self._vars[section].values():
                var.set("")
        self._clear_extra_ui()
        self._template_var.set("空白")
        self._last_template = "空白"
        self._update_field_visibility()
        self._refresh_preview()
        self._dirty = False          # 放在 var.set() 之後，避免 trace 污染 dirty 狀態
        self.title("ServiceEdit")
        self._set_help_text(DEFAULT_HELP)

    def _open_file(self):
        path = filedialog.askopenfilename(
            title="開啟 .service",
            filetypes=[("systemd unit", "*.service"), ("所有檔案", "*.*")],
        )
        if path:
            self._load_file(Path(path))

    def _load_file(self, path: Path):
        try:
            data = parse_service_file(path)
        except Exception as exc:
            messagebox.showerror("載入失敗", str(exc), parent=self)
            return

        self._current_path = path
        self._dirty = False
        self._set_form_data(data)
        self._template_var.set("空白")
        self._last_template = "空白"
        self.title(f"ServiceEdit — {path.name}")

    def _save_file(self):
        if self._current_path:
            self._write_path(self._current_path)
        else:
            self._save_file_as()

    def _save_file_as(self):
        path = filedialog.asksaveasfilename(
            title="儲存 .service",
            defaultextension=".service",
            filetypes=[("systemd unit", "*.service"), ("所有檔案", "*.*")],
            initialfile=(self._current_path.name if self._current_path else "output.service"),
        )
        if path:
            self._write_path(Path(path))

    def _write_path(self, path: Path):
        data = self._gather_data()
        warnings = validate_service(data)
        if warnings:
            msg = "下列項目需要注意：\n\n" + "\n".join(f"• {w}" for w in warnings) + "\n\n仍要儲存？"
            if not messagebox.askyesno("儲存確認", msg, parent=self):
                return

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(render_service(data), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("儲存失敗", str(exc), parent=self)
            return

        self._current_path = path
        self._dirty = False
        self.title(f"ServiceEdit — {path.name}")
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
    app = ServiceEditApp(initial_path=initial_path)
    app.mainloop()
