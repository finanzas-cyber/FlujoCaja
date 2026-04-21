#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

python manage.py loaddata conceptos.json
python manage.py loaddata movimientos_2025_2026.json
python manage.py cargar_datos