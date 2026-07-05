"""Convierte el catálogo PDF a una imagen PNG por página en paginas_catalogo/.

Es el primer paso del flujo mensual: cuando llega el catálogo nuevo de
Betterware, guárdalo como catalogo.pdf en esta carpeta y corre:

  python pdf_a_paginas.py

(o `python pdf_a_paginas.py otro_archivo.pdf` si tiene otro nombre)

Requiere PyMuPDF:  pip install pymupdf

Las páginas anteriores en paginas_catalogo/ se sobrescriben (mismo nombre
pagina_N.png). Si el catálogo nuevo tiene MENOS páginas que el anterior,
las sobrantes viejas se borran para no mezclar catálogos.
"""
import os
import re
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Falta PyMuPDF. Instálalo con:  pip install pymupdf")
    raise SystemExit(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "paginas_catalogo")

# Escala de render: 3.0 da ~1800px de ancho para un PDF tamaño carta, más que
# suficiente para marcar productos y para la web (que lo baja a 1400px).
ZOOM = 3.0


def main():
    pdf_name = sys.argv[1] if len(sys.argv) > 1 else "catalogo.pdf"
    pdf_path = pdf_name if os.path.isabs(pdf_name) else os.path.join(BASE_DIR, pdf_name)
    if not os.path.exists(pdf_path):
        print(f"No se encontró el PDF: {pdf_path}")
        return 1

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    doc = fitz.open(pdf_path)
    total = len(doc)
    print(f"Convirtiendo {total} páginas de {os.path.basename(pdf_path)}...\n")

    matrix = fitz.Matrix(ZOOM, ZOOM)
    for i, page in enumerate(doc, 1):
        out = os.path.join(OUTPUT_DIR, f"pagina_{i}.png")
        pix = page.get_pixmap(matrix=matrix)
        pix.save(out)
        print(f"[{i}/{total}] pagina_{i}.png  ({pix.width}x{pix.height})")
    doc.close()

    # Borrar páginas sobrantes de un catálogo anterior más largo
    borradas = 0
    for f in os.listdir(OUTPUT_DIR):
        m = re.match(r"pagina_(\d+)\.png$", f)
        if m and int(m.group(1)) > total:
            os.remove(os.path.join(OUTPUT_DIR, f))
            borradas += 1
    if borradas:
        print(f"\nSe borraron {borradas} páginas sobrantes del catálogo anterior.")

    print(f"\nListo: {total} páginas en {OUTPUT_DIR}")
    print("Siguiente paso:  python subir_paginas.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
