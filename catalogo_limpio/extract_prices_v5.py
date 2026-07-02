import fitz
import re
import json

PDF_PATH = "catalogo.pdf"
SQL_PATH = "productos.sql"
OUT_JSON = "precios_catalogo_v5.json"
OUT_REPORT = "reporte_v5.txt"

sql_prices = {}; sql_names = {}
with open(SQL_PATH, "r", encoding="utf-8") as f:
    for line in f:
        m = re.search(r"\('(\d{5})',\s*'([^']*)',\s*([\d.]+)\)", line)
        if m:
            sql_prices[m.group(1)] = float(m.group(3))
            sql_names[m.group(1)] = m.group(2)
sql_set = set(sql_prices.keys())

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
    spans = []
    for b in d["blocks"]:
        if "lines" not in b: continue
        for l in b["lines"]:
            for s in l["spans"]:
                t = s["text"]
                if not t.strip(): continue
                spans.append({"x0":s["bbox"][0],"y0":s["bbox"][1],"x1":s["bbox"][2],"y1":s["bbox"][3],
                    "text":t,"size":s["size"],"cx":(s["bbox"][0]+s["bbox"][2])/2,"cy":(s["bbox"][1]+s["bbox"][3])/2})

    # --- Clusters de precio ---
    prices = []
    used = set()
    for i, sp in enumerate(spans):
        if i in used: continue
        t = sp["text"].strip()
        if not (t == "$" or t.startswith("$")): continue
        main = None
        for j in range(i+1, min(i+8, len(spans))):
            if j in used: continue
            sj = spans[j]
            if sj["x0"] < sp["x0"] - 5: continue
            if abs(sj["cy"] - sp["cy"]) > 30: continue
            tj = sj["text"].strip()
            if re.search(r"\d", tj) and sj["size"] >= 22 and main is None:
                main = sj; used.add(j); break
        if t.startswith("$") and len(t) > 1 and main is None:
            v = num(t[1:])
            if v is not None and v < 50000:
                prices.append({"value":v,"has_cents":False,"cx":sp["cx"],"cy":sp["cy"],
                    "x0":sp["x0"],"y0":sp["y0"],"x1":sp["x1"],"y1":sp["y1"]})
                used.add(i)
            continue
        if main is None: continue
        cents = None
        for j in range(i+1, len(spans)):
            if j in used or j == i: continue
            sj = spans[j]
            if sj["x0"] < main["x1"] - 5: continue
            if sj["cy"] > main["cy"] + 10: continue
            if abs(sj["x0"] - main["x1"]) > 15: continue
            if sj["text"].strip() == "90" and sj["size"] < main["size"] - 3:
                cents = "90"; used.add(j); break
        main_val = num(re.sub(r"[^\d]", "", main["text"]))
        if main_val is None or main_val >= 50000:
            used.discard(i); continue
        val = main_val + 0.90 if cents else main_val
        x0=min(sp["x0"],main["x0"]); y0=min(sp["y0"],main["y0"])
        x1=max(sp["x1"],main["x1"]); y1=max(sp["y1"],main["y1"])
        prices.append({"value":val,"has_cents":cents is not None,"cx":(x0+x1)/2,"cy":(y0+y1)/2,
            "x0":x0,"y0":y0,"x1":x1,"y1":y1})
        used.add(i)

    # --- Codigos ---
    codes = []
    for sp in spans:
        m = re.search(r"(?<!\d)(\d{5})(?!\d)", sp["text"])
        if m and m.group(1) in sql_set:
            codes.append({"code":m.group(1),"cx":sp["cx"],"cy":sp["cy"],"x0":sp["x0"],"x1":sp["x1"]})
    codes.sort(key=lambda c: c["cy"])

    # --- Marcadores "Al comprar 3 productos" ---
    comprar = [sp for sp in spans if "comprar" in sp["text"].lower()]
    producto = [sp for sp in spans if "producto" in sp["text"].lower()]
    markers = []
    for cs in comprar:
        for ps in producto:
            if abs(cs["cy"]-ps["cy"]) > 60: continue
            if abs(cs["cx"]-ps["cx"]) > 250: continue
            markers.append({"x0":min(cs["x0"],ps["x0"]),"x1":max(cs["x1"],ps["x1"]),
                "cx":(min(cs["x0"],ps["x0"])+max(cs["x1"],ps["x1"]))/2,
                "y_top":min(cs["y0"],ps["y0"]),"y_bot":max(cs["y1"],ps["y1"]),"cy":(cs["cy"]+ps["cy"])/2})
            break

    # --- Asociacion por tarjeta ---
    for idx, cd in enumerate(codes):
        code_key = cd["code"]; cx, cy = cd["cx"], cd["cy"]
        # limite inferior de tarjeta: siguiente codigo en misma columna (x cercano)
        card_bottom = cy + 600
        for nxt in codes[idx+1:]:
            if nxt["cy"] <= cy: continue
            if abs(nxt["cx"] - cx) > 250: continue
            card_bottom = nxt["cy"]
            break
        # precios en la tarjeta (x solapado, y entre cy-20 y card_bottom)
        card_prices = []
        for p in prices:
            if p["cy"] < cy - 30: continue
            if p["cy"] > card_bottom - 5: continue
            ox0 = max(p["x0"], cd["x0"]-150); ox1 = min(p["x1"], cd["x1"]+150)
            if ox1 - ox0 < 10:
                # tambien permitir cercania en x
                if abs(p["cx"]-cx) > 300: continue
            card_prices.append(p)
        if not card_prices: continue
        # marcador en la tarjeta
        card_marker = None
        for mk in markers:
            if mk["cy"] < cy - 10: continue
            if mk["cy"] > card_bottom - 5: continue
            ox0 = max(mk["x0"]-40, cd["x0"]-150); ox1 = min(mk["x1"]+40, cd["x1"]+150)
            if ox1 - ox0 < 10 and abs(mk["cx"]-cx) > 300: continue
            card_marker = mk; break
        promo = None; regular = None
        if card_marker is not None:
            # promo = precio arriba del marcador, dentro de card_prices
            cands = [p for p in card_prices if p["cy"] < card_marker["y_top"] + 5 and p["cy"] > card_marker["y_top"] - 140]
            if cands:
                promo = min(cands, key=lambda p: card_marker["y_top"]-p["cy"])
            # regular = precio arriba del promo (mas alto)
            if promo is not None:
                regs = [p for p in card_prices if p["cy"] < promo["cy"] - 5]
                if regs:
                    regular = min(regs, key=lambda p: abs(p["cx"]-cx))
        if regular is None:
            # regular = precio mas cercano en x (que no sea promo)
            regs = [p for p in card_prices if p is not promo]
            if regs:
                regular = min(regs, key=lambda p: abs(p["cx"]-cx))
        canonical = promo if promo is not None else regular
        info = {"regular":round(regular["value"],2) if regular else None,
            "promo":round(promo["value"],2) if promo else None,
            "canonico":round(canonical["value"],2) if canonical else None,
            "tipo":"promo" if promo else ("regular" if regular else "none"),
            "page":page_num, "np":len(card_prices)}
        prev = results.get(code_key)
        if prev is None:
            results[code_key] = info
        else:
            ns = (info["promo"] is not None)+(info["regular"] is not None)
            os_ = (prev["promo"] is not None)+(prev["regular"] is not None)
            if ns > os_ or (info["promo"] is not None and prev["promo"] is None):
                results[code_key] = info

doc.close()
with open(OUT_JSON,"w",encoding="utf-8") as f:
    json.dump(results,f,ensure_ascii=False,indent=2)

lines=[]
lines.append("="*110); lines.append("REPORTE v5"); lines.append("="*110)
encontrados=0;coinciden=0;difieren=[];no_enc=[]
for code in sorted(sql_prices.keys()):
    sql_p=sql_prices[code]; info=results.get(code)
    if info and info["canonico"] is not None:
        encontrados+=1
        if abs(info["canonico"]-sql_p)<0.011: coinciden+=1
        else: difieren.append((code,sql_p,info["canonico"],info["tipo"],info.get("regular"),info.get("promo"),info["page"],info.get("np")))
    else: no_enc.append((code,sql_p,info.get("page") if info else None))
lines.append(f"Total SQL: {len(sql_prices)} | Encontrados: {encontrados} | Coinciden: {coinciden} | Difieren: {len(difieren)} | No enc: {len(no_enc)}")
lines.append("")
lines.append("--- DIFIEREN ---")
lines.append(f"{'Codigo':<8}{'Nombre':<30}{'SQL':>9}{'Catal':>9}{'Tipo':>8}{'Reg':>9}{'Promo':>9}{'Pag':>5}{'#P':>4}")
for c,sp,cp,t,r,pr,pg,np in difieren:
    lines.append(f"{c:<8}{sql_names[c][:28]:<30}{sp:>9.2f}{cp:>9.2f}{t:>8}{(r or 0):>9.2f}{(pr or 0):>9.2f}{pg:>5}{np:>4}")
lines.append("")
lines.append("--- NO ENCONTRADOS ---")
for c,sp,pg in no_enc:
    lines.append(f"{c}  {sql_names[c][:28]:<30} SQL={sp}  page={pg}")
with open(OUT_REPORT,"w",encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"Encontrados: {encontrados}/{len(sql_prices)} | Coinciden: {coinciden} | Difieren: {len(difieren)} | No enc: {len(no_enc)}")
