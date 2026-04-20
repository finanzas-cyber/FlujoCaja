#!/usr/bin/env bash
# exit on error
set -o errexit

# Instalar dependencias
pip install -r requirements.txt

# Recolectar archivos estáticos
python manage.py collectstatic --no-input

# Correr migraciones (por si hay cambios en las tablas)
python manage.py migrate

# EJECUTAR TU NUEVO COMANDO AUTOMÁTICO
# Esto borrará la basura y cargará el JSON limpio
python manage.py cargar_datos