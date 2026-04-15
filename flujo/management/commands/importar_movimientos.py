from decimal import Decimal

import pyodbc
from django.core.management.base import BaseCommand

from flujo.models import Concepto, CuentaBanco, Movimiento


class Command(BaseCommand):
    help = "Importa movimientos desde Softland CWMOVIM solo para 2026"

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
            WHERE CpbAno = '2026'
            ORDER BY CpbFec, CpbNum
        """)

        importados = 0
        repetidos = 0
        ignorados = 0
        procesados = 0

        ultimo_cpbnum = None  # 🔥 clave

        for row in cursor.fetchall():
            procesados += 1

            if procesados % 500 == 0:
                self.stdout.write(
                    f"Procesados: {procesados} | Importados: {importados} | Repetidos: {repetidos} | Ignorados: {ignorados}"
                )

            pctcod = (row.PctCod or "").strip()
            cpbnum = (row.CpbNum or "").strip()

            # 🔥 ARRASTRE DE COMPROBANTE
            if cpbnum:
                ultimo_cpbnum = cpbnum
            else:
                cpbnum = ultimo_cpbnum

            fecha = row.CpbFec
            anio = int(str(row.CpbAno).strip()) if row.CpbAno else 0
            mes = int(str(row.CpbMes).strip()) if row.CpbMes else 0
            mov_debe = Decimal(str(row.MovDebe or 0))
            mov_haber = Decimal(str(row.MovHaber or 0))
            descripcion = (row.MovGlosa or "").strip()
            cajcod = (row.CajCod or "").strip()

            cuenta_banco = cuentas.get(pctcod)
            if not cuenta_banco:
                ignorados += 1
                continue

            concepto = conceptos.get(cajcod)

            fecha_guardar = fecha.date() if hasattr(fecha, "date") else fecha

            existe = Movimiento.objects.filter(
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
            ).exists()

            if existe:
                repetidos += 1
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
            )
            importados += 1

        conn.close()

        self.stdout.write(self.style.SUCCESS(
            f"Importacion terminada. Procesados: {procesados}, Importados: {importados}, Repetidos: {repetidos}, Ignorados: {ignorados}"
        ))