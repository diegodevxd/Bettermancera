import fitz, re, json

PDF_PATH = "catalogo.pdf"
SQL_PATH = "productos.sql"
V5 = "precios_catalogo_v5.json"
OUT = "verificacion_diferencias.txt"

sql_prices={}; sql_names={}
with open(SQL_PATH,encoding="utf-8") as f:
    for line in f:
        m=re.search(r"\('(\d{5})',\s*'([^']*)',\s*([\d.]+)\)",line)
        if m: sql_prices[m.group(1)]=float(m.group(3)); sql_names[m.group(1)]=m.group(2)
sql_set=set(sql_prices.keys())
res=json.load(open(V5,encoding="utf-8"))

# diferencias
dif=[]
for code in sorted(sql_prices):
    info=res.get(code)
    if info and info["canonico"] is not None and abs(info["canonico"]-sql_prices[code])>=0.011:
        dif.append((code, info["page"]))
print("Diferencias a verificar:", len(dif))

def num(s):
    s=s.replace(",","").strip()
    try:return float(s)
    except:return None

doc=fitz.open(PDF_PATH)
out=[]
for code, pagenum in dif:
    page=doc[pagenum-1]
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
    # encontrar el codigo
    codes=[]
    for sp in spans:
        m=re.search(r"(?<!\d)(\d{5})(?!\d)",sp["text"])
        if m and m.group(1) in sql_set:
            codes.append({"code":m.group(1),"cx":sp["cx"],"cy":sp["cy"],"x0":sp["x0"],"x1":sp["x1"]})
    codes.sort(key=lambda c:c["cy"])
    # encontrar el codigo objetivo
    target=None
    for i,c in enumerate(codes):
        if c["code"]==code:
            target=(i,c); break
    if target is None:
        out.append(f"\n##### {code} {sql_names[code]} SQL={sql_prices[code]} pag={pagenum} -- CODIGO NO HALLADO EN PAGINA")
        continue
    i,cd=target
    # card: de cd.cy al siguiente codigo en columna
    bottom=cd["cy"]+600
    for nxt in codes[i+1:]:
        if nxt["cy"]<=cd["cy"]: continue
        if abs(nxt["cx"]-cd["cx"])>250: continue
        bottom=nxt["cy"]; break
    # spans en la card
    card=[sp for sp in spans if sp["cy"]>=cd["cy"]-25 and sp["cy"]<=bottom-5 and (abs(sp["cx"]-cd["cx"])<350)]
    card.sort(key=lambda s:s["cy"])
    info=res.get(code)
    out.append(f"\n##### {code} {sql_names[code]}  SQL={sql_prices[code]}  pag={pagenum}")
    out.append(f"    v5: regular={info.get('regular')} promo={info.get('promo')} canonico={info.get('canonico')} tipo={info.get('tipo')} #precios={info.get('np')}")
    out.append(f"    card: y={cd['cy']:.0f}..{bottom:.0f}  cx={cd['cx']:.0f}")
    for sp in card:
        t=sp["text"].strip()
        # marcar precios y textos clave
        flag=""
        if t.startswith("$") or t=="$" or re.match(r"^\d",t) and sp["size"]>=22: flag="  <-- PRECIO?"
        if "comprar" in t.lower() or "producto" in t.lower(): flag="  <-- PROMO MARKER"
        out.append(f"      y={sp['cy']:.0f} x={sp['cx']:.0f} sz={sp['size']:.0f} '{t}'{flag}")
with open(OUT,"w",encoding="utf-8") as f:
    f.write("\n".join(out))
print("Escrito:",OUT)
