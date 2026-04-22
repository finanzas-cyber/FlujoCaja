import json
from flujo.models import Concepto

p = 'proyecciones_ok.json'

with open(p, encoding='utf-8') as f:
    data = json.load(f)

limpio = []
eliminados = []

for x in data:
    valor = str(x['fields'].get('concepto', '')).strip()

    # solo aceptar números reales
    try:
        codigo = int(valor)
        limpio.append(x)
    except:
        eliminados.append((x.get('pk'), valor))

print('eliminados_no_numericos:', eliminados)

mapa = {int(c.codigo): c.id for c in Concepto.objects.all()}

faltantes = sorted({
    int(x['fields']['concepto'])
    for x in limpio
    if int(x['fields']['concepto']) not in mapa
})

print('faltantes:', faltantes)

for x in limpio:
    codigo = int(str(x['fields']['concepto']).strip())
    x['fields']['concepto'] = mapa[codigo]

with open(p, 'w', encoding='utf-8') as f:
    json.dump(limpio, f, indent=2, ensure_ascii=False)

print('convertido_ok')