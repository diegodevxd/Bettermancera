import os, re
sql = set()
for l in open('productos.sql', encoding='utf-8'):
    m = re.search(r"\('(\d{5})'", l)
    if m:
        sql.add(m.group(1))
ex = set(f[:5] for f in os.listdir('fotos_catalogo') if f.endswith('.png'))
print('Productos SQL:', len(sql))
print('Con foto:', len(ex & sql))
print('Sin foto:', len(sql - ex))
print('Sin foto:', sorted(sql - ex))
