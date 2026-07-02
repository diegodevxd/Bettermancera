import fitz
import re
import json

PDF_PATH = "catalogo.pdf"
SQL_PATH = "productos.sql"
OUT_JSON = "precios_catalogo.json"
OUT_REPORT = "reporte_comparacion.txt"

# --- Cargar codigos del SQL ---
sql_prices = {}
with open(SQL_PATH, "r", encoding="utf-8") as f:
    for line in f:
        m = re.search(r"\('(\d{5})',\s*'[^']*',\s*([\d.]+)\)", line)
        if m:
            sql_prices[m.group(1)] = float(m.group(2))
print("Productos en SQL:", len(sql_prices))

RE_CODE = re.compile(r"\b(\d{5})\b")
RE_PRICE = re.compile(r"\$\s*([\d,]+(?:\.\d+)?)")

def parse_price(s):
    s = s.replace(",", "").strip()
    try:
        return float(s)
    except:
        return None

doc = fitz.open(PDF_PATH)
total_pages = len(doc)

# Estructura: code -> {"regular": x, "promo": y, "page": p, "name": ...}
results = {}

for pidx in range(total_pages):
    page = doc[pidx]
    page_num = pidx + 1
    blocks = page.get_text("blocks")
    # blocks: (x0,y0,x1,y1,text,block_no,block_type)

    # Filtrar bloques con texto
    text_blocks = []
    for b in blocks:
        if len(b) < 5:
            continue
        txt = b[4]
        if not txt.strip():
            continue
        text_blocks.append({
            "x0": b[0], "y0": b[1], "x1": b[2], "y1": b[3],
            "text": txt,
        })

    # 1. Bloques-producto: contienen un codigo de 5 digitos
    product_blocks = []
    price_only_blocks = []
    for tb in text_blocks:
        codes = RE_CODE.findall(tb["text"])
        # limpiar codigo: que sean exactamente 5 digitos (no parte de otro numero)
        valid_codes = []
        for c in RE_CODE.finditer(tb["text"]):
            # verificar que no es parte de un numero mas largo
            start, end = c.start(), c.end()
            before = tb["text"][:start]
            after = tb["text"][end:]
            # si antes hay digito o despues hay digito, no es codigo standalone
            if (before and before[-1].isdigit()) or (after and after[0].isdigit()):
                continue
            valid_codes.append(c.group(0))
        if valid_codes:
            tb["codes"] = valid_codes
            product_blocks.append(tb)
        else:
            # bloque solo de precio?
            prices = RE_PRICE.findall(tb["text"])
            if prices and not RE_CODE.search(tb["text"]):
                tb["prices"] = [parse_price(p) for p in prices if parse_price(p) is not None]
                if tb["prices"]:
                    price_only_blocks.append(tb)

    # 2. Para cada bloque-producto, extraer precio regular (en el mismo bloque)
    for pb in product_blocks:
        for code in pb["codes"]:
            if code not in sql_prices:
                continue  # solo nos importan los del SQL
            # precio regular en el bloque
            reg_prices = [parse_price(p) for p in RE_PRICE.findall(pb["text"]) if parse_price(p) is not None]
            regular = reg_prices[0] if reg_prices else None

            # buscar promo: bloque solo-precio directamente debajo (y0 > pb.y1, y0 < pb.y1+250, x solapado)
            promo = None
            for pob in price_only_blocks:
                # x solapado?
                ox0 = max(pb["x0"], pob["x0"])
                ox1 = min(pb["x1"], pob["x1"])
                if ox1 - ox0 < 20:  # poco solape horizontal
                    continue
                # debajo?
                if pob["y0"] < pb["y1"] - 10:
                    continue
                if pob["y0"] > pb["y1"] + 260:
                    continue
                # verificar texto "al comprar" / "3 productos" cerca (abajo del promo)
                has_promo_text = False
                for tb2 in text_blocks:
                    if tb2 is pob:
                        continue
                    if tb2["y0"] < pob["y0"] - 5 or tb2["y0"] > pob["y1"] + 60:
                        continue
                    low = tb2["text"].lower()
                    if ("comprar" in low and "producto" in low) or "comprar  3" in low or "3  productos" in low:
                        has_promo_text = True
                        break
                if has_promo_text and pob["prices"]:
                    promo = pob["prices"][0]
                    break

            entry = results.get(code)
            new_info = {
                "regular": regular,
                "promo": promo,
                "page": page_num,
                "block_text": pb["text"].replace("\n", " | ")[:120],
            }
            # Si ya existe, preferir la entrada que tenga mas info (regular+promo)
            if entry is None:
                results[code] = new_info
            else:
                # preferir la que tenga promo, o la que tenga regular
                old_score = (entry["promo"] is not None) + (entry["regular"] is not None)
                new_score = (promo is not None) + (regular is not None)
                if new_score > old_score:
                    results[code] = new_info

doc.close()

# Determinar precio canonico: promo si existe, sino regular
for code, info in results.items():
    if info["promo"] is not None:
        info["canonico"] = info["promo"]
        info["tipo"] = "promo"
    elif info["regular"] is not None:
        info["canonico"] = info["regular"]
        info["tipo"] = "regular"
    else:
        info["canonico"] = None
        info["tipo"] = "sin_precio"

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# Reporte de comparacion
lines = []
lines.append("=" * 90)
lines.append("REPORTE DE COMPARACION PRECIOS SQL vs CATALOGO")
lines.append("=" * 90)

encontrados = 0
no_encontrados = []
coinciden = 0
difieren = []
for code in sorted(sql_prices.keys()):
    sql_p = sql_prices[code]
    info = results.get(code)
    if info and info["canonico"] is not None:
        encontrados += 1
        cat_p = info["canonico"]
        if abs(cat_p - sql_p) < 0.01:
            coinciden += 1
        else:
            difieren.append((code, sql_p, cat_p, info["tipo"], info["regular"], info["promo"], info["page"]))
    else:
        no_encontrados.append((code, sql_p, info.get("page") if info else None))

lines.append(f"Total productos SQL: {len(sql_prices)}")
lines.append(f"Encontrados en catalogo: {encontrados}")
lines.append(f"  - Coinciden con SQL: {coinciden}")
lines.append(f"  - DIFIEREN: {len(difieren)}")
lines.append(f"No encontrados: {len(no_encontrados)}")
lines.append("")
lines.append("--- PRECIOS QUE DIFIEREN (SQL vs catalogo) ---")
lines.append(f"{'Codigo':<8}{'SQL':>10}{'Catalogo':>10}{'Tipo':>8}{'Regular':>10}{'Promo':>10}{'Pag':>5}")
for code, sql_p, cat_p, tipo, reg, promo, pg in difieren:
    lines.append(f"{code:<8}{sql_p:>10.2f}{cat_p:>10.2f}{tipo:>8}{(reg or 0):>10.2f}{(promo or 0):>10.2f}{pg:>5}")
lines.append("")
lines.append("--- PRODUCTOS NO ENCONTRADOS EN CATALOGO ---")
for code, sql_p, pg in no_encontrados:
    lines.append(f"{code}  SQL={sql_p}  page={pg}")

with open(OUT_REPORT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Encontrados: {encontrados}/{len(sql_prices)}")
print(f"Coinciden: {coinciden}")
print(f"Difieren: {len(difieren)}")
print(f"No encontrados: {len(no_encontrados)}")
print("Reporte:", OUT_REPORT)
