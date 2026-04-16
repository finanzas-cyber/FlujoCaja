#!/usr/bin/env bash

python manage.py migrate
python manage.py flush --no-input

python manage.py loaddata conceptos_ok.json
python manage.py loaddata cuentas_ok.json
python manage.py loaddata movimientos_ok.json
python manage.py loaddata proyecciones_ok.json