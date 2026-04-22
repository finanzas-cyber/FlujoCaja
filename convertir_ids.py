import json
from flujo.models import Concepto

p = 'proyecciones_ok.json'

with open(p, encoding='utf-8') as f:
    data = json.load(f)

# mapa codigo -> id
mapa = {str(c.codigo): c.id for c in Concepto.objects.all()}

faltantes = []

for x in data:
    codigo = str(x['fields']['concepto']).strip()

    if codigo not in mapa:
        faltantes.append(codigo)
    else:
        x['fields']['concepto'] = mapa[codigo]

print("faltantes:", sorted(set(faltantes)))

with open(p, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("convertido_ok")