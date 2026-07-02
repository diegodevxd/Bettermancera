"""
Optimiza las imágenes extraídas del catálogo para uso web.

- Recorta a relación 1:1 (centro de la imagen).
- Redimensiona a 800x800 px.
- Convierte a WebP con calidad 85%.
- Guarda en la carpeta fotos_productos_web/.
"""
import sys
from pathlib import Path
from PIL import Image

INPUT_DIR = Path("fotos_productos_corregidas")
OUTPUT_DIR = Path("fotos_productos_web")
TARGET_SIZE = (800, 800)
QUALITY = 85


def optimizar_imagen(input_path: Path, output_path: Path) -> bool:
    try:
        with Image.open(input_path) as img:
            # Convertir a RGB si es necesario (elimina transparencia problemática en algunos casos)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            width, height = img.size

            # Recorte 1:1 desde el centro
            if width != height:
                min_side = min(width, height)
                left = (width - min_side) // 2
                top = (height - min_side) // 2
                right = left + min_side
                bottom = top + min_side
                img = img.crop((left, top, right, bottom))

            # Redimensionar a tamaño objetivo
            img = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)

            # Guardar como WebP
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, "WEBP", quality=QUALITY, method=6)
            return True
    except Exception as e:
        print(f"  [ERROR] {input_path.name}: {e}")
        return False


def main():
    if not INPUT_DIR.exists():
        print(f"[FATAL] No se encontró la carpeta de entrada: {INPUT_DIR.resolve()}")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    archivos = sorted([f for f in INPUT_DIR.iterdir() if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}])
    total = len(archivos)

    print(f"Optimizando {total} imágenes...")
    print(f"Entrada: {INPUT_DIR.resolve()}")
    print(f"Salida:  {OUTPUT_DIR.resolve()}")
    print(f"Formato: WebP 1:1 {TARGET_SIZE[0]}x{TARGET_SIZE[1]} calidad {QUALITY}\n")

    ok = 0
    fail = 0
    for i, archivo in enumerate(archivos, 1):
        nombre_salida = archivo.stem + ".webp"
        output_path = OUTPUT_DIR / nombre_salida
        print(f"[{i:03d}/{total}] {archivo.name} -> {nombre_salida} ...", end=" ", flush=True)
        if optimizar_imagen(archivo, output_path):
            ok += 1
            print("OK")
        else:
            fail += 1

    print(f"\n{'='*50}")
    print(f"Optimizadas: {ok} | Fallidas: {fail}")

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
