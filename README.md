# BetterMancera — Tienda Web y Extractor de Catálogo PDF

Tienda y catálogo web en producción con carrito de compras, procesamiento de pagos con tarjeta y un pipeline automatizado en Python para extraer productos, precios y fotografías desde catálogos PDF mensuales.

## Arquitectura

- **Catálogo y tienda web (`index.html`, `tienda.js`):** Interfaz responsiva con búsqueda, vista por categorías, carrito persistente, flujo de pago con Stripe Elements y políticas legales (términos y aviso de privacidad).
- **Pagos seguros (`Stripe` + `Supabase Edge Functions`):** Creación de `PaymentIntents` en el servidor mediante Edge Functions en Deno (`STRIPE_SECRET_KEY` como variable de entorno en Supabase), evitando exponer llaves privadas en el cliente.
- **Base de datos y almacenamiento (`Supabase`):** Catálogo de productos, pedidos y almacenamiento optimizado de imágenes en Supabase Storage.
- **Pipeline de extracción PDF (`catalogo/`, `catalogo_limpio/`):** Scripts en Python para renderizar páginas del catálogo mensual, detectar códigos y precios desde la capa de texto (con respaldo de OCR / visión), recortar automáticamente las fotografías de cada producto y publicarlas en Supabase Storage.

## Stack

- **Frontend:** HTML5, Tailwind CSS, JavaScript vanilla, Stripe.js
- **Backend / BaaS:** Supabase (PostgreSQL, Storage, Edge Functions)
- **Automatización / Datos:** Python, PyMuPDF, herramientas de OCR y visión

## Configuración

1. Copia `config.example.js` a `config.js` (excluido en `.gitignore`) para desarrollo local:

   ```js
   window.BM_CONFIG = {
     SUPABASE_URL: 'https://TU_PROYECTO.supabase.co',
     SUPABASE_KEY: 'TU_PUBLISHABLE_O_ANON_KEY',
     STRIPE_PUBLISHABLE_KEY: 'pk_...',
     STRIPE_EDGE_FUNCTION: 'https://TU_PROYECTO.supabase.co/functions/v1/swift-endpoint',
   };
   ```

2. En Vercel, define `SUPABASE_URL`, `SUPABASE_KEY`, `STRIPE_PUBLISHABLE_KEY` y `STRIPE_EDGE_FUNCTION` en **Environment Variables** para que `scripts/build-config.js` genere `config.js` en tiempo de compilación.
3. Para ejecutar los scripts de carga en Python, exporta `SUPABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY` en tu terminal sin guardarlas en el repositorio.
