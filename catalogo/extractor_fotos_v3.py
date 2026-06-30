"""
Extractor v6: layout inteligente + celda por producto + mejor aparición.

- SPLIT: catálogo 2 columnas con fotos izq/der
- STACKED: productos apilados a ancho completo
- GRID: 4 columnas (págs. 89, 111-113)
- HERO: página de un solo producto
- PROMO: banner inferior (y > 1450)
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import fitz

PDF_GLOB = "*.pdf"
SQL_PATH = Path("productos_completos_ia.sql")
OUTPUT_DIR = Path("fotos_productos_nuevo")
REGEX_CODIGO = re.compile(r"\b(2[0-9]{4})\b")
RENDER_SCALE = 2.0
FOOTER_Y = 1735
MARGIN = 10
MIN_IMAGE_BYTES = 5000
MAX_BG_AREA_RATIO = 0.34
MIN_IMG_H = 100
ROW_Y_TOL = 45
NUM_COLS_GRID = 4
PROMO_Y = 1450


class LayoutKind(Enum):
    HERO = "hero"
    GRID = "grid"
    SPLIT = "split"
    STACKED = "stacked"


@dataclass
class TextoCodigo:
    codigo: str
    rect: fitz.Rect


@dataclass
class Candidato:
    codigo: str
    clip: fitz.Rect
    pagina_num: int
    calidad: float


def cargar_codigos_sql(ruta: Path) -> set[str]:
    return set(re.findall(r"\('(\d{5})'", Path(ruta).read_text(encoding="utf-8")))


def extraer_codigos_pagina(pagina: fitz.Page, codigos_validos: set[str]) -> list[TextoCodigo]:
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


def bounds_pagina(pagina: fitz.Page) -> tuple[float, float]:
    return pagina.rect.x0 + MARGIN, pagina.rect.x1 - MARGIN


def es_pagina_grid(codigos: list[TextoCodigo]) -> bool:
    if len(codigos) < 4:
        return False
    filas: dict[int, list[TextoCodigo]] = defaultdict(list)
    for c in codigos:
        filas[int(round(c.rect.y0 / ROW_Y_TOL))].append(c)
    return max(len(v) for v in filas.values()) >= 3


def tiene_columnas_izq_der(codigos: list[TextoCodigo], pagina: fitz.Page) -> bool:
    w = pagina.rect.width
    izq = any((c.rect.x0 + c.rect.x1) / 2 < w * 0.38 for c in codigos)
    der = any((c.rect.x0 + c.rect.x1) / 2 > w * 0.62 for c in codigos)
    return izq and der


def imagen_hero(pagina: fitz.Page) -> bool:
    pr = pagina.rect
    area = pr.width * pr.height
    for info in pagina.get_image_info(xrefs=True):
        bbox = fitz.Rect(info["bbox"])
        if bbox.width * bbox.height / area > 0.38 and bbox.height > 500:
            return True
    return False


def clasificar_pagina(codigos: list[TextoCodigo], pagina: fitz.Page) -> LayoutKind:
    if len(codigos) == 1 and not es_promo(codigos[0]) and imagen_hero(pagina):
        return LayoutKind.HERO
    if es_pagina_grid(codigos):
        return LayoutKind.GRID
    cxs = [(c.rect.x0 + c.rect.x1) / 2 for c in codigos]
    all_right = all(cx > pagina.rect.width * 0.65 for cx in cxs)
    all_left = all(cx < pagina.rect.width * 0.35 for cx in cxs)
    if all_right or all_left:
        for info in pagina.get_image_info(xrefs=True):
            bbox = fitz.Rect(info["bbox"])
            if bbox.height > 400 and bbox.width >= pagina.rect.width * 0.78:
                return LayoutKind.STACKED
    if tiene_columnas_izq_der(codigos, pagina):
        return LayoutKind.SPLIT
    return LayoutKind.SPLIT


def indice_columna(codigo: TextoCodigo, pagina: fitz.Page, grid: bool) -> int:
    cx = (codigo.rect.x0 + codigo.rect.x1) / 2
    w = pagina.rect.width
    if grid:
        if cx < w * 0.25:
            return 0
        if cx < w * 0.5:
            return 1
        if cx < w * 0.75:
            return 2
        return 3
    return 0 if cx < w * 0.5 else 1


def bounds_columna(
    idx: int, pagina: fitz.Page, grid: bool, codigos_col: list[TextoCodigo] | None = None
) -> tuple[float, float]:
    w = pagina.rect.width
    if grid and codigos_col:
        cxs = [(c.rect.x0 + c.rect.x1) / 2 for c in codigos_col]
        cx = sum(cxs) / len(cxs)
        medio = w / 8
        x0 = max(pagina.rect.x0 + MARGIN, cx - medio)
        x1 = min(pagina.rect.x1 - MARGIN, cx + medio)
        return x0, x1
    if grid:
        step = w / NUM_COLS_GRID
        x0 = pagina.rect.x0 + idx * step + (MARGIN if idx == 0 else 4)
        x1 = pagina.rect.x0 + (idx + 1) * step - (MARGIN if idx == NUM_COLS_GRID - 1 else 4)
        return x0, x1
    mid = w * 0.5
    if idx == 0:
        return pagina.rect.x0 + MARGIN, mid - 4
    return mid + 4, pagina.rect.x1 - MARGIN


def celda_usa_ancho_completo(
    codigo: TextoCodigo,
    todos: list[TextoCodigo],
    pagina: fitz.Page,
    y0: float,
    y1: float,
) -> bool:
    cx = (codigo.rect.x0 + codigo.rect.x1) / 2
    mi_lado_izq = cx < pagina.rect.width * 0.5
    cy = codigo.rect.y0

    fila = [c for c in todos if abs(c.rect.y0 - cy) < ROW_Y_TOL]
    w = pagina.rect.width
    izq = [c for c in fila if (c.rect.x0 + c.rect.x1) / 2 < w * 0.5]
    der = [c for c in fila if (c.rect.x0 + c.rect.x1) / 2 >= w * 0.5]
    if mi_lado_izq and der:
        return False
    if not mi_lado_izq and izq:
        return False

    for c in todos:
        if c.codigo == codigo.codigo:
            continue
        cx2 = (c.rect.x0 + c.rect.x1) / 2
        otro_izq = cx2 < w * 0.5
        if otro_izq == mi_lado_izq:
            continue
        if y0 - 25 <= c.rect.y0 <= y1 + 25:
            return False

    return True


def es_promo(codigo: TextoCodigo) -> bool:
    return codigo.rect.y0 >= PROMO_Y


def slot_vertical(
    lista: list[TextoCodigo], i: int, pagina: fitz.Page
) -> tuple[float, float]:
    codigo = lista[i]
    cy = codigo.rect.y0

    if es_promo(codigo):
        return cy - 18, min(FOOTER_Y, cy + 200)

    if i == 0:
        y0 = pagina.rect.y0 + MARGIN
        if cy > 280:
            y0 = max(MARGIN, cy - 35)
    elif abs(lista[i - 1].rect.y0 - cy) < ROW_Y_TOL:
        y0 = cy - 18
    else:
        y0 = (lista[i - 1].rect.y0 + cy) / 2

    y1 = FOOTER_Y
    for j in range(i + 1, len(lista)):
        if abs(lista[j].rect.y0 - cy) >= ROW_Y_TOL:
            y1 = lista[j].rect.y0 - 12
            break

    if len(lista) == 1 and cy < 450 and not es_promo(codigo):
        y1 = min(y1, cy + 520)

    return y0, min(FOOTER_Y, max(y0 + 120, y1))


def celda_producto(
    codigo: TextoCodigo,
    lista: list[TextoCodigo],
    i: int,
    todos: list[TextoCodigo],
    pagina: fitz.Page,
    layout: LayoutKind,
) -> fitz.Rect:
    y0, y1 = slot_vertical(lista, i, pagina)
    grid = layout == LayoutKind.GRID

    if layout == LayoutKind.HERO:
        x0, x1 = bounds_pagina(pagina)
        y0, y1 = pagina.rect.y0 + MARGIN, FOOTER_Y
    elif layout == LayoutKind.GRID:
        col_idx = indice_columna(codigo, pagina, True)
        col_codes = [c for c in todos if indice_columna(c, pagina, True) == col_idx]
        x0, x1 = bounds_columna(col_idx, pagina, True, col_codes)
    elif layout == LayoutKind.STACKED:
        x0, x1 = bounds_pagina(pagina)
    elif layout == LayoutKind.SPLIT and celda_usa_ancho_completo(codigo, todos, pagina, y0, y1):
        x0, x1 = bounds_pagina(pagina)
    else:
        x0, x1 = bounds_columna(indice_columna(codigo, pagina, False), pagina, False)

    if not es_promo(codigo) and codigo.rect.y0 > 400:
        y0 = max(y0, codigo.rect.y0 - 28)

    return fitz.Rect(x0, y0, x1, y1) & pagina.rect


def overlap_area(a: fitz.Rect, b: fitz.Rect) -> float:
    x = max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))
    y = max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0))
    return x * y


def imagenes_candidatas(pagina: fitz.Page, celda: fitz.Rect) -> list[fitz.Rect]:
    pr = pagina.rect
    area_pag = pr.width * pr.height
    resultados: list[fitz.Rect] = []

    for info in pagina.get_image_info(xrefs=True):
        if int(info.get("size", 0)) < MIN_IMAGE_BYTES:
            continue
        bbox = fitz.Rect(info["bbox"])
        if bbox.height < MIN_IMG_H:
            continue
        if overlap_area(bbox, celda) < 2000:
            continue
        ratio = (bbox.width * bbox.height) / area_pag if area_pag > 0 else 0
        if ratio > 0.88:
            continue
        resultados.append(bbox)

    return resultados


def puntaje_imagen(
    codigo: TextoCodigo,
    bbox: fitz.Rect,
    celda: fitz.Rect,
    pagina: fitz.Page,
    layout: LayoutKind,
    todos: list[TextoCodigo],
) -> float:
    ov = overlap_area(bbox, celda)
    if ov < 2500:
        return 999999.0

    code_y = codigo.rect.y0
    area_ratio = (bbox.width * bbox.height) / (pagina.rect.width * pagina.rect.height)

    if bbox.y1 < code_y - 100:
        return 999999.0

    if code_y > bbox.y1 + 20:
        gap = code_y - bbox.y1
        if gap < 120:
            return 999999.0

    if bbox.y0 > code_y + 450 and ov < celda.height * celda.width * 0.15:
        return 999999.0

    aspect = bbox.width / max(bbox.height, 1)
    limite_aspect = 1.75 if layout in (LayoutKind.STACKED, LayoutKind.HERO) else 1.45
    if es_promo(codigo):
        limite_aspect = 2.5
    if aspect > limite_aspect:
        return 999999.0

    if layout == LayoutKind.GRID:
        cx_img = (bbox.x0 + bbox.x1) / 2
        cx_code = (codigo.rect.x0 + codigo.rect.x1) / 2
        step = pagina.rect.width / NUM_COLS_GRID
        if int(cx_img / step) != int(cx_code / step):
            return 999999.0
        if abs(cx_img - cx_code) > 95:
            return 999999.0

    if es_promo(codigo):
        if not (80 <= bbox.height <= 350):
            return 999999.0
    elif bbox.height < 200 and area_ratio < 0.06:
        return 999999.0

    exceso_arriba = max(0.0, code_y - bbox.y0)
    if exceso_arriba > 420 and not es_promo(codigo):
        return 999999.0

    if layout == LayoutKind.SPLIT and not celda_usa_ancho_completo(
        codigo, todos, pagina, celda.y0, celda.y1
    ):
        cx = (bbox.x0 + bbox.x1) / 2
        lado = (codigo.rect.x0 + codigo.rect.x1) / 2
        mid = pagina.rect.width * 0.5
        if lado < mid and cx > mid + 80:
            return 999999.0
        if lado >= mid and cx < mid - 80:
            return 999999.0

    header = bbox.y0 + max(150, bbox.height * 0.32)
    en_cabecera = bbox.y0 <= code_y <= header

    dist_top = abs(code_y - bbox.y0)
    if en_cabecera:
        puntaje = dist_top * 0.3
    else:
        centro = (bbox.y0 + bbox.y1) / 2
        puntaje = dist_top + abs(code_y - centro) * 0.2

    if bbox.height > celda.height * 1.35 and not es_promo(codigo):
        puntaje *= 1.4

    if ov >= celda.height * celda.width * 0.25:
        puntaje *= 0.75

    if bbox.height >= 400:
        puntaje *= 0.55

    if area_ratio > MAX_BG_AREA_RATIO and not en_cabecera and layout != LayoutKind.HERO:
        puntaje *= 1.8

    return puntaje


def refinar_clip(
    codigo: TextoCodigo,
    celda: fitz.Rect,
    bbox: fitz.Rect,
    pagina: fitz.Page,
    layout: LayoutKind,
) -> fitz.Rect:
    pad = 8
    y0 = max(celda.y0, bbox.y0 - pad)
    y1 = min(celda.y1, bbox.y1 + pad, FOOTER_Y)

    if layout == LayoutKind.GRID:
        cx = (bbox.x0 + bbox.x1) / 2
        if celda.x0 <= cx <= celda.x1 + 20:
            x0 = max(celda.x0 - pad, bbox.x0 - pad)
            x1 = min(max(celda.x1, bbox.x1 + pad), celda.x1 + 100)
        else:
            x0, x1 = celda.x0, celda.x1
    else:
        x0, x1 = celda.x0, celda.x1

    if es_promo(codigo):
        y0 = max(celda.y0, codigo.rect.y0 - 20)
        y1 = min(celda.y1, max(bbox.y1, codigo.rect.y0 + 120) + pad)
        x0 = max(celda.x0, min(bbox.x0, codigo.rect.x0 - 60) - pad)
        x1 = min(celda.x1, max(bbox.x1, codigo.rect.x1 + 200) + pad)

    return fitz.Rect(x0, y0, x1, y1) & pagina.rect


def clip_producto(
    codigo: TextoCodigo,
    lista: list[TextoCodigo],
    i: int,
    todos: list[TextoCodigo],
    pagina: fitz.Page,
    layout: LayoutKind,
) -> fitz.Rect:
    celda = celda_producto(codigo, lista, i, todos, pagina, layout)

    if layout == LayoutKind.HERO:
        return celda
    imagenes = imagenes_candidatas(pagina, celda)

    mejor: fitz.Rect | None = None
    mejor_puntaje = 999999.0

    for bbox in imagenes:
        p = puntaje_imagen(codigo, bbox, celda, pagina, layout, todos)
        if p < mejor_puntaje:
            mejor_puntaje = p
            mejor = bbox

    if mejor and mejor_puntaje < 999999.0:
        return refinar_clip(codigo, celda, mejor, pagina, layout)

    return celda


def clip_pagina(
    codigos: list[TextoCodigo], pagina: fitz.Page, layout: LayoutKind
) -> dict[str, fitz.Rect]:
    clips: dict[str, fitz.Rect] = {}
    grid = layout == LayoutKind.GRID
    por_col: dict[int, list[TextoCodigo]] = defaultdict(list)

    for c in codigos:
        por_col[indice_columna(c, pagina, grid)].append(c)

    for lista in por_col.values():
        if not lista:
            continue
        lista.sort(key=lambda c: c.rect.y0)
        for i, codigo in enumerate(lista):
            clips[codigo.codigo] = clip_producto(codigo, lista, i, codigos, pagina, layout)

    return clips


def calidad_candidato(
    codigo: TextoCodigo, clip: fitz.Rect, layout: LayoutKind, pagina: fitz.Page
) -> float:
    if clip.width < 40 or clip.height < 40:
        return -1.0

    score = clip.width * clip.height
    page_area = pagina.rect.width * pagina.rect.height
    fill = (clip.width * clip.height) / page_area

    ratio = clip.width / max(clip.height, 1)
    if ratio < 0.25 or ratio > 2.8:
        score *= 0.55

    if clip.height < 180:
        score *= 0.45
    if clip.width < 220:
        score *= 0.55

    if fill > 0.55 and layout != LayoutKind.HERO:
        score *= 0.12

    if layout == LayoutKind.HERO:
        score *= 1.5
    elif layout == LayoutKind.GRID:
        score *= 0.88

    if codigo.rect.y0 < 800 and clip.height > 400:
        score *= 0.008

    if codigo.rect.y0 >= PROMO_Y:
        if 90 <= clip.height <= 280 and clip.width >= 350:
            score *= 6.0
        elif clip.height > 400:
            score *= 0.05

    if clip.height >= 350 and clip.width >= 400:
        score *= 1.15

    return score


def renderizar(pagina: fitz.Page, clip: fitz.Rect) -> bytes:
    pix = pagina.get_pixmap(matrix=fitz.Matrix(RENDER_SCALE, RENDER_SCALE), clip=clip, alpha=False)
    return pix.tobytes("png")


def guardar(codigo: str, clip: fitz.Rect, pagina: fitz.Page) -> bool:
    if clip.width < 40 or clip.height < 40:
        return False
    dest = OUTPUT_DIR / f"{codigo}.png"
    tmp = OUTPUT_DIR / f"_{codigo}.tmp.png"
    try:
        tmp.write_bytes(renderizar(pagina, clip))
        tmp.replace(dest)
    except OSError:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return False
    return True


def main() -> int:
    pdf_path = next(Path(".").glob(PDF_GLOB), None)
    if not pdf_path:
        print("[ERROR] No hay PDF.")
        return 1

    desde: str | None = None
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg.startswith("--desde="):
            desde = arg.split("=", 1)[1]
        elif arg == "--desde" and i < len(sys.argv) - 1:
            desde = sys.argv[i + 1]

    codigos_sql = cargar_codigos_sql(SQL_PATH)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    codigos_objetivo = sorted(c for c in codigos_sql if not desde or c >= desde)

    print(
        f"Extraccion v6 -> {OUTPUT_DIR.resolve()}\n"
        f"Productos: {len(codigos_objetivo)}"
        + (f" (desde {desde})" if desde else " (completo)")
        + "\n"
    )

    mejores: dict[str, Candidato] = {}
    doc = fitz.open(pdf_path)

    try:
        for num in range(len(doc)):
            pagina = doc.load_page(num)
            codigos = extraer_codigos_pagina(pagina, codigos_sql)
            if not codigos:
                continue
            codigos = [c for c in codigos if c.codigo in codigos_objetivo]
            if not codigos:
                continue

            layout = clasificar_pagina(codigos, pagina)
            clips = clip_pagina(codigos, pagina, layout)

            for codigo in codigos:
                clip = clips.get(codigo.codigo)
                if not clip:
                    continue
                calidad = calidad_candidato(codigo, clip, layout, pagina)
                prev = mejores.get(codigo.codigo)
                if prev is None or calidad > prev.calidad:
                    mejores[codigo.codigo] = Candidato(
                        codigo=codigo.codigo,
                        clip=clip,
                        pagina_num=num,
                        calidad=calidad,
                    )

        guardadas = 0
        for cand in mejores.values():
            pagina = doc.load_page(cand.pagina_num)
            if guardar(cand.codigo, cand.clip, pagina):
                guardadas += 1
    finally:
        doc.close()

    hechos = {p.stem for p in OUTPUT_DIR.glob("*.png")} & set(codigos_objetivo)
    faltantes = sorted(set(codigos_objetivo) - hechos)
    print(f"Actualizadas: {guardadas} | Objetivo: {len(codigos_objetivo)} | Hechas: {len(hechos)}")
    if faltantes:
        print(f"Faltantes ({len(faltantes)}): {', '.join(faltantes[:30])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
