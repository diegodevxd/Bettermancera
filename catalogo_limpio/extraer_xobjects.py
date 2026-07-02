"""
Extracción de imágenes de catálogo PDF usando PyMuPDF (fitz).

Estrategia:
- Extrae XObjects de imagen nativos de cada página.
- Filtra por tamaño (descarta <100x100 y >80% de la página).
- Reconstruye tiles: agrupa imágenes pequeñas adyacentes en un solo recorte.
- Match por cercanía espacial con códigos de 5 dígitos del texto.
- Guarda cada imagen válida como [codigo].png.
"""

import os
import re
import gc
import fitz

PDF_PATH = "catalogo.pdf"
OUTPUT_DIR = "fotos_catalogo"
MIN_SIZE = 100          # px mínimos (ancho y alto)
MAX_PAGE_RATIO = 0.80   # descarta fondos >80% de la página
MAX_MATCH_DIST = 100    # distancia máxima en px para asociar código

RE_CODE = re.compile(r"\b\d{5}\b")


def get_code_blocks(page):
    """Devuelve lista de (codigo, bbox) encontrados en el texto de la página."""
    codes = []
    try:
        blocks = page.get_text("blocks")
    except Exception:
        return codes

    for b in blocks:
        # block = (x0, y0, x1, y1, text, block_no, block_type)
        if len(b) < 5:
            continue
        text = b[4]
        for m in RE_CODE.finditer(text):
            code = m.group(0)
            # bbox del bloque de texto
            block_bbox = fitz.Rect(b[0], b[1], b[2], b[3])
            codes.append((code, block_bbox))
    return codes


def distance_point_to_rect(px, py, rect):
    """Distancia euclidiana mínima de un punto a un rectángulo."""
    dx = max(rect.x0 - px, 0, px - rect.x1)
    dy = max(rect.y0 - py, 0, py - rect.y1)
    return (dx * dx + dy * dy) ** 0.5


def find_nearest_code(img_rect, code_blocks):
    """Busca el código de 5 dígitos más cercano a la imagen."""
    cx = (img_rect.x0 + img_rect.x1) / 2
    cy = (img_rect.y0 + img_rect.y1) / 2
    best_code = None
    best_dist = float("inf")

    for code, code_bbox in code_blocks:
        d = distance_point_to_rect(cx, cy, code_bbox)
        if d < best_dist:
            best_dist = d
            best_code = code

    if best_code is not None and best_dist <= MAX_MATCH_DIST:
        return best_code, best_dist
    return None, None


def extract_image_objects(page, doc):
    """
    Extrae todos los XObject de imagen de la página con su bbox.
    Devuelve lista de dict: {xref, bbox, width, height, img_bytes}
    """
    images = []
    page_rect = page.rect
    page_area = page_rect.width * page_rect.height

    try:
        raw_images = page.get_images(full=True)
    except Exception:
        return images

    for img_info in raw_images:
        xref = img_info[0]
        try:
            bbox = page.get_image_bbox(img_info)
        except Exception:
            continue

        if bbox.is_empty or bbox.is_infinite:
            continue

        w = bbox.width
        h = bbox.height

        # Filtro de tamaño mínimo
        if w < MIN_SIZE or h < MIN_SIZE:
            continue

        # Filtro de tamaño máximo (fondos)
        img_area = w * h
        if img_area > page_area * MAX_PAGE_RATIO:
            continue

        # Extraer bytes de la imagen
        try:
            pix = fitz.Pixmap(doc, xref)
            img_bytes = pix.tobytes("png")
            img_w = pix.width
            img_h = pix.height
            pix = None
        except Exception:
            continue

        images.append({
            "xref": xref,
            "bbox": bbox,
            "width": img_w,
            "height": img_h,
            "bytes": img_bytes,
        })

    return images


def cluster_tiles(images, gap_threshold=20):
    """
    Reconstrucción de tiles: agrupa imágenes pequeñas adyacentes
    que podrían formar una sola imagen compuesta.

    Devuelve lista de grupos. Cada grupo es una lista de imágenes.
    Las imágenes que no se agrupan se devuelven como grupos de un solo elemento.
    """
    if not images:
        return []

    clusters = []
    used = [False] * len(images)

    for i, img_a in enumerate(images):
        if used[i]:
            continue
        cluster = [img_a]
        used[i] = True

        # Buscar imágenes adyacentes
        for j in range(i + 1, len(images)):
            if used[j]:
                continue
            img_b = images[j]
            for c_img in cluster:
                if are_adjacent(c_img["bbox"], img_b["bbox"], gap_threshold):
                    cluster.append(img_b)
                    used[j] = True
                    break

        clusters.append(cluster)

    return clusters


def are_adjacent(rect_a, rect_b, gap=20):
    """Verifica si dos rectángulos están adyacentes dentro de un gap."""
    # Expandir rect_a por el gap y ver si intersecta con rect_b
    expanded = fitz.Rect(
        rect_a.x0 - gap,
        rect_a.y0 - gap,
        rect_a.x1 + gap,
        rect_a.y1 + gap,
    )
    if expanded.intersects(rect_b):
        # Verificar que no haya demasiado traslape (no son la misma imagen)
        inter = expanded & rect_b
        if inter.is_empty:
            return True
        # Si el traslape es pequeño relativo a b, son adyacentes
        if inter.get_area() < 0.5 * rect_b.get_area():
            return True
    return False


def render_cluster(page, cluster):
    """
    Renderiza el área que cubre un cluster de imágenes como un solo recorte HD.
    Usa get_pixmap con clip sobre la unión de los bboxes.
    """
    if not cluster:
        return None

    # Calcular bounding box de la unión
    x0 = min(img["bbox"].x0 for img in cluster)
    y0 = min(img["bbox"].y0 for img in cluster)
    x1 = max(img["bbox"].x1 for img in cluster)
    y1 = max(img["bbox"].y1 for img in cluster)
    union_rect = fitz.Rect(x0, y0, x1, y1)

    # Renderizar esa área en alta resolución
    matrix = fitz.Matrix(3, 3)
    pix = page.get_pixmap(clip=union_rect, matrix=matrix)
    img_bytes = pix.tobytes("png")
    pix = None
    return img_bytes, union_rect


def save_image(img_bytes, code, output_dir):
    """Guarda los bytes de imagen como [codigo].png."""
    path = os.path.join(output_dir, f"{code}.png")
    with open(path, "wb") as f:
        f.write(img_bytes)


def process_page(page, doc, output_dir, seen_codes):
    """Procesa una sola página: extrae, filtra, agrupa y asocia imágenes."""
    # 1. Extraer objetos de imagen
    images = extract_image_objects(page, doc)

    if not images:
        return 0

    # 2. Obtener códigos de texto
    code_blocks = get_code_blocks(page)

    # 3. Clusterizar tiles
    clusters = cluster_tiles(images)

    # 4. Para cada cluster, renderizar y asociar código
    saved = 0
    for cluster in clusters:
        # Renderizar el cluster como un solo recorte
        result = render_cluster(page, cluster)
        if result is None:
            continue
        img_bytes, cluster_rect = result

        # Buscar código cercano al centro del cluster
        best_code = None
        best_dist = float("inf")
        for code, code_bbox in code_blocks:
            cx = (cluster_rect.x0 + cluster_rect.x1) / 2
            cy = (cluster_rect.y0 + cluster_rect.y1) / 2
            d = distance_point_to_rect(cx, cy, code_bbox)
            if d < best_dist:
                best_dist = d
                best_code = code

        if best_code and best_dist <= MAX_MATCH_DIST:
            if best_code in seen_codes:
                continue
            seen_codes.add(best_code)
            save_image(img_bytes, best_code, output_dir)
            saved += 1
            print(f"  + {best_code} (dist:{best_dist:.0f}, tiles:{len(cluster)})")

        # Liberar memoria
        del img_bytes

    # Liberar imágenes extraídas
    for img in images:
        del img["bytes"]
    del images, clusters
    gc.collect()
    return saved


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(PDF_PATH):
        print(f"[ERROR] No se encuentra {PDF_PATH}")
        return

    doc = fitz.open(PDF_PATH)
    total_pages = len(doc)
    print(f"PDF: {total_pages} páginas\n")

    seen_codes = set()
    total_saved = 0

    for page_num in range(total_pages):
        page = doc[page_num]
        print(f"Página {page_num + 1}/{total_pages}...", end=" ")
        saved = process_page(page, doc, OUTPUT_DIR, seen_codes)
        total_saved += saved
        print(f"({saved} guardadas)")

        # Liberar página
        del page
        gc.collect()

    doc.close()
    print(f"\nListo. Total imágenes guardadas: {total_saved}")


if __name__ == "__main__":
    main()
