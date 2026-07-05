import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FOLDER = os.path.join(BASE_DIR, "paginas_catalogo")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "fotos_catalogo")
SQL_PATH = os.path.join(BASE_DIR, "productos.sql")
MAPPING_PATH = os.path.join(BASE_DIR, "mapeo_final.json")
RECORDS_PATH = os.path.join(BASE_DIR, "flipbook_bboxes.json")

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


from subir_paginas import (
    load_dotenv_if_present,
    subir_fotos_recortes,
    subir_hotspots,
    subir_todas_las_paginas,
)

DETECTADOS_PATH = os.path.join(BASE_DIR, "productos_detectados.json")


def load_products():
    """Lista de productos del catálogo vigente.

    Fuente preferida: productos_detectados.json (generado desde el PDF con
    leer_catalogo_pdf.py o el botón "Leer catálogo PDF"). Si no existe, se
    usa el productos.sql heredado."""
    if os.path.exists(DETECTADOS_PATH):
        try:
            with open(DETECTADOS_PATH, encoding="utf-8") as f:
                data = json.load(f)
            return {
                cid: {"nombre": d["nombre"], "precio": d["precio"], "pagina": d.get("pagina")}
                for cid, d in data.items()
            }
        except Exception:
            pass

    products = {}
    if os.path.exists(SQL_PATH):
        with open(SQL_PATH, encoding="utf-8") as f:
            for line in f:
                m = re.search(r"\('(\d{5})',\s*'([^']*)',\s*([\d.]+)\)", line)
                if m:
                    products[m.group(1)] = {"nombre": m.group(2), "precio": float(m.group(3))}
    return products


def load_page_map(products=None):
    page_map = {}
    # Páginas detectadas directamente del PDF (la fuente más confiable)
    if products:
        for cid, d in products.items():
            if d.get("pagina"):
                page_map[cid] = d["pagina"]
    if page_map:
        return page_map
    # Fallback heredado: mapeo_final.json
    if os.path.exists(MAPPING_PATH):
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


def load_records():
    if os.path.exists(RECORDS_PATH):
        try:
            with open(RECORDS_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_records(records):
    with open(RECORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2, sort_keys=True)


def natural_sort_key(name):
    nums = re.findall(r"\d+", name)
    return int(nums[0]) if nums else 0


class CropDialog(tk.Toplevel):
    def __init__(self, master, crop_img, app, pagina, bbox_px):
        super().__init__(master)
        self.app = app
        self.crop_img = crop_img
        self.pagina = pagina
        self.bbox_px = bbox_px  # (ix0, iy0, ix1, iy1) en pixeles de la imagen original
        self.result = None
        self.configure(bg=PANEL)
        self.title("Guardar producto")
        self.transient(master)
        self.grab_set()

        w, h = crop_img.size
        self.resizable(False, False)

        title = tk.Label(self, text="Confirma el producto", bg=PANEL, fg=TEXT, font=FONT_H)
        title.grid(row=0, column=0, columnspan=2, padx=20, pady=(16, 4), sticky="w")

        dim_lbl = tk.Label(self, text=f"Selección: {w} x {h} px · página {pagina}", bg=PANEL, fg=MUTED, font=FONT_SB)
        dim_lbl.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 8), sticky="w")

        prev_w = 300
        prev_h = int(h * prev_w / w) if w else 100
        prev_h = min(prev_h, 380)
        preview = crop_img.copy()
        preview.thumbnail((prev_w, prev_h))
        self.tk_prev = ImageTk.PhotoImage(preview)
        prev = tk.Label(self, image=self.tk_prev, bg="#0d0d14", bd=0, highlightthickness=1,
                        highlightbackground=BORDER)
        prev.grid(row=2, column=0, rowspan=7, padx=(20, 12), pady=4, sticky="n")

        form = tk.Frame(self, bg=PANEL)
        form.grid(row=2, column=1, padx=(0, 20), pady=4, sticky="n")

        def _field(label_text):
            tk.Label(form, text=label_text, bg=PANEL, fg=MUTED, font=FONT_SB).pack(anchor="w")
            var = tk.StringVar()
            entry = tk.Entry(form, textvariable=var, font=FONT_MONO, width=26,
                             bg=PANEL2, fg=TEXT, insertbackground=TEXT, relief="flat",
                             highlightthickness=1, highlightbackground=ACCENT, highlightcolor=ACCENT)
            entry.pack(fill="x", pady=(2, 8))
            return var, entry

        self.id_var, id_entry = _field("Código del producto")
        self.id_var.set(app.pending_id or "")
        id_entry.focus_set()
        id_entry.icursor("end")

        self.name_status = tk.StringVar()
        self.name_status_lbl = tk.Label(form, textvariable=self.name_status, bg=PANEL, fg=SUCCESS,
                                        font=FONT_SB, wraplength=230, justify="left")
        self.name_status_lbl.pack(anchor="w", pady=(0, 8))

        self.nombre_var, _ = _field("Nombre")
        self.precio_var, _ = _field("Precio regular")
        self.precio_oferta_var, _ = _field("Precio oferta (opcional)")
        self.categoria_var, _ = _field("Categoría (opcional)")

        btns = tk.Frame(self, bg=PANEL)
        btns.grid(row=9, column=0, columnspan=2, padx=20, pady=(8, 16), sticky="ew")
        save_btn = tk.Button(btns, text="Guardar", command=self._save, bg=ACCENT, fg="#0d0d14",
                             font=FONT_H, relief="flat", activebackground=ACCENT2, cursor="hand2",
                             width=12, bd=0)
        save_btn.pack(side="left", padx=(0, 8))
        tk.Button(btns, text="Cancelar", command=self.destroy, bg=PANEL2, fg=TEXT, font=FONT,
                  relief="flat", activebackground=PANEL, cursor="hand2", width=10, bd=0,
                  highlightthickness=1, highlightbackground=BORDER).pack(side="left")
        self.save_btn = save_btn

        self.id_var.trace_add("write", self._on_id_change)
        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self.destroy())
        self._on_id_change()

    def _on_id_change(self, *_):
        cid = self.id_var.get().strip()
        existing_record = self.app.records.get(cid)
        base_product = self.app.products.get(cid)

        if existing_record:
            self.name_status.set("✓  " + existing_record.get("nombre", "") + "  (ya tiene datos, se sobrescriben)")
            self.name_status_lbl.config(fg=SUCCESS)
            precio_reg = existing_record.get("precio_regular", existing_record.get("precio"))
            if not self.nombre_var.get():
                self.nombre_var.set(existing_record.get("nombre", ""))
            if not self.precio_var.get() and precio_reg is not None:
                self.precio_var.set(str(precio_reg))
            if not self.precio_oferta_var.get() and existing_record.get("precio_oferta") is not None:
                self.precio_oferta_var.set(str(existing_record.get("precio_oferta")))
            if not self.categoria_var.get():
                self.categoria_var.set(existing_record.get("categoria") or "")
        elif base_product:
            self.name_status.set("✓  " + base_product["nombre"])
            self.name_status_lbl.config(fg=SUCCESS)
            if not self.nombre_var.get():
                self.nombre_var.set(base_product["nombre"])
            if not self.precio_var.get():
                self.precio_var.set(str(base_product["precio"]))
        elif cid:
            self.name_status.set("⚠  Código nuevo, no está en productos.sql")
            self.name_status_lbl.config(fg=DANGER)
        else:
            self.name_status.set("")

        self.save_btn.config(state="normal" if cid else "disabled")

    def _save(self):
        cid = self.id_var.get().strip()
        nombre = self.nombre_var.get().strip()
        precio_txt = self.precio_var.get().strip()
        precio_oferta_txt = self.precio_oferta_var.get().strip()
        categoria = self.categoria_var.get().strip()

        if not cid:
            return
        if not nombre:
            messagebox.showerror("Falta el nombre", "Escribe el nombre del producto.", parent=self)
            return
        try:
            precio_regular = float(precio_txt)
        except ValueError:
            messagebox.showerror("Precio inválido", "El precio regular debe ser un número, ej. 199.90", parent=self)
            return
        if precio_oferta_txt:
            try:
                precio_oferta = float(precio_oferta_txt)
            except ValueError:
                messagebox.showerror("Precio inválido", "El precio de oferta debe ser un número, ej. 149.90", parent=self)
                return
        else:
            precio_oferta = precio_regular

        ix0, iy0, ix1, iy1 = self.bbox_px
        img_w, img_h = self.app.img_w, self.app.img_h
        bbox_norm = {
            "x0": round(ix0 / img_w, 5),
            "y0": round(iy0 / img_h, 5),
            "x1": round(ix1 / img_w, 5),
            "y1": round(iy1 / img_h, 5),
        }

        # Recorte local como miniatura de referencia para la propia herramienta
        # (no se sube a Supabase; el flipbook usa la página completa).
        out = os.path.join(OUTPUT_FOLDER, f"{cid}.png")
        try:
            self.crop_img.save(out)
        except Exception:
            pass

        self.app.records[cid] = {
            "nombre": nombre,
            "categoria": categoria or None,
            "precio_regular": precio_regular,
            "precio_oferta": precio_oferta,
            "pagina": self.pagina,
            "bbox_norm": bbox_norm,
        }
        save_records(self.app.records)

        self.result = cid
        self.destroy()


class ExtractorApp:
    def __init__(self, root):
        self.root = root
        self.products = load_products()
        self.page_map = load_page_map(self.products)
        self.records = load_records()
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
        self.filter_done_only = tk.BooleanVar(value=False)
        self.search_var = tk.StringVar()

        self._build_ui()
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
        tk.Label(header, text="Marca productos del catálogo", bg=PANEL, fg=MUTED, font=FONT_SB).pack(anchor="w")

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

        tip = tk.Label(side, text="Selecciona un producto de la lista y luego\narrastra sobre la imagen para marcarlo.\nDoble-clic salta a la página del producto.",
                       bg=PANEL, fg=MUTED, font=FONT_SB, justify="left")
        tip.pack(fill="x", padx=18, pady=(0, 12))

        self.preview_thumb = tk.Label(side, bg=PANEL, bd=0)
        self.preview_thumb.pack(fill="x", padx=18, pady=(0, 12))

        upload_frame = tk.Frame(side, bg=PANEL)
        upload_frame.pack(fill="x", padx=18, pady=(0, 18))
        self._btn(upload_frame, "Leer catálogo PDF", self._leer_catalogo_pdf).pack(fill="x", pady=(0, 6))
        self._btn(upload_frame, "Subir a Supabase", self._upload_to_supabase, primary=True).pack(fill="x", pady=(0, 6))
        self._btn(upload_frame, "Subir páginas", self._upload_paginas).pack(fill="x")

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

    def _refresh_list(self):
        self.plist.delete(0, "end")
        q = self.search_var.get().strip().lower()
        pending = 0
        for cid in sorted(self.products):
            name = self.products[cid]["nombre"]
            done = cid in self.records
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
        done = sum(1 for cid in self.products if cid in self.records)
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
            name = self.products.get(self.pending_id, {}).get("nombre", "")
            self.sel_lbl.config(text=f"Marcar: {self.pending_id} — {name}")
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
        pg = self.records.get(cid, {}).get("pagina") or self.page_map.get(cid)
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
        self._set_status(f"Página {n} de {total} · {self.images[self.current_idx]}  ·  arrastra para marcar un producto")

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
            self._set_status("Selección demasiado pequeña — ignorada")
            return
        crop = self.orig.crop((ix0, iy0, ix1, iy1))
        pagina = self.current_idx + 1
        dlg = CropDialog(self.root, crop, self, pagina, (ix0, iy0, ix1, iy1))
        self.root.wait_window(dlg)
        if dlg.result:
            cid = dlg.result
            self._refresh_list()
            self._set_status(f"Guardado: {cid}  ({self.records[cid]['nombre']})  · página {pagina}")
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

    # ------------------------------------------------------------------
    # Lectura del catálogo PDF y subida a Supabase
    # ------------------------------------------------------------------

    def _leer_catalogo_pdf(self):
        pdf_path = os.path.join(BASE_DIR, "catalogo.pdf")
        if not os.path.exists(pdf_path):
            messagebox.showerror(
                "No hay PDF",
                "No se encontró catalogo.pdf en esta carpeta.\n"
                "Guarda el catálogo del mes como catalogo.pdf y vuelve a intentar.",
            )
            return
        if not messagebox.askyesno(
            "Leer catálogo PDF",
            "Se va a leer catalogo.pdf para llenar la lista de productos\n"
            "(códigos, nombres, precios y páginas). ¿Continuar?",
        ):
            return
        try:
            from leer_catalogo_pdf import extraer_productos
            detectados = extraer_productos(pdf_path)
        except Exception as e:
            messagebox.showerror("Error al leer el PDF", str(e))
            return
        if not detectados:
            messagebox.showwarning("Sin resultados", "No se detectó ningún producto en el PDF.")
            return

        with open(DETECTADOS_PATH, "w", encoding="utf-8") as f:
            json.dump(detectados, f, ensure_ascii=False, indent=2, sort_keys=True)

        self.products = load_products()
        self.page_map = load_page_map(self.products)
        self._refresh_list()
        paginas = sorted({d["pagina"] for d in detectados.values()})
        messagebox.showinfo(
            "Catálogo leído",
            f"Se detectaron {len(detectados)} productos en {len(paginas)} páginas.\n\n"
            "La lista de la derecha ya está actualizada. Revisa nombre y precio\n"
            "al marcar cada producto: la detección no es perfecta al 100%.",
        )

    # ------------------------------------------------------------------
    # Subida a Supabase (productos + páginas)
    # ------------------------------------------------------------------

    def _check_credentials(self):
        load_dotenv_if_present()
        supabase_url = os.environ.get("SUPABASE_URL", "")
        service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not supabase_url or not service_key:
            messagebox.showerror(
                "Falta configuración",
                "Define SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY en un archivo .env "
                "junto a este script (o en la carpeta betterorden/).\n\n"
                "La service_role key está en el panel de Supabase:\n"
                "Project Settings → API keys → service_role.",
            )
            return None, None
        return supabase_url, service_key

    def _upload_to_supabase(self):
        supabase_url, service_key = self._check_credentials()
        if not supabase_url:
            return

        if not self.records:
            messagebox.showinfo("Nada que subir", "Todavía no marcaste ningún producto.")
            return

        rows = []
        for cid, rec in self.records.items():
            precio_regular = rec.get("precio_regular", rec.get("precio"))
            rows.append({
                "codigo": cid,
                "nombre": rec["nombre"],
                "categoria": rec.get("categoria"),
                "precio_regular": precio_regular,
                "precio_oferta": rec.get("precio_oferta", precio_regular),
            })

        if not messagebox.askyesno(
            "Confirmar subida",
            f"Se van a subir/actualizar {len(rows)} productos en Supabase "
            "(nombre, precios y su foto recortada). ¿Continuar?",
        ):
            return

        try:
            body = json.dumps(rows).encode("utf-8")
            url = f"{supabase_url}/rest/v1/productos?on_conflict=codigo"
            req = urllib.request.Request(url, data=body, method="POST")
            req.add_header("apikey", service_key)
            req.add_header("Authorization", f"Bearer {service_key}")
            req.add_header("Content-Type", "application/json")
            req.add_header("Prefer", "resolution=merge-duplicates,return=minimal")
            with urllib.request.urlopen(req, timeout=60) as resp:
                ok = resp.status in (200, 201, 204)
        except urllib.error.HTTPError as e:
            messagebox.showerror("Error al subir", f"[{e.code}] {e.read().decode()[:400]}")
            return
        except Exception as e:
            messagebox.showerror("Error al subir", str(e))
            return

        if not ok:
            messagebox.showerror("Error", "Supabase no confirmó la subida de productos.")
            return

        self._write_backup_sql(rows)
        subir_hotspots(supabase_url, service_key)  # posiciones (por si se usa el flipbook a futuro)

        # Fotos de tarjeta: los recortes marcados se suben en segundo plano.
        codigos = list(self.records.keys())
        self._set_status(f"{len(rows)} productos actualizados. Subiendo fotos...")

        def progress(i, total, name):
            self.root.after(0, lambda: self._set_status(f"Subiendo fotos [{i}/{total}] {name}"))

        def worker():
            fotos_ok, fotos_fail = subir_fotos_recortes(codigos, progress_cb=progress)
            self.root.after(0, lambda: self._on_upload_fotos_done(len(rows), fotos_ok, fotos_fail))

        threading.Thread(target=worker, daemon=True).start()

    def _on_upload_fotos_done(self, n_productos, fotos_ok, fotos_fail):
        self._set_status(f"Productos: {n_productos} · fotos subidas: {fotos_ok} · fallidas: {fotos_fail}")
        if fotos_fail:
            messagebox.showwarning(
                "Terminado con detalles",
                f"{n_productos} productos actualizados.\nFotos subidas: {fotos_ok}\n"
                f"Fotos con problema: {fotos_fail} (revisa la consola).",
            )
        else:
            messagebox.showinfo(
                "Listo",
                f"{n_productos} productos actualizados y {fotos_ok} fotos subidas.\n"
                "Ya están visibles en la tienda.",
            )

    def _write_backup_sql(self, rows):
        path = os.path.join(BASE_DIR, f"productos_sync_{time.strftime('%Y%m%d_%H%M%S')}.sql")
        lines = ["-- Respaldo generado por extractor_asistido.py (subida automática a Supabase).",
                 "INSERT INTO productos (codigo, nombre, categoria, precio_regular, precio_oferta) VALUES"]
        values = []
        for r in rows:
            categoria_sql = "NULL" if not r["categoria"] else "'" + r["categoria"].replace("'", "''") + "'"
            nombre_sql = r["nombre"].replace("'", "''")
            values.append(
                f"('{r['codigo']}', '{nombre_sql}', {categoria_sql}, {r['precio_regular']}, {r['precio_oferta']})"
            )
        lines.append(",\n".join(values) + "\nON CONFLICT (codigo) DO UPDATE SET\n"
                      "  nombre = EXCLUDED.nombre,\n  categoria = EXCLUDED.categoria,\n"
                      "  precio_regular = EXCLUDED.precio_regular,\n  precio_oferta = EXCLUDED.precio_oferta;")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _upload_paginas(self):
        supabase_url, _service_key = self._check_credentials()
        if not supabase_url:
            return
        if not messagebox.askyesno("Subir páginas", f"Se van a subir {len(self.images)} páginas del catálogo a Supabase. Puede tardar varios minutos. ¿Continuar?"):
            return

        self._set_status("Subiendo páginas a Supabase...")

        def progress(i, total, name):
            self.root.after(0, lambda: self._set_status(f"Subiendo páginas [{i}/{total}] {name}"))

        def worker():
            ok, fail = subir_todas_las_paginas(progress_cb=progress)
            self.root.after(0, lambda: self._on_upload_paginas_done(ok, fail))

        threading.Thread(target=worker, daemon=True).start()

    def _on_upload_paginas_done(self, ok, fail):
        self._set_status(f"Páginas subidas: {ok} · fallidas: {fail}")
        if fail:
            messagebox.showwarning("Terminado con errores", f"Subidas: {ok}\nFallidas: {fail}\nRevisa la consola para más detalle.")
        else:
            messagebox.showinfo("Listo", f"{ok} páginas subidas a Supabase.")


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
