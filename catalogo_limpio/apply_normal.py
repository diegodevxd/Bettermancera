import re, json

SQL_PATH = "productos.sql"
JSON_PATH = "precios_normales.json"

# Overrides manuales (code -> precio normal correcto)
# 26400: centavos falsos (119.90 -> 119)
# 26405: por nombre 'Organi Rollo Black' (catalog 26408 normal=119), no el 269 del codigo
# 26844: por nombre 'Canasta Black' (catalog 20844 normal=259), no el 399 del codigo
# 25432: por nombre 'Protecti Desague Max' (catalog 23332 normal=34.90), no encontrado
# 26005: dejar 400 (banner "a solo $400", normal no disponible en catalogo)
OVERRIDES = {
    "26400": 119.0,
    "26405": 119.0,
    "26844": 259.0,
    "25432": 34.9,
    "26005": 400.0,
}

normales = json.load(open(JSON_PATH, encoding="utf-8"))

def fmt_price(v):
    # mantener formato: enteros con .0, decimales con .9 etc.
    if abs(v - round(v)) < 0.001:
        return f"{round(v):.1f}"
    # si tiene .9 (centavos), mostrar con un decimal
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    # asegurar al menos un decimal
    if "." not in s:
        s += ".0"
    return s

lines_out = []
cambios = 0
with open(SQL_PATH, encoding="utf-8") as f:
    for line in f:
        m = re.search(r"^(\(')(\d{5})(',\s*')([^']*)(',\s*)([\d.]+)(\),?)$", line.rstrip("\n"))
        if not m:
            lines_out.append(line.rstrip("\n"))
            continue
        prefix, code, mid, name, mid2, old_price, suffix = m.groups()
        old_p = float(old_price)
        # determinar nuevo precio
        if code in OVERRIDES:
            new_p = OVERRIDES[code]
        elif code in normales and normales[code].get("normal") is not None:
            new_p = normales[code]["normal"]
        else:
            new_p = old_p  # no encontrado: mantener
        if abs(new_p - old_p) > 0.011:
            cambios += 1
        lines_out.append(f"{prefix}{code}{mid}{name}{mid2}{fmt_price(new_p)}{suffix}")

with open(SQL_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(lines_out) + "\n")

print(f"Productos procesados. Precios cambiados: {cambios}")
# verificar ejemplos
for code in ["26813","26987","26812","24526","26405","26844","26400","25432","26005"]:
    for l in lines_out:
        if f"'{code}'," in l:
            print(" ", l.strip())
            break
