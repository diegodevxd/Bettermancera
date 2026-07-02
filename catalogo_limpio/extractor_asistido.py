import os
import re
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FOLDER = os.path.join(BASE_DIR, "paginas_catalogo")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "fotos_catalogo")
SQL_PATH = os.path.join(BASE_DIR, "productos.sql")
MAPPING_PATH = os.path.join(BASE_DIR, "mapeo_final.json")

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

BG = "#1a1b26"
PANEL = "#16161e"
PANEL2 = "#232331"
ACCENT = "#7aa2f7"
ACCENT2 = "#bb9af7"
TEXT = "#c0caf5"
MUTED = "#565f89"
SUCCESS = "#9ece6a"
DANGER = "#f7768e"
BORDER = "#2a2e42"

FONT = ("Segoe UI", 10)
FONT_SB = ("Segoe UI", 9)
FONT_H = ("Segoe UI Semibold", 13)
FONT_TITLE = ("Segoe UI Semibold", 16)
FONT_MONO = ("Cascadia Code", 10)


def load_products():
    products = {}
    if os.path.exists(SQL_PATH):
        with open(SQL_PATH, encoding="utf-8") as f:
            for line in f:
                m = re.search(r"\('(\d{5})',\s*'([^']*)'", line)
                if m:
                    products[m.group(1)] = m.group(2)
    return products


def load_page_map():
    page_map = {}
    if os.path.exists(MAPPING_PATH):
        import json
        try:
            with open(MAPPING_PATH, encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                pid = item.get("id_sql")
                pg = item.get("pagina_origen")
                if pid and pg:
                    page_map[pid] = pg
        except Exception:
            pass
    return page_map


def natural_sort_key(name):
    nums = re.findall(r"\d+", name)
    return int(nums[0]) if nums else 0


class CropDialog(tk.Toplevel):
    def __init__(self, master, crop_img, app):
        super().__init__(master)
        self.app = app
        self.crop_img = crop_img
        self.result = None
        self.configure(bg=PANEL)
        self.title("Guardar recorte")
        self.transient(master)
        self.grab_set()

        w, h = crop_img.size
        self.resizable(False, False)

        title = tk.Label(self, text="Confirma el recorte", bg=PANEL, fg=TEXT, font=FONT_H)
        title.grid(row=0, column=0, columnspan=2, padx=20, pady=(16, 4), sticky="w")

        dim_lbl = tk.Label(self, text=f"Tamaño: {w} x {h} px", bg=PANEL, fg=MUTED, font=FONT_SB)
        dim_lbl.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 8), sticky="w")

        prev_w = 360
        prev_h = int(h * prev_w / w) if w else 100
        prev_h = min(prev_h, 460)
        preview = crop_img.copy()
        preview.thumbnail((prev_w, prev_h))
        self.tk_prev = ImageTk.PhotoImage(preview)
        prev = tk.Label(self, image=self.tk_prev, bg="#0d0d14", bd=0, highlightthickness=1,
                        highlightbackground=BORDER)
        prev.grid(row=2, column=0, rowspan=4, padx=(20, 12), pady=4, sticky="n")

        form = tk.Frame(self, bg=PANEL)
        form.grid(row=2, column=1, padx=(0, 20), pady=4, sticky="n")

        tk.Label(form, text="ID del producto", bg=PANEL, fg=MUTED, font=FONT_SB).pack(anchor="w")
        self.id_var = tk.StringVar(value=app.pending_id or "")
        id_entry = tk.Entry(form, textvariable=self.id_var, font=FONT_MONO, width=18,
                            bg=PANEL2, fg=TEXT, insertbackground=TEXT, relief="flat",
                            highlightthickness=1, highlightbackground=ACCENT, highlightcolor=ACCENT)
        id_entry.pack(fill="x", pady=(2, 6))
        id_entry.focus_set()
        id_entry.icursor("end")

        self.name_var = tk.StringVar()
        self.name_lbl = tk.Label(form, textvariable=self.name_var, bg=PANEL, fg=SUCCESS,
                                 font=FONT, wraplength=240, justify="left")
        self.name_lbl.pack(anchor="w", pady=(0, 12))

        self.id_var.trace_add("write", self._on_id_change)

        btns = tk.Frame(self, bg=PANEL)
        btns.grid(row=6, column=0, columnspan=2, padx=20, pady=(8, 16), sticky="ew")
        save_btn = tk.Button(btns, text="Guardar", command=self._save, bg=ACCENT, fg="#0d0d14",
                             font=FONT_H, relief="flat", activebackground=ACCENT2, cursor="hand2",
                             width=12, bd=0)
        save_btn.pack(side="left", padx=(0, 8))
        tk.Button(btns, text="Cancelar", command=self.destroy, bg=PANEL2, fg=TEXT, font=FONT,
                  relief="flat", activebackground=PANEL, cursor="hand2", width=10, bd=0,
                  highlightthickness=1, highlightbackground=BORDER).pack(side="left")
        self.save_btn = save_btn

        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self.destroy())
        self._on_id_change()

    def _on_id_change(self, *_):
        cid = self.id_var.get().strip()
        if cid in self.app.products:
            self.name_var.set("✓  " + self.app.products[cid])
            self.name_lbl.config(fg=SUCCESS)
            self.save_btn.config(state="normal")
        elif cid:
            self.name_var.set("⚠  ID no encontrado en el catálogo")
            self.name_lbl.config(fg=DANGER)
            self.save_btn.config(state="normal")
        else:
            self.name_var.set("")
            self.save_btn.config(state="disabled")

    def _save(self):
        cid = self.id_var.get().strip()
        if not cid:
            return
        out = os.path.join(OUTPUT_FOLDER, f"{cid}.png")
        if os.path.exists(out):
            if not messagebox.askyesno("Sobrescribir", f"Ya existe {cid}.png\n¿Sobrescribir?",
                                       parent=self, icon="warning"):
                return
        self.crop_img.save(out)
        self.result = cid
        self.destroy()


class ExtractorApp:
    def __init__(self, root):
        self.root = root
        self.products = load_products()
        self.page_map = load_page_map()
        self.images = sorted(
            [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith((".png", ".jpg", ".jpeg"))],
            key=natural_sort_key,
        )
        if not self.images:
            messagebox.showerror("Error", f"No hay imágenes en {INPUT_FOLDER}/")
            root.destroy()
            return

        self.current_idx = 0
        self.zoom = 1.0
        self.orig = None
        self.img_w = self.img_h = 1
        self.tk_img = None
        self.img_item = None

        self.start_cx = self.start_cy = None
        self.cur_cx = self.cur_cy = None
        self.rect_item = None
        self.dim_item = None
        self.dim_bg_item = None

        self.pending_id = None
        self.saved_ids = set()
        self.filter_done_only = tk.BooleanVar(value=False)
        self.search_var = tk.StringVar()

        self._build_ui()
        self._scan_saved()
        self._refresh_list()
        self.load_image()
        self.root.after(50, self._focus_canvas)

    def _btn(self, parent, text, command, primary=False):
        if primary:
            b = tk.Button(parent, text=text, command=command, bg=ACCENT, fg="#0d0d14",
                          font=FONT, relief="flat", activebackground=ACCENT2, cursor="hand2",
                          bd=0, padx=12, pady=5)
        else:
            b = tk.Button(parent, text=text, command=command, bg=PANEL2, fg=TEXT, font=FONT,
                          relief="flat", activebackground=PANEL, cursor="hand2", bd=0, padx=12,
                          pady=5, highlightthickness=1, highlightbackground=BORDER)
        b.bind("<Enter>", lambda e: b.config(bg=ACCENT2 if primary else BORDER))
        b.bind("<Leave>", lambda e: b.config(bg=ACCENT if primary else PANEL2))
        return b

    def _build_ui(self):
        self.root.configure(bg=BG)
        self.root.geometry("1320x860")
        self.root.minsize(1000, 640)

        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True)

        self._build_sidebar(main)
        self._build_canvas_area(main)
        self._build_statusbar(self.root)

        self.root.bind("<Prior>", lambda e: self.goto_page(self.current_idx - 1))
        self.root.bind("<Next>", lambda e: self.goto_page(self.current_idx + 1))
        self.root.bind("<Control-equal>", lambda e: self._zoom(1.25))
        self.root.bind("<Control-minus>", lambda e: self._zoom(0.8))
        self.root.bind("<Escape>", self._cancel_sel)

    def _build_sidebar(self, parent):
        side = tk.Frame(parent, bg=PANEL, width=330, bd=0, highlightthickness=0)
        side.pack(side="right", fill="y", padx=(0, 0))
        side.pack_propagate(False)

        header = tk.Frame(side, bg=PANEL)
        header.pack(fill="x", padx=18, pady=(18, 10))
        tk.Label(header, text="Extractor BW", bg=PANEL, fg=ACCENT, font=FONT_TITLE).pack(anchor="w")
        tk.Label(header, text="Recorta fotos del catálogo", bg=PANEL, fg=MUTED, font=FONT_SB).pack(anchor="w")

        nav = tk.Frame(side, bg=PANEL)
        nav.pack(fill="x", padx=18, pady=(0, 6))
        self._btn(nav, "«", lambda: self.goto_page(0)).pack(side="left")
        self._btn(nav, "‹", lambda: self.goto_page(self.current_idx - 1)).pack(side="left", padx=(6, 0))
        self.page_lbl = tk.Label(nav, text="", bg=PANEL, fg=TEXT, font=FONT, width=12)
        self.page_lbl.pack(side="left", fill="x", expand=True)
        self._btn(nav, "›", lambda: self.goto_page(self.current_idx + 1)).pack(side="right", padx=(0, 0))
        self._btn(nav, "»", lambda: self.goto_page(len(self.images) - 1)).pack(side="right", padx=(0, 6))

        pgframe = tk.Frame(side, bg=PANEL)
        pgframe.pack(fill="x", padx=18, pady=(0, 12))
        tk.Label(pgframe, text="Ir a página:", bg=PANEL, fg=MUTED, font=FONT_SB).pack(side="left")
        self.goto_entry = tk.Entry(pgframe, width=5, font=FONT_MONO, bg=PANEL2, fg=TEXT,
                                   insertbackground=TEXT, relief="flat", highlightthickness=1,
                                   highlightbackground=BORDER, justify="center")
        self.goto_entry.pack(side="left", padx=6)
        self.goto_entry.bind("<Return>", self._goto_entry)
        self._btn(pgframe, "Ir", self._goto_entry).pack(side="left", padx=4)

        zoom_frame = tk.Frame(side, bg=PANEL)
        zoom_frame.pack(fill="x", padx=18, pady=(0, 14))
        tk.Label(zoom_frame, text="Zoom", bg=PANEL, fg=MUTED, font=FONT_SB).pack(side="left")
        self._btn(zoom_frame, "－", lambda: self._zoom(0.8)).pack(side="right")
        self.zoom_lbl = tk.Label(zoom_frame, text="100%", bg=PANEL, fg=TEXT, font=FONT, width=8)
        self.zoom_lbl.pack(side="right", padx=6)
        self._btn(zoom_frame, "＋", lambda: self._zoom(1.25)).pack(side="right")

        search_frame = tk.Frame(side, bg=PANEL)
        search_frame.pack(fill="x", padx=18, pady=(0, 6))
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=FONT,
                                     bg=PANEL2, fg=TEXT, insertbackground=TEXT, relief="flat",
                                     highlightthickness=1, highlightbackground=BORDER)
        self.search_entry.pack(fill="x", side="left", expand=True, ipady=3)
        self.search_entry.bind("<KeyRelease>", lambda e: self._refresh_list())
        self.search_var.trace_add("write", lambda *_: self._refresh_list())

        filt = tk.Frame(side, bg=PANEL)
        filt.pack(fill="x", padx=18, pady=(0, 8))
        tk.Checkbutton(filt, text="Solo pendientes", variable=self.filter_done_only, bg=PANEL,
                       fg=MUTED, selectcolor=PANEL2, activebackground=PANEL, activeforeground=TEXT,
                       font=FONT_SB, bd=0, command=self._refresh_list,
                       highlightthickness=0).pack(side="left")
        self.count_lbl = tk.Label(filt, text="", bg=PANEL, fg=ACCENT, font=FONT_SB)
        self.count_lbl.pack(side="right")

        list_wrap = tk.Frame(side, bg=PANEL)
        list_wrap.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        sb = tk.Scrollbar(list_wrap, bg=PANEL, troughcolor=PANEL, bd=0,
                          highlightthickness=0)
        sb.pack(side="right", fill="y")
        self.plist = tk.Listbox(list_wrap, bg=PANEL, fg=TEXT, selectbackground=ACCENT,
                                selectforeground="#0d0d14", font=FONT_SB, bd=0, highlightthickness=0,
                                activestyle="none", yscrollcommand=sb.set)
        self.plist.pack(side="left", fill="both", expand=True)
        sb.config(command=self.plist.yview, bg=PANEL)
        self.plist.bind("<<ListboxSelect>>", self._on_list_select)
        self.plist.bind("<Double-Button-1>", self._jump_to_product_page)

        tip = tk.Label(side, text="Selecciona un producto de la lista y luego\narrastra sobre la imagen para recortar.\nDoble-clic salta a la página del producto.",
                       bg=PANEL, fg=MUTED, font=FONT_SB, justify="left")
        tip.pack(fill="x", padx=18, pady=(0, 16))

        self.preview_thumb = tk.Label(side, bg=PANEL, bd=0)
        self.preview_thumb.pack(fill="x", padx=18, pady=(0, 18))

    def _build_canvas_area(self, parent):
        wrap = tk.Frame(parent, bg="#0d0d14")
        wrap.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(wrap, bg="#0d0d14", bd=0, highlightthickness=0, cursor="cross")
        self.canvas.pack(side="left", fill="both", expand=True)

        xsb = tk.Scrollbar(wrap, orient="horizontal", bg=PANEL, troughcolor=PANEL, bd=0,
                           highlightthickness=0)
        ysb = tk.Scrollbar(wrap, orient="vertical", bg=PANEL, troughcolor=PANEL, bd=0,
                           highlightthickness=0)
        ysb.pack(side="right", fill="y")
        xsb.pack(side="bottom", fill="x")
        self.canvas.config(xscrollcommand=xsb.set, yscrollcommand=ysb.set)
        xsb.config(command=self.canvas.xview, bg=PANEL)
        ysb.config(command=self.canvas.yview, bg=PANEL)

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Shift-MouseWheel>", self._on_wheel_h)
        self.canvas.bind("<Configure>", lambda e: self._update_scroll())

    def _build_statusbar(self, parent):
        bar = tk.Frame(parent, bg=PANEL2, height=26, bd=0)
        bar.pack(side="bottom", fill="x")
        self.status_lbl = tk.Label(bar, text="", bg=PANEL2, fg=MUTED, font=FONT_SB, anchor="w")
        self.status_lbl.pack(side="left", padx=12, pady=3)
        self.sel_lbl = tk.Label(bar, text="", bg=PANEL2, fg=ACCENT, font=FONT_SB)
        self.sel_lbl.pack(side="right", padx=12, pady=3)

    def _focus_canvas(self):
        self.canvas.focus_set()

    def _scan_saved(self):
        self.saved_ids = set()
        if os.path.isdir(OUTPUT_FOLDER):
            for f in os.listdir(OUTPUT_FOLDER):
                m = re.match(r"(\d{5})\.png$", f)
                if m:
                    self.saved_ids.add(m.group(1))

    def _refresh_list(self):
        self.plist.delete(0, "end")
        q = self.search_var.get().strip().lower()
        pending = 0
        for cid in sorted(self.products):
            name = self.products[cid]
            done = cid in self.saved_ids
            if done and self.filter_done_only.get():
                continue
            label = f"{'✓' if done else '•'} {cid}  {name}"
            if q:
                if q not in cid.lower() and q not in name.lower():
                    continue
            self.plist.insert("end", label)
            if done:
                self.plist.itemconfig("end", {"foreground": MUTED, "selectforeground": MUTED})
            if not done:
                pending += 1
        done = len(self.saved_ids)
        total = len(self.products)
        self.count_lbl.config(text=f"{done}/{total} · {pending} pend.")

    def _on_list_select(self, _=None):
        sel = self.plist.curselection()
        if not sel:
            return
        text = self.plist.get(sel[0])
        m = re.match(r"[✓•]\s+(\d{5})", text)
        if m:
            self.pending_id = m.group(1)
            name = self.products.get(self.pending_id, "")
            self.sel_lbl.config(text=f"Recortar: {self.pending_id} — {name}")
            self.canvas.focus_set()

    def _jump_to_product_page(self, _=None):
        sel = self.plist.curselection()
        if not sel:
            return
        text = self.plist.get(sel[0])
        m = re.match(r"[✓•]\s+(\d{5})", text)
        if not m:
            return
        cid = m.group(1)
        pg = self.page_map.get(cid)
        if not pg:
            self._set_status(f"No se sabe la página de {cid}")
            return
        idx = pg - 1
        if 0 <= idx < len(self.images):
            self.goto_page(idx)

    def _set_status(self, text):
        self.status_lbl.config(text=text)

    def load_image(self):
        path = os.path.join(INPUT_FOLDER, self.images[self.current_idx])
        try:
            self.orig = Image.open(path).convert("RGB")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir {path}\n{e}")
            return
        self.img_w, self.img_h = self.orig.size
        self._fit_zoom()
        self._render()
        n = self.current_idx + 1
        total = len(self.images)
        self.page_lbl.config(text=f" {n} / {total} ")
        self._set_status(f"Página {n} de {total} · {self.images[self.current_idx]}  ·  arrastra para recortar")

    def _fit_zoom(self):
        self.canvas.update_idletasks()
        cw = max(self.canvas.winfo_width(), 100)
        ch = max(self.canvas.winfo_height(), 100)
        zw = cw / self.img_w
        zh = ch / self.img_h
        z = min(zw, zh)
        self.zoom = max(0.05, min(z, 1.0))

    def _render(self):
        if self.orig is None:
            return
        dw = max(1, int(self.img_w * self.zoom))
        dh = max(1, int(self.img_h * self.zoom))
        disp = self.orig.resize((dw, dh), Image.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(disp)
        self.canvas.delete("all")
        self.canvas.config(scrollregion=(0, 0, dw, dh))
        self.img_item = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        self.zoom_lbl.config(text=f"{int(self.zoom * 100)}%")
        self._cancel_sel()

    def goto_page(self, idx):
        if not (0 <= idx < len(self.images)):
            return
        self.current_idx = idx
        self.load_image()

    def _goto_entry(self, _=None):
        try:
            n = int(self.goto_entry.get())
        except ValueError:
            self._set_status("Número de página inválido")
            return
        self.goto_page(n - 1)
        self.goto_entry.delete(0, "end")

    def _zoom(self, factor):
        self.zoom = max(0.05, min(self.zoom * factor, 8.0))
        self._render()

    def _on_wheel(self, e):
        if e.state & 0x4:
            self._on_wheel_h(e)
            return
        if e.delta > 0:
            self.zoom = min(self.zoom * 1.1, 8.0)
        else:
            self.zoom = max(self.zoom / 1.1, 0.05)
        self._zoom_at(e.x, e.y)

    def _on_wheel_h(self, e):
        self.canvas.xview_scroll(int(-e.delta / 120), "units")

    def _zoom_at(self, cx, cy):
        img_x = self.canvas.canvasx(cx) / self.zoom
        img_y = self.canvas.canvasy(cy) / self.zoom
        self._render()
        target_x = img_x * self.zoom
        target_y = img_y * self.zoom
        dw = self.img_w * self.zoom
        dh = self.img_h * self.zoom
        frac_x = max(0, min(1, (target_x - cx) / dw)) if dw else 0
        frac_y = max(0, min(1, (target_y - cy) / dh)) if dh else 0
        self.canvas.xview_moveto(frac_x)
        self.canvas.yview_moveto(frac_y)

    def _update_scroll(self):
        if self.orig is not None:
            dw = int(self.img_w * self.zoom)
            dh = int(self.img_h * self.zoom)
            self.canvas.config(scrollregion=(0, 0, dw, dh))

    def _on_press(self, e):
        self.start_cx = self.canvas.canvasx(e.x)
        self.start_cy = self.canvas.canvasy(e.y)
        self.cur_cx = self.start_cx
        self.cur_cy = self.start_cy
        self._draw_rect()

    def _on_drag(self, e):
        self.cur_cx = self.canvas.canvasx(e.x)
        self.cur_cy = self.canvas.canvasy(e.y)
        self._draw_rect()

    def _draw_rect(self):
        x0, y0 = self.start_cx, self.start_cy
        x1, y1 = self.cur_cx, self.cur_cy
        if self.rect_item is None:
            self.rect_item = self.canvas.create_rectangle(x0, y0, x1, y1, outline=ACCENT,
                                                          width=2, dash=(6, 4))
            self.dim_bg_item = self.canvas.create_rectangle(x0, y0, x0 + 130, y0 + 22,
                                                            fill="#0d0d14", outline=ACCENT)
            self.dim_item = self.canvas.create_text(x0 + 6, y0 + 11, anchor="w", fill=TEXT,
                                                    font=FONT_SB, text="")
        else:
            self.canvas.coords(self.rect_item, x0, y0, x1, y1)
        w = abs(x1 - x0)
        h = abs(y1 - y0)
        ix = int(w / self.zoom)
        iy = int(h / self.zoom)
        top = min(y0, y1)
        left = min(x0, x1)
        self.canvas.coords(self.dim_bg_item, left, top, left + 140, top + 22)
        self.canvas.coords(self.dim_item, left + 6, top + 11)
        self.canvas.itemconfig(self.dim_item, text=f"{ix} x {iy} px")
        self.canvas.tag_raise(self.rect_item)
        self.canvas.tag_raise(self.dim_bg_item)
        self.canvas.tag_raise(self.dim_item)

    def _cancel_sel(self, _=None):
        self.start_cx = self.start_cy = None
        self.cur_cx = self.cur_cy = None
        if self.rect_item is not None:
            self.canvas.delete(self.rect_item)
            self.canvas.delete(self.dim_item)
            self.canvas.delete(self.dim_bg_item)
            self.rect_item = self.dim_item = self.dim_bg_item = None

    def _on_release(self, e):
        if self.start_cx is None:
            return
        x0 = min(self.start_cx, self.cur_cx) / self.zoom
        y0 = min(self.start_cy, self.cur_cy) / self.zoom
        x1 = max(self.start_cx, self.cur_cx) / self.zoom
        y1 = max(self.start_cy, self.cur_cy) / self.zoom
        ix0 = max(0, int(x0))
        iy0 = max(0, int(y0))
        ix1 = min(self.img_w, int(x1))
        iy1 = min(self.img_h, int(y1))
        self._cancel_sel()
        if ix1 - ix0 < 20 or iy1 - iy0 < 20:
            self._set_status("Recorte demasiado pequeño — ignorado")
            return
        crop = self.orig.crop((ix0, iy0, ix1, iy1))
        dlg = CropDialog(self.root, crop, self)
        self.root.wait_window(dlg)
        if dlg.result:
            cid = dlg.result
            self.saved_ids.add(cid)
            self._refresh_list()
            self._set_status(f"Guardado: {cid}.png  ({self.products.get(cid, '—')})")
            self._show_thumb(cid)
            self.pending_id = None
            self.sel_lbl.config(text="")
            self._advance_pending()

    def _show_thumb(self, cid):
        path = os.path.join(OUTPUT_FOLDER, f"{cid}.png")
        try:
            im = Image.open(path)
            im.thumbnail((294, 200))
            self._thumb = ImageTk.PhotoImage(im)
            self.preview_thumb.config(image=self._thumb, text="")
        except Exception:
            pass

    def _advance_pending(self):
        if self.filter_done_only.get():
            self._refresh_list()
        items = self.plist.get(0, "end")
        if items:
            self.plist.selection_clear(0, "end")
            self.plist.selection_set(0)
            self.plist.see(0)
            self._on_list_select()


def main():
    root = tk.Tk()
    root.title("Extractor de Fotos — Catálogo Betterware")
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    ExtractorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
