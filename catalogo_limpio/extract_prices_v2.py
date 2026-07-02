import fitz
import re
import json

PDF_PATH = "catalogo.pdf"
SQL_PATH = "productos.sql"
OUT_JSON = "precios_catalogo_v2.json"
OUT_REPORT = "reporte_v2.txt"

# --- Cargar codigos del SQL ---
sql_prices = {}
sql_names = {}
with open(SQL_PATH, "r", encoding="utf-8") as f:
    for line in f:
        m = re.search(r"\('(\d{5})',\s*'([^']*)',\s*([\d.]+)\)", line)
        if m:
            sql_prices[m.group(1)] = float(m.group(3))
            sql_names[m.group(1)] = m.group(2)
print("Productos en SQL:", len(sql_prices))

sql_set = set(sql_prices.keys())
RE_CODE = re.compile(r"^\d{5}$")

def num(s):
    s = s.replace(",", "").strip()
    try:
        return float(s)
    except:
        return None

doc = fitz.open(PDF_PATH)
total_pages = len(doc)

# results: code -> {regular, promo, page, ...}
results = {}

for pidx in range(total_pages):
    page = doc[pidx]
    page_num = pidx + 1
    d = page.get_text("dict")
    page_w = page.rect.width
    page_h = page.rect.height

    # 1. Recopilar spans: (x0,y0,x1,y1,text,size,origin_x,origin_y)
    spans = []
    for b in d["blocks"]:
        if "lines" not in b:
            continue
        for l in b["lines"]:
            for s in l["spans"]:
                t = s["text"]
                if not t.strip():
                    continue
                spans.append({
                    "x0": s["bbox"][0], "y0": s["bbox"][1],
                    "x1": s["bbox"][2], "y1": s["bbox"][3],
                    "text": t, "size": s["size"],
                    "cx": (s["bbox"][0]+s["bbox"][2])/2,
                    "cy": (s["bbox"][1]+s["bbox"][3])/2,
                })

    # 2. Detectar clusters de precio: $ + numero principal + (opcional centavos superindice)
    prices = []
    used = set()
    for i, sp in enumerate(spans):
        if i in used:
            continue
        t = sp["text"].strip()
        # El $ puede venir solo o pegado al numero
        if t == "$" or t.startswith("$"):
            # numero principal: el siguiente span a la derecha, mayor size
            main = None
            cents = None
            for j in range(i+1, min(i+6, len(spans))):
                if j in used:
                    continue
                sj = spans[j]
                # debe estar a la derecha y misma linea (y cercano)
                if sj["x0"] < sp["x0"] - 5:
                    continue
                if abs(sj["cy"] - sp["cy"]) > 25:
                    continue
                tj = sj["text"].strip()
                # ¿numero principal? (contiene digitos, size grande >= 22)
                if re.search(r"\d", tj) and sj["size"] >= 22 and main is None:
                    main = sj
                    used.add(j)
                    break
            if t.startswith("$") and len(t) > 1 and main is None:
                # el $ viene pegado al numero: ej "$699"
                num_part = t[1:]
                # buscar centavos
                val = num(num_part)
                if val is not None:
                    prices.append({
                        "value": val, "has_cents": False,
                        "cx": sp["cx"], "cy": sp["cy"],
                        "x0": sp["x0"], "y0": sp["y0"], "x1": sp["x1"], "y1": sp["y1"],
                    })
                    used.add(i)
                    continue
            if main is not None:
                # buscar centavos: span pequeño a la derecha del main, levantado (cy menor)
                for j in range(i+1, len(spans)):
                    if j in used or j is i:
                        continue
                    sj = spans[j]
                    if sj["x0"] < main["x1"] - 5:
                        continue
                    if sj["cy"] > main["cy"] + 8:
                        continue  # los centavos estan levantados (cy menor o igual)
                    if abs(sj["x0"] - main["x1"]) > 20:
                        continue
                    tj = sj["text"].strip()
                    if re.fullmatch(r"\d{1,2}", tj) and sj["size"] < main["size"] - 3 and abs(sj["x0"] - main["x1"]) < 15 and tj == "90":
                        cents = tj
                        used.add(j)
                        break
                main_val = num(re.sub(r"[^\d]", "", main["text"]))
                if main_val is None:
                    continue
                if cents is not None:
                    # centavos: 2 digitos
                    val = main_val + (int(cents)/100.0)
                else:
                    val = main_val
                # bbox conjunto
                x0 = min(sp["x0"], main["x0"])
                y0 = min(sp["y0"], main["y0"])
                x1 = max(sp["x1"], main["x1"])
                y1 = max(sp["y1"], main["y1"])
                prices.append({
                    "value": val, "has_cents": cents is not None,
                    "cx": (x0+x1)/2, "cy": (y0+y1)/2,
                    "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                })
                used.add(i)

    # 3. Detectar marcadores "Al comprar 3 productos"
    markers = []
    for sp in spans:
        low = sp["text"].lower()
        if "comprar" in low and "producto" in low:
            markers.append(sp)
        elif low.strip() == "3" and any("comprar" in s["text"].lower() for s in spans if abs(s["cy"]-sp["cy"])<20):
            # parte del marcador, ya capturado arriba
            pass
    # agrupar marcadores cercanos en y
    markers.sort(key=lambda s: s["cy"])
    grouped_markers = []
    for m in markers:
        if grouped_markers and abs(m["cy"] - grouped_markers[-1]["cy"]) < 30:
            # mismo marcador, extender x
            grouped_markers[-1]["x0"] = min(grouped_markers[-1]["x0"], m["x0"])
            grouped_markers[-1]["x1"] = max(grouped_markers[-1]["x1"], m["x1"])
            grouped_markers[-1]["cx"] = (grouped_markers[-1]["x0"]+grouped_markers[-1]["x1"])/2
            grouped_markers[-1]["cy"] = max(grouped_markers[-1]["cy"], m["cy"])
        else:
            grouped_markers.append(dict(m))

    # 4. Para cada marcador, el precio promo es el price cluster mas cercano ARRIBA (cy < marker.cy)
    promo_prices = []
    for mk in grouped_markers:
        best = None
        best_dist = None
        for p in prices:
            if p["cy"] > mk["cy"] + 5:
                continue  # debe estar arriba
            if p["cy"] < mk["cy"] - 120:
                continue  # no muy lejos
            # solape x
            ox0 = max(p["x0"], mk["x0"]-30)
            ox1 = min(p["x1"], mk["x1"]+30)
            if ox1 - ox0 < 10:
                continue
            dist = mk["cy"] - p["cy"]
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best = p
        if best is not None:
            best["is_promo"] = True
            promo_prices.append(best)

    # 5. Detectar codigos de producto (extraer 5 digitos, limpiar prefijo \u2002)
    codes = []
    for sp in spans:
        m = re.search(r"(?<!\d)(\d{5})(?!\d)", sp["text"])
        if m and m.group(1) in sql_set:
            sp2 = dict(sp)
            sp2["code"] = m.group(1)
            codes.append(sp2)

    # 6. Asociar codigo -> precio
    if page_num == 8:
        print("DEBUG pag8 prices:", [(round(p["value"],2), round(p["cx"]), round(p["cy"]), p.get("is_promo",False)) for p in prices])
        print("DEBUG pag8 codes:", [(sp["code"], round(sp["cx"]), round(sp["cy"])) for sp in codes])
    for cd in codes:
        code_key = cd["code"]
        cx, cy = cd["cx"], cd["cy"]
        # precios debajo del codigo (cy > cd.cy - 15), dentro de ventana
        cands = []
        for p in prices:
            if p["cy"] < cy - 20:
                continue
            if p["cy"] > cy + 600:
                continue
            # cercania x
            dx = abs(p["cx"] - cx)
            if dx > 400:
                continue
            cands.append(p)
        if not cands:
            continue
        # elegir promo si existe
        promo = None
        for p in cands:
            if p.get("is_promo"):
                if promo is None or abs(p["cx"]-cx) < abs(promo["cx"]-cx):
                    promo = p
        # regular = el price mas cercano que no sea promo
        regular = None
        for p in cands:
            if p.get("is_promo"):
                continue
            if regular is None or abs(p["cx"]-cx) < abs(regular["cx"]-cx):
                regular = p

        canonical = promo if promo is not None else regular
        info = {
            "regular": regular["value"] if regular else None,
            "promo": promo["value"] if promo else None,
            "canonico": canonical["value"] if canonical else None,
            "tipo": "promo" if promo else ("regular" if regular else "none"),
            "page": page_num,
        }
        prev = results.get(code_key)
        if prev is None:
            results[code_key] = info
        else:
            # preferir el que tenga promo, o mas info
            new_score = (info["promo"] is not None) + (info["regular"] is not None)
            old_score = (prev["promo"] is not None) + (prev["regular"] is not None)
            if new_score > old_score:
                results[code_key] = info

doc.close()

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# Reporte
lines = []
lines.append("=" * 100)
lines.append("REPORTE v2 - PRECIOS SQL vs CATALOGO")
lines.append("=" * 100)
encontrados = 0
coinciden = 0
difieren = []
no_enc = []
for code in sorted(sql_prices.keys()):
    sql_p = sql_prices[code]
    info = results.get(code)
    if info and info["canonico"] is not None:
        encontrados += 1
        cat_p = info["canonico"]
        if abs(cat_p - sql_p) < 0.011:
            coinciden += 1
        else:
            difieren.append((code, sql_p, cat_p, info["tipo"], info["regular"], info["promo"], info["page"]))
    else:
        no_enc.append((code, sql_p, info.get("page") if info else None))

lines.append(f"Total SQL: {len(sql_prices)}  | Encontrados: {encontrados}  | Coinciden: {coinciden}  | Difieren: {len(difieren)}  | No encontrados: {len(no_enc)}")
lines.append("")
lines.append("--- DIFIEREN ---")
lines.append(f"{'Codigo':<8}{'Nombre':<32}{'SQL':>9}{'Catal':>9}{'Tipo':>8}{'Reg':>9}{'Promo':>9}{'Pag':>5}")
for code, sql_p, cat_p, tipo, reg, promo, pg in difieren:
    nm = sql_names[code][:30]
    lines.append(f"{code:<8}{nm:<32}{sql_p:>9.2f}{cat_p:>9.2f}{tipo:>8}{(reg or 0):>9.2f}{(promo or 0):>9.2f}{pg:>5}")
lines.append("")
lines.append("--- NO ENCONTRADOS ---")
for code, sql_p, pg in no_enc:
    lines.append(f"{code}  {sql_names[code][:30]:<32} SQL={sql_p}  page={pg}")

with open(OUT_REPORT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Encontrados: {encontrados}/{len(sql_prices)}")
print(f"Coinciden: {coinciden}")
print(f"Difieren: {len(difieren)}")
print(f"No encontrados: {len(no_enc)}")
print("Reporte:", OUT_REPORT)
