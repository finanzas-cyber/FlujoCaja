from django.core.management.base import BaseCommand
from flujo.models import Concepto


class Command(BaseCommand):
    help = "Carga conceptos base de flujo de caja"

    def handle(self, *args, **kwargs):

        datos = [
            # INGRESOS
            ("100101", "CULTIVOS ANUALES", Concepto.TIPO_INGRESO),
            ("100102", "ARANDANO NACIONAL", Concepto.TIPO_INGRESO),
            ("100103", "MANZANA NACIONAL", Concepto.TIPO_INGRESO),
            ("100104", "EXPORTACION ARANDANOS", Concepto.TIPO_INGRESO),
            ("100105", "PACKING MANZANOS", Concepto.TIPO_INGRESO),
            ("100106", "SERVICIOS", Concepto.TIPO_INGRESO),

            # EGRESOS
            ("200101", "MANO DE OBRA", Concepto.TIPO_EGRESO),
            ("200102", "IMPOSICIONES", Concepto.TIPO_EGRESO),
            ("200103", "FINIQUITOS", Concepto.TIPO_EGRESO),
            ("200104", "TRASLADO PERSONAL", Concepto.TIPO_EGRESO),
            ("200105", "EMBALAJES", Concepto.TIPO_EGRESO),
            ("200106", "INSUMOS AGRICOLAS", Concepto.TIPO_EGRESO),
            ("200107", "ENERGIA Y COMBUSTIBLE", Concepto.TIPO_EGRESO),
            ("200108", "MANTENCIONES", Concepto.TIPO_EGRESO),
            ("200109", "ARRIENDO PREDIOS Y OTROS", Concepto.TIPO_EGRESO),
            ("200110", "FLETES A PUERTO", Concepto.TIPO_EGRESO),
            ("200111", "SEGUROS", Concepto.TIPO_EGRESO),
            ("200112", "GASTOS ADUANA-SAG-EXP", Concepto.TIPO_EGRESO),
            ("200113", "SERVICIOS EXTERNOS", Concepto.TIPO_EGRESO),
            ("200114", "INVERSIONES", Concepto.TIPO_EGRESO),
            ("200115", "OTROS COSTOS AGRICOLAS", Concepto.TIPO_EGRESO),
            ("200116", "OTROS GASTOS ADMINISTRACION", Concepto.TIPO_EGRESO),
            ("200117", "DEUDAS TEMPORADA ANTERIOR", Concepto.TIPO_EGRESO),
            ("200118", "IVA CF PAGADO", Concepto.TIPO_EGRESO),
            ("200119", "PAGO IMPUESTOS", Concepto.TIPO_EGRESO),

            # FINANCIAMIENTO
            ("300101", "PANEL SOLAR", Concepto.TIPO_FINANCIAMIENTO),
            ("300102", "CONTROL DE HELADA", Concepto.TIPO_FINANCIAMIENTO),
            ("300103", "(Fogape)// RIEGO COBERTURA", Concepto.TIPO_FINANCIAMIENTO),
            ("300104", "TRACTOR", Concepto.TIPO_FINANCIAMIENTO),
            ("300105", "DEV. MAURO", Concepto.TIPO_FINANCIAMIENTO),
            ("300106", "PAE", Concepto.TIPO_FINANCIAMIENTO),
            ("300107", "NUEVO PAE", Concepto.TIPO_FINANCIAMIENTO),
            ("300108", "PRESTAMO MAURO", Concepto.TIPO_FINANCIAMIENTO),
            ("300109", "VENTA DE ACTIVO", Concepto.TIPO_FINANCIAMIENTO),

            # EXCLUIR
            ("400101", "TRASPASO ENTRE CUENTAS", Concepto.TIPO_EXCLUIR),
        ]

        creados = 0
        actualizados = 0

        for codigo, nombre, tipo in datos:
            obj, created = Concepto.objects.update_or_create(
                codigo=codigo,
                defaults={
                    "nombre": nombre,
                    "tipo": tipo,
                    "activo": True,
                }
            )

            if created:
                creados += 1
            else:
                actualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f"Conceptos cargados. Nuevos: {creados}, actualizados: {actualizados}"
        ))