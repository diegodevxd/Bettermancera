# Cómo actualizar el catálogo cada mes

La tienda muestra los productos como **tarjetas** (foto, nombre, precio y
botón de carrito). Para actualizarla cada mes ya no hay que escribir SQL ni
subir fotos una por una: todo se hace desde el extractor asistido.

El rectángulo que dibujas sobre cada producto en el extractor **es la foto
de su tarjeta** — al subir, se recorta, se comprime y se publica sola.

## Configuración (solo la primera vez)

1. Entra al panel de Supabase → **Project Settings → API keys** y copia la
   **service_role key** (la secreta, no la pública).
2. En esta carpeta (`catalogo_limpio/`) crea un archivo llamado `.env` con
   estas dos líneas (pega tu llave real):

   ```
   SUPABASE_URL=https://lijzftjgevwnjorpycxa.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=aqui-va-tu-service-role-key
   ```

   Ese archivo NO se sube a git (ya está en .gitignore). No lo compartas.
3. Si nunca lo has instalado: `pip install pymupdf pillow`

## Cada mes, 2 pasos

### 1. Convertir el PDF nuevo a imágenes

Guarda el catálogo nuevo como `catalogo.pdf` en esta carpeta y corre:

```
python pdf_a_paginas.py
```

Eso llena `paginas_catalogo/` con una imagen por página (lo que el
extractor usa para trabajar).

### 2. Marcar y subir los productos

```
python extractor_asistido.py
```

1. Botón **"Leer catálogo PDF"**: llena la lista de la derecha con los
   productos del PDF nuevo (código, nombre, precio y página) — detección
   automática, ~99% de precisión en precios.
2. **Doble-clic** en un producto de la lista → salta a su página.
3. **Arrastra un rectángulo** alrededor de la foto del producto (ese
   recorte será la foto de la tarjeta en la tienda). En la ventanita el
   código, nombre y precio ya vienen llenos — revisa el precio, agrega el
   de oferta si tiene, y Enter.
4. La lista muestra cuáles llevas (✓) y cuáles faltan ("Solo pendientes"
   para filtrar). Puedes hacerlo en varias sesiones, nada se pierde.
5. Botón **"Subir a Supabase"**: sube nombres/precios a la base de datos
   y las fotos recortadas al almacenamiento, todo en uno. Los productos
   aparecen en la tienda al instante, sin tocar código ni redeploy.

## Notas

- Los productos del mes anterior que no marques siguen existiendo en la
  base de datos (los pedidos viejos los necesitan), solo que con su foto
  y precio anteriores. Si un producto sale del catálogo y no quieres que
  se venda, avísale al programador para ocultarlo.
- Las fotos pueden tardar unos minutos en refrescar para quien ya había
  visitado la página (caché). Los precios se actualizan al instante.
- El archivo `productos_sync_FECHA.sql` que se genera al subir es solo un
  respaldo/bitácora; no hay que hacer nada con él.
- El botón "Subir páginas" y `subir_paginas.py` son de la versión
  "catálogo tipo libro" (guardada en `respaldo_flipbook/` por si algún
  día se quiere volver a usar); para las tarjetas no se necesitan.
