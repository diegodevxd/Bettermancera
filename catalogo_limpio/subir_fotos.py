"""Sube todas las fotos de fotos_catalogo/ al bucket productos_fotos de Supabase.

El nombre de archivo (sin extension) debe coincidir con la columna `codigo`
de la tabla productos, por ejemplo 26813.png -> codigo '26813'.

Requiere las variables de entorno:
  - SUPABASE_URL
  - SUPABASE_SERVICE_ROLE_KEY (necesaria porque el bucket no permite escritura anonima)

No pongas el service_role key en este archivo ni lo compartas. Definelo en la
terminal antes de ejecutar, por ejemplo en PowerShell:

  $env:SUPABASE_URL = "https://lijzftjgevwnjorpycxa.supabase.co"
  $env:SUPABASE_SERVICE_ROLE_KEY = "tu-service-role-key"
  python subir_fotos.py
"""
import io
import os
from pathlib import Path
import urllib.request
import urllib.error

from PIL import Image

BASE_DIR = Path(__file__).resolve().parent

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
BUCKET = "productos_fotos"
FOTOS_DIR = BASE_DIR / "fotos_catalogo"

# Las fotos de origen vienen de paginas escaneadas en alta resolucion
# (hasta 2700x3900px), pero en el catalogo se muestran a ~300-400px.
# Las redimensionamos antes de subir para que carguen rapido.
MAX_DIMENSION = 1000

MIME_MAP = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def resize_if_needed(img: Image.Image) -> Image.Image:
    if max(img.size) <= MAX_DIMENSION:
        return img
    img = img.copy()
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
    return img


def upload_bytes(filename: str, data: bytes, mime: str) -> bool:
    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{filename}"

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", mime)
    req.add_header("x-upsert", "true")  # sobrescribe si ya existe

    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status in (200, 201):
                return True
            print(f"  [{resp.status}] {filename}")
            return False
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  [ERROR {e.code}] {filename}: {body[:120]}")
        return False
    except Exception as e:
        print(f"  [EXCEPCION] {filename}: {e}")
        return False


def upload_file(filepath: Path) -> bool:
    # La app pide primero el .webp; si queda un .webp viejo en el bucket
    # (de una subida anterior), tapa al .png nuevo. Por eso subimos ambos,
    # ya redimensionados: el .png (respaldo) y el .webp (formato principal).
    ext = filepath.suffix.lower()
    mime = MIME_MAP.get(ext, "application/octet-stream")

    try:
        original_img = Image.open(filepath)
        original_img.load()
    except Exception as e:
        print(f"  [ERROR AL ABRIR] {filepath.name}: {e}")
        return False

    resized = resize_if_needed(original_img)

    png_buf = io.BytesIO()
    resized.convert("RGBA" if resized.mode in ("RGBA", "LA") else "RGB").save(
        png_buf, format="PNG", optimize=True
    )
    ok_original = upload_bytes(filepath.name, png_buf.getvalue(), mime)

    ok_webp = True
    if ext != ".webp":
        try:
            webp_img = resized.convert("RGB")
            buf = io.BytesIO()
            webp_img.save(buf, format="WEBP", quality=82, method=6)
            webp_name = filepath.stem + ".webp"
            ok_webp = upload_bytes(webp_name, buf.getvalue(), "image/webp")
        except Exception as e:
            print(f"  [WEBP EXCEPCION] {filepath.name}: {e}")
            ok_webp = False

    return ok_original and ok_webp


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Faltan variables de entorno.")
        print("Define SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY (usa service_role, no anon).")
        return 1

    if not FOTOS_DIR.exists():
        print(f"No se encontro la carpeta: {FOTOS_DIR}")
        return 1

    files = sorted([f for f in FOTOS_DIR.iterdir() if f.is_file() and f.suffix.lower() in MIME_MAP])
    total = len(files)
    print(f"Subiendo {total} imagenes a {SUPABASE_URL}/storage/v1/object/{BUCKET}/...\n")

    ok = 0
    fail = 0
    for i, f in enumerate(files, 1):
        print(f"[{i}/{total}] {f.name} ...", end=" ", flush=True)
        if upload_file(f):
            print("OK")
            ok += 1
        else:
            fail += 1

    print(f"\n{'=' * 50}")
    print(f"Subidas: {ok} | Fallidas: {fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
