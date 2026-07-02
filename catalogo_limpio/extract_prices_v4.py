import fitz
import re
import json

PDF_PATH = "catalogo.pdf"
SQL_PATH = "productos.sql"
OUT_JSON = "precios_catalogo_v4.json"
OUT_REPORT = "reporte_v4.txt"

sql_prices = {}; sql_names = {}
with open(SQL_PATH, "r", encoding="utf-8") as f:
    for line in f:
        m = re.search(r"\('(\d{5})',\s*'([^']*)',\s*([\d.]+)\)", line)
        if m:
            sql_prices[m.group(1)] = float(m.group(3))
            sql_names[m.group(1)] = m.group(2)
sql_set = set(sql_prices.keys())
print("SQL:", len(sql_prices))

def num(s):
    s = s.replace(",", "").strip()
    try: return float(s)
    except: return None

doc = fitz.open(PDF_PATH)
results = {}

for pidx in range(len(doc)):
    page = doc[pidx]
    page_num = pidx + 1
    d = page.get_text("dict")

    # Recopilar spans con indice de bloque
    blocks = []
    for bi, b in enumerate(d["blocks"]):
        if "lines" not in b:
            continue
        bx0, by0, bx1, by1 = b["bbox"]
        bspans = []
        btext_parts = []
        for l in b["lines"]:
            for s in l["spans"]:
                t = s["text"]
                if not t.strip():
                    continue
                sp = {"x0": s["bbox"][0], "y0": s["bbox"][1], "x1": s["bbox"][2], "y1": s["bbox"][3],
                      "text": t, "size": s["size"],
                      "cx": (s["bbox"][0]+s["bbox"][2])/2, "cy": (s["bbox"][1]+s["bbox"][3])/2,
                      "block": bi}
                bspans.append(sp)
                btext_parts.append(t)
        if not bspans:
            continue
        blocks.append({"bi": bi, "x0": bx0, "y0": by0, "x1": bx1, "y1": by1,
                       "cx": (bx0+bx1)/2, "cy": (by0+by1)/2,
                       "spans": bspans, "text": " ".join(btext_parts)})

    all_spans = [sp for blk in blocks for sp in blk["spans"]]

    # --- Clusters de precio (span-level) con bloque de origen ---
    prices = []
    used = set()
    for i, sp in enumerate(all_spans):
        if i in used:
            continue
        t = sp["text"].strip()
        if not (t == "$" or t.startswith("$")):
            continue
        main = None
        for j in range(i+1, min(i+8, len(all_spans))):
            if j in used:
                continue
            sj = all_spans[j]
            if sj["block"] != sp["block"]:
                continue
            if sj["x0"] < sp["x0"] - 5:
                continue
            if abs(sj["cy"] - sp["cy"]) > 30:
                continue
            tj = sj["text"].strip()
            if re.search(r"\d", tj) and sj["size"] >= 22 and main is None:
                main = sj; used.add(j); break
        if t.startswith("$") and len(t) > 1 and main is None:
            v = num(t[1:])
            if v is not None and v < 50000:
                prices.append({"value": v, "has_cents": False, "cx": sp["cx"], "cy": sp["cy"],
                    "x0": sp["x0"], "y0": sp["y0"], "x1": sp["x1"], "y1": sp["y1"], "block": sp["block"]})
                used.add(i)
            continue
        if main is None:
            continue
        cents = None
        for j in range(i+1, len(all_spans)):
            if j in used or j == i:
                continue
            sj = all_spans[j]
            if sj["block"] != sp["block"]:
                continue
            if sj["x0"] < main["x1"] - 5:
                continue
            if sj["cy"] > main["cy"] + 10:
                continue
            if abs(sj["x0"] - main["x1"]) > 15:
                continue
            tj = sj["text"].strip()
            if tj == "90" and sj["size"] < main["size"] - 3:
                cents = "90"; used.add(j); break
        main_val = num(re.sub(r"[^\d]", "", main["text"]))
        if main_val is None or main_val >= 50000:
            used.discard(i)
            continue
        val = main_val + 0.90 if cents else main_val
        x0 = min(sp["x0"], main["x0"]); y0 = min(sp["y0"], main["y0"])
        x1 = max(sp["x1"], main["x1"]); y1 = max(sp["y1"], main["y1"])
        prices.append({"value": val, "has_cents": cents is not None, "cx": (x0+x1)/2, "cy": (y0+y1)/2,
            "x0": x0, "y0": y0, "x1": x1, "y1": y1, "block": sp["block"]})
        used.add(i)

    # Indexar precios por bloque
    prices_by_block = {}
    for p in prices:
        prices_by_block.setdefault(p["block"], []).append(p)

    # --- Codigos por bloque ---
    code_in_block = {}  # bi -> [(code, cx, cy)]
    for blk in blocks:
        for sp in blk["spans"]:
            m = re.search(r"(?<!\d)(\d{5})(?!\d)", sp["text"])
            if m and m.group(1) in sql_set:
                code_in_block.setdefault(blk["bi"], []).append((m.group(1), sp["cx"], sp["cy"]))

    # --- Bloques marcador "Al comprar 3 productos" ---
    marker_blocks = []
    for blk in blocks:
        low = blk["text"].lower()
        if "comprar" in low and "producto" in low:
            marker_blocks.append(blk)

    # --- Para cada marcador, precio promo en bloque directamente arriba ---
    # y codigo en bloque mas arriba (que tenga codigo)
    for mk in marker_blocks:
        # bloques arriba (y1 <= mk.y0), solapando x, ordenados por cercania
        above = [blk for blk in blocks
                 if blk["y1"] <= mk["y0"] + 5
                 and (min(blk["x1"], mk["x1"]) - max(blk["x0"], mk["x0"])) > 10
                 and blk["y0"] > mk["y0"] - 400]
        above.sort(key=lambda b: mk["y0"] - b["y0"])  # mas cercano primero
        # precio promo: primer bloque arriba que tenga precio (sin codigo)
        promo_price = None
        promo_block_bi = None
        for blk in above:
            if blk["bi"] in prices_by_block and blk["bi"] not in code_in_block:
                promo_price = prices_by_block[blk["bi"]][0]
                promo_block_bi = blk["bi"]
                break
        if promo_price is None:
            # quizas el precio esta en un bloque con codigo (precio regular y promo mezclados)
            for blk in above:
                if blk["bi"] in prices_by_block:
                    # tomar el precio mas bajo (mayor y) del bloque
                    ps = prices_by_block[blk["bi"]]
                    promo_price = max(ps, key=lambda p: p["cy"])
                    promo_block_bi = blk["bi"]
                    break
        # codigo: primer bloque arriba (desde el bloque promo) que tenga codigo
        code_assigned = None
        if promo_block_bi is not None:
            promo_blk = next(b for b in blocks if b["bi"] == promo_block_bi)
            for blk in above:
                if blk["y1"] > promo_blk["y0"]:  # debajo o igual al bloque promo
                    continue
                if blk["bi"] in code_in_block:
                    # el codigo mas cercano en x al promo
                    cands_code = code_in_block[blk["bi"]]
                    code_assigned = min(cands_code, key=lambda c: abs(c[1]-promo_price["cx"]))
                    break
        if promo_price is not None and code_assigned is not None:
            code_key = code_assigned[0]
            info = {
                "regular": None,  # se llenara despues
                "promo": round(promo_price["value"], 2),
                "canonico": round(promo_price["value"], 2),
                "tipo": "promo", "page": page_num,
                "promo_block": promo_block_bi,
            }
            prev = results.get(code_key)
            if prev is None or (prev.get("promo") is None and info["promo"] is not None):
                results[code_key] = info

    # --- Para codigos SIN promo: precio regular en el mismo bloque ---
    for blk in blocks:
        if blk["bi"] not in code_in_block:
            continue
        if blk["bi"] not in prices_by_block:
            continue
        for code_tup in code_in_block[blk["bi"]]:
            code_key, ccx, ccy = code_tup
            if code_key in results and results[code_key].get("promo") is not None:
                # ya tiene promo; llenar regular
                ps = prices_by_block[blk["bi"]]
                # regular = precio mas cercano al codigo en x
                reg = min(ps, key=lambda p: abs(p["cx"]-ccx))
                results[code_key]["regular"] = round(reg["value"], 2)
                continue
            # sin promo: precio regular = mas cercano en x en el mismo bloque
            ps = prices_by_block[blk["bi"]]
            reg = min(ps, key=lambda p: abs(p["cx"]-ccx))
            info = {"regular": round(reg["value"], 2), "promo": None,
                    "canonico": round(reg["value"], 2), "tipo": "regular", "page": page_num}
            prev = results.get(code_key)
            if prev is None:
                results[code_key] = info
            elif prev.get("promo") is None and prev.get("regular") is None:
                results[code_key] = info

doc.close()

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

lines = []
lines.append("="*110); lines.append("REPORTE v4"); lines.append("="*110)
encontrados=0; coinciden=0; difieren=[]; no_enc=[]
for code in sorted(sql_prices.keys()):
    sql_p = sql_prices[code]
    info = results.get(code)
    if info and info["canonico"] is not None:
        encontrados += 1
        if abs(info["canonico"]-sql_p) < 0.011:
            coinciden += 1
        else:
            difieren.append((code, sql_p, info["canonico"], info["tipo"], info.get("regular"), info.get("promo"), info["page"]))
    else:
        no_enc.append((code, sql_p, info.get("page") if info else None))
lines.append(f"Total SQL: {len(sql_prices)} | Encontrados: {encontrados} | Coinciden: {coinciden} | Difieren: {len(difieren)} | No enc: {len(no_enc)}")
lines.append("")
lines.append("--- DIFIEREN ---")
lines.append(f"{'Codigo':<8}{'Nombre':<30}{'SQL':>9}{'Catal':>9}{'Tipo':>8}{'Reg':>9}{'Promo':>9}{'Pag':>5}")
for c,sp,cp,t,r,pr,pg in difieren:
    lines.append(f"{c:<8}{sql_names[c][:28]:<30}{sp:>9.2f}{cp:>9.2f}{t:>8}{(r or 0):>9.2f}{(pr or 0):>9.2f}{pg:>5}")
lines.append("")
lines.append("--- NO ENCONTRADOS ---")
for c,sp,pg in no_enc:
    lines.append(f"{c}  {sql_names[c][:28]:<30} SQL={sp}  page={pg}")
with open(OUT_REPORT,"w",encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"Encontrados: {encontrados}/{len(sql_prices)} | Coinciden: {coinciden} | Difieren: {len(difieren)} | No enc: {len(no_enc)}")
