from django.core.management.base import BaseCommand
from django.core.management import call_command
from flujo.models import Proyeccion
import os

class Command(BaseCommand):
    help = 'Limpia la base de datos y carga el JSON de proyecciones'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Iniciando limpieza de Proyecciones...'))
        
        # 1. Borrar proyecciones existentes para evitar conflictos
        cantidad, _ = Proyeccion.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'Se eliminaron {cantidad} registros antiguos.'))

        # 2. Cargar el archivo JSON
        archivo_fixture = 'proyecciones_ok.json'
        
        if os.path.exists(archivo_fixture):
            self.stdout.write(f'Cargando datos desde {archivo_fixture}...')
            try:
                # El comando loaddata de Django ahora entrará a una tabla limpia
                call_command('loaddata', archivo_fixture)
                self.stdout.write(self.style.SUCCESS('¡Datos cargados exitosamente!'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error al cargar: {e}'))
        else:
            self.stdout.write(self.style.ERROR(f'No se encontró el archivo {archivo_fixture}'))