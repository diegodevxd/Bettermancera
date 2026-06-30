"""
Corrige nombres de productos en productos_completos_ia.sql basándose en
el texto visible en las imágenes del catálogo PDF.

Genera:
- productos_corregidos.sql  (archivo completo corregido)
- actualizar_productos.sql  (sentencias UPDATE para Supabase)
"""
import re
from pathlib import Path

SQL_PATH = Path("productos_completos_ia.sql")
OUTPUT_SQL = Path("productos_corregidos.sql")
UPDATE_SQL = Path("actualizar_productos.sql")

# Mapeo de códigos con nombres corregidos según el texto visible en el PDF.
# Solo se incluyen los que se detectaron con alta confianza.
CORRECCIONES = {
    "26054": "Gurmy Toy Story",
    "21525": "Marcianitos Pop",
    "26812": "Set Otomesitas",
    "25610": "Organi Rack WC",
    "26878": "Tulipán Solar",
    "21750": "Guarda Clima",
    "25979": "Organi Gorras",
    "25981": "Absorbe Humedad",
    "26302": "Better Ganchos Combo",
    "26537": "Espátula Rinde Dúo",
    "26836": "Set Sujeti Ganchos",
    "25639": "Gira Squizi",
    "24880": "Organi Blanquillos",
    "26703": "Lonchera Box",
    "26997": "Tina Plegable Masaje",
    "26116": "Set Fibra Esponja",
    "26134": "Baggy Tech",
    "23346": "Piscina Pop",
    "23345": "Cambia Pañales Baby",
    "25804": "Multi Repisas Bambú",
    "24111": "Sticks Tuberías",
    "25581": "Talla Pomex Pro",
}


def main():
    if not SQL_PATH.exists():
        print(f"[FATAL] No se encontró {SQL_PATH}")
        return 1

    texto = SQL_PATH.read_text(encoding="utf-8", errors="ignore")

    # Reemplazar nombres en el INSERT
    def reemplazar_nombre(match):
        codigo = match.group(1)
        nombre = match.group(2)
        if codigo in CORRECCIONES:
            nuevo = CORRECCIONES[codigo]
            return f"('{codigo}', '{nuevo}',"
        return match.group(0)

    texto_corregido = re.sub(
        r"\(\s*'(\d{4,6})'\s*,\s*'([^']+)'\s*,",
        reemplazar_nombre,
        texto,
    )

    OUTPUT_SQL.write_text(texto_corregido, encoding="utf-8")
    print(f"Generado: {OUTPUT_SQL.resolve()}")

    # Generar sentencias UPDATE
    updates = ["-- Actualizar nombres corregidos en Supabase", "BEGIN;"]
    for codigo, nuevo_nombre in CORRECCIONES.items():
        updates.append(
            f"UPDATE public.productos SET nombre = '{nuevo_nombre}' WHERE codigo = '{codigo}';"
        )
    updates.append("COMMIT;")

    UPDATE_SQL.write_text("\n".join(updates), encoding="utf-8")
    print(f"Generado: {UPDATE_SQL.resolve()}")
    print(f"Total correcciones aplicadas: {len(CORRECCIONES)}")

    return 0


if __name__ == "__main__":
    exit(main())
