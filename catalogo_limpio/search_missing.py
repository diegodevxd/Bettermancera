import fitz, re

PDF_PATH = "catalogo.pdf"
doc = fitz.open(PDF_PATH)

# productos a localizar por nombre (no encontrados o mismatch)
targets = {
    "20223": "Cepillo WC Flex",
    "23734": "Converti Pañalera",
    "25133": "Mechu Mop",
    "26005": "Cubi Hielos",
    "26997": "Tina Spa",
    "26844": "Canasta Black",
    "26405": "Organi Rollo Black",
    "20224": "Cepillo Conmigo",
    "25432": "Protecti Desag",
    "25966": "Luz Noche",
}

for code, name in targets.items():
    print(f"\n===== {code} '{name}' =====")
    # buscar paginas que contienen el nombre
    pages = []
    for pidx in range(len(doc)):
        t = doc[pidx].get_text()
        if name.lower() in t.lower():
            pages.append(pidx)
    if not pages:
        print("  NO HALLADO en texto del PDF")
        continue
    for pidx in pages[:3]:
        page = doc[pidx]
        d = page.get_text("dict")
        spans = []
        for b in d["blocks"]:
            if "lines" not in b: continue
            for l in b["lines"]:
                for s in l["spans"]:
                    if s["text"].strip():
                        spans.append({"x0":s["bbox"][0],"y0":s["bbox"][1],"x1":s["bbox"][2],"y1":s["bbox"][3],"text":s["text"],"size":s["size"],"cx":(s["bbox"][0]+s["bbox"][2])/2,"cy":(s["bbox"][1]+s["bbox"][3])/2})
        # buscar el span con el nombre
        for sp in spans:
            if name.lower() in sp["text"].lower():
                nx, ny = sp["cx"], sp["cy"]
                # buscar codigo (5 digitos) cercano arriba y precios cercanos
                nearby = [s for s in spans if abs(s["cy"]-ny)<200 and abs(s["cx"]-nx)<300]
                nearby.sort(key=lambda s:s["cy"])
                print(f"  pag {pidx+1}: nombre @ y={ny:.0f} x={nx:.0f}")
                for s in nearby:
                    t=s["text"].strip()
                    if re.fullmatch(r"\d{5}", t) or t.startswith("$") or (re.search(r"\d",t) and s["size"]>=22) or "comprar" in t.lower() or "producto" in t.lower():
                        print(f"    y={s['cy']:.0f} x={s['cx']:.0f} sz={s['size']:.0f} '{t}'")
                break
