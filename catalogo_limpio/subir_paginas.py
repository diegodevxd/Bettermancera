"""Sube el catálogo tipo "libro" (flipbook) a Supabase Storage.

Hace TODO lo necesario, sin pasos manuales en el panel de Supabase:
  1. Crea el bucket público `catalogo_paginas` si no existe.
  2. Redimensiona cada página de paginas_catalogo/ y la sube como .webp
     (pagina_001.webp, pagina_002.webp, ...).
  3. Sube hotspots.json con el total de páginas y la posición de cada
     producto (lo que se haya marcado con extractor_asistido.py).

Las páginas se redimensionan porque el origen son escaneos en alta resolución
(varios MB por página); en el navegador se muestran a ancho de pantalla.

Credenciales: variables de entorno SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY,
o un archivo .env junto a este script (o en la carpeta betterorden/) con
esas dos líneas (KEY=VALUE).

Uso:
  python subir_paginas.py
"""
import json
import io
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import urllib.error

from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
RECORDS_PATH = BASE_DIR / "flipbook_bboxes.json"

BUCKET = "catalogo_paginas"
PAGINAS_DIR = BASE_DIR / "paginas_catalogo"

# Tamaño objetivo del lado largo de la imagen de página. El origen puede ser
# de hasta ~3000x5300px; a este tamaño se sigue leyendo bien el detalle de
# cada producto, pesando muchísimo menos.
MAX_DIMENSION = 1400
WEBP_QUALITY = 80


def load_dotenv_if_present():
    """Busca un .env en catalogo_limpio/, usuarios/ o betterorden/ y carga
    SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY sin pisar variables ya definidas."""
    candidates = [BASE_DIR / ".env", BASE_DIR.parent / ".env", BASE_DIR.parent.parent / ".env"]
    for env_path in candidates:
        if not env_path.exists():
            continue
        with open(env_path, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                val = val.strip().strip('"').strip("'")
                # Ignora placeholders tipo TU_SERVICE_ROLE_KEY
                if val and not val.startswith("TU_"):
                    os.environ.setdefault(key.strip(), val)


def _supabase_config():
    return os.environ.get("SUPABASE_URL", "").rstrip("/"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


def _request(url, data, method, headers):
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def ensure_bucket(supabase_url, service_key):
    """Crea el bucket público si no existe. Devuelve True si está listo."""
    status, body = _request(
        f"{supabase_url}/storage/v1/bucket",
        json.dumps({"id": BUCKET, "name": BUCKET, "public": True}).encode("utf-8"),
        "POST",
        {
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            "Content-Type": "application/json",
        },
    )
    if status in (200, 201):
        print(f"Bucket '{BUCKET}' creado.")
        return True
    if "already exists" in body.lower() or status == 409:
        return True
    print(f"[ERROR al crear bucket] [{status}] {body[:200]}")
    return False


def page_number(filename: str):
    m = re.search(r"(\d+)", filename)
    return int(m.group(1)) if m else None


def resize_for_web(img: Image.Image) -> Image.Image:
    if max(img.size) <= MAX_DIMENSION:
        return img
    img = img.copy()
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
    return img


def upload_bytes(supabase_url, service_key, filename: str, data: bytes, mime: str, bucket: str = BUCKET) -> bool:
    status, body = _request(
        f"{supabase_url}/storage/v1/object/{bucket}/{filename}",
        data,
        "POST",
        {
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            "Content-Type": mime,
            "x-upsert": "true",
        },
    )
    if status in (200, 201):
        return True
    print(f"  [ERROR {status}] {filename}: {body[:150]}")
    return False


# ---------------------------------------------------------------------------
# Fotos de producto (recortes del extractor) → bucket productos_fotos
# La tienda muestra las tarjetas con estas fotos, resueltas por codigo.
# ---------------------------------------------------------------------------

FOTOS_BUCKET = "productos_fotos"
FOTOS_DIR = BASE_DIR / "fotos_catalogo"
FOTO_MAX_DIMENSION = 1000


def subir_fotos_recortes(codigos=None, progress_cb=None):
    """Sube los recortes de fotos_catalogo/ al bucket productos_fotos
    (resized, en .png y .webp). Si `codigos` se da, solo esos; si no, todos.
    Devuelve (ok, fail)."""
    load_dotenv_if_present()
    supabase_url, service_key = _supabase_config()
    if not supabase_url or not service_key:
        print("ERROR: Faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY.")
        return 0, 0

    if codigos is None:
        archivos = sorted(FOTOS_DIR.glob("*.png"))
    else:
        archivos = [FOTOS_DIR / f"{c}.png" for c in sorted(codigos)]

    total = len(archivos)
    ok = 0
    fail = 0
    for i, f in enumerate(archivos, 1):
        if progress_cb:
            progress_cb(i, total, f.name)
        if not f.exists():
            print(f"  [SIN FOTO] {f.name}")
            fail += 1
            continue
        try:
            img = Image.open(f)
            img.load()
        except Exception as e:
            print(f"  [ERROR AL ABRIR] {f.name}: {e}")
            fail += 1
            continue

        if max(img.size) > FOTO_MAX_DIMENSION:
            img = img.copy()
            img.thumbnail((FOTO_MAX_DIMENSION, FOTO_MAX_DIMENSION), Image.LANCZOS)

        rgb = img.convert("RGB")

        png_buf = io.BytesIO()
        rgb.save(png_buf, format="PNG", optimize=True)
        ok_png = upload_bytes(supabase_url, service_key, f.name, png_buf.getvalue(), "image/png", bucket=FOTOS_BUCKET)

        webp_buf = io.BytesIO()
        rgb.save(webp_buf, format="WEBP", quality=82, method=6)
        ok_webp = upload_bytes(supabase_url, service_key, f.stem + ".webp", webp_buf.getvalue(), "image/webp", bucket=FOTOS_BUCKET)

        if ok_png and ok_webp:
            ok += 1
        else:
            fail += 1

    return ok, fail


def load_records():
    if RECORDS_PATH.exists():
        try:
            with open(RECORDS_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def build_hotspots_payload(total_paginas):
    """Arma el hotspots.json que lee la página web: total de páginas y, por
    código de producto, en qué página está y su rectángulo normalizado."""
    records = load_records()
    productos = {}
    for cid, rec in records.items():
        if rec.get("pagina") and rec.get("bbox_norm"):
            productos[cid] = {"pagina": rec["pagina"], "bbox": rec["bbox_norm"]}
    return {
        "total_paginas": total_paginas,
        "actualizado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "productos": productos,
    }


def subir_hotspots(supabase_url=None, service_key=None, total_paginas=None):
    """Sube (o actualiza) hotspots.json. Devuelve True si se subió bien."""
    if supabase_url is None or service_key is None:
        load_dotenv_if_present()
        supabase_url, service_key = _supabase_config()
    if not supabase_url or not service_key:
        print("ERROR: Faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY.")
        return False
    if not ensure_bucket(supabase_url, service_key):
        return False
    if total_paginas is None:
        files = list(PAGINAS_DIR.glob("*.png")) + list(PAGINAS_DIR.glob("*.jpg"))
        total_paginas = max((page_number(f.name) or 0 for f in files), default=0)
    payload = build_hotspots_payload(total_paginas)
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    ok = upload_bytes(supabase_url, service_key, "hotspots.json", data, "application/json")
    if ok:
        print(f"hotspots.json subido: {total_paginas} páginas, {len(payload['productos'])} productos con posición.")
    return ok


def subir_todas_las_paginas(progress_cb=None):
    """Sube todas las páginas + hotspots.json. Devuelve (ok, fail).

    progress_cb, si se da, se llama como progress_cb(i, total, nombre_archivo)
    antes de subir cada página (útil para mostrar progreso en una UI)."""
    load_dotenv_if_present()
    supabase_url, service_key = _supabase_config()
    if not supabase_url or not service_key:
        print("ERROR: Faltan variables de entorno SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY.")
        return 0, 0

    if not PAGINAS_DIR.exists():
        print(f"No se encontro la carpeta: {PAGINAS_DIR}")
        return 0, 0

    if not ensure_bucket(supabase_url, service_key):
        return 0, 0

    files = [f for f in PAGINAS_DIR.iterdir() if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg")]
    files = sorted(files, key=lambda f: page_number(f.name) or 0)
    total = len(files)

    ok = 0
    fail = 0
    max_page_seen = 0
    for i, f in enumerate(files, 1):
        n = page_number(f.name)
        if not n:
            print(f"  [OMITIDO] {f.name}: no se pudo determinar el número de página")
            fail += 1
            continue
        max_page_seen = max(max_page_seen, n)
        filename = f"pagina_{n:03d}.webp"
        if progress_cb:
            progress_cb(i, total, filename)
        else:
            print(f"[{i}/{total}] {filename} ...", end=" ", flush=True)

        try:
            img = Image.open(f)
            img.load()
        except Exception as e:
            print(f"  [ERROR AL ABRIR] {f.name}: {e}")
            fail += 1
            continue

        resized = resize_for_web(img.convert("RGB"))
        buf = io.BytesIO()
        resized.save(buf, format="WEBP", quality=WEBP_QUALITY, method=6)

        if upload_bytes(supabase_url, service_key, filename, buf.getvalue(), "image/webp"):
            ok += 1
            if not progress_cb:
                print("OK")
        else:
            fail += 1

    if max_page_seen:
        subir_hotspots(supabase_url, service_key, max_page_seen)

    return ok, fail


def main():
    ok, fail = subir_todas_las_paginas()
    print(f"\n{'=' * 50}")
    print(f"Subidas: {ok} | Fallidas: {fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
