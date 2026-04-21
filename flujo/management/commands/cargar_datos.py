from django.core.management.base import BaseCommand
from django.core.management import call_command
from flujo.models import Proyeccion
import os

class Command(BaseCommand):
    help = 'Limpia la base de datos y carga el JSON de proyecciones'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando limpieza de Proyecciones...')

        cantidad, _ = Proyeccion.objects.all().delete()
        self.stdout.write(f'Se eliminaron {cantidad} registros antiguos.')

        base_dir = os.path.dirname(
                       os.path.dirname(
                           os.path.dirname(
                               os.path.dirname(
                                   os.path.abspath(__file__)))))

        archivo_fixture = os.path.join(base_dir, 'proyecciones_ok.json')

        self.stdout.write(f'Buscando fixture en: {archivo_fixture}')

        if os.path.exists(archivo_fixture):
            self.stdout.write('Archivo encontrado. Cargando...')
            try:
                call_command('loaddata', archivo_fixture)
                self.stdout.write('Datos cargados exitosamente!')
            except Exception as e:
                self.stdout.write(f'ERROR al cargar: {e}')
                raise
        else:
            self.stdout.write(f'ERROR: No se encontro el archivo en {archivo_fixture}')
            raise FileNotFoundError(f'Fixture no encontrado: {archivo_fixture}')