-- Políticas seguras para el bucket público de fotos de productos.
-- Ejecutar en Supabase SQL Editor.
-- Las subidas/administración deben hacerse con service_role (por ejemplo,
-- desde el script local subir_imagenes.py usando SUPABASE_SERVICE_ROLE_KEY).

-- Asegurar que el bucket existe y es público (solo lectura directa)
INSERT INTO storage.buckets (id, name, public)
VALUES ('productos_fotos', 'productos_fotos', true)
ON CONFLICT (id) DO UPDATE SET public = true;

-- Habilitar RLS en storage.objects (si no lo está)
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Eliminar políticas anteriores conflictivas para este bucket
DROP POLICY IF EXISTS "anon sube productos_fotos" ON storage.objects;
DROP POLICY IF EXISTS "anon lee productos_fotos" ON storage.objects;
DROP POLICY IF EXISTS "anon actualiza productos_fotos" ON storage.objects;

-- Política para permitir lectura pública (imágenes del catálogo)
CREATE POLICY "anon lee productos_fotos"
ON storage.objects FOR SELECT TO anon
USING (bucket_id = 'productos_fotos');

-- No se permite INSERT/UPDATE/DELETE anónimo en este bucket.
-- Si en el futuro se necesita que usuarios autenticados suban archivos,
-- crear políticas específicas para authenticated con restricciones de propiedad.
