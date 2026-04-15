from django.core.management.base import BaseCommand
from flujo.models import CuentaBanco


class Command(BaseCommand):
    help = "Carga cuentas banco y nómina"

    def handle(self, *args, **kwargs):

        datos = [
            # BANCOS
            ("1-1-01-10", "BANCO CHILE"),
            ("1-1-01-11", "BANCO CHILE USD"),
            ("1-1-01-12", "BANCO SECURITY"),
            ("1-1-01-13", "BANCO BCI"),
            ("1-1-01-14", "BANCO BCI USD"),
            ("1-1-01-15", "BANCO BCI EURO"),
            ("1-1-01-16", "BANCO SCOTIABANK"),
            ("1-1-01-17", "BANCO SCOTIABANK USD"),
            ("1-1-01-18", "BANCO SCOTIABANK EURO"),
            ("1-1-01-19", "BANCO ITAU"),
            ("1-1-01-20", "BANCO ITAU USD"),
            ("1-1-01-21", "BANCO ESTADO"),

            # NOMINA
            ("2-1-05-21", "NOMINA BANCO CHILE"),
            ("2-1-05-22", "NOMINA BANCO BCI"),
            ("2-1-05-23", "NOMINA SCOTIABANK"),
            ("2-1-05-24", "NOMINA ITAU"),
        ]

        creados = 0
        actualizados = 0

        for codigo, nombre in datos:
            obj, created = CuentaBanco.objects.update_or_create(
                codigo=codigo,
                defaults={
                    "nombre": nombre,
                    "activo": True,
                }
            )

            if created:
                creados += 1
            else:
                actualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f"Cuentas cargadas. Nuevas: {creados}, actualizadas: {actualizados}"
        ))