import fitz  # PyMuPDF
import re
import ollama

pdf_path = "Catálogo Julio 2026.pdf"
documento = fitz.open(pdf_path)

regex_codigo = r'\b(2[0-9]{4})\b'
regex_precio = r'\$([0-9,]+\.?[0-9]*)'

productos_encontrados = []
codigos_procesados = set()

print("Iniciando escaneo del catálogo con Ollama. Esto puede tardar un par de minutos...")

for num_pagina in range(len(documento)):
    pagina = documento.load_page(num_pagina)
    texto = pagina.get_text("text")
    lineas = texto.split('\n')
    
    for i, linea in enumerate(lineas):
        match_codigo = re.search(regex_codigo, linea)
        if match_codigo:
            codigo = match_codigo.group(1)
            
            # Evitar productos duplicados en distintas páginas
            if codigo in codigos_procesados:
                continue
            codigos_procesados.add(codigo)
            
            # Tomar 4 líneas antes y 6 después para darle contexto a la IA
            inicio = max(0, i - 4)
            fin = min(len(lineas), i + 6)
            contexto_cercano = " ".join(lineas[inicio:fin])
            
            # Buscar los precios matemáticamente
            precios = re.findall(regex_precio, contexto_cercano)
            precio_regular = 0
            precio_oferta = 0
            if len(precios) >= 2:
                p1 = float(precios[0].replace(',', ''))
                p2 = float(precios[1].replace(',', ''))
                precio_regular = max(p1, p2)
                precio_oferta = min(p1, p2)
            elif len(precios) == 1:
                precio_regular = float(precios[0].replace(',', ''))
                precio_oferta = precio_regular
                
            # Prompt estricto para Qwen
            prompt = f"Extrae SOLO el nombre del producto Betterware con código {codigo} de este texto. No agregues saludos, ni puntos, ni comillas, ni explicaciones, solo el nombre:\n\n{contexto_cercano}"
            
            try:
                # Nota: Cambia 'qwen' por 'gemma' o la versión exacta que tengas corriendo (ej. 'qwen:7b')
                respuesta = ollama.chat(model='llama3.1', messages=[
                    {'role': 'user', 'content': prompt}
                ])
                nombre_real = respuesta['message']['content'].strip()
                # Limpiar comillas simples o dobles para no romper la sintaxis SQL
                nombre_real = nombre_real.replace("'", "").replace('"', '') 
            except Exception as e:
                nombre_real = f"Producto {codigo}"
                print(f"Error con el código {codigo}: {e}")

            print(f"Listo: {codigo} - {nombre_real} (Regular: ${precio_regular} | Oferta: ${precio_oferta})")
            
            productos_encontrados.append({
                "codigo": codigo,
                "nombre": nombre_real,
                "precio_regular": precio_regular,
                "precio_oferta": precio_oferta
            })

# Guardar el archivo SQL listo para Vercel/Supabase
with open("productos_completos_ia.sql", "w", encoding="utf-8") as f:
    f.write("INSERT INTO public.productos (codigo, nombre, precio_regular, precio_oferta) VALUES\n")
    valores = [f"('{p['codigo']}', '{p['nombre']}', {p['precio_regular']}, {p['precio_oferta']})" for p in productos_encontrados]
    f.write(",\n".join(valores) + ";")

print(f"\n¡Finalizado! Se guardaron {len(productos_encontrados)} productos en 'productos_completos_ia.sql'")