"""
╔══════════════════════════════════════════════════════════════════════╗
║  EXTRACTOR DE FOTOS DE CATÁLOGO BETTERWARE CON GEMINI VISION API   ║
║  Usa IA semántica para detectar y recortar productos del PDF       ║
║  SDK: google-genai (nueva librería oficial)                        ║
╚══════════════════════════════════════════════════════════════════════╝

Dependencias:
    pip install pdf2image Pillow google-genai

Requisitos externos:
    - Poppler para Windows (ya instalado en tu ruta)
    - API Key de Google Gemini (variable de entorno GEMINI_API_KEY)

Uso:
    set GEMINI_API_KEY=tu_api_key_aqui
    python extraer_fotos_gemini.py
"""

import os
import sys
import json
import re
import time
import logging
from pathlib import Path
from io import BytesIO

from pdf2image import convert_from_path
from PIL import Image
from google import genai
from google.genai import types

# ─────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────────

# Rutas
CATALOGO_PDF = Path(__file__).parent / "catalogo.pdf"
CARPETA_SALIDA = Path(__file__).parent / "fotos_catalogo"
POPPLER_PATH = r"C:\Users\pibed\Downloads\Release-26.02.0-0\poppler-26.02.0\Library\bin"

# Parámetros de rasterización
DPI_RENDERIZADO = 300   # Alta resolución para recortes nítidos
DPI_ENVIO_GEMINI = 150  # Resolución reducida para enviar a la API (ahorra tokens)

# Rate limiting para la API gratuita (15 RPM)
PAUSA_ENTRE_PAGINAS = 4  # segundos

# Modelos a intentar (en orden de preferencia)
MODELOS_GEMINI = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-2.0-flash-lite",
]

# Retry con backoff exponencial para errores 429
MAX_REINTENTOS = 5
BACKOFF_BASE = 30  # segundos base para el primer reintento

# Páginas a procesar (None = todas, o especificar rango como (1, 10))
RANGO_PAGINAS = (5, 8)


# ─────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            Path(__file__).parent / "extraccion_log.txt",
            encoding="utf-8",
            mode="w",
        ),
    ],
)
log = logging.getLogger("extractor")

# ─────────────────────────────────────────────────────────────────────
# PROMPT PARA GEMINI
# ─────────────────────────────────────────────────────────────────────

PROMPT_DETECCION = """Eres un detector de productos de un catálogo de ventas Betterware.

TAREA: Analiza esta página del catálogo e identifica TODOS los productos visibles.

Para CADA producto encontrado, devuelve:
1. "codigo": El código numérico del producto (número de 5 dígitos que aparece cerca de cada producto). Si no puedes leer el código con certeza, usa "DESCONOCIDO".
2. "caja": Las coordenadas del recuadro que encierra SOLAMENTE la fotografía/imagen del producto (NO incluyas texto, precios ni descripciones). Formato: [ymin, xmin, ymax, xmax] donde cada valor es un entero de 0 a 1000 (coordenadas normalizadas).

REGLAS ESTRICTAS:
- El recuadro debe encerrar SOLO la imagen/foto del producto, no el texto descriptivo.
- Las coordenadas están normalizadas: 0 = borde superior/izquierdo, 1000 = borde inferior/derecho.
- Si hay variantes de color del mismo producto, agrúpalas en UN solo recuadro.
- Si una página no tiene productos (es portada, índice, etc.), devuelve una lista vacía.
- NO inventes productos que no existan en la imagen.

FORMATO DE RESPUESTA (JSON puro, sin markdown, sin ```):
[
  {"codigo": "12345", "caja": [100, 50, 400, 500]},
  {"codigo": "67890", "caja": [450, 50, 800, 500]}
]

Si no hay productos en la página:
[]"""


# ─────────────────────────────────────────────────────────────────────
# FUNCIONES PRINCIPALES
# ─────────────────────────────────────────────────────────────────────


def configurar_gemini() -> tuple[genai.Client, str]:
    """
    Configura el cliente de Google GenAI y busca un modelo disponible.
    Retorna (client, nombre_modelo).
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        log.error(
            "No se encontró GEMINI_API_KEY en las variables de entorno.\n"
            "Configúrala con: set GEMINI_API_KEY=tu_clave_aqui"
        )
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # Probar cada modelo hasta encontrar uno que funcione
    modelo_elegido = None
    for modelo_nombre in MODELOS_GEMINI:
        try:
            log.info(f"Probando modelo: {modelo_nombre}...")
            # Hacer una llamada de prueba mínima (solo texto)
            respuesta = client.models.generate_content(
                model=modelo_nombre,
                contents="Responde solo: OK",
                config=types.GenerateContentConfig(
                    max_output_tokens=10,
                ),
            )
            if respuesta.text:
                modelo_elegido = modelo_nombre
                log.info(f"✔ Modelo disponible: {modelo_elegido}")
                break
        except Exception as e:
            log.warning(f"✖ Modelo {modelo_nombre} no disponible: {e}")
            continue

    if not modelo_elegido:
        log.error(
            "Ningún modelo de Gemini está disponible.\n"
            "Posibles causas:\n"
            "  1. Agotaste tu cuota diaria gratuita (se reinicia a medianoche PT)\n"
            "  2. Tu API key es inválida\n"
            "  3. Tu región no tiene acceso al free tier\n"
            "Visita: https://aistudio.google.com/apikey para verificar."
        )
        sys.exit(1)

    # Pausa post-prueba para no desperdiciar rate limit
    time.sleep(2)
    return client, modelo_elegido


def llamar_gemini_con_retry(
    client: genai.Client,
    modelo: str,
    imagen_pil: Image.Image,
) -> str | None:
    """
    Envía la imagen a Gemini con reintentos automáticos para errores 429.
    Usa backoff exponencial: 30s, 60s, 120s, 240s, 480s.
    Retorna el texto de la respuesta o None si falla.
    """
    for intento in range(MAX_REINTENTOS):
        try:
            respuesta = client.models.generate_content(
                model=modelo,
                contents=[PROMPT_DETECCION, imagen_pil],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=4096,
                ),
            )

            if respuesta.text:
                return respuesta.text
            else:
                log.warning("  ⚠ Gemini devolvió respuesta vacía.")
                return None

        except Exception as e:
            error_str = str(e)

            # Detectar error 429 (rate limit / quota)
            if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                espera = BACKOFF_BASE * (2 ** intento)

                # Intentar extraer el tiempo de espera sugerido por la API
                retry_match = re.search(r"retry\s+in\s+([\d.]+)s", error_str, re.IGNORECASE)
                if retry_match:
                    espera = max(espera, float(retry_match.group(1)) + 5)

                log.warning(
                    f"  ⏳ Rate limit (429). Reintento {intento + 1}/{MAX_REINTENTOS} "
                    f"en {espera:.0f}s..."
                )
                time.sleep(espera)
                continue

            # Otros errores: no reintentar
            log.error(f"  ✖ Error de Gemini (no recuperable): {e}")
            return None

    log.error(f"  ✖ Se agotaron los {MAX_REINTENTOS} reintentos por rate limit.")
    return None


def rasterizar_pagina(pdf_path: Path, numero_pagina: int, dpi: int) -> Image.Image:
    """
    Rasteriza UNA sola página del PDF para manejar bien la memoria.
    Usa first_page y last_page de pdf2image para no cargar todo el PDF.
    """
    imagenes = convert_from_path(
        str(pdf_path),
        dpi=dpi,
        first_page=numero_pagina,
        last_page=numero_pagina,
        poppler_path=POPPLER_PATH,
        fmt="png",
        thread_count=4,
    )
    return imagenes[0]


def obtener_total_paginas(pdf_path: Path) -> int:
    """Obtiene el total de páginas del PDF usando pdf2image."""
    from pdf2image import pdfinfo_from_path

    info = pdfinfo_from_path(str(pdf_path), poppler_path=POPPLER_PATH)
    return info["Pages"]


def redimensionar_para_api(
    imagen: Image.Image, dpi_objetivo: int, dpi_original: int
) -> Image.Image:
    """
    Crea una versión más pequeña de la imagen para enviar a la API.
    Esto reduce el consumo de tokens sin perder calidad en el recorte final.
    """
    factor = dpi_objetivo / dpi_original
    nuevo_ancho = int(imagen.width * factor)
    nuevo_alto = int(imagen.height * factor)
    return imagen.resize((nuevo_ancho, nuevo_alto), Image.LANCZOS)


def parsear_respuesta_gemini(respuesta_texto: str) -> list[dict]:
    """
    Parsea la respuesta de Gemini extrayendo el JSON.
    Maneja casos donde Gemini agrega markdown u otros artefactos.
    """
    texto = respuesta_texto.strip()

    # Quitar bloques de código markdown si los hay
    if "```" in texto:
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", texto, re.DOTALL)
        if match:
            texto = match.group(1).strip()

    # Intentar parsear directamente
    try:
        datos = json.loads(texto)
        if isinstance(datos, list):
            return datos
        elif isinstance(datos, dict) and "productos" in datos:
            return datos["productos"]
        else:
            log.warning(f"Respuesta JSON inesperada: {type(datos)}")
            return []
    except json.JSONDecodeError:
        # Último intento: buscar un array JSON en el texto
        match = re.search(r"\[.*\]", texto, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        log.warning(f"No se pudo parsear la respuesta de Gemini:\n{texto[:500]}")
        return []


def desnormalizar_coordenadas(
    caja: list[int], ancho_px: int, alto_px: int
) -> tuple[int, int, int, int] | None:
    """
    Convierte coordenadas normalizadas (0-1000) a píxeles reales.
    Formato entrada: [ymin, xmin, ymax, xmax]
    Formato salida:  (left, upper, right, lower) para PIL.crop()
    """
    ymin, xmin, ymax, xmax = caja

    left = int((xmin / 1000) * ancho_px)
    upper = int((ymin / 1000) * alto_px)
    right = int((xmax / 1000) * ancho_px)
    lower = int((ymax / 1000) * alto_px)

    # Clamp para evitar coordenadas fuera de rango
    left = max(0, min(left, ancho_px))
    upper = max(0, min(upper, alto_px))
    right = max(0, min(right, ancho_px))
    lower = max(0, min(lower, alto_px))

    # Asegurar que el recuadro tenga dimensiones válidas
    if right <= left or lower <= upper:
        return None

    return (left, upper, right, lower)


def recortar_y_guardar(
    imagen_hires: Image.Image,
    codigo: str,
    caja: list[int],
    carpeta: Path,
) -> bool:
    """
    Recorta el producto de la imagen en alta resolución y lo guarda como PNG.
    Retorna True si se guardó correctamente.
    """
    coords = desnormalizar_coordenadas(caja, imagen_hires.width, imagen_hires.height)
    if coords is None:
        log.warning(f"  ⚠ Código {codigo}: coordenadas inválidas {caja}")
        return False

    left, upper, right, lower = coords
    ancho = right - left
    alto = lower - upper

    # Filtrar recortes demasiado pequeños (probablemente errores)
    if ancho < 50 or alto < 50:
        log.warning(
            f"  ⚠ Código {codigo}: recorte muy pequeño ({ancho}x{alto}px), ignorado"
        )
        return False

    recorte = imagen_hires.crop(coords)

    # Guardar como PNG con compresión optimizada
    ruta_salida = carpeta / f"{codigo}.png"
    recorte.save(str(ruta_salida), format="PNG", optimize=True)
    log.info(f"  ✔ {codigo}.png guardado ({ancho}x{alto}px)")
    return True


# ─────────────────────────────────────────────────────────────────────
# BUCLE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────


def main():
    log.info("=" * 60)
    log.info("EXTRACTOR DE FOTOS - CATÁLOGO BETTERWARE")
    log.info("Usando SDK: google-genai (nueva API oficial)")
    log.info("=" * 60)

    # Validaciones iniciales
    if not CATALOGO_PDF.exists():
        log.error(f"No se encontró el PDF: {CATALOGO_PDF}")
        sys.exit(1)

    CARPETA_SALIDA.mkdir(exist_ok=True)
    log.info(f"PDF: {CATALOGO_PDF}")
    log.info(f"Salida: {CARPETA_SALIDA}")

    # Configurar Gemini (prueba modelos hasta encontrar uno activo)
    client, modelo_nombre = configurar_gemini()

    # Obtener total de páginas
    total_paginas = obtener_total_paginas(CATALOGO_PDF)
    log.info(f"Total de páginas en el PDF: {total_paginas}")

    # Determinar rango de páginas a procesar
    if RANGO_PAGINAS:
        inicio, fin = RANGO_PAGINAS
        paginas = range(inicio, min(fin + 1, total_paginas + 1))
    else:
        paginas = range(1, total_paginas + 1)

    log.info(f"Procesando páginas: {paginas.start} a {paginas.stop - 1}")
    log.info("-" * 60)

    # Contadores
    total_productos_extraidos = 0
    total_errores = 0
    paginas_sin_productos = 0
    codigos_extraidos = set()

    for num_pagina in paginas:
        log.info(f"\n{'─' * 40}")
        log.info(f"📄 Página {num_pagina}/{total_paginas}")
        log.info(f"{'─' * 40}")

        try:
            # ── PASO 1: Rasterizar la página en alta resolución ──
            log.info(f"  Rasterizando a {DPI_RENDERIZADO} DPI...")
            imagen_hires = rasterizar_pagina(CATALOGO_PDF, num_pagina, DPI_RENDERIZADO)
            log.info(f"  Imagen HiRes: {imagen_hires.width}x{imagen_hires.height}px")

            # ── PASO 2: Crear versión reducida para la API ──
            imagen_api = redimensionar_para_api(
                imagen_hires, DPI_ENVIO_GEMINI, DPI_RENDERIZADO
            )
            log.info(f"  Imagen API: {imagen_api.width}x{imagen_api.height}px")

            # ── PASO 3: Enviar a Gemini con retry automático ──
            log.info("  Enviando a Gemini Vision...")
            respuesta_texto = llamar_gemini_con_retry(client, modelo_nombre, imagen_api)

            if not respuesta_texto:
                log.warning("  ⚠ Sin respuesta de Gemini. Saltando página.")
                total_errores += 1
                time.sleep(PAUSA_ENTRE_PAGINAS)
                continue

            # ── PASO 4: Parsear respuesta ──
            productos = parsear_respuesta_gemini(respuesta_texto)
            log.info(f"  Productos detectados: {len(productos)}")

            if not productos:
                log.info("  (página sin productos o de contenido editorial)")
                paginas_sin_productos += 1
                time.sleep(PAUSA_ENTRE_PAGINAS)
                continue

            # ── PASO 5: Recortar y guardar cada producto ──
            for producto in productos:
                try:
                    codigo = str(producto.get("codigo", "")).strip()
                    caja = producto.get("caja", [])

                    # Validar código
                    if not codigo or codigo == "DESCONOCIDO":
                        log.warning(f"  ⚠ Producto sin código válido: {producto}")
                        total_errores += 1
                        continue

                    # Validar caja
                    if (
                        not isinstance(caja, list)
                        or len(caja) != 4
                        or not all(isinstance(v, (int, float)) for v in caja)
                    ):
                        log.warning(f"  ⚠ Código {codigo}: caja inválida {caja}")
                        total_errores += 1
                        continue

                    # Recortar de la imagen en alta resolución
                    exito = recortar_y_guardar(
                        imagen_hires, codigo, caja, CARPETA_SALIDA
                    )
                    if exito:
                        total_productos_extraidos += 1
                        codigos_extraidos.add(codigo)

                except Exception as e:
                    log.error(f"  ✖ Error procesando producto {producto}: {e}")
                    total_errores += 1

            # Liberar memoria de las imágenes grandes
            del imagen_hires
            del imagen_api

        except Exception as e:
            log.error(f"  ✖ Error fatal en página {num_pagina}: {e}")
            total_errores += 1

        # ── Rate limiting ──
        if num_pagina < paginas.stop - 1:
            log.info(f"  ⏳ Pausa de {PAUSA_ENTRE_PAGINAS}s (rate limit)...")
            time.sleep(PAUSA_ENTRE_PAGINAS)

    # ─────────────────────────────────────────────────────────────────
    # RESUMEN FINAL
    # ─────────────────────────────────────────────────────────────────
    log.info("\n" + "=" * 60)
    log.info("RESUMEN DE EXTRACCIÓN")
    log.info("=" * 60)
    log.info(f"  Modelo usado:          {modelo_nombre}")
    log.info(f"  Páginas procesadas:    {len(paginas)}")
    log.info(f"  Páginas sin productos: {paginas_sin_productos}")
    log.info(f"  Productos extraídos:   {total_productos_extraidos}")
    log.info(f"  Códigos únicos:        {len(codigos_extraidos)}")
    log.info(f"  Errores/warnings:      {total_errores}")
    log.info(f"  Carpeta de salida:     {CARPETA_SALIDA}")
    log.info("=" * 60)

    # Guardar log de códigos extraídos
    log_codigos = Path(__file__).parent / "codigos_extraidos.txt"
    with open(log_codigos, "w", encoding="utf-8") as f:
        for codigo in sorted(codigos_extraidos):
            f.write(f"{codigo}\n")
    log.info(f"  Lista de códigos guardada en: {log_codigos}")


if __name__ == "__main__":
    main()
