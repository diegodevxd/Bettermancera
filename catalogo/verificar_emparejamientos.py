"""
Verifica si los nombres de productos en el SQL coinciden con el texto
visible en las imágenes extraídas del PDF.

Para cada código:
1. Busca su posición en el PDF.
2. Recupera el bounding box de la imagen que fue emparejada (la más cercana).
3. Extrae todo el texto dentro de esa imagen.
4. Comprueba si el nombre del SQL aparece (parcialmente) en ese texto.
5. Reporta discrepancias.
"""
import fitz
import re
import sys
from pathlib import Path
from difflib import SequenceMatcher

PDF_PATH = Path("Catálogo Julio 2026.pdf")
SQL_PATH = Path("productos_completos_ia.sql")


def parse_productos_sql(sql_path: Path):
    """Devuelve dict {codigo: nombre}."""
    texto = sql_path.read_text(encoding="utf-8", errors="ignore")
    productos = {}
    for codigo, nombre in re.findall(r"\(\s*'(\d{4,6})'\s*,\s*'([^']+)'", texto):
        productos[codigo] = nombre
    return productos


def limpiar_texto(t: str) -> str:
    return re.sub(r"[^a-záéíóúüñ0-9 ]+", "", t.lower().strip())


def similitud(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def main():
    if not PDF_PATH.exists():
        print(f"[FATAL] No se encontró el PDF: {PDF_PATH}")
        return 1

    productos = parse_productos_sql(SQL_PATH)
    print(f"Productos en SQL: {len(productos)}\n")

    doc = fitz.open(str(PDF_PATH))

    sospechosos = []
    no_encontrados = []

    for codigo, nombre_sql in productos.items():
        mejor_sim = 0.0
        mejor_texto = ""
        encontrado = False

        for n in range(doc.page_count):
            page = doc.load_page(n)
            rects = page.search_for(codigo)
            if not rects:
                continue

            for r in rects:
                # Verificar que el texto en el rect sea exactamente el código
                txt = page.get_textbox(r).strip()
                if re.sub(r"[^0-9]", "", txt) != codigo:
                    continue

                # Encontrar imagen más cercana
                c = ((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
                imgs = page.get_image_info(xrefs=True)
                mejor_img = None
                mejor_dist = float("inf")
                for img in imgs:
                    bbox = img.get("bbox")
                    if not bbox:
                        continue
                    ir = fitz.Rect(bbox)
                    # distancia del centro del texto al borde más cercano de la imagen
                    dx = max(ir.x0 - c[0], 0, c[0] - ir.x1)
                    dy = max(ir.y0 - c[1], 0, c[1] - ir.y1)
                    d = (dx ** 2 + dy ** 2) ** 0.5
                    if d < mejor_dist:
                        mejor_dist = d
                        mejor_img = ir

                if mejor_img is None:
                    continue

                # Extraer texto dentro de la imagen encontrada
                texto_img = page.get_textbox(mejor_img).strip()
                if not texto_img:
                    continue

                encontrado = True
                nombre_limpio = limpiar_texto(nombre_sql)
                texto_limpio = limpiar_texto(texto_img)
                sim = similitud(nombre_limpio, texto_limpio)

                # También buscar palabras clave del nombre dentro del texto
                palabras = [p for p in nombre_limpio.split() if len(p) > 3]
                coincidencias = sum(1 for p in palabras if p in texto_limpio)
                ratio_palabras = coincidencias / max(len(palabras), 1)

                # Score combinado
                score = max(sim, ratio_palabras * 0.8)
                if score > mejor_sim:
                    mejor_sim = score
                    mejor_texto = texto_img[:300]

        if not encontrado:
            no_encontrados.append(codigo)
        elif mejor_sim < 0.35:
            sospechosos.append({
                "codigo": codigo,
                "nombre_sql": nombre_sql,
                "texto_img": mejor_texto,
                "score": mejor_sim,
            })

    doc.close()

    print(f"Sospechosos de mismatch: {len(sospechosos)}")
    print("=" * 70)
    for item in sospechosos:
        print(f"\nCódigo: {item['codigo']}")
        print(f"Nombre SQL: {item['nombre_sql']}")
        print(f"Texto en imagen: {item['texto_img'][:200]}")
        print(f"Score: {item['score']:.2f}")

    print(f"\n\nNo encontrados en PDF: {len(no_encontrados)}")
    for c in no_encontrados:
        print(f"  - {c}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
