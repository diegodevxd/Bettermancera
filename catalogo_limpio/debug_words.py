import fitz
import re

PDF_PATH = "catalogo.pdf"
doc = fitz.open(PDF_PATH)

for pidx in [7, 10]:  # pagina 8 y 11
    page = doc[pidx]
    words = page.get_text("words")
    print(f"\n===== PAGINA {pidx+1} =====  ({len(words)} words)")
    for w in words:
        # w = (x0,y0,x1,y1,word,block,line,wordno)
        txt = w[4]
        print(f"({w[0]:.0f},{w[1]:.0f},{w[2]:.0f},{w[3]:.0f}) '{txt}'")
