import os
import re
import gc
import json
import easyocr
import numpy as np
from PIL import Image

SQL_PATH = "productos.sql"
PAGES_DIR = "paginaspng"
OUTPUT_DIR = "productos_recortados"
MAPPING_FILE = "mapeo_final.json"
LOG_FILE = "log_advertencias.txt"
MARGIN = 10

os.makedirs(OUTPUT_DIR, exist_ok=True)

RE_INSERT = re.compile(
    r"INSERT INTO productos.*?VALUES\s*\(\s*'(\d{5})'\s*,\s*'([^']*)'(?:'[^']*')*\s*,\s*[\d.]+\s*,\s*'[^']*'\s*\)",
    re.IGNORECASE,
)
RE_CODE = re.compile(r"^\d{5}$")


def parse_sql(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    matches = RE_INSERT.findall(content)
    master = {}
    for code, nombre in matches:
        master[code] = nombre
    return master


def get_centroid(bbox):
    pts = np.array(bbox)
    return int(np.mean(pts[:, 0])), int(np.mean(pts[:, 1]))


def compute_crop_bounds(cx, cy, all_centroids, img_w, img_h):
    x_left = 0
    x_right = img_w
    y_top = 0
    y_bottom = img_h

    for ox, oy in all_centroids:
        if ox == cx and oy == cy:
            continue
        if oy > cy - 200 and oy < cy + 200:
            if ox < cx:
                x_left = max(x_left, (ox + cx) // 2)
            elif ox > cx:
                x_right = min(x_right, (ox + cx) // 2)
        if ox > cx - 300 and ox < cx + 300:
            if oy < cy:
                y_top = max(y_top, (oy + cy) // 2)
            elif oy > cy:
                y_bottom = min(y_bottom, (oy + cy) // 2)

    x_left = min(x_left, cx - 50)
    x_right = max(x_right, cx + 50)
    y_top = min(y_top, cy - 50)
    y_bottom = max(y_bottom, cy + 50)

    x_left = max(0, x_left + MARGIN)
    y_top = max(0, y_top + MARGIN)
    x_right = min(img_w, x_right - MARGIN)
    y_bottom = min(img_h, y_bottom - MARGIN)

    if x_right <= x_left or y_bottom <= y_top:
        return None

    return (x_left, y_top, x_right, y_bottom)


print("[1/4] Parseando SQL...")
master_db = parse_sql(SQL_PATH)
valid_codes = set(master_db.keys())
print(f"      {len(valid_codes)} productos en la base de datos.")

print("[2/4] Cargando EasyOCR...")
reader = easyocr.Reader(["es"], gpu=False, verbose=False)

print("[3/4] Procesando páginas...\n")

page_files = sorted(
    [f for f in os.listdir(PAGES_DIR) if f.endswith(".png")],
    key=lambda f: int(re.search(r"\d+", f).group()),
)

seen_codes = set()
mapping = []
no_image_codes = set(valid_codes)
warnings = []
total_linked = 0
total_no_match = 0

for idx, filename in enumerate(page_files):
    page_num = int(re.search(r"\d+", filename).group())
    page_path = os.path.join(PAGES_DIR, filename)

    try:
        img = Image.open(page_path)
        img_w, img_h = img.size
        img_np = np.array(img)

        ocr_results = reader.readtext(img_np)

        page_codes = []
        for bbox, text, conf in ocr_results:
            clean = text.strip()
            if not RE_CODE.match(clean):
                continue
            if clean not in valid_codes:
                continue
            cx, cy = get_centroid(bbox)
            page_codes.append((clean, cx, cy, bbox))

        all_centroids = [(cx, cy) for _, cx, cy, _ in page_codes]

        linked = 0
        for code, cx, cy, bbox in page_codes:
            if code in seen_codes:
                continue

            crop_bounds = compute_crop_bounds(cx, cy, all_centroids, img_w, img_h)
            if crop_bounds is None:
                continue

            crop = img.crop(crop_bounds)
            out_name = f"{code}.png"
            crop.save(os.path.join(OUTPUT_DIR, out_name))

            seen_codes.add(code)
            no_image_codes.discard(code)
            linked += 1
            total_linked += 1

            mapping.append({
                "id_sql": code,
                "descripcion_sql": master_db[code],
                "pagina_origen": page_num,
                "bbox": [crop_bounds[0], crop_bounds[1], crop_bounds[2], crop_bounds[3]],
                "archivo_recortado": f"productos_recortados/{out_name}",
                "estado": "vinculado",
            })

        print(f"  Página {page_num:>3}/115 | Vinculados: {linked} | Sin coincidencia: {total_no_match}")

        del img, img_np, ocr_results
        gc.collect()

    except Exception as e:
        print(f"  Página {page_num:>3}/115 | ERROR: {e}")
        warnings.append(f"Error página {page_num}: {e}")
        gc.collect()
        continue

print("\n[4/4] Generando outputs...")

for code in no_image_codes:
    mapping.append({
        "id_sql": code,
        "descripcion_sql": master_db[code],
        "pagina_origen": None,
        "bbox": None,
        "archivo_recortado": None,
        "estado": "producto_sin_imagen",
    })
    warnings.append(f"producto_sin_imagen: {code} - {master_db[code][:50]}")

with open(MAPPING_FILE, "w", encoding="utf-8") as f:
    json.dump(mapping, f, ensure_ascii=False, indent=2)

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(warnings) + "\n")

print(f"\n{'='*50}")
print(f"RESUMEN FINAL")
print(f"{'='*50}")
print(f"  Vinculados (con imagen):     {total_linked}")
print(f"  Sin imagen (en SQL):         {len(no_image_codes)}")
print(f"  Total productos SQL:         {len(valid_codes)}")
print(f"  Imágenes guardadas en:       {OUTPUT_DIR}/")
print(f"  Mapeo JSON:                  {MAPPING_FILE}")
print(f"  Log advertencias:            {LOG_FILE}")
