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

        CuentaBanco.objects.get_or_create(
            codigo="001",
            defaults={
                "nombre": "BANCO PRINCIPAL",
                "activo": True,
            },
        )

        self.stdout.write(self.style.SUCCESS("✔ Datos maestros cargados"))