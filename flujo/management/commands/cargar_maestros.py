from django.core.management.base import BaseCommand
from flujo.models import Concepto, CuentaBanco


class Command(BaseCommand):
    help = "Carga datos maestros iniciales"

    def handle(self, *args, **kwargs):
        self.stdout.write("Cargando conceptos...")

        conceptos = [
            ("ING", "INGRESO", Concepto.TIPO_INGRESO),
            ("EGR", "EGRESO", Concepto.TIPO_EGRESO),
            ("FIN", "FINANCIAMIENTO", Concepto.TIPO_FINANCIAMIENTO),
            ("EXC", "EXCLUIR", Concepto.TIPO_EXCLUIR),
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
                self.stdout.write(f"✔ Concepto creado: {codigo}")
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
                self.stdout.write(f"✔ Cuenta banco creada: {codigo}")
            else:
                self.stdout.write(f"- Ya existe cuenta banco: {codigo}")

        self.stdout.write(self.style.SUCCESS("✔ Datos maestros cargados"))