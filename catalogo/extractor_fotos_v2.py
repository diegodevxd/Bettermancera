"""
Extractor v2 de fotos de catálogo Betterware.

Mejoras respecto a v1:
- Renderiza la región VISIBLE en el PDF (get_pixmap clip), no el bitmap embebido completo.
- Filtra fondos de página y banners grandes.
- Empareja código + imagen con heurísticas de layout de catálogo móvil.
- Solo guarda códigos presentes en productos_completos_ia.sql.
- Salida en carpeta nueva: fotos_productos_nuevo/
"""

from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import fitz

PDF_GLOB = "*.pdf"
SQL_PATH = Path("productos_completos_ia.sql")
OUTPUT_DIR = Path("fotos_productos_nuevo")
REGEX_CODIGO = re.compile(r"\b(2[0-9]{4})\b")
RENDER_SCALE = 2.0
MIN_IMAGE_BYTES = 8 * 1024
MAX_BG_AREA_RATIO = 0.28
MAX_DIM_PAGE_RATIO = 0.72
MIN_BBOX_SIZE = 60
MIN_ASPECT = 0.35
MAX_ASPECT = 3.5


@dataclass
class TextoCodigo:
    codigo: str
    rect: fitz.Rect


@dataclass
class ImagenPagina:
    bbox: fitz.Rect
    width: int
    height: int
    size_bytes: int
    key: str


def cargar_codigos_sql(ruta: Path) -> set[str]:
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró SQL: {ruta}")
    texto = ruta.read_text(encoding="utf-8")
    return set(re.findall(r"\('(\d{5})'", texto))


def centro(rect: fitz.Rect) -> tuple[float, float]:
    return ((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)


def solapamiento_horizontal(a: fitz.Rect, b: fitz.Rect) -> float:
    solape = max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))
    return solape / max(a.width, 1.0)


def puntaje_proximidad(texto: fitz.Rect, imagen: fitz.Rect) -> float:
    cx_t, cy_t = centro(texto)
    cx_i, cy_i = centro(imagen)
    dx = abs(cx_t - cx_i)
    dy = cy_i - cy_t
    dist = math.hypot(cx_t - cx_i, cy_t - cy_i)
    solape_x = solapamiento_horizontal(texto, imagen)

    if solape_x < 0.12:
        return dist * 2.0

    if dy < -40:
        return dist + 10000.0

    if dy > 900:
        return dist + 5000.0

    return (dx * 0.4) + (max(0.0, dy) * 0.6)


def extraer_codigos(pagina: fitz.Page, codigos_validos: set[str]) -> list[TextoCodigo]:
    vistos: set[str] = set()
    resultados: list[TextoCodigo] = []

    for bloque in pagina.get_text("dict").get("blocks", []):
        if bloque.get("type") != 0:
            continue
        for linea in bloque.get("lines", []):
            for span in linea.get("spans", []):
                bbox = span.get("bbox")
                if not bbox:
                    continue
                rect = fitz.Rect(bbox)
                for match in REGEX_CODIGO.finditer(span.get("text", "")):
                    codigo = match.group(1)
                    if codigo not in codigos_validos or codigo in vistos:
                        continue
                    vistos.add(codigo)
                    resultados.append(TextoCodigo(codigo=codigo, rect=rect))

    return resultados


def es_imagen_fondo(bbox: fitz.Rect, pagina: fitz.Page) -> bool:
    pw, ph = pagina.rect.width, pagina.rect.height
    area_pag = pw * ph
    area_bbox = bbox.width * bbox.height
    if area_pag <= 0:
        return True
    if area_bbox / area_pag > MAX_BG_AREA_RATIO:
        return True
    if bbox.width / pw > MAX_DIM_PAGE_RATIO or bbox.height / ph > MAX_DIM_PAGE_RATIO:
        return True
    if bbox.width < MIN_BBOX_SIZE or bbox.height < MIN_BBOX_SIZE:
        return True
    aspect = bbox.width / max(bbox.height, 1.0)
    if aspect < MIN_ASPECT or aspect > MAX_ASPECT:
        return True
    return False


def extraer_imagenes(pagina: fitz.Page) -> list[ImagenPagina]:
    imagenes: list[ImagenPagina] = []

    for idx, info in enumerate(pagina.get_image_info(xrefs=True)):
        size_bytes = int(info.get("size", 0))
        if size_bytes < MIN_IMAGE_BYTES:
            continue

        bbox_raw = info.get("bbox")
        if not bbox_raw or len(bbox_raw) != 4:
            continue

        bbox = fitz.Rect(bbox_raw)
        if es_imagen_fondo(bbox, pagina):
            continue

        xref = int(info.get("xref", 0))
        number = int(info.get("number", idx))
        key = f"xref-{xref}" if xref > 0 else f"inline-{number}-{round(bbox.x0)}-{round(bbox.y0)}"

        imagenes.append(
            ImagenPagina(
                bbox=bbox,
                width=int(info.get("width", 0)),
                height=int(info.get("height", 0)),
                size_bytes=size_bytes,
                key=key,
            )
        )

    return imagenes


def emparejar(
    codigos: list[TextoCodigo], imagenes: list[ImagenPagina]
) -> list[tuple[TextoCodigo, ImagenPagina, float]]:
    if not codigos or not imagenes:
        return []

    candidatos: list[tuple[float, TextoCodigo, ImagenPagina]] = []
    for codigo in codigos:
        for imagen in imagenes:
            candidatos.append((puntaje_proximidad(codigo.rect, imagen.bbox), codigo, imagen))

    candidatos.sort(key=lambda item: item[0])

    codigos_asignados: set[str] = set()
    imagenes_usadas: set[str] = set()
    emparejamientos: list[tuple[TextoCodigo, ImagenPagina, float]] = []

    for puntaje, codigo, imagen in candidatos:
        if codigo.codigo in codigos_asignados or imagen.key in imagenes_usadas:
            continue
        codigos_asignados.add(codigo.codigo)
        imagenes_usadas.add(imagen.key)
        emparejamientos.append((codigo, imagen, puntaje))

    return emparejamientos


def renderizar_region(pagina: fitz.Page, bbox: fitz.Rect) -> bytes:
    """Renderiza exactamente lo visible en el PDF (recorte correcto)."""
    clip = bbox + (-2, -2, 2, 2)
    clip = clip & pagina.rect
    matrix = fitz.Matrix(RENDER_SCALE, RENDER_SCALE)
    pix = pagina.get_pixmap(matrix=matrix, clip=clip, alpha=False)
    return pix.tobytes("png")


def guardar_imagen(pagina: fitz.Page, codigo: str, imagen: ImagenPagina, carpeta: Path) -> bool:
    try:
        contenido = renderizar_region(pagina, imagen.bbox)
    except Exception as exc:
        print(f"  [ERROR] Render {codigo}: {exc}")
        return False

    if len(contenido) < MIN_IMAGE_BYTES:
        print(f"  [AVISO] {codigo} muy pequeña ({len(contenido)} bytes)")
        return False

    destino = carpeta / f"{codigo}.png"
    destino.write_bytes(contenido)
    print(
        f"  [OK] {codigo}.png "
        f"({int(imagen.bbox.width)}x{int(imagen.bbox.height)} visible, {len(contenido)//1024} KB)"
    )
    return True


def main() -> int:
    pdf_path = next(Path(".").glob(PDF_GLOB), None)
    if not pdf_path:
        print("[ERROR] No hay PDF en el directorio actual.")
        return 1

    try:
        codigos_sql = cargar_codigos_sql(SQL_PATH)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"PDF     : {pdf_path.resolve()}")
    print(f"SQL     : {len(codigos_sql)} códigos")
    print(f"Salida  : {OUTPUT_DIR.resolve()}\n")

    guardadas = 0
    sin_imagen: list[str] = []
    codigos_encontrados: set[str] = set()

    doc = fitz.open(pdf_path)
    try:
        for num in range(len(doc)):
            pagina = doc.load_page(num)
            codigos = extraer_codigos(pagina, codigos_sql)
            if not codigos:
                continue

            imagenes = extraer_imagenes(pagina)
            if not imagenes:
                for c in codigos:
                    sin_imagen.append(c.codigo)
                print(f"Pág {num+1}: {len(codigos)} códigos, 0 imágenes válidas")
                continue

            pares = emparejar(codigos, imagenes)
            emparejados = {c.codigo for c, _, _ in pares}

            print(f"Pág {num+1}: {len(codigos)} códigos | {len(imagenes)} imgs | {len(pares)} pares")

            for codigo_obj, imagen, _ in pares:
                if guardar_imagen(pagina, codigo_obj.codigo, imagen, OUTPUT_DIR):
                    guardadas += 1
                    codigos_encontrados.add(codigo_obj.codigo)

            for c in codigos:
                if c.codigo not in emparejados:
                    sin_imagen.append(c.codigo)
                    print(f"  [AVISO] Sin imagen: {c.codigo}")
    finally:
        doc.close()

    faltantes = sorted(codigos_sql - codigos_encontrados)
    reporte = OUTPUT_DIR / "_reporte.txt"
    reporte.write_text(
        "\n".join(
            [
                f"Guardadas: {guardadas}",
                f"Sin imagen en PDF: {len(sin_imagen)}",
                f"Faltantes vs SQL: {len(faltantes)}",
                "",
                "Sin imagen:",
                *sorted(set(sin_imagen)),
                "",
                "Faltantes SQL:",
                *faltantes,
            ]
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 50)
    print(f"Imágenes guardadas : {guardadas}")
    print(f"Sin emparejar      : {len(set(sin_imagen))}")
    print(f"Faltantes vs SQL   : {len(faltantes)}")
    print(f"Reporte            : {reporte}")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
