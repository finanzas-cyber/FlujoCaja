import json

def limpiar_proyecciones(archivo):
    try:
        # Usamos utf-8-sig por si acaso quedó algún rastro del BOM de PowerShell
        with open(archivo, 'r', encoding='utf-8-sig') as f:
            datos = json.load(f)
        
        datos_limpios = []
        borrados_nulos = 0
        borrados_invalidos = 0
        
        for reg in datos:
            if reg['model'] == 'flujo.proyeccion':
                concepto_id = reg['fields'].get('concepto')
                
                # REGLA 1: No nulos
                if concepto_id is None:
                    borrados_nulos += 1
                    continue
                
                # REGLA 2: No permitir el ID fantasma 999999
                if concepto_id == 999999:
                    borrados_invalidos += 1
                    continue
                
                datos_limpios.append(reg)
            else:
                datos_limpios.append(reg)

        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(datos_limpios, f, indent=4, ensure_ascii=False)
        
        print(f"--- Limpieza terminada ---")
        print(f"Borrados por Nulos: {borrados_nulos}")
        print(f"Borrados por ID 999999: {borrados_invalidos}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    limpiar_proyecciones('proyecciones_ok.json')