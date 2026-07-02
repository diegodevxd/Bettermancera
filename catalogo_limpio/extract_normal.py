import fitz, re, json

PDF_PATH = "catalogo.pdf"
SQL_PATH = "productos.sql"
OUT_JSON = "precios_normales.json"
OUT_REPORT = "reporte_normales.txt"

sql_prices={}; sql_names={}
with open(SQL_PATH,encoding="utf-8") as f:
    for line in f:
        m=re.search(r"\('(\d{5})',\s*'([^']*)',\s*([\d.]+)\)",line)
        if m: sql_prices[m.group(1)]=float(m.group(3)); sql_names[m.group(1)]=m.group(2)
sql_set=set(sql_prices.keys())

def num(s):
    s=s.replace(",","").strip()
    try: return float(s)
    except: return None

doc=fitz.open(PDF_PATH)
results={}

for pidx in range(len(doc)):
    if pidx==110:  # pagina 111 "Vamos Mexico" - layout especial, ya tiene precios normales en SQL
        continue
    page=doc[pidx]; page_num=pidx+1
    d=page.get_text("dict")
    spans=[]
    for b in d["blocks"]:
        if "lines" not in b: continue
        for l in b["lines"]:
            for s in l["spans"]:
                t=s["text"]
                if not t.strip(): continue
                spans.append({"x0":s["bbox"][0],"y0":s["bbox"][1],"x1":s["bbox"][2],"y1":s["bbox"][3],
                    "text":t,"size":s["size"],"cx":(s["bbox"][0]+s["bbox"][2])/2,"cy":(s["bbox"][1]+s["bbox"][3])/2})

    # --- Clusters de precio (span-level, centavos "90") ---
    prices=[]
    used=set()
    for i,sp in enumerate(spans):
        if i in used: continue
        t=sp["text"].strip()
        if not (t=="$" or t.startswith("$")): continue
        main=None
        for j in range(i+1,min(i+8,len(spans))):
            if j in used: continue
            sj=spans[j]
            if sj["x0"]<sp["x0"]-5: continue
            if abs(sj["cy"]-sp["cy"])>30: continue
            tj=sj["text"].strip()
            if re.search(r"\d",tj) and sj["size"]>=22 and main is None:
                main=sj; used.add(j); break
        if t.startswith("$") and len(t)>1 and main is None:
            v=num(t[1:])
            if v is not None and v<50000:
                prices.append({"value":v,"cx":sp["cx"],"cy":sp["cy"],"x0":sp["x0"],"y0":sp["y0"],"x1":sp["x1"],"y1":sp["y1"]})
                used.add(i)
            continue
        if main is None: continue
        cents=None
        for j in range(i+1,len(spans)):
            if j in used or j==i: continue
            sj=spans[j]
            if sj["x0"]<main["x1"]-5: continue
            if sj["cy"]>main["cy"]+10: continue
            if abs(sj["x0"]-main["x1"])>15: continue
            if sj["text"].strip()=="90" and sj["size"]<main["size"]-3:
                cents="90"; used.add(j); break
        main_val=num(re.sub(r"[^\d]","",main["text"]))
        if main_val is None or main_val>=50000:
            used.discard(i); continue
        val=main_val+0.90 if cents else main_val
        x0=min(sp["x0"],main["x0"]); y0=min(sp["y0"],main["y0"])
        x1=max(sp["x1"],main["x1"]); y1=max(sp["y1"],main["y1"])
        prices.append({"value":val,"cx":(x0+x1)/2,"cy":(y0+y1)/2,"x0":x0,"y0":y0,"x1":x1,"y1":y1})
        used.add(i)

    # --- Codigos ---
    codes=[]
    for sp in spans:
        m=re.search(r"(?<!\d)(\d{5})(?!\d)",sp["text"])
        if m and m.group(1) in sql_set:
            codes.append({"code":m.group(1),"cx":sp["cx"],"cy":sp["cy"],"x0":sp["x0"],"x1":sp["x1"]})

    # --- Precio normal = el precio MAXIMO cerca del codigo debajo de el (el promo siempre es menor) ---
    for cd in codes:
        code_key=cd["code"]; cx,cy=cd["cx"],cd["cy"]
        best=None
        for p in prices:
            dy=p["cy"]-cy
            if dy<-30 or dy>320: continue  # cerca del codigo, debajo (o ligeramente arriba)
            if abs(p["cx"]-cx)>100:  # ventana x ajustada para no agarrar vecinos
                continue
            if best is None or p["value"]>best["value"]:
                best=p
        if best is None: continue
        info={"normal":round(best["value"],2),"page":page_num}
        prev=results.get(code_key)
        # preferir el que tenga un valor mayor (mas probablemente el normal)
        if prev is None or best["value"]>prev["normal"]:
            results[code_key]=info

doc.close()
with open(OUT_JSON,"w",encoding="utf-8") as f:
    json.dump(results,f,ensure_ascii=False,indent=2)

# Reporte
lines=[]; lines.append("="*100); lines.append("REPORTE PRECIOS NORMALES"); lines.append("="*100)
encontrados=0; cambiados=0; iguales=0; difieren=[]; no_enc=[]
for code in sorted(sql_prices.keys()):
    sql_p=sql_prices[code]; info=results.get(code)
    if info and info["normal"] is not None:
        encontrados+=1
        if abs(info["normal"]-sql_p)<0.011: iguales+=1
        else:
            cambiados+=1; difieren.append((code,sql_p,info["normal"],info["page"]))
    else: no_enc.append((code,sql_p))
lines.append(f"Total SQL: {len(sql_prices)} | Encontrados: {encontrados} | Iguales(ya normal): {iguales} | A cambiar: {cambiados} | No enc: {len(no_enc)}")
lines.append("")
lines.append("--- PRECIOS A CAMBIAR (SQL actual -> normal catalogo) ---")
lines.append(f"{'Codigo':<8}{'Nombre':<32}{'SQL':>10}{'Normal':>10}{'Pag':>5}")
for c,sp,np_,pg in difieren:
    lines.append(f"{c:<8}{sql_names[c][:30]:<32}{sp:>10.2f}{np_:>10.2f}{pg:>5}")
lines.append("")
lines.append("--- NO ENCONTRADOS ---")
for c,sp in no_enc:
    lines.append(f"{c}  {sql_names[c][:30]:<32} SQL={sp}")
with open(OUT_REPORT,"w",encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"Encontrados: {encontrados}/{len(sql_prices)} | Iguales: {iguales} | A cambiar: {cambiados} | No enc: {len(no_enc)}")
# verificar ejemplos del usuario
for c in ['26813','26987']:
    print(f"  {c} {sql_names[c]}: SQL={sql_prices[c]} -> normal={results.get(c,{}).get('normal')}")
