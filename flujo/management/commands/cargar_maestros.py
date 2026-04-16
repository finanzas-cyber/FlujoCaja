from django.core.management.base import BaseCommand
from flujo.models import Concepto, CuentaBanco


class Command(BaseCommand):
    help = "Carga datos maestros iniciales"

    def handle(self, *args, **kwargs):
        self.stdout.write("Cargando conceptos...")

        conceptos = [
            ("100101", "CULTIVOS ANUALES", Concepto.TIPO_INGRESO),
            ("100102", "ARANDANO NACIONAL", Concepto.TIPO_INGRESO),
            ("100103", "MANZANA NACIONAL", Concepto.TIPO_INGRESO),
            ("100104", "EXPORTACION ARANDANOS", Concepto.TIPO_INGRESO),
            ("100105", "PACKING MANZANOS", Concepto.TIPO_INGRESO),
            ("100106", "SERVICIOS", Concepto.TIPO_INGRESO),

            ("200101", "MANO DE OBRA", Concepto.TIPO_EGRESO),
            ("200102", "IMPOSICIONES", Concepto.TIPO_EGRESO),
            ("200103", "FINIQUITOS", Concepto.TIPO_EGRESO),
            ("200104", "TRASLADOS", Concepto.TIPO_EGRESO),
            ("200105", "MAQUINARIA", Concepto.TIPO_EGRESO),
            ("200106", "COMBUSTIBLES Y LUBRICANTES", Concepto.TIPO_EGRESO),
            ("200107", "MANTENCION Y REPARACION", Concepto.TIPO_EGRESO),
            ("200108", "MATERIALES DE EMBALAJE", Concepto.TIPO_EGRESO),
            ("200109", "AGROQUIMICOS", Concepto.TIPO_EGRESO),
            ("200110", "FERTILIZANTES", Concepto.TIPO_EGRESO),
            ("200111", "RIEGO", Concepto.TIPO_EGRESO),
            ("200112", "GASTOS GENERALES", Concepto.TIPO_EGRESO),
            ("200113", "HONORARIOS", Concepto.TIPO_EGRESO),
            ("200114", "SERVICIOS BASICOS", Concepto.TIPO_EGRESO),
            ("200115", "SEGUROS", Concepto.TIPO_EGRESO),
            ("200116", "ARRIENDOS", Concepto.TIPO_EGRESO),
            ("200117", "CONTRIBUCIONES", Concepto.TIPO_EGRESO),
            ("200118", "PATENTES Y PERMISOS", Concepto.TIPO_EGRESO),
            ("200119", "GASTOS BANCARIOS", Concepto.TIPO_EGRESO),
            ("200120", "INTERESES", Concepto.TIPO_EGRESO),
            ("200121", "IMPUESTOS", Concepto.TIPO_EGRESO),
            ("200122", "IVA NO RECUPERABLE", Concepto.TIPO_EGRESO),
            ("200123", "OTROS EGRESOS", Concepto.TIPO_EGRESO),

            ("800010", "MONEY MARKET", Concepto.TIPO_FINANCIAMIENTO),
            ("800020", "PRESTAMOS", Concepto.TIPO_FINANCIAMIENTO),
            ("800030", "APORTES", Concepto.TIPO_FINANCIAMIENTO),
            ("800040", "RETIROS", Concepto.TIPO_FINANCIAMIENTO),
            ("800050", "TRASPASOS", Concepto.TIPO_FINANCIAMIENTO),
            ("800100", "RECUPERACION IVA EXP", Concepto.TIPO_INGRESO),

            ("0000000000", "EXCLUIR", Concepto.TIPO_EXCLUIR),
        ]

        for codigo, nombre, tipo in conceptos:
            obj, created = Concepto.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nombre": nombre,
                    "tipo": tipo,
                    "activo": True,
                },
            )
            if created:
                self.stdout.write(f"Concepto creado: {codigo}")
            else:
                actualizado = False
                if obj.nombre != nombre:
                    obj.nombre = nombre
                    actualizado = True
                if obj.tipo != tipo:
                    obj.tipo = tipo
                    actualizado = True
                if obj.activo is not True:
                    obj.activo = True
                    actualizado = True
                if actualizado:
                    obj.save()
                    self.stdout.write(f"Concepto actualizado: {codigo}")
                else:
                    self.stdout.write(f"- Ya existe: {codigo}")

        self.stdout.write("Cargando cuentas banco...")

        cuentas_banco = [
            ("1-1-01-10", "1-1-01-10"),
            ("1-1-01-11", "1-1-01-11"),
            ("1-1-01-13", "1-1-01-13"),
            ("1-1-01-16", "1-1-01-16"),
            ("1-1-01-19", "1-1-01-19"),
            ("2-1-05-21", "2-1-05-21"),
            ("1-1-01-17", "1-1-01-17"),
            ("1-1-01-20", "1-1-01-20"),
            ("1-1-01-14", "1-1-01-14"),
            ("2-1-05-24", "2-1-05-24"),
        ]

        for codigo, nombre in cuentas_banco:
            obj, created = CuentaBanco.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nombre": nombre,
                    "activo": True,
                },
            )
            if created:
                self.stdout.write(f"Cuenta banco creada: {codigo}")
            else:
                actualizado = False
                if obj.nombre != nombre:
                    obj.nombre = nombre
                    actualizado = True
                if obj.activo is not True:
                    obj.activo = True
                    actualizado = True
                if actualizado:
                    obj.save()
                    self.stdout.write(f"Cuenta banco actualizada: {codigo}")
                else:
                    self.stdout.write(f"- Ya existe cuenta banco: {codigo}")

        self.stdout.write(self.style.SUCCESS("Datos maestros cargados"))