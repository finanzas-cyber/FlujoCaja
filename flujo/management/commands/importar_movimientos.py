from decimal import Decimal
import hashlib

import pyodbc
from django.core.management.base import BaseCommand

from flujo.models import Concepto, CuentaBanco, Movimiento


class Command(BaseCommand):
    help = "Importa movimientos desde Softland CWMOVIM para 2025 S2 y 2026"

    def handle(self, *args, **kwargs):
        ruta_mdb = r"W:\SOFTLAND\DATOS\SLHOE5\Sodatos.mdb"

        cuentas = {
            c.codigo: c
            for c in CuentaBanco.objects.filter(activo=True)
        }

        conceptos = {
            c.codigo: c
            for c in Concepto.objects.filter(activo=True)
        }

        if not cuentas:
            self.stdout.write(self.style.ERROR(
                "No existen cuentas banco activas cargadas en Django."
            ))
            return

        conn = pyodbc.connect(
            rf"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={ruta_mdb};"
        )

        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                PctCod,
                CpbNum,
                CpbFec,
                CpbAno,
                CpbMes,
                MovDebe,
                MovHaber,
                MovGlosa,
                CajCod
            FROM CWMOVIM
            WHERE
                (CpbAno = '2025' AND Val(CpbMes) >= 7)
                OR
                (CpbAno = '2026')
            ORDER BY CpbFec, CpbNum
        """)

        importados = 0
        actualizados = 0
        repetidos = 0
        ignorados = 0
        eliminados = 0
        procesados = 0
        self.stdout.write('Limpiando movimientos reales 2026...')
        Movimiento.objects.filter(anio=2026).delete()

        ultimo_cpbnum = None
        secuencia_por_grupo = {}
        origenes_vigentes = set()

        for row in cursor.fetchall():
            procesados += 1

            if procesados % 500 == 0:
                self.stdout.write(
                    "Procesados: "
                    f"{procesados} | Importados: {importados} | "
                    f"Actualizados: {actualizados} | Repetidos: {repetidos} | "
                    f"Ignorados: {ignorados}"
                )

            pctcod = (row.PctCod or "").strip()
            cpbnum = (row.CpbNum or "").strip()

            if cpbnum:
                ultimo_cpbnum = cpbnum
            else:
                cpbnum = ultimo_cpbnum or ""

            fecha = row.CpbFec
            anio = int(str(row.CpbAno).strip()) if row.CpbAno else 0
            mes = int(str(row.CpbMes).strip()) if row.CpbMes else 0
            mov_debe = Decimal(str(row.MovDebe or 0))
            mov_haber = Decimal(str(row.MovHaber or 0))
            descripcion = (row.MovGlosa or "").strip()
            cajcod = (row.CajCod or "").strip()

            cuenta_banco = cuentas.get(pctcod)
            if cpbnum == 'TU_NUMERO': self.stdout.write(f'--- REVISANDO: {cpbnum} | Cuenta: {pctcod} | CajCod: {cajcod} ---')
            if not cuenta_banco:
                ignorados += 1
                continue

            if cajcod == "0000000000":
                ignorados += 1
                continue

            if descripcion.upper() == "MOVIMIENTO DE APERTURA":
                ignorados += 1
                continue

            concepto = conceptos.get(cajcod)
            if not concepto:
                ignorados += 1
                continue

            fecha_guardar = fecha.date() if hasattr(fecha, "date") else fecha

            grupo = (
                pctcod,
                cpbnum,
                fecha_guardar.isoformat() if fecha_guardar else "",
            )
            secuencia_por_grupo[grupo] = secuencia_por_grupo.get(grupo, 0) + 1
            nro_linea = secuencia_por_grupo[grupo]

            origen_clave = f"{pctcod}|{cpbnum}|{fecha_guardar}|{nro_linea}"
            origenes_vigentes.add(origen_clave)

            texto_hash = "|".join([
                str(pctcod),
                str(cpbnum),
                str(fecha_guardar),
                str(anio),
                str(mes),
                str(mov_debe),
                str(mov_haber),
                descripcion,
                cajcod,
                str(concepto.id),
            ])
            origen_hash = hashlib.sha256(texto_hash.encode("utf-8")).hexdigest()

            movimiento = Movimiento.objects.filter(
                origen_clave=origen_clave
            ).first()

            if movimiento:
                if movimiento.origen_hash == origen_hash:
                    repetidos += 1
                    continue

                movimiento.cuenta_banco = cuenta_banco
                movimiento.concepto = concepto
                movimiento.fecha = fecha_guardar
                movimiento.anio = anio
                movimiento.mes = mes
                movimiento.cpbnum = cpbnum
                movimiento.mov_debe = mov_debe
                movimiento.mov_haber = mov_haber
                movimiento.descripcion = descripcion
                movimiento.cajcod = cajcod
                movimiento.origen_hash = origen_hash
                movimiento.save(update_fields=[
                    "cuenta_banco",
                    "concepto",
                    "fecha",
                    "anio",
                    "mes",
                    "cpbnum",
                    "mov_debe",
                    "mov_haber",
                    "descripcion",
                    "cajcod",
                    "origen_hash",
                ])
                actualizados += 1
                continue

            Movimiento.objects.create(
                cuenta_banco=cuenta_banco,
                concepto=concepto,
                fecha=fecha_guardar,
                anio=anio,
                mes=mes,
                cpbnum=cpbnum,
                mov_debe=mov_debe,
                mov_haber=mov_haber,
                descripcion=descripcion,
                cajcod=cajcod,
                origen_clave=origen_clave,
                origen_hash=origen_hash,
            )
            importados += 1

        conn.close()

        movimientos_a_eliminar = Movimiento.objects.exclude(
            origen_clave__in=origenes_vigentes
        ).exclude(
            origen_clave=""
        )
        eliminados = movimientos_a_eliminar.count()
        if eliminados:
            movimientos_a_eliminar.delete()

        self.stdout.write(self.style.SUCCESS(
            "Importacion terminada. "
            f"Procesados: {procesados}, "
            f"Importados: {importados}, "
            f"Actualizados: {actualizados}, "
            f"Repetidos: {repetidos}, "
            f"Ignorados: {ignorados}, "
            f"Eliminados: {eliminados}"
        ))
