"""
Extractor de fotos de catálogo PDF por proximidad geométrica (modo visual).

Lógica:
1. Lee códigos de productos desde un archivo SQL.
2. Por cada código, busca su texto en cada página del PDF.
3. Detecta TODAS las imágenes visibles de la página (incluidas inline/xref=0)
   usando page.get_image_info(xrefs=True).
4. Filtra fondos de página e imágenes demasiado pequeñas.
5. Calcula un puntaje de proximidad que premia la alineación horizontal y la
   ubicación debajo/izquierda del código (layout típico Betterware).
6. "Fotografía" la imagen ganadora con page.get_pixmap(clip=rect, matrix=...).
7. Guarda el recorte como {codigo}.png.

Requiere: pip install pymupdf
"""
import fitz  # PyMuPDF
import math
import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Set

# -----------------------------------------------------------------------------
# CONFIGURACIÓN
# -----------------------------------------------------------------------------
PDF_PATH = Path("Catálogo Julio 2026.pdf")
SQL_PATH = Path("productos_completos_ia.sql")
OUTPUT_DIR = Path("fotos_productos_corregidas")

# Resolución del recorte final. Matrix(3,3) ~= 216 dpi en documentos estándar.
SCALE_MATRIX = fitz.Matrix(3, 3)

# Filtros de imágenes
MIN_IMAGE_BYTES = 10 * 1024       # 10 KB — evita íconos/máscaras
MIN_IMAGE_DIMENSION = 80          # px mínimos de ancho y alto
MAX_BG_AREA_RATIO = 0.40          # Ignora imágenes que cubren >40% de la página

# Umbral de distancia máxima (puntos). 220 pts ~= 7.7 cm.
# Si la imagen más cercana está más lejos que esto, se descarta.
MAX_DISTANCE_POINTS = 260

# Regex para códigos Betterware (empiezan con 2 y tienen 5 dígitos)
REGEX_CODIGO = re.compile(r"\b(2\d{4})\b")


# -----------------------------------------------------------------------------
# UTILIDADES
# -----------------------------------------------------------------------------
def parse_codigos_desde_sql(sql_path: Path) -> List[str]:
    """Extrae los códigos de producto de sentencias INSERT del SQL."""
    if not sql_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo SQL: {sql_path.resolve()}")

    texto = sql_path.read_text(encoding="utf-8", errors="ignore")
    codigos = re.findall(r"\(\s*'(\d{4,6})'\s*,", texto)
    vistos: Set[str] = set()
    unicos: List[str] = []
    for c in codigos:
        if c not in vistos:
            vistos.add(c)
            unicos.append(c)
    return unicos


def centro(rect: fitz.Rect) -> Tuple[float, float]:
    return ((rect.x0 + rect.x1) / 2.0, (rect.y0 + rect.y1) / 2.0)


def distancia_euclidiana(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def distancia_punto_a_rect(punto: Tuple[float, float], rect: fitz.Rect) -> float:
    """
    Distancia mínima de un punto a cualquier punto dentro de un rectángulo.
    Devuelve 0 si el punto está dentro del rectángulo.
    """
    x, y = punto
    dx = max(rect.x0 - x, 0, x - rect.x1)
    dy = max(rect.y0 - y, 0, y - rect.y1)
    return math.hypot(dx, dy)


def punto_mas_cercano(punto: Tuple[float, float], rect: fitz.Rect) -> Tuple[float, float]:
    """Devuelve el punto del rectángulo más cercano al punto dado."""
    x, y = punto
    return (
        max(rect.x0, min(x, rect.x1)),
        max(rect.y0, min(y, rect.y1)),
    )


def solapamiento_horizontal(texto: fitz.Rect, imagen: fitz.Rect) -> float:
    """Proporción del ancho del texto que se solapa horizontalmente con la imagen."""
    solape = max(0.0, min(texto.x1, imagen.x1) - max(texto.x0, imagen.x0))
    return solape / max(texto.width, 1.0)


def puntaje_proximidad(texto: fitz.Rect, imagen: fitz.Rect) -> float:
    """
    Puntaje de cercanía entre un código y una imagen.
    Usa distancia del centro del texto al borde más cercano de la imagen,
    por lo que funciona bien incluso cuando el ID está dentro de una foto grande.
    Menor puntaje = mejor emparejamiento.
    """
    c_t = centro(texto)
    distancia = distancia_punto_a_rect(c_t, imagen)

    # Punto de la imagen más cercano al texto, para calcular alineación
    p_cercano = punto_mas_cercano(c_t, imagen)
    dx = abs(c_t[0] - p_cercano[0])
    dy = p_cercano[1] - c_t[1]  # positivo si imagen está debajo del texto
    solape_x = solapamiento_horizontal(texto, imagen)

    # Si el texto cae dentro de la imagen: muy buen candidato
    if distancia == 0:
        return dx * 0.2 + max(0.0, dy) * 0.3

    # Sin alineación horizontal: distancia pura con penalización
    if solape_x < 0.15:
        return distancia * 1.5

    # Misma columna pero imagen claramente arriba del texto: penalizar
    if dy < -80:
        return distancia + 8000.0

    # Premia alineación horizontal y que la imagen esté debajo o cerca
    return (dx * 0.35) + (max(0.0, dy) * 0.65) + distancia * 0.1


def normalizar_texto_codigo(texto: str) -> str:
    """Conserva solo dígitos y devuelve el texto limpio."""
    return re.sub(r"[^0-9]", "", texto)


# -----------------------------------------------------------------------------
# EXTRACCIÓN DE ELEMENTOS DE PÁGINA
# -----------------------------------------------------------------------------
def extraer_codigos_pagina(page: fitz.Page) -> List[Tuple[str, fitz.Rect]]:
    """
    Extrae códigos de producto de una página usando get_text('dict').
    Devuelve lista de (codigo, rect).
    """
    resultados: List[Tuple[str, fitz.Rect]] = []
    try:
        bloques = page.get_text("dict").get("blocks", [])
    except Exception as exc:
        print(f"  [AVISO] No se pudo leer texto de la página: {exc}")
        return resultados

    for bloque in bloques:
        if bloque.get("type") != 0:
            continue
        for linea in bloque.get("lines", []):
            for span in linea.get("spans", []):
                texto = span.get("text", "")
                bbox = span.get("bbox")
                if not bbox or len(bbox) != 4:
                    continue
                rect = fitz.Rect(bbox)
                for coincidencia in REGEX_CODIGO.finditer(texto):
                    codigo = coincidencia.group(1)
                    # Validar que el texto exacto en el rectángulo sea el código
                    txt_en_rect = normalizar_texto_codigo(page.get_textbox(rect))
                    if txt_en_rect == codigo or codigo in txt_en_rect:
                        resultados.append((codigo, rect))
    return resultados


def extraer_imagenes_pagina(
    page: fitz.Page, max_bg_ratio: float = MAX_BG_AREA_RATIO
) -> List[Dict]:
    """
    Obtiene imágenes visibles de la página usando get_image_info.
    Filtra fondos y miniaturas. Incluye imágenes inline (xref=0).
    El parámetro max_bg_ratio permite relajar el filtro en casos límite.
    """
    area_pagina = page.rect.width * page.rect.height
    imagenes: List[Dict] = []

    try:
        info_imagenes = page.get_image_info(xrefs=True)
    except Exception as exc:
        print(f"  [AVISO] get_image_info falló: {exc}")
        return imagenes

    for info in info_imagenes:
        try:
            size_bytes = int(info.get("size", 0))
            ancho = int(info.get("width", 0))
            alto = int(info.get("height", 0))
            bbox_raw = info.get("bbox")

            if size_bytes < MIN_IMAGE_BYTES:
                continue
            if ancho < MIN_IMAGE_DIMENSION or alto < MIN_IMAGE_DIMENSION:
                continue
            if not bbox_raw or len(bbox_raw) != 4:
                continue

            bbox = fitz.Rect(bbox_raw)
            area_imagen = bbox.width * bbox.height
            if area_pagina > 0 and (area_imagen / area_pagina) > max_bg_ratio:
                continue

            imagenes.append({
                "xref": int(info.get("xref", 0)),
                "number": int(info.get("number", 0)),
                "bbox": bbox,
                "width": ancho,
                "height": alto,
                "size": size_bytes,
            })
        except Exception:
            continue

    return imagenes


# -----------------------------------------------------------------------------
# EMPAREJAMIENTO
# -----------------------------------------------------------------------------
def emparejar_codigo_imagen(
    codigos: List[Tuple[str, fitz.Rect]],
    imagenes: List[Dict],
) -> Optional[Tuple[str, fitz.Rect, Dict, float]]:
    """
    Dado un código y las imágenes de una página, devuelve la mejor imagen
    siempre que esté dentro del umbral de distancia (del texto al borde de la imagen).
    """
    if not codigos or not imagenes:
        return None

    mejor: Optional[Tuple[str, fitz.Rect, Dict, float]] = None
    mejor_puntaje = float("inf")

    for codigo, rect_texto in codigos:
        c_t = centro(rect_texto)
        for img in imagenes:
            distancia = distancia_punto_a_rect(c_t, img["bbox"])
            if distancia > MAX_DISTANCE_POINTS:
                continue
            puntaje = puntaje_proximidad(rect_texto, img["bbox"])
            if puntaje < mejor_puntaje:
                mejor_puntaje = puntaje
                mejor = (codigo, rect_texto, img, distancia)

    return mejor


def emparejar_fallback_fondo(
    codigo: str,
    rect_texto: fitz.Rect,
    imagenes: List[Dict],
) -> Optional[Tuple[fitz.Rect, Dict, float]]:
    """
    Fallback para IDs que no encontraron imagen cercana normalmente.
    Busca la imagen más pequeña que contenga el texto del código.
    Útil cuando el catálogo usa fondos de página grandes como fotos de producto.
    """
    c_t = centro(rect_texto)
    candidatas = []
    for img in imagenes:
        distancia = distancia_punto_a_rect(c_t, img["bbox"])
        if distancia == 0:  # el texto está dentro de la imagen
            area = img["bbox"].width * img["bbox"].height
            candidatas.append((area, img, distancia))

    if not candidatas:
        return None

    # Preferir la imagen más pequeña que aún contenga el texto
    candidatas.sort(key=lambda x: x[0])
    _, img, distancia = candidatas[0]
    return (rect_texto, img, distancia)


# -----------------------------------------------------------------------------
# RENDERIZADO Y GUARDADO
# -----------------------------------------------------------------------------
def guardar_recorte_imagen(
    page: fitz.Page, image_rect: fitz.Rect, output_path: Path
) -> bool:
    """
    Renderiza el área indicada del PDF a alta resolución y la guarda como PNG.
    """
    try:
        # Margen pequeño para evitar bordes cortados, limitado a la página
        clip = (image_rect + (-2, -2, 2, 2)) & page.rect
        pix = page.get_pixmap(matrix=SCALE_MATRIX, clip=clip)
        pix.save(str(output_path))
        return True
    except Exception as e:
        print(f"    [ERROR renderizando {output_path.name}]: {e}")
        return False


# -----------------------------------------------------------------------------
# FLUJO PRINCIPAL
# -----------------------------------------------------------------------------
def main(force: bool = False):
    print("=" * 70)
    print("Extractor de fotos por proximidad geométrica (modo visual)")
    print("=" * 70)

    if not PDF_PATH.exists():
        print(f"[FATAL] No se encontró el PDF: {PDF_PATH.resolve()}")
        return 1

    try:
        codigos_sql = parse_codigos_desde_sql(SQL_PATH)
    except Exception as e:
        print(f"[FATAL] {e}")
        return 1

    if force:
        print("[INFO] Modo --force activado: se reemplazarán archivos existentes.")

    print(f"Códigos encontrados en SQL: {len(codigos_sql)}")
    print(f"PDF: {PDF_PATH.resolve()}")
    print(f"Salida: {OUTPUT_DIR.resolve()}")
    print("-" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(PDF_PATH))
    print(f"Páginas en PDF: {doc.page_count}\n")

    # Pre-calcular códigos e imágenes por página
    # Guardamos dos listas de imágenes: normal (sin fondos grandes) y
    # completa (incluye imágenes grandes, para fallback).
    codigos_por_pagina: Dict[int, List[Tuple[str, fitz.Rect]]] = {}
    imagenes_por_pagina: Dict[int, List[Dict]] = {}
    imagenes_completas_por_pagina: Dict[int, List[Dict]] = {}

    for n in range(doc.page_count):
        page = doc.load_page(n)
        codigos_por_pagina[n] = extraer_codigos_pagina(page)
        imagenes_por_pagina[n] = extraer_imagenes_pagina(page)
        imagenes_completas_por_pagina[n] = extraer_imagenes_pagina(page, max_bg_ratio=0.95)

    encontrados: List[str] = []
    no_encontrados: List[str] = []

    total = len(codigos_sql)
    for idx, codigo in enumerate(codigos_sql, start=1):
        out_file = OUTPUT_DIR / f"{codigo}.png"

        if out_file.exists() and not force:
            print(f"[{idx:03d}/{total}] {codigo} -> ya existe, saltando")
            encontrados.append(codigo)
            continue

        mejor_global: Optional[Tuple[int, fitz.Rect, Dict, float]] = None
        mejor_puntaje_global = float("inf")

        # --- PASO 1: emparejamiento normal ---
        for n in range(doc.page_count):
            codigos_filtrados = [
                (c, r) for c, r in codigos_por_pagina[n] if c == codigo
            ]
            if not codigos_filtrados:
                continue

            page = doc.load_page(n)
            candidato = emparejar_codigo_imagen(
                codigos_filtrados, imagenes_por_pagina[n]
            )
            if candidato:
                _, rect_texto, img, distancia = candidato
                puntaje = puntaje_proximidad(rect_texto, img["bbox"])
                if puntaje < mejor_puntaje_global:
                    mejor_puntaje_global = puntaje
                    mejor_global = (n, rect_texto, img, distancia)

        # --- PASO 2: fallback con imágenes grandes ---
        if mejor_global is None:
            for n in range(doc.page_count):
                codigos_filtrados = [
                    (c, r) for c, r in codigos_por_pagina[n] if c == codigo
                ]
                if not codigos_filtrados:
                    continue

                for _, rect_texto in codigos_filtrados:
                    resultado = emparejar_fallback_fondo(
                        codigo, rect_texto, imagenes_completas_por_pagina[n]
                    )
                    if resultado:
                        _, img, distancia = resultado
                        # Guardar como mejor opción de fallback
                        mejor_global = (n, rect_texto, img, distancia)
                        break
                if mejor_global:
                    break

        if mejor_global is None:
            print(f"[{idx:03d}/{total}] {codigo} -> NO ENCONTRADO")
            no_encontrados.append(codigo)
            continue

        pagina, _, img, distancia = mejor_global
        page = doc.load_page(pagina)
        ok = guardar_recorte_imagen(page, img["bbox"], out_file)
        if ok:
            print(
                f"[{idx:03d}/{total}] {codigo} -> OK "
                f"(pág. {pagina + 1}, dist. {distancia:.1f} pts, "
                f"{img['width']}x{img['height']}, {img['size'] // 1024} KB)"
            )
            encontrados.append(codigo)
        else:
            no_encontrados.append(codigo)

    doc.close()

    # Reporte final
    print("\n" + "=" * 70)
    print("REPORTE FINAL")
    print("=" * 70)
    print(f"Total procesados:  {total}")
    print(f"Encontrados:       {len(encontrados)}")
    print(f"No encontrados:    {len(no_encontrados)}")

    if no_encontrados:
        print("\nIDs no encontrados o con error:")
        for c in no_encontrados:
            print(f"  - {c}")

    faltantes_path = OUTPUT_DIR / "_faltantes.txt"
    faltantes_path.write_text("\n".join(no_encontrados), encoding="utf-8")
    print(f"\nLista de faltantes guardada en: {faltantes_path}")

    return 0 if not no_encontrados else 2


if __name__ == "__main__":
    force = "--force" in sys.argv or "-f" in sys.argv
    sys.exit(main(force=force))
