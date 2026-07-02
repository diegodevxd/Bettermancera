"""Segunda pasada: extrae productos faltantes con filtros más permisivos."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import fitz

from extractor_fotos_v2 import (
    OUTPUT_DIR,
    SQL_PATH,
    ImagenPagina,
    cargar_codigos_sql,
    emparejar,
    extraer_codigos,
    guardar_imagen,
)

PDF_GLOB = "*.pdf"
MAX_BG_AREA_RATIO_RELAXED = 0.55


def extraer_imagenes_relajado(pagina: fitz.Page):
    from extractor_fotos_v2 import ImagenPagina, MIN_IMAGE_BYTES, MIN_BBOX_SIZE

    imagenes = []
    pw, ph = pagina.rect.width, pagina.rect.height
    area_pag = pw * ph

    for idx, info in enumerate(pagina.get_image_info(xrefs=True)):
        size_bytes = int(info.get("size", 0))
        if size_bytes < MIN_IMAGE_BYTES:
            continue
        bbox_raw = info.get("bbox")
        if not bbox_raw:
            continue
        bbox = fitz.Rect(bbox_raw)
        if bbox.width < MIN_BBOX_SIZE or bbox.height < MIN_BBOX_SIZE:
            continue
        if area_pag > 0 and (bbox.width * bbox.height) / area_pag > MAX_BG_AREA_RATIO_RELAXED:
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


def main() -> int:
    pdf_path = next(Path(".").glob(PDF_GLOB), None)
    if not pdf_path:
        print("No PDF")
        return 1

    codigos_sql = cargar_codigos_sql(SQL_PATH)
    existentes = {p.stem for p in OUTPUT_DIR.glob("*.png")}
    faltantes = sorted(codigos_sql - existentes)
    if not faltantes:
        print("Todos los códigos ya tienen imagen.")
        return 0

    print(f"Reintentando {len(faltantes)} códigos faltantes...\n")
    faltantes_set = set(faltantes)
    resueltos: set[str] = set()

    doc = fitz.open(pdf_path)
    try:
        for num in range(len(doc)):
            pagina = doc.load_page(num)
            codigos = [
                c
                for c in extraer_codigos(pagina, faltantes_set - resueltos)
                if c.codigo in faltantes_set
            ]
            if not codigos:
                continue

            imagenes = extraer_imagenes_relajado(pagina)
            if not imagenes:
                continue

            pares = emparejar(codigos, imagenes)
            if not pares:
                continue

            print(f"Pág {num+1}: {len(pares)} recuperados")
            for codigo_obj, imagen, _ in pares:
                if guardar_imagen(pagina, codigo_obj.codigo, imagen, OUTPUT_DIR):
                    resueltos.add(codigo_obj.codigo)
    finally:
        doc.close()

    print(f"\nRecuperados: {len(resueltos)}")
    print("Siguen faltando:", sorted(faltantes_set - resueltos))
    return 0


if __name__ == "__main__":
    sys.exit(main())
