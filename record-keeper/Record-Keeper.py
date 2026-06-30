import json
import os
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from PIL import Image, ImageTk
from datetime import datetime, timezone

JSON_PATH = r"../../HEAT-Labs-Configs/player-records.json"
SCREENSHOTS_FOLDER = r"../../HEAT-Labs-Images-Features/player-records"

C_BG = "#0f1117"
C_PANEL = "#181c27"
C_CARD = "#1e2235"
C_BORDER = "#2a3050"
C_ACCENT = "#00e5c8"
C_ACCENT2 = "#0077ff"
C_TEXT = "#e8eaf0"
C_SUBTEXT = "#7b82a0"
C_SUCCESS = "#22c55e"
C_WARN = "#f59e0b"
C_ERROR = "#ef4444"
C_NEW_BADGE = "#1a3a2a"
C_NEW_TEXT = "#22c55e"
C_DONE_BADGE = "#1a1f35"
C_DONE_TEXT = "#5c6280"
C_LOGGED_BADGE = "#1a2a3a"
C_LOGGED_TEXT = "#5c9eff"
C_NOT_LOGGED_BADGE = "#3a1a1a"
C_NOT_LOGGED_TEXT = "#ff5c5c"

MODES = ["conquest", "control", "hardpoint", "kill-confirmed"]
MODE_LABELS = {"conquest": "Conquest", "control": "Control", "hardpoint": "Hardpoint",
               "kill-confirmed": "Kill Confirmed"}


def parse_filename(filename):
    stem = Path(filename).stem
    stem_clean = re.sub(r"-\d+$", "", stem)
    parts = stem_clean.split("_", 1)
    date_part = parts[0] if len(parts) > 0 else ""
    player_part = parts[1] if len(parts) > 1 else stem_clean
    return player_part, date_part


def is_kill_confirmed_mode(mode_folder):
    return mode_folder == "kill-confirmed"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_known_proofs(data):
    proofs = set()
    for mode_data in data.get("records", {}).values():
        if not isinstance(mode_data, dict):
            continue
        for records in mode_data.values():
            # Check if records is a list before iterating
            if not isinstance(records, list):
                continue
            for rec in records:
                # Check if rec is a dictionary before calling .get()
                if isinstance(rec, dict):
                    p = rec.get("proof", "")
                    if p:
                        proofs.add(Path(p).name)
    return proofs


def count_empty_fields(record):
    """Count how many required fields are empty in a record"""
    required_fields = ["captures", "destroyed", "deaths", "assists", "damage_caused", "damage_blocked",
                       "credits", "tech", "intel", "XP", "agent", "vehicle", "outcome", "map"]

    empty_count = 0
    for field in required_fields:
        value = record.get(field)
        if value in [None, "", 0, "0"]:
            empty_count += 1
    return empty_count


def get_complete_records(data):
    """Get set of fully logged records (allow up to 2 empty fields)"""
    complete = set()
    required_fields = ["captures", "destroyed", "deaths", "assists", "damage_caused", "damage_blocked",
                       "credits", "tech", "intel", "XP", "agent", "vehicle", "outcome", "map"]

    for mode_data in data.get("records", {}).values():
        if not isinstance(mode_data, dict):
            continue
        for records in mode_data.values():
            if not isinstance(records, list):
                continue
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                # Check if record has at most 2 empty fields
                empty_count = 0
                for field in required_fields:
                    value = rec.get(field)
                    if value in [None, "", 0, "0"]:
                        empty_count += 1
                if empty_count <= 2:  # Allow up to 2 empty fields
                    p = rec.get("proof", "")
                    if p:
                        complete.add(Path(p).name)
    return complete


def get_partial_records(data, complete_proofs):
    """Get set of records that exist but are not complete (more than 2 empty fields)"""
    partial = set()
    required_fields = ["captures", "destroyed", "deaths", "assists", "damage_caused", "damage_blocked",
                       "credits", "tech", "intel", "XP", "agent", "vehicle", "outcome", "map"]

    for mode_data in data.get("records", {}).values():
        if not isinstance(mode_data, dict):
            continue
        for records in mode_data.values():
            if not isinstance(records, list):
                continue
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                p = rec.get("proof", "")
                if not p:
                    continue

                proof_name = Path(p).name
                if proof_name in complete_proofs:
                    continue

                # Check if record has any data (at least one field filled)
                has_data = False
                for field in required_fields:
                    value = rec.get(field)
                    if value not in [None, "", 0, "0"]:
                        has_data = True
                        break

                if has_data:
                    partial.add(proof_name)
    return partial


def scan_screenshots(folder, known_proofs, complete_proofs, partial_proofs):
    results = []
    base = Path(folder)
    for mode in MODES:
        sub = base / mode
        if not sub.exists():
            continue
        for f in sorted(sub.iterdir()):
            if f.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                continue
            player, _ = parse_filename(f.name)

            # Determine status
            if f.name in complete_proofs:
                status = "logged"  # Complete with <=2 empty fields
            elif f.name in partial_proofs:
                status = "partial"  # Exists but incomplete (>2 empty fields)
            elif f.name in known_proofs:
                status = "partial"  # Known but not in complete or partial sets
            else:
                status = "not_logged"  # Not in JSON at all

            results.append({
                "mode": mode,
                "player": player,
                "filename": f.name,
                "filepath": str(f),
                "status": status,
            })
    return results


class HeatRecordKeeper(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HEAT Labs — Player Record Keeper")
        self.geometry("1340x820")
        self.minsize(1100, 700)
        self.configure(bg=C_BG)

        self.json_path = tk.StringVar(value=JSON_PATH)
        self.folder_path = tk.StringVar(value=SCREENSHOTS_FOLDER)
        self.records_data = {}
        self.screenshots = []
        self.current_idx = -1
        self.field_vars = {}
        self.preview_img = None
        self.current_preview_path = None
        self.resize_after_id = None

        self._build_ui()
        self._try_auto_load()

    def _build_ui(self):
        self._build_titlebar()
        self._build_path_bar()
        self._build_body()

    def _build_titlebar(self):
        bar = tk.Frame(self, bg=C_PANEL, height=54)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        logo = tk.Label(bar, text="⬡  HEAT Labs", bg=C_PANEL, fg=C_ACCENT, font=("Segoe UI", 15, "bold"))
        logo.pack(side="left", padx=20, pady=12)

        subtitle = tk.Label(bar, text="Player Record Keeper", bg=C_PANEL, fg=C_SUBTEXT, font=("Segoe UI", 10))
        subtitle.pack(side="left", pady=14)

        self.status_lbl = tk.Label(bar, text="", bg=C_PANEL, fg=C_SUBTEXT, font=("Segoe UI", 9))
        self.status_lbl.pack(side="right", padx=20)

    def _build_path_bar(self):
        bar = tk.Frame(self, bg=C_BORDER, height=1)
        bar.pack(fill="x")

        frame = tk.Frame(self, bg=C_PANEL, pady=10)
        frame.pack(fill="x")

        def path_row(parent, label, var, browse_fn):
            row = tk.Frame(parent, bg=C_PANEL)
            row.pack(side="left", padx=(16, 0))
            tk.Label(row, text=label, bg=C_PANEL, fg=C_SUBTEXT, font=("Segoe UI", 8)).pack(anchor="w")
            inner = tk.Frame(row, bg=C_CARD, bd=0, highlightthickness=1, highlightbackground=C_BORDER)
            inner.pack(fill="x")
            e = tk.Entry(inner, textvariable=var, bg=C_CARD, fg=C_TEXT, insertbackground=C_TEXT, relief="flat",
                         font=("Segoe UI", 9), width=42)
            e.pack(side="left", padx=8, pady=5)
            tk.Button(inner, text="…", command=browse_fn, bg=C_CARD, fg=C_SUBTEXT, relief="flat", font=("Segoe UI", 9),
                      cursor="hand2", activebackground=C_BORDER, activeforeground=C_TEXT).pack(side="left", padx=(0, 4))

        path_row(frame, "JSON FILE", self.json_path, self._browse_json)
        path_row(frame, "SCREENSHOTS FOLDER", self.folder_path, self._browse_folder)

        tk.Button(frame, text="  SCAN  ", command=self._load_and_scan, bg=C_ACCENT, fg=C_BG, relief="flat",
                  font=("Segoe UI", 9, "bold"), cursor="hand2", activebackground="#00c4ad", activeforeground=C_BG,
                  padx=12, pady=6).pack(side="left", padx=16, pady=4)

    def _build_body(self):
        tk.Frame(self, bg=C_BORDER, height=1).pack(fill="x")

        body = tk.Frame(self, bg=C_BG)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0, minsize=310)
        body.columnconfigure(1, weight=0, minsize=1)
        body.columnconfigure(2, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_list_panel(body)
        tk.Frame(body, bg=C_BORDER, width=1).grid(row=0, column=1, sticky="ns")
        self._build_detail_panel(body)

    def _build_list_panel(self, parent):
        pane = tk.Frame(parent, bg=C_PANEL)
        pane.grid(row=0, column=0, sticky="nsew")
        pane.rowconfigure(1, weight=1)
        pane.columnconfigure(0, weight=1)

        hdr = tk.Frame(pane, bg=C_PANEL, pady=10)
        hdr.grid(row=0, column=0, sticky="ew", padx=12)
        tk.Label(hdr, text="SCREENSHOTS", bg=C_PANEL, fg=C_TEXT, font=("Segoe UI", 9, "bold")).pack(side="left")
        self.count_lbl = tk.Label(hdr, text="", bg=C_PANEL, fg=C_SUBTEXT, font=("Segoe UI", 8))
        self.count_lbl.pack(side="right")

        tab_bar = tk.Frame(pane, bg=C_PANEL)
        tab_bar.grid(row=0, column=0, sticky="ew", pady=(36, 0), padx=12)
        self.filter_var = tk.StringVar(value="all")
        for val, lbl in [("all", "All"), ("logged", "LOGGED"), ("not_logged", "NOT LOGGED"), ("partial", "PARTIAL")]:
            b = tk.Radiobutton(tab_bar, text=lbl, variable=self.filter_var, value=val, command=self._refresh_list,
                               bg=C_PANEL, fg=C_SUBTEXT, selectcolor=C_CARD, activebackground=C_PANEL,
                               activeforeground=C_TEXT, font=("Segoe UI", 8), relief="flat", indicatoron=False, padx=10,
                               pady=4, bd=0, cursor="hand2")
            b.pack(side="left", padx=(0, 2))

        container = tk.Frame(pane, bg=C_PANEL)
        container.grid(row=1, column=0, sticky="nsew", padx=0)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        canvas = tk.Canvas(container, bg=C_PANEL, bd=0, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")

        sb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        sb.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=sb.set)

        self.list_frame = tk.Frame(canvas, bg=C_PANEL)
        self.list_window = canvas.create_window((0, 0), window=self.list_frame, anchor="nw")

        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        self.list_frame.bind("<Configure>", _on_frame_configure)

        def _on_canvas_configure(e):
            canvas.itemconfig(self.list_window, width=e.width)

        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self._list_canvas = canvas

    def _build_detail_panel(self, parent):
        pane = tk.Frame(parent, bg=C_BG)
        pane.grid(row=0, column=2, sticky="nsew")
        pane.rowconfigure(1, weight=1)
        pane.columnconfigure(0, weight=1)

        self.empty_lbl = tk.Label(pane, text="Select a screenshot from the list\nto review and confirm its data.",
                                  bg=C_BG, fg=C_SUBTEXT, font=("Segoe UI", 11))
        self.empty_lbl.grid(row=0, column=0, rowspan=2, sticky="nsew", pady=200)

        self.detail_frame = tk.Frame(pane, bg=C_BG)
        self.detail_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.detail_frame.grid_remove()
        self.detail_frame.rowconfigure(1, weight=1)
        self.detail_frame.columnconfigure(0, weight=1)
        self.detail_frame.columnconfigure(1, weight=0, minsize=340)

        self._build_detail_header()
        self._build_detail_left()
        self._build_detail_right()

        self.bind("<Configure>", self._on_window_resize)

    def _build_detail_header(self):
        hdr = tk.Frame(self.detail_frame, bg=C_PANEL, height=52)
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew")
        hdr.pack_propagate(False)

        self.detail_title = tk.Label(hdr, text="", bg=C_PANEL, fg=C_TEXT, font=("Segoe UI", 12, "bold"))
        self.detail_title.pack(side="left", padx=16, pady=14)

        self.detail_mode_badge = tk.Label(hdr, text="", bg=C_ACCENT2, fg="white", font=("Segoe UI", 8, "bold"), padx=8,
                                          pady=2)
        self.detail_mode_badge.pack(side="left", padx=6, pady=18)

        nav_frame = tk.Frame(hdr, bg=C_PANEL)
        nav_frame.pack(side="right", padx=16)
        tk.Button(nav_frame, text="◀", command=self._prev_screenshot, bg=C_CARD, fg=C_TEXT, relief="flat",
                  font=("Segoe UI", 10), cursor="hand2", padx=8, pady=4, activebackground=C_BORDER).pack(side="left",
                                                                                                         padx=2)
        tk.Button(nav_frame, text="▶", command=self._next_screenshot, bg=C_CARD, fg=C_TEXT, relief="flat",
                  font=("Segoe UI", 10), cursor="hand2", padx=8, pady=4, activebackground=C_BORDER).pack(side="left")

    def _build_detail_left(self):
        left = tk.Frame(self.detail_frame, bg=C_BG)
        left.grid(row=1, column=0, sticky="nsew", padx=16, pady=12)
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        img_container = tk.Frame(left, bg=C_CARD, bd=0, highlightthickness=1, highlightbackground=C_BORDER)
        img_container.grid(row=0, column=0, sticky="nsew")
        img_container.rowconfigure(0, weight=1)
        img_container.columnconfigure(0, weight=1)

        self.img_label = tk.Label(img_container, bg=C_CARD)
        self.img_label.grid(row=0, column=0, sticky="nsew")

        self.status_msg = tk.Label(left, text="", bg=C_BG, fg=C_ACCENT, font=("Segoe UI", 9))
        self.status_msg.grid(row=1, column=0, pady=4)

    def _on_window_resize(self, event):
        if self.current_preview_path and not self.resize_after_id:
            self.resize_after_id = self.after(200, self._delayed_resize)

    def _delayed_resize(self):
        self.resize_after_id = None
        if self.current_preview_path:
            self._load_preview(self.current_preview_path)

    def _build_detail_right(self):
        right = tk.Frame(self.detail_frame, bg=C_PANEL, width=340)
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        canvas = tk.Canvas(right, bg=C_PANEL, bd=0, highlightthickness=0, width=340)
        canvas.grid(row=1, column=0, sticky="nsew")

        sb = ttk.Scrollbar(right, orient="vertical", command=canvas.yview)
        sb.grid(row=1, column=1, sticky="ns")
        canvas.configure(yscrollcommand=sb.set)

        self.fields_frame = tk.Frame(canvas, bg=C_PANEL)
        win = canvas.create_window((0, 0), window=self.fields_frame, anchor="nw")

        def _on_ff_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        self.fields_frame.bind("<Configure>", _on_ff_configure)

        def _on_c_configure(e):
            canvas.itemconfig(win, width=e.width)

        canvas.bind("<Configure>", _on_c_configure)

        self._right_canvas = canvas

        btn_frame = tk.Frame(right, bg=C_PANEL, pady=10)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12)

        tk.Button(btn_frame, text="  ✓  CONFIRM & SAVE  ", command=self._confirm_and_save, bg=C_ACCENT, fg=C_BG,
                  relief="flat", font=("Segoe UI", 9, "bold"), cursor="hand2", padx=14, pady=6,
                  activebackground="#00c4ad").pack(side="left")

    def _prev_screenshot(self):
        if self.current_idx > 0:
            self._select_screenshot(self.current_idx - 1)

    def _next_screenshot(self):
        if self.current_idx < len(self._visible_indices()) - 1:
            self._select_screenshot(self.current_idx + 1)

    def _visible_indices(self):
        flt = self.filter_var.get()
        return [i for i, s in enumerate(self.screenshots) if
                flt == "all" or s["status"] == flt]

    def _browse_json(self):
        p = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if p:
            self.json_path.set(p)

    def _browse_folder(self):
        p = filedialog.askdirectory()
        if p:
            self.folder_path.set(p)

    def _try_auto_load(self):
        if Path(JSON_PATH).exists() and Path(SCREENSHOTS_FOLDER).exists():
            self.after(300, self._load_and_scan)

    def _load_and_scan(self):
        jp = self.json_path.get()
        fp = self.folder_path.get()

        if not Path(jp).exists():
            messagebox.showerror("Error", f"JSON file not found:\n{jp}")
            return
        if not Path(fp).exists():
            messagebox.showerror("Error", f"Screenshots folder not found:\n{fp}")
            return

        try:
            self.records_data = load_json(jp)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load JSON:\n{e}")
            return

        known = get_known_proofs(self.records_data)
        complete = get_complete_records(self.records_data)
        partial = get_partial_records(self.records_data, complete)
        self.screenshots = scan_screenshots(fp, known, complete, partial)

        # Count statuses
        logged_count = sum(1 for s in self.screenshots if s["status"] == "logged")
        partial_count = sum(1 for s in self.screenshots if s["status"] == "partial")
        not_logged_count = sum(1 for s in self.screenshots if s["status"] == "not_logged")

        self.count_lbl.config(
            text=f"✓ {logged_count} logged · ⚡ {partial_count} partial · ✗ {not_logged_count} not logged")
        self.status_lbl.config(text=f"Loaded {len(self.screenshots)} screenshots from {fp}")

        self._refresh_list()

    def _refresh_list(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        flt = self.filter_var.get()
        visible = [(i, s) for i, s in enumerate(self.screenshots) if
                   flt == "all" or s["status"] == flt]

        if not visible:
            tk.Label(self.list_frame, text="Nothing here.", bg=C_PANEL, fg=C_SUBTEXT, font=("Segoe UI", 9)).pack(
                pady=20)
            return

        for list_pos, (real_idx, s) in enumerate(visible):
            self._make_list_item(list_pos, real_idx, s)

    def _make_list_item(self, list_pos, real_idx, s):
        status = s["status"]

        # Determine card colors based on status
        if status == "logged":
            card_bg = C_LOGGED_BADGE
            text_color = C_LOGGED_TEXT
            status_text = "LOGGED"
            status_bg = C_LOGGED_BADGE
            status_fg = C_LOGGED_TEXT
        elif status == "partial":
            card_bg = C_DONE_BADGE
            text_color = C_DONE_TEXT
            status_text = "PARTIAL"
            status_bg = C_DONE_BADGE
            status_fg = C_DONE_TEXT
        else:  # not_logged
            card_bg = C_NEW_BADGE
            text_color = C_NEW_TEXT
            status_text = "NOT LOGGED"
            status_bg = C_NEW_BADGE
            status_fg = C_NEW_TEXT

        card = tk.Frame(self.list_frame, bg=card_bg, cursor="hand2", pady=8, padx=10)
        card.pack(fill="x", padx=0, pady=1)
        card.columnconfigure(1, weight=1)

        mode_colors = {"conquest": "#f59e0b", "control": "#0077ff", "hardpoint": "#ef4444", "kill-confirmed": "#a855f7"}
        dot_color = mode_colors.get(s["mode"], C_ACCENT)
        dot = tk.Frame(card, bg=dot_color, width=4)
        dot.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 8))

        tk.Label(card, text=s["player"], bg=card["bg"], fg=C_TEXT if status == "logged" else C_SUBTEXT,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w")

        info = f"{MODE_LABELS[s['mode']]}  ·  {s['filename']}"
        tk.Label(card, text=info, bg=card["bg"], fg=C_SUBTEXT, font=("Segoe UI", 7)).grid(row=1, column=1, sticky="w")

        badge = tk.Label(card, text=status_text, bg=status_bg, fg=status_fg, font=("Segoe UI", 7, "bold"), padx=5,
                         pady=1)
        badge.grid(row=0, column=2, rowspan=2, padx=6)

        def on_click(e, idx=real_idx):
            self._select_screenshot(idx)

        for w in (card, dot, badge) + tuple(card.winfo_children()):
            try:
                w.bind("<Button-1>", on_click)
            except Exception:
                pass

    def _get_existing_record(self, s):
        mode_key = s["mode"]
        player = s["player"]
        filename = s["filename"]

        mode_data = self.records_data.get("records", {}).get(mode_key, {})
        player_records = mode_data.get(player, [])

        for rec in player_records:
            proof_path = Path(rec.get("proof", ""))
            if proof_path.name == filename:
                return rec
        return None

    def _select_screenshot(self, real_idx):
        self.current_idx = real_idx
        s = self.screenshots[real_idx]

        self.empty_lbl.grid_remove()
        self.detail_frame.grid()

        self.detail_title.config(text=f"{s['player']}  ·  {s['filename']}")
        mode_lbl = MODE_LABELS.get(s["mode"], s["mode"])
        self.detail_mode_badge.config(text=mode_lbl.upper())

        self.current_preview_path = s["filepath"]
        self._load_preview(s["filepath"])

        existing_record = self._get_existing_record(s)
        self._build_fields(s, existing_record)

        if existing_record:
            # Check how many empty fields
            empty_count = count_empty_fields(existing_record)
            if s["status"] == "logged":
                self.status_msg.config(
                    text=f"✓ Complete record found ({empty_count} empty fields allowed). Edit and confirm to update.")
            else:
                self.status_msg.config(
                    text=f"⚠ Partial record found ({empty_count} empty fields). Complete missing fields and confirm.")
        else:
            self.status_msg.config(text="✗ No record found. Enter data and confirm.")

    def _load_preview(self, filepath):
        try:
            img = Image.open(filepath)

            if self.img_label.winfo_width() > 1:
                avail_w = max(200, self.img_label.winfo_width() - 20)
                avail_h = max(200, self.img_label.winfo_height() - 20)
            else:
                avail_w = 600
                avail_h = 400

            img.thumbnail((avail_w, avail_h), Image.LANCZOS)
            self.preview_img = ImageTk.PhotoImage(img)
            self.img_label.config(image=self.preview_img)
        except Exception as e:
            self.img_label.config(image="", text=f"Preview unavailable: {e}")

    def _build_fields(self, s, existing_record=None):
        for w in self.fields_frame.winfo_children():
            w.destroy()
        self.field_vars.clear()

        is_kc = is_kill_confirmed_mode(s["mode"])

        if is_kc:
            stat_fields = [
                ("confirms", "Confirms"),
                ("denies", "Denies"),
                ("destroyed", "Destroyed"),
                ("deaths", "Deaths"),
                ("assists", "Assists"),
                ("damage_caused", "Damage Caused"),
                ("damage_blocked", "Damage Blocked"),
            ]
        else:
            stat_fields = [
                ("captures", "Captures"),
                ("destroyed", "Destroyed"),
                ("deaths", "Deaths"),
                ("assists", "Assists"),
                ("damage_caused", "Damage Caused"),
                ("damage_blocked", "Damage Blocked"),
            ]

        meta_fields = [
            ("credits", "Credits (Rewards)"),
            ("tech", "Tech (Rewards)"),
            ("intel", "Intel (Rewards)"),
            ("XP", "Vehicle XP"),
            ("agent", "Agent"),
            ("vehicle", "Vehicle"),
            ("outcome", "Outcome"),
            ("map", "Map"),
        ]

        def section(title):
            tk.Label(self.fields_frame, text=title, bg=C_PANEL, fg=C_SUBTEXT, font=("Segoe UI", 7, "bold")).pack(
                anchor="w", padx=14, pady=(12, 2))
            tk.Frame(self.fields_frame, bg=C_BORDER, height=1).pack(fill="x", padx=14, pady=(0, 6))

        def field_row(key, label):
            row = tk.Frame(self.fields_frame, bg=C_PANEL)
            row.pack(fill="x", padx=14, pady=3)
            row.columnconfigure(1, weight=1)
            tk.Label(row, text=label, bg=C_PANEL, fg=C_SUBTEXT, font=("Segoe UI", 8), width=16, anchor="w").grid(row=0,
                                                                                                                 column=0,
                                                                                                                 sticky="w")

            if existing_record and key in existing_record:
                default_value = str(existing_record[key])
            else:
                default_value = ""

            var = tk.StringVar(value=default_value)
            self.field_vars[key] = var
            ent = tk.Entry(row, textvariable=var, bg=C_CARD, fg=C_TEXT, insertbackground=C_TEXT, relief="flat",
                           font=("Segoe UI", 9), highlightthickness=1, highlightbackground=C_BORDER,
                           highlightcolor=C_ACCENT)
            ent.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        section("MATCH STATS")
        for k, lbl in stat_fields:
            field_row(k, lbl)

        section("REWARDS & META")
        for k, lbl in meta_fields:
            field_row(k, lbl)

        section("PROOF")
        proof_url = self._build_proof_url(s)
        row = tk.Frame(self.fields_frame, bg=C_PANEL)
        row.pack(fill="x", padx=14, pady=3)
        tk.Label(row, text=proof_url, bg=C_PANEL, fg=C_ACCENT, font=("Segoe UI", 7), wraplength=300,
                 justify="left").pack(anchor="w")

        tk.Frame(self.fields_frame, bg=C_PANEL, height=20).pack()

    def _build_proof_url(self, s):
        base = "https://cdn6.heatlabs.net/player-records"
        return f"{base}/{s['mode']}/{s['filename']}"

    def _update_last_updated(self, mode_key):
        """Update the last_updated timestamp for a specific mode"""
        # Get current UTC time in ISO format
        now_utc = datetime.now(timezone.utc)
        timestamp = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Ensure the ROOT and last_updated structure exists
        records = self.records_data.setdefault("records", {})
        root = records.setdefault("ROOT", {})
        last_updated = root.setdefault("last_updated", {})

        # Update the timestamp for this mode
        last_updated[mode_key] = timestamp

        # Also update a general "last_updated" field if it exists
        root["last_updated"] = last_updated

    def _confirm_and_save(self):
        if self.current_idx < 0:
            return

        s = self.screenshots[self.current_idx]
        mode_key = s["mode"]

        record = {}
        for key, var in self.field_vars.items():
            raw = var.get().strip()
            try:
                if key in ["credits", "tech", "intel", "XP", "captures", "confirms", "denies", "destroyed", "deaths",
                           "assists", "damage_caused", "damage_blocked"]:
                    record[key] = int(re.sub(r"[^\d]", "", raw)) if raw else 0
                else:
                    record[key] = raw
            except Exception:
                record[key] = 0 if key in ["credits", "tech", "intel", "XP", "captures", "confirms", "denies",
                                           "destroyed", "deaths", "assists", "damage_caused", "damage_blocked"] else raw

        record["mode"] = MODE_LABELS[s["mode"]]
        record["proof"] = self._build_proof_url(s)

        rec_block = self.records_data.setdefault("records", {})
        mode_block = rec_block.setdefault(mode_key, {})
        player_list = mode_block.setdefault(s["player"], [])

        proof = record["proof"]
        updated = False
        for i, existing in enumerate(player_list):
            if Path(existing.get("proof", "")).name == Path(proof).name:
                player_list[i] = record
                updated = True
                break
        if not updated:
            player_list.append(record)

        # Update the last_updated timestamp for this mode
        self._update_last_updated(mode_key)

        try:
            save_json(self.json_path.get(), self.records_data)
        except Exception as e:
            messagebox.showerror("Save Error", str(e))
            return

        # Update the status based on completeness (allow up to 2 empty fields)
        required_fields = ["captures", "destroyed", "deaths", "assists", "damage_caused", "damage_blocked",
                           "credits", "tech", "intel", "XP", "agent", "vehicle", "outcome", "map"]

        empty_count = 0
        for field in required_fields:
            value = record.get(field)
            if value in [None, "", 0, "0"]:
                empty_count += 1

        if empty_count <= 2:
            self.screenshots[self.current_idx]["status"] = "logged"
        elif empty_count < len(required_fields):
            self.screenshots[self.current_idx]["status"] = "partial"
        else:
            self.screenshots[self.current_idx]["status"] = "not_logged"

        self._refresh_list()

        # Get the timestamp we just set for display
        timestamp = self.records_data["records"]["ROOT"]["last_updated"].get(mode_key, "Unknown")
        self.status_lbl.config(text=f"Saved record for {s['player']} ({mode_key}) - Last updated: {timestamp}")
        self.status_msg.config(
            text=f"Record saved! {empty_count} empty fields. {'Updated' if updated else 'Added new entry'}.")

        self._build_fields(s, record)

        # Auto-navigate to next non-logged item
        next_indices = [i for i, sc in enumerate(self.screenshots) if sc["status"] != "logged"]
        if next_indices and self.current_idx < len(self.screenshots) - 1:
            # Find next item after current
            for idx in next_indices:
                if idx > self.current_idx:
                    self.after(600, lambda: self._select_screenshot(idx))
                    break


if __name__ == "__main__":
    app = HeatRecordKeeper()
    s = ttk.Style(app)
    try:
        s.theme_use("clam")
    except Exception:
        pass
    s.configure("Vertical.TScrollbar", background=C_CARD, troughcolor=C_PANEL, arrowcolor=C_SUBTEXT,
                bordercolor=C_BORDER, lightcolor=C_CARD, darkcolor=C_CARD)
    app.mainloop()