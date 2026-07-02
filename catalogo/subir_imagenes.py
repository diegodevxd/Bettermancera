"""Sube todas las imágenes optimizadas de fotos_productos_web al bucket productos_fotos de Supabase.

Requiere las variables de entorno:
  - SUPABASE_URL
  - SUPABASE_SERVICE_ROLE_KEY (necesaria porque el bucket ya no permite escritura anónima)

Puedes crear un archivo .env en la raíz del proyecto con estas variables.
"""
import os
import sys
from pathlib import Path
import urllib.request
import urllib.error
import json

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
BUCKET = "productos_fotos"
FOTOS_DIR = Path("fotos_productos_web")

MIME_MAP = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

def upload_file(filepath: Path) -> bool:
    filename = filepath.name
    ext = filepath.suffix.lower()
    mime = MIME_MAP.get(ext, "application/octet-stream")

    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{filename}"

    with open(filepath, "rb") as f:
        data = f.read()

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
        print(f"  [EXCEPCIÓN] {filename}: {e}")
        return False

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Faltan variables de entorno.")
        print("Define SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY (usa service_role, no anon).")
        print("Ejemplo con PowerShell:")
        print("  $env:SUPABASE_URL='https://tu-proyecto.supabase.co'")
        print("  $env:SUPABASE_SERVICE_ROLE_KEY='eyJ...'")
        return 1

    if not FOTOS_DIR.exists():
        print(f"No se encontró la carpeta: {FOTOS_DIR.resolve()}")
        return 1

    files = sorted([f for f in FOTOS_DIR.iterdir() if f.is_file() and f.suffix.lower() in MIME_MAP])
    total = len(files)
    print(f"Subiendo {total} imágenes a supabase.co/storage/v1/object/{BUCKET}/...\n")

    ok = 0
    fail = 0
    for i, f in enumerate(files, 1):
        print(f"[{i}/{total}] {f.name} ...", end=" ", flush=True)
        if upload_file(f):
            print("OK")
            ok += 1
        else:
            fail += 1

    print(f"\n{'='*50}")
    print(f"Subidas: {ok} | Fallidas: {fail}")
    return 0 if fail == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
