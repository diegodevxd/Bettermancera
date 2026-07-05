"""Lee el catálogo PDF y detecta los productos (código, nombre, precio y
página) desde su capa de texto. Genera productos_detectados.json, que el
extractor asistido usa como lista de productos del mes.

Con esto ya no hay que mantener productos.sql a mano: cada mes, con el PDF
nuevo en esta carpeta, corre

  python leer_catalogo_pdf.py

o usa el botón "Leer catálogo PDF" dentro del extractor asistido.

Nota: el precio detectado es el precio normal (el primero junto al nombre).
Los precios rojos tipo "al comprar 3 productos" son condicionales y se
guardan aparte como referencia; el precio de oferta real se captura a mano
en el extractor al marcar cada producto.
"""
import json
import os
import re
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Falta PyMuPDF. Instálalo con:  pip install pymupdf")
    raise SystemExit(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(BASE_DIR, "productos_detectados.json")

RE_CODIGO = re.compile(r"^\s*[  \s]*(\d{5})[  \s]*$")
RE_PRECIO = re.compile(r"\$\s*([\d,]+(?:\.\d{1,2})?)")


def _limpia(texto):
    return re.sub(r"[  ]+", " ", texto).strip()


def _parse_precio(m):
    raw = m.group(1)
    valor = float(raw.replace(",", ""))
    # Betterware imprime los centavos en superíndice ($69⁹⁰), que en la capa
    # de texto se pega como "6990". Los precios de miles reales siempre traen
    # coma ($1,100), así que 4+ dígitos sin coma ni punto son pesos.centavos.
    if "," not in raw and "." not in raw and valor >= 1000:
        valor = valor / 100
    return valor


def extraer_productos(pdf_path):
    """Devuelve {codigo: {nombre, precio, precio_condicional, pagina}}."""
    doc = fitz.open(pdf_path)
    productos = {}

    for pno, page in enumerate(doc, 1):
        lineas = [_limpia(l) for l in page.get_text("text").splitlines()]

        for i, linea in enumerate(lineas):
            m = RE_CODIGO.match(linea)
            if not m:
                continue
            codigo = m.group(1)

            # Nombre: las líneas no vacías que siguen, hasta topar con un precio
            nombre_partes = []
            precio = None
            precio_condicional = None
            j = i + 1
            while j < len(lineas) and j <= i + 8:
                l = lineas[j]
                j += 1
                if not l:
                    continue
                pm = RE_PRECIO.search(l)
                if pm:
                    precio = _parse_precio(pm)
                    break
                if RE_CODIGO.match(l):
                    j -= 1
                    break
                nombre_partes.append(l)

            # Precio condicional (caja roja "al comprar N productos"), si viene
            # justo después del precio normal.
            while j < len(lineas) and j <= i + 12:
                l = lineas[j]
                j += 1
                if not l:
                    continue
                if RE_CODIGO.match(l):
                    break
                pm = RE_PRECIO.search(l)
                if pm:
                    precio_condicional = _parse_precio(pm)
                break

            nombre = " ".join(nombre_partes).strip()
            if not nombre or precio is None:
                continue

            # Si el mismo código sale en varias páginas (portada, índice),
            # nos quedamos con la primera aparición completa.
            if codigo not in productos:
                productos[codigo] = {
                    "nombre": nombre,
                    "precio": precio,
                    "precio_condicional": precio_condicional,
                    "pagina": pno,
                }

    doc.close()
    return productos


def main():
    pdf_name = sys.argv[1] if len(sys.argv) > 1 else "catalogo.pdf"
    pdf_path = pdf_name if os.path.isabs(pdf_name) else os.path.join(BASE_DIR, pdf_name)
    if not os.path.exists(pdf_path):
        print(f"No se encontró el PDF: {pdf_path}")
        return 1

    productos = extraer_productos(pdf_path)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(productos, f, ensure_ascii=False, indent=2, sort_keys=True)

    paginas = sorted({p["pagina"] for p in productos.values()})
    print(f"Detectados {len(productos)} productos en {len(paginas)} páginas.")
    print(f"Guardado en: {OUTPUT_PATH}")
    print("\nSiguiente paso: abre extractor_asistido.py y marca cada producto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
