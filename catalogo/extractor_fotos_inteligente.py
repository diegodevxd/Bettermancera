"""
Extractor inteligente de fotos de productos Betterware desde catálogo PDF.

Empareja códigos de producto (texto) con imágenes usando coordenadas espaciales
(bounding boxes) y distancia ponderada entre centros.
"""

from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

PDF_PATH = Path("Catálogo Julio 2026.pdf")
OUTPUT_DIR = Path("fotos_productos")
REGEX_CODIGO = re.compile(r"\b(2[0-9]{4})\b")
MIN_IMAGE_BYTES = 10 * 1024  # 10 KB — filtra íconos y logotipos pequeños
MAX_BG_AREA_RATIO = 0.40  # Ignorar imágenes que cubren >40% de la página (fondo)
MIN_IMAGE_DIMENSION = 80  # px mínimos de ancho y alto


@dataclass
class TextoCodigo:
    codigo: str
    rect: fitz.Rect


@dataclass
class ImagenPagina:
    bbox: fitz.Rect
    xref: int
    width: int
    height: int
    size_bytes: int
    number: int


# ---------------------------------------------------------------------------
# Utilidades geométricas
# ---------------------------------------------------------------------------


def centro(rect: fitz.Rect) -> tuple[float, float]:
    """Centro geométrico de un rectángulo."""
    return ((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)


def distancia_euclidiana(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distancia euclidiana entre dos puntos."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def solapamiento_horizontal(texto: fitz.Rect, imagen: fitz.Rect) -> float:
    """
    Proporción del ancho del texto que se solapa horizontalmente con la imagen.
    Valor entre 0.0 (sin solape) y 1.0 (solape total).
    """
    solape = max(0.0, min(texto.x1, imagen.x1) - max(texto.x0, imagen.x0))
    ancho_texto = max(texto.width, 1.0)
    return solape / ancho_texto


def puntaje_proximidad(texto: fitz.Rect, imagen: fitz.Rect) -> float:
    """
    Calcula qué tan "cercana" está una imagen respecto al código de producto.

    Combina:
      - Distancia euclidiana entre centros (fallback general).
      - Preferencia por imágenes en la misma columna (solape horizontal).
      - Preferencia por imágenes debajo o a la izquierda del código (layout típico
        de catálogos Betterware: código arriba-derecha, foto abajo).

    Menor puntaje = mejor emparejamiento.
    """
    centro_texto = centro(texto)
    centro_imagen = centro(imagen)
    dx = abs(centro_texto[0] - centro_imagen[0])
    dy = centro_imagen[1] - centro_texto[1]  # positivo si la imagen está abajo

    distancia = distancia_euclidiana(centro_texto, centro_imagen)
    solape_x = solapamiento_horizontal(texto, imagen)

    # Sin alineación horizontal: confiar en distancia euclidiana pura
    if solape_x < 0.15:
        return distancia * 1.5

    # Misma columna: penalizar imágenes claramente por encima del código
    if dy < -60:
        return distancia + 8000.0

    # Ponderar: alinear en X, preferir imagen debajo del texto
    return (dx * 0.35) + (max(0.0, dy) * 0.65)


# ---------------------------------------------------------------------------
# Extracción de elementos de la página
# ---------------------------------------------------------------------------


def extraer_codigos(pagina: fitz.Page) -> list[TextoCodigo]:
    """Busca códigos Betterware en la página y devuelve sus bounding boxes."""
    codigos: list[TextoCodigo] = []

    try:
        bloques = pagina.get_text("dict").get("blocks", [])
    except Exception as exc:
        print(f"  [AVISO] No se pudo leer texto de la página: {exc}")
        return codigos

    for bloque in bloques:
        if bloque.get("type") != 0:
            continue
        for linea in bloque.get("lines", []):
            for span in linea.get("spans", []):
                texto = span.get("text", "")
                bbox = span.get("bbox")
                if not bbox:
                    continue
                rect = fitz.Rect(bbox)
                for coincidencia in REGEX_CODIGO.finditer(texto):
                    codigos.append(TextoCodigo(codigo=coincidencia.group(1), rect=rect))

    return codigos


def extraer_imagenes(pagina: fitz.Page) -> list[ImagenPagina]:
    """Obtiene imágenes de la página con coordenadas, filtrando las demasiado pequeñas."""
    imagenes: list[ImagenPagina] = []
    area_pagina = pagina.rect.width * pagina.rect.height

    try:
        info_imagenes = pagina.get_image_info(xrefs=True)
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
            if area_pagina > 0 and (area_imagen / area_pagina) > MAX_BG_AREA_RATIO:
                continue

            imagenes.append(
                ImagenPagina(
                    bbox=bbox,
                    xref=int(info.get("xref", 0)),
                    width=ancho,
                    height=alto,
                    size_bytes=size_bytes,
                    number=int(info.get("number", 0)),
                )
            )
        except Exception as exc:
            print(f"  [AVISO] Imagen omitida por error de parseo: {exc}")
            continue

    return imagenes


def emparejar_codigos_imagenes(
    codigos: list[TextoCodigo],
    imagenes: list[ImagenPagina],
) -> list[tuple[TextoCodigo, ImagenPagina, float]]:
    """
    Empareja cada código con la imagen más cercana usando puntaje de proximidad.

    Usa asignación greedy: ordena todos los pares por puntaje y asigna sin
    reutilizar la misma imagen para dos códigos distintos.
    """
    if not codigos or not imagenes:
        return []

    candidatos: list[tuple[float, TextoCodigo, ImagenPagina]] = []
    for codigo in codigos:
        for imagen in imagenes:
            puntaje = puntaje_proximidad(codigo.rect, imagen.bbox)
            candidatos.append((puntaje, codigo, imagen))

    candidatos.sort(key=lambda item: item[0])

    codigos_asignados: set[str] = set()
    imagenes_usadas: set[int] = set()
    emparejamientos: list[tuple[TextoCodigo, ImagenPagina, float]] = []

    for puntaje, codigo, imagen in candidatos:
        clave_imagen = imagen.xref if imagen.xref else imagen.number
        if codigo.codigo in codigos_asignados or clave_imagen in imagenes_usadas:
            continue
        codigos_asignados.add(codigo.codigo)
        imagenes_usadas.add(clave_imagen)
        emparejamientos.append((codigo, imagen, puntaje))

    return emparejamientos


# ---------------------------------------------------------------------------
# Guardado de imágenes
# ---------------------------------------------------------------------------


def extension_desde_datos(ext: str | None, image_bytes: bytes) -> str:
    """Determina la extensión del archivo a partir del metadata o magic bytes."""
    if ext:
        ext = ext.lower().lstrip(".")
        if ext == "jpeg":
            return "jpg"
        if ext in {"png", "jpg", "webp", "gif", "bmp", "tiff"}:
            return ext

    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if image_bytes[:2] == b"\xff\xd8":
        return "jpg"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "webp"
    return "png"


def extraer_bytes_imagen(
    documento: fitz.Document,
    pagina: fitz.Page,
    imagen: ImagenPagina,
) -> tuple[bytes, str]:
    """
    Extrae el binario de una imagen emparejada.

    - Si tiene xref válido: doc.extract_image(xref).
    - Si xref == 0 (inline): recorte con pixmap del bbox en la página.
    """
    if imagen.xref > 0:
        datos = documento.extract_image(imagen.xref)
        ext = extension_desde_datos(datos.get("ext"), datos["image"])
        return datos["image"], ext

    # Imagen inline / sin xref: renderizar la región del bbox
    pix = pagina.get_pixmap(clip=imagen.bbox, alpha=False)
    return pix.tobytes("png"), "png"


def guardar_imagen(
    documento: fitz.Document,
    pagina: fitz.Page,
    codigo: str,
    imagen: ImagenPagina,
    carpeta: Path,
) -> bool:
    """Extrae y guarda la imagen con el nombre {codigo}.{ext}."""
    try:
        contenido, extension = extraer_bytes_imagen(documento, pagina, imagen)
    except Exception as exc:
        print(f"  [ERROR] No se pudo extraer imagen para {codigo}: {exc}")
        return False

    if len(contenido) < MIN_IMAGE_BYTES:
        print(f"  [AVISO] Imagen de {codigo} demasiado pequeña ({len(contenido)} bytes), omitida.")
        return False

    destino = carpeta / f"{codigo}.{extension}"
    if destino.exists():
        print(f"  [INFO] {destino.name} ya existe, se conserva la versión anterior.")
        return False

    try:
        destino.write_bytes(contenido)
        print(
            f"  [OK] {codigo}.{extension} "
            f"({imagen.width}x{imagen.height}, {len(contenido) // 1024} KB)"
        )
        return True
    except OSError as exc:
        print(f"  [ERROR] No se pudo guardar {destino.name}: {exc}")
        return False


# ---------------------------------------------------------------------------
# Flujo principal
# ---------------------------------------------------------------------------


def main() -> int:
    if not PDF_PATH.exists():
        print(f"[ERROR] No se encontró el PDF: {PDF_PATH.resolve()}")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Carpeta de salida: {OUTPUT_DIR.resolve()}")
    print(f"Procesando: {PDF_PATH.resolve()}\n")

    guardadas = 0
    omitidas = 0
    errores = 0

    try:
        documento = fitz.open(PDF_PATH)
    except Exception as exc:
        print(f"[ERROR] No se pudo abrir el PDF: {exc}")
        return 1

    try:
        total_paginas = len(documento)
        for num_pagina in range(total_paginas):
            print(f"--- Página {num_pagina + 1}/{total_paginas} ---")

            try:
                pagina = documento.load_page(num_pagina)
            except Exception as exc:
                print(f"  [ERROR] No se pudo cargar la página: {exc}")
                errores += 1
                continue

            try:
                codigos = extraer_codigos(pagina)
                imagenes = extraer_imagenes(pagina)
            except Exception as exc:
                print(f"  [ERROR] Falló el análisis de la página: {exc}")
                errores += 1
                continue

            if not codigos:
                print("  Sin códigos de producto en esta página.")
                continue

            if not imagenes:
                print(f"  {len(codigos)} código(s) encontrado(s), pero sin imágenes válidas.")
                omitidas += len(codigos)
                continue

            print(f"  Códigos: {len(codigos)} | Imágenes candidatas: {len(imagenes)}")

            try:
                emparejamientos = emparejar_codigos_imagenes(codigos, imagenes)
            except Exception as exc:
                print(f"  [ERROR] Falló el emparejamiento: {exc}")
                errores += 1
                continue

            codigos_emparejados = {c.codigo for c, _, _ in emparejamientos}
            for codigo in codigos:
                if codigo.codigo not in codigos_emparejados:
                    print(f"  [AVISO] Sin imagen emparejada para código {codigo.codigo}")
                    omitidas += 1

            for codigo_obj, imagen, puntaje in emparejamientos:
                try:
                    if guardar_imagen(documento, pagina, codigo_obj.codigo, imagen, OUTPUT_DIR):
                        guardadas += 1
                    else:
                        omitidas += 1
                except Exception as exc:
                    print(f"  [ERROR] Excepción al guardar {codigo_obj.codigo}: {exc}")
                    errores += 1

    finally:
        documento.close()

    print("\n" + "=" * 50)
    print(f"Imágenes guardadas : {guardadas}")
    print(f"Omitidas / duplicadas: {omitidas}")
    print(f"Errores            : {errores}")
    print(f"Destino            : {OUTPUT_DIR.resolve()}")
    print("=" * 50)

    return 0 if errores == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
