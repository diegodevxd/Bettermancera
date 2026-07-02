import fitz
import re
import json

PDF_PATH = "catalogo.pdf"
SQL_PATH = "productos.sql"
OUT_JSON = "precios_catalogo_v3.json"
OUT_REPORT = "reporte_v3.txt"

# --- Cargar SQL ---
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

def num(s):
    s = s.replace(",", "").strip()
    try:
        return float(s)
    except:
        return None

doc = fitz.open(PDF_PATH)
total_pages = len(doc)
results = {}

for pidx in range(total_pages):
    page = doc[pidx]
    page_num = pidx + 1
    d = page.get_text("dict")

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

    # --- 1. Clusters de precio ---
    prices = []
    used = set()
    for i, sp in enumerate(spans):
        if i in used:
            continue
        t = sp["text"].strip()
        if not (t == "$" or t.startswith("$")):
            continue
        main = None
        for j in range(i+1, min(i+8, len(spans))):
            if j in used:
                continue
            sj = spans[j]
            if sj["x0"] < sp["x0"] - 5:
                continue
            if abs(sj["cy"] - sp["cy"]) > 30:
                continue
            tj = sj["text"].strip()
            if re.search(r"\d", tj) and sj["size"] >= 22 and main is None:
                main = sj
                used.add(j)
                break
        # $ pegado al numero: "$699"
        if t.startswith("$") and len(t) > 1 and main is None:
            v = num(t[1:])
            if v is not None and v < 50000:
                prices.append({"value": v, "has_cents": False,
                    "cx": sp["cx"], "cy": sp["cy"],
                    "x0": sp["x0"], "y0": sp["y0"], "x1": sp["x1"], "y1": sp["y1"]})
                used.add(i)
            continue
        if main is None:
            continue
        # centavos superindice "90"
        cents = None
        for j in range(i+1, len(spans)):
            if j in used or j == i:
                continue
            sj = spans[j]
            if sj["x0"] < main["x1"] - 5:
                continue
            if sj["cy"] > main["cy"] + 10:
                continue
            if abs(sj["x0"] - main["x1"]) > 15:
                continue
            tj = sj["text"].strip()
            if tj == "90" and sj["size"] < main["size"] - 3:
                cents = "90"
                used.add(j)
                break
        main_val = num(re.sub(r"[^\d]", "", main["text"]))
        if main_val is None or main_val >= 50000:
            used.discard(i)
            continue
        val = main_val + 0.90 if cents else main_val
        x0 = min(sp["x0"], main["x0"]); y0 = min(sp["y0"], main["y0"])
        x1 = max(sp["x1"], main["x1"]); y1 = max(sp["y1"], main["y1"])
        prices.append({"value": val, "has_cents": cents is not None,
            "cx": (x0+x1)/2, "cy": (y0+y1)/2,
            "x0": x0, "y0": y0, "x1": x1, "y1": y1})
        used.add(i)

    # --- 2. Marcadores "Al comprar 3 productos del catalogo" ---
    # buscar spans con "comprar" y agrupar con "producto" cercano
    comprar_spans = [sp for sp in spans if "comprar" in sp["text"].lower()]
    producto_spans = [sp for sp in spans if "producto" in sp["text"].lower()]
    markers = []
    used_marker = set()
    for cs in comprar_spans:
        for ps in producto_spans:
            if abs(cs["cy"] - ps["cy"]) > 60:
                continue
            if abs(cs["cx"] - ps["cx"]) > 250:
                continue
            # marker encontrado
            mx0 = min(cs["x0"], ps["x0"]); mx1 = max(cs["x1"], ps["x1"])
            my_top = min(cs["y0"], ps["y0"])
            my_bot = max(cs["y1"], ps["y1"])
            markers.append({"x0": mx0, "x1": mx1, "cx": (mx0+mx1)/2,
                "y_top": my_top, "y_bot": my_bot, "cy": (my_top+my_bot)/2})
            break

    # --- 3. Para cada marker, precio promo = price mas cercano ARRIBA ---
    for mk in markers:
        best = None
        best_dy = None
        for p in prices:
            if p["cy"] > mk["y_top"] + 5:
                continue  # debe estar arriba
            if p["cy"] < mk["y_top"] - 130:
                continue
            ox0 = max(p["x0"], mk["x0"]-40); ox1 = min(p["x1"], mk["x1"]+40)
            if ox1 - ox0 < 10:
                continue
            dy = mk["y_top"] - p["cy"]
            if best_dy is None or dy < best_dy:
                best_dy = dy
                best = p
        if best is not None:
            best["is_promo"] = True
            best["marker"] = mk

    # --- 4. Codigos ---
    codes = []
    for sp in spans:
        m = re.search(r"(?<!\d)(\d{5})(?!\d)", sp["text"])
        if m and m.group(1) in sql_set:
            sp2 = dict(sp)
            sp2["code"] = m.group(1)
            codes.append(sp2)

    # --- 5. Asociar codigo -> precio ---
    for cd in codes:
        code_key = cd["code"]
        cx, cy = cd["cx"], cd["cy"]
        # candidatos: debajo del codigo, en columna
        cands = []
        for p in prices:
            if p["cy"] < cy - 25:
                continue
            if p["cy"] > cy + 700:
                continue
            if abs(p["cx"] - cx) > 380:
                continue
            cands.append(p)
        if not cands:
            continue
        # marker debajo del codigo?
        code_marker = None
        for mk in markers:
            if mk["cy"] < cy - 10:
                continue
            if mk["cy"] > cy + 700:
                continue
            if (mk["x0"] + mk["x1"])/2 - cx > 380 or cx - (mk["x0"]+mk["x1"])/2 > 380:
                # x solape aproximado
                ox0 = max(mk["x0"]-40, cx-200); ox1 = min(mk["x1"]+40, cx+200)
                if ox1 - ox0 < 10:
                    continue
            code_marker = mk
            break
        promo = None
        regular = None
        if code_marker is not None:
            # promo = price arriba del marker, dentro de cands
            for p in cands:
                if p.get("is_promo") and p.get("marker") is code_marker:
                    promo = p
                    break
            if promo is None:
                # price mas cercano arriba del marker
                best = None; best_dy = None
                for p in cands:
                    if p["cy"] > code_marker["y_top"] + 5:
                        continue
                    if p["cy"] < code_marker["y_top"] - 130:
                        continue
                    dy = code_marker["y_top"] - p["cy"]
                    if best_dy is None or dy < best_dy:
                        best_dy = dy; best = p
                promo = best
        # regular = price mas cercano en x que no sea promo
        for p in cands:
            if p is promo:
                continue
            if regular is None or abs(p["cx"]-cx) < abs(regular["cx"]-cx):
                regular = p
        canonical = promo if promo is not None else regular
        info = {
            "regular": round(regular["value"],2) if regular else None,
            "promo": round(promo["value"],2) if promo else None,
            "canonico": round(canonical["value"],2) if canonical else None,
            "tipo": "promo" if promo else ("regular" if regular else "none"),
            "page": page_num,
        }
        prev = results.get(code_key)
        if prev is None:
            results[code_key] = info
        else:
            new_score = (info["promo"] is not None) + (info["regular"] is not None)
            old_score = (prev["promo"] is not None) + (prev["regular"] is not None)
            if new_score > old_score or (info["promo"] is not None and prev["promo"] is None):
                results[code_key] = info

doc.close()

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

lines = []
lines.append("=" * 110)
lines.append("REPORTE v3")
lines.append("=" * 110)
encontrados = 0; coinciden = 0; difieren = []; no_enc = []
for code in sorted(sql_prices.keys()):
    sql_p = sql_prices[code]
    info = results.get(code)
    if info and info["canonico"] is not None:
        encontrados += 1
        if abs(info["canonico"] - sql_p) < 0.011:
            coinciden += 1
        else:
            difieren.append((code, sql_p, info["canonico"], info["tipo"], info["regular"], info["promo"], info["page"]))
    else:
        no_enc.append((code, sql_p, info.get("page") if info else None))
lines.append(f"Total SQL: {len(sql_prices)} | Encontrados: {encontrados} | Coinciden: {coinciden} | Difieren: {len(difieren)} | No encontrados: {len(no_enc)}")
lines.append("")
lines.append("--- DIFIEREN ---")
lines.append(f"{'Codigo':<8}{'Nombre':<30}{'SQL':>9}{'Catal':>9}{'Tipo':>8}{'Reg':>9}{'Promo':>9}{'Pag':>5}")
for code, sql_p, cat_p, tipo, reg, promo, pg in difieren:
    lines.append(f"{code:<8}{sql_names[code][:28]:<30}{sql_p:>9.2f}{cat_p:>9.2f}{tipo:>8}{(reg or 0):>9.2f}{(promo or 0):>9.2f}{pg:>5}")
lines.append("")
lines.append("--- NO ENCONTRADOS ---")
for code, sql_p, pg in no_enc:
    lines.append(f"{code}  {sql_names[code][:28]:<30} SQL={sql_p}  page={pg}")
with open(OUT_REPORT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"Encontrados: {encontrados}/{len(sql_prices)} | Coinciden: {coinciden} | Difieren: {len(difieren)} | No enc: {len(no_enc)}")
