import fitz
import re
import os
from PIL import Image
import io

PDF_PATH = "catalogo.pdf"
OUTPUT_DIR = "fotos_catalogo"
SQL_PATH = "productos.sql"
SCALE = 3.0
MARGIN = 15

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Cargar IDs del SQL
sql_ids = set()
sql_names = {}
for l in open(SQL_PATH, encoding="utf-8"):
    m = re.search(r"\('(\d{5})',\s*'([^']*)'", l)
    if m:
        sql_ids.add(m.group(1))
        sql_names[m.group(1)] = m.group(2)

# IDs faltantes
existing = set()
for f in os.listdir(OUTPUT_DIR):
    m = re.match(r"(\d{5})\.png$", f)
    if m:
        existing.add(m.group(1))
missing = sql_ids - existing
print(f"Faltan: {len(missing)} productos")

doc = fitz.open(PDF_PATH)
saved = {}
skipped = []

for pidx in range(len(doc)):
    page = doc[pidx]
    page_num = pidx + 1

    # Buscar codigos de 5 digitos en el texto
    blocks = page.get_text("dict")["blocks"]
    code_positions = []  # (code, x0, y0, x1, y1)
    for b in blocks:
        if "lines" not in b:
            continue
        for l in b["lines"]:
            for s in l["spans"]:
                t = s["text"]
                m = re.search(r"(?<!\d)(\d{5})(?!\d)", t)
                if m:
                    code = m.group(1)
                    if code in missing:
                        bbox = s["bbox"]
                        code_positions.append((code, bbox[0], bbox[1], bbox[2], bbox[3]))

    if not code_positions:
        continue

    # Renderizar pagina a alta resolucion
    matrix = fitz.Matrix(SCALE, SCALE)
    pix = page.get_pixmap(matrix=matrix)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    pw, ph = img.size
    page_rect = page.rect

    # Funcion para convertir coords PDF -> coords imagen
    def to_img(x, y):
        return x * SCALE, y * SCALE

    # Para cada codigo, calcular limites del recorte
    all_codes_on_page = []
    for b in blocks:
        if "lines" not in b:
            continue
        for l in b["lines"]:
            for s in l["spans"]:
                m = re.search(r"(?<!\d)(\d{5})(?!\d)", s["text"])
                if m:
                    bbox = s["bbox"]
                    cx = (bbox[0] + bbox[2]) / 2
                    cy = (bbox[1] + bbox[3]) / 2
                    all_codes_on_page.append((m.group(1), bbox[0], bbox[1], bbox[2], bbox[3], cx, cy))

    for code, cx0, cy0, cx1, cy1 in code_positions:
        ccx = (cx0 + cx1) / 2
        ccy = (cy0 + cy1) / 2

        # Limites basados en codigos vecinos
        # Vertical: de este codigo al siguiente abajo en la misma columna
        y_bottom = page_rect.height
        codes_below = [(c, x0, y0, x1, y1, ccx2, ccy2)
                       for c, x0, y0, x1, y1, ccx2, ccy2 in all_codes_on_page
                       if ccy2 > ccy + 20 and abs(ccx2 - ccx) < 280]
        if codes_below:
            y_bottom = min(c[6] for c in codes_below)

        # Horizontal: midpoint al codigo mas cercano a la izquierda/derecha en misma fila
        x_left = 0
        x_right = page_rect.width
        codes_right = [(c, x0, y0, x1, y1, ccx2, ccy2)
                       for c, x0, y0, x1, y1, ccx2, ccy2 in all_codes_on_page
                       if ccx2 > ccx + 50 and abs(ccy2 - ccy) < 300]
        if codes_right:
            nearest_right = min(codes_right, key=lambda c: c[5])
            x_right = (ccx + nearest_right[5]) / 2

        codes_left = [(c, x0, y0, x1, y1, ccx2, ccy2)
                      for c, x0, y0, x1, y1, ccx2, ccy2 in all_codes_on_page
                      if ccx2 < ccx - 50 and abs(ccy2 - ccy) < 300]
        if codes_left:
            nearest_left = max(codes_left, key=lambda c: c[5])
            x_left = (ccx + nearest_left[5]) / 2

        # Recorte: desde un poco arriba del codigo hasta y_bottom
        crop_x0 = max(0, x_left - MARGIN)
        crop_y0 = max(0, cy0 - 30)
        crop_x1 = min(page_rect.width, x_right + MARGIN)
        crop_y1 = min(page_rect.height, y_bottom + MARGIN)

        # Convertir a coords de imagen
        ix0, iy0 = to_img(crop_x0, crop_y0)
        ix1, iy1 = to_img(crop_x1, crop_y1)
        ix0, iy0, ix1, iy1 = int(ix0), int(iy0), int(ix1), int(iy1)

        if ix1 - ix0 < 50 or iy1 - iy0 < 50:
            continue

        crop = img.crop((ix0, iy0, ix1, iy1))
        out_path = os.path.join(OUTPUT_DIR, f"{code}.png")
        crop.save(out_path)
        saved[code] = page_num
        print(f"  + {code} pag {page_num} ({crop.size[0]}x{crop.size[1]})")

doc.close()

# Reportar
not_in_pdf = missing - set(saved.keys())
print(f"\nGuardados: {len(saved)}")
print(f"No encontrados en PDF: {len(not_in_pdf)}")
for c in sorted(not_in_pdf):
    print(f"  {c} {sql_names.get(c, '?')}")
