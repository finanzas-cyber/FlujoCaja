from collections import OrderedDict
from decimal import Decimal
from io import StringIO
from pathlib import Path
from datetime import datetime
import subprocess

from django.contrib import messages
from django.core import serializers
from django.core.management import call_command
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Movimiento, Concepto, Proyeccion, ConfiguracionFlujo


def es_concepto_manual(concepto):
    if not concepto:
        return False
    nombre = (concepto.nombre or "").upper()
    return "CEREZA" in nombre


def actualizar_softland(request):
    if request.method != "POST":
        return redirect("inicio")

    salida = StringIO()

    try:
        call_command("importar_movimientos", stdout=salida)
        messages.success(
            request,
            "Actualización desde Softland realizada correctamente. " + salida.getvalue().strip()
        )
    except Exception as e:
        messages.error(request, f"Error al actualizar desde Softland: {e}")

    return redirect("inicio")


def generar_proyecciones_json(request):
    if request.method != "POST":
        return redirect("inicio")

    try:
        proyecciones = Proyeccion.objects.all().order_by("id")

        data = serializers.serialize(
            "json",
            proyecciones,
            indent=2,
            use_natural_foreign_keys=False,
        )

        ruta = Path("proyecciones_ok.json")
        ruta.write_text(data, encoding="utf-8")

        messages.success(request, "Archivo proyecciones_ok.json generado correctamente.")
    except Exception as e:
        messages.error(request, f"Error al generar JSON: {e}")

    return redirect("inicio")


def publicar_proyecciones(request):
    if request.method != "POST":
        return redirect("inicio")

    try:
        repo_root = Path(__file__).resolve().parent.parent
        ruta_json = repo_root / "proyecciones_ok.json"

        proyecciones = Proyeccion.objects.all().order_by("id")
        data = serializers.serialize(
            "json",
            proyecciones,
            indent=2,
            use_natural_foreign_keys=False,
        )
        ruta_json.write_text(data, encoding="utf-8")

        subprocess.run(
            ["git", "add", "proyecciones_ok.json"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )

        diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet", "--", "proyecciones_ok.json"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        if diff.returncode == 0:
            messages.success(
                request,
                "No había cambios nuevos en proyecciones_ok.json. No fue necesario publicar."
            )
            return redirect("inicio")

        commit_msg = "Publicar proyecciones " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        subprocess.run(
            ["git", "commit", "-m", commit_msg, "--", "proyecciones_ok.json"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )

        push = subprocess.run(
            ["git", "push"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )

        messages.success(
            request,
            "Proyecciones publicadas correctamente en GitHub. " + push.stdout.strip()
        )

    except subprocess.CalledProcessError as e:
        detalle = (e.stderr or e.stdout or str(e)).strip()
        messages.error(request, f"Error al publicar proyecciones: {detalle}")
    except Exception as e:
        messages.error(request, f"Error al publicar proyecciones: {e}")

    return redirect("inicio")


def guardar_proyeccion(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método no permitido"}, status=405)

    try:
        concepto_id = (request.POST.get("concepto_id") or "").strip()
        mes = (request.POST.get("mes") or "").strip()
        monto = (request.POST.get("monto") or "").strip()
        anio = (request.POST.get("anio") or "").strip()

        if not concepto_id or not mes:
            return JsonResponse({"ok": False, "error": "Faltan datos"}, status=400)

        concepto = Concepto.objects.get(id=int(concepto_id))

        if anio:
            anio_proyeccion = int(anio)
        else:
            mes_numero = int(mes)
            anio_proyeccion = 2026
            if 1 <= mes_numero <= 12:
                anio_proyeccion = 2026

        proyeccion, _ = Proyeccion.objects.get_or_create(
            concepto=concepto,
            anio=anio_proyeccion,
            mes=int(mes),
            defaults={
                "monto": Decimal("0"),
                "descripcion": "",
                "activo": True,
            },
        )

        proyeccion.monto = Decimal(monto or "0")
        proyeccion.activo = True
        proyeccion.save()

        return JsonResponse({"ok": True})

    except Concepto.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Concepto no existe"}, status=404)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


def guardar_movimiento_real(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método no permitido"}, status=405)

    try:
        concepto_id = int((request.POST.get("concepto_id") or "").strip())
        mes = int((request.POST.get("mes") or "").strip())
        anio = int((request.POST.get("anio") or "").strip())
        monto = Decimal((request.POST.get("monto") or "0").strip())

        movimientos = Movimiento.objects.filter(
            concepto_id=concepto_id,
            mes=mes,
            anio=anio,
        ).exclude(cajcod="0000000000").order_by("fecha", "id")

        if not movimientos.exists():
            return JsonResponse({"ok": False, "error": "No hay movimientos para editar"}, status=404)

        total_actual = sum((m.monto for m in movimientos), Decimal("0"))
        diferencia = monto - total_actual

        if diferencia == 0:
            return JsonResponse({"ok": True})

        movimiento = movimientos.first()

        if diferencia > 0:
            movimiento.mov_debe += diferencia
        else:
            movimiento.mov_haber += abs(diferencia)

        movimiento.save()

        return JsonResponse({"ok": True})

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


def guardar_configuracion_flujo(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método no permitido"}, status=405)

    try:
        campo = (request.POST.get("campo") or "").strip()
        monto = Decimal((request.POST.get("monto") or "0").strip())

        if campo not in ["saldo_inicial_base", "money_market_inicial_base"]:
            return JsonResponse({"ok": False, "error": "Campo inválido"}, status=400)

        config, _ = ConfiguracionFlujo.objects.get_or_create(
            id=1,
            defaults={
                "saldo_inicial_base": Decimal("143498696"),
                "money_market_inicial_base": Decimal("0"),
            },
        )

        setattr(config, campo, monto)
        config.save()

        return JsonResponse({"ok": True})

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


def detalle_movimientos_real(request):
    if request.method != "GET":
        return JsonResponse({"ok": False, "error": "Método no permitido"}, status=405)

    try:
        concepto_id = int((request.GET.get("concepto_id") or "").strip())
        mes = int((request.GET.get("mes") or "").strip())
        anio = int((request.GET.get("anio") or "2026").strip())

        concepto = Concepto.objects.get(id=concepto_id)

        movimientos = Movimiento.objects.select_related(
            "cuenta_banco",
            "concepto",
        ).filter(
            anio=anio,
            mes=mes,
            concepto_id=concepto_id,
        ).exclude(
            cajcod="0000000000"
        ).order_by(
            "fecha",
            "id",
        )

        data = []
        total = Decimal("0")

        for m in movimientos:
            monto = m.monto
            total += monto
            data.append({
                "fecha": m.fecha.strftime("%d-%m-%Y") if m.fecha else "",
                "cpbnum": m.cpbnum or "",
                "cuenta": m.cuenta_banco.codigo if m.cuenta_banco else "",
                "descripcion": m.descripcion or "",
                "monto": float(monto),
            })

        return JsonResponse({
            "ok": True,
            "concepto_id": concepto.id,
            "concepto_codigo": concepto.codigo,
            "concepto_nombre": concepto.nombre,
            "anio": anio,
            "mes": mes,
            "total": str(total),
            "movimientos": data,
        })

    except ValueError:
        return JsonResponse({"ok": False, "error": "Parámetros inválidos"}, status=400)
    except Concepto.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Concepto no existe"}, status=404)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


def inicio(request):
    config, _ = ConfiguracionFlujo.objects.get_or_create(
        id=1,
        defaults={
            "saldo_inicial_base": Decimal("143498696"),
            "money_market_inicial_base": Decimal("0"),
        },
    )

    saldo_inicial_base = config.saldo_inicial_base
    money_market_inicial_base = config.money_market_inicial_base

    hoy = timezone.localdate()
    anio_actual = 2026
    mes_actual = hoy.month if hoy.year == anio_actual else 4

    filtro = (request.GET.get("q") or "").strip()
    orden = (request.GET.get("orden") or "-fecha").strip()

    movimientos = Movimiento.objects.select_related(
        "cuenta_banco",
        "concepto",
    ).exclude(cajcod="0000000000")

    if filtro:
        movimientos = movimientos.filter(
            Q(descripcion__icontains=filtro)
            | Q(cpbnum__icontains=filtro)
            | Q(cuenta_banco__codigo__icontains=filtro)
            | Q(cajcod__icontains=filtro)
        )

    movimientos = movimientos.annotate(
        monto_calculado=F("mov_debe") - F("mov_haber")
    )

    ordenes_validos = {
        "fecha": ["fecha", "id"],
        "-fecha": ["-fecha", "-id"],
        "cpbnum": ["cpbnum", "-fecha", "-id"],
        "-cpbnum": ["-cpbnum", "-fecha", "-id"],
        "cuenta": ["cuenta_banco__codigo", "-fecha", "-id"],
        "-cuenta": ["-cuenta_banco__codigo", "-fecha", "-id"],
        "monto": ["monto_calculado", "-fecha", "-id"],
        "-monto": ["-monto_calculado", "-fecha", "-id"],
    }

    movimientos = movimientos.order_by(*ordenes_validos.get(orden, ["-fecha", "-id"]))

    movimientos_periodo = list(
        Movimiento.objects.select_related("concepto").filter(
            Q(anio=2025, mes__gte=7) | Q(anio=2026)
        ).exclude(cajcod="0000000000").order_by("anio", "mes", "fecha", "id")
    )

    proyecciones_periodo = list(
        Proyeccion.objects.select_related("concepto").filter(
            Q(anio=2025, mes__gte=7) | Q(anio=2026),
            activo=True,
        ).order_by("anio", "mes", "concepto__codigo", "id")
    )

    meses_base = [
        (2025, 7, "jul-25"),
        (2025, 8, "ago-25"),
        (2025, 9, "sep-25"),
        (2025, 10, "oct-25"),
        (2025, 11, "nov-25"),
        (2025, 12, "dic-25"),
        (2026, 1, "ene-26"),
        (2026, 2, "feb-26"),
        (2026, 3, "mar-26"),
        (2026, 4, "abr-26"),
        (2026, 5, "may-26"),
        (2026, 6, "jun-26"),
        (2026, 7, "jul-26"),
        (2026, 8, "ago-26"),
        (2026, 9, "sep-26"),
        (2026, 10, "oct-26"),
        (2026, 11, "nov-26"),
        (2026, 12, "dic-26"),
    ]

    periodos_con_reales = {(m.anio, m.mes) for m in movimientos_periodo}

    columnas_flujo = []
    for anio_columna, mes_numero, mes_nombre in meses_base:
        periodo = (anio_columna, mes_numero)

        if anio_columna == 2025:
            if periodo in periodos_con_reales:
                columnas_flujo.append({
                    "clave": f"{anio_columna}_{mes_numero}_real",
                    "anio": anio_columna,
                    "mes_numero": mes_numero,
                    "mes_nombre": mes_nombre,
                    "etiqueta": "REAL",
                    "origen": "REAL",
                    "es_mes_actual": False,
                })
            else:
                columnas_flujo.append({
                    "clave": f"{anio_columna}_{mes_numero}_proyectado",
                    "anio": anio_columna,
                    "mes_numero": mes_numero,
                    "mes_nombre": mes_nombre,
                    "etiqueta": "PROY.",
                    "origen": "PROYECTADO",
                    "es_mes_actual": False,
                })
        elif anio_columna < anio_actual or (anio_columna == anio_actual and mes_numero < mes_actual):
            columnas_flujo.append({
                "clave": f"{anio_columna}_{mes_numero}_real",
                "anio": anio_columna,
                "mes_numero": mes_numero,
                "mes_nombre": mes_nombre,
                "etiqueta": "REAL",
                "origen": "REAL",
                "es_mes_actual": False,
            })
        elif anio_columna == anio_actual and mes_numero == mes_actual:
            columnas_flujo.append({
                "clave": f"{anio_columna}_{mes_numero}_real",
                "anio": anio_columna,
                "mes_numero": mes_numero,
                "mes_nombre": mes_nombre,
                "etiqueta": "REAL",
                "origen": "REAL",
                "es_mes_actual": True,
            })
            columnas_flujo.append({
                "clave": f"{anio_columna}_{mes_numero}_proyectado",
                "anio": anio_columna,
                "mes_numero": mes_numero,
                "mes_nombre": mes_nombre,
                "etiqueta": "PROY.",
                "origen": "PROYECTADO",
                "es_mes_actual": True,
            })
        else:
            columnas_flujo.append({
                "clave": f"{anio_columna}_{mes_numero}_proyectado",
                "anio": anio_columna,
                "mes_numero": mes_numero,
                "mes_nombre": mes_nombre,
                "etiqueta": "PROY.",
                "origen": "PROYECTADO",
                "es_mes_actual": False,
            })

    conceptos_ingresos = list(
        Concepto.objects.filter(
            activo=True,
            tipo=Concepto.TIPO_INGRESO,
        ).order_by("codigo")
    )
    conceptos_egresos = list(
        Concepto.objects.filter(
            activo=True,
            tipo=Concepto.TIPO_EGRESO,
        ).order_by("codigo")
    )
    conceptos_financiamiento = list(
        Concepto.objects.filter(
            activo=True,
            tipo=Concepto.TIPO_FINANCIAMIENTO,
        ).exclude(codigo="999999").order_by("codigo")
    )

    money_market_concepto = Concepto.objects.filter(codigo="800010").first()
    money_market_concepto_id = money_market_concepto.id if money_market_concepto else None

    diferencia_tc_concepto = Concepto.objects.filter(codigo="999999").first()
    diferencia_tc_concepto_id = diferencia_tc_concepto.id if diferencia_tc_concepto else None

    montos_reales_por_concepto_mes = {}
    montos_proyectados_por_concepto_mes = {}
    montos_manuales_por_concepto_mes = {}

    totales_reales_mensuales = {}
    totales_proyectados_mensuales = {}
    totales_manuales_mensuales = {}

    money_market_real_mensual = {}
    money_market_proyectado_mensual = {}
    diferencia_tc_valores = {}

    for anio_columna, mes_numero, _ in meses_base:
        clave_periodo = (anio_columna, mes_numero)

        totales_reales_mensuales[clave_periodo] = {
            "ingresos": Decimal("0"),
            "egresos": Decimal("0"),
            "financiamiento": Decimal("0"),
            "excluir": Decimal("0"),
        }
        totales_proyectados_mensuales[clave_periodo] = {
            "ingresos": Decimal("0"),
            "egresos": Decimal("0"),
            "financiamiento": Decimal("0"),
            "excluir": Decimal("0"),
        }
        totales_manuales_mensuales[clave_periodo] = {
            "ingresos": Decimal("0"),
            "egresos": Decimal("0"),
            "financiamiento": Decimal("0"),
            "excluir": Decimal("0"),
        }
        money_market_real_mensual[clave_periodo] = Decimal("0")
        money_market_proyectado_mensual[clave_periodo] = Decimal("0")
        diferencia_tc_valores[clave_periodo] = Decimal("0")

    periodos_validos = {(anio_columna, mes_numero) for anio_columna, mes_numero, _ in meses_base}

    for m in movimientos_periodo:
        if not m.concepto or (m.anio, m.mes) not in periodos_validos:
            continue

        if diferencia_tc_concepto_id and m.concepto_id == diferencia_tc_concepto_id:
            continue

        # CEREZA ahora no se excluye

        key = (m.concepto_id, m.anio, m.mes)
        clave_periodo = (m.anio, m.mes)

        montos_reales_por_concepto_mes[key] = montos_reales_por_concepto_mes.get(key, Decimal("0")) + m.monto

        if m.concepto.tipo == Concepto.TIPO_INGRESO:
            totales_reales_mensuales[clave_periodo]["ingresos"] += m.monto
        elif m.concepto.tipo == Concepto.TIPO_EGRESO:
            totales_reales_mensuales[clave_periodo]["egresos"] += m.monto
        elif m.concepto.tipo == Concepto.TIPO_FINANCIAMIENTO:
            totales_reales_mensuales[clave_periodo]["financiamiento"] += m.monto
        elif m.concepto.tipo == Concepto.TIPO_EXCLUIR:
            totales_reales_mensuales[clave_periodo]["excluir"] += m.monto

        if money_market_concepto_id and m.concepto_id == money_market_concepto_id:
            money_market_real_mensual[clave_periodo] += m.monto

    for p in proyecciones_periodo:
        if not p.concepto or (p.anio, p.mes) not in periodos_validos:
            continue

        clave_periodo = (p.anio, p.mes)

        if es_concepto_manual(p.concepto):
            key = (p.concepto_id, p.anio, p.mes)
            montos_manuales_por_concepto_mes[key] = montos_manuales_por_concepto_mes.get(key, Decimal("0")) + p.monto

            if p.concepto.tipo == Concepto.TIPO_INGRESO:
                totales_manuales_mensuales[clave_periodo]["ingresos"] += p.monto
            elif p.concepto.tipo == Concepto.TIPO_EGRESO:
                totales_manuales_mensuales[clave_periodo]["egresos"] += p.monto
            elif p.concepto.tipo == Concepto.TIPO_FINANCIAMIENTO:
                totales_manuales_mensuales[clave_periodo]["financiamiento"] += p.monto
            elif p.concepto.tipo == Concepto.TIPO_EXCLUIR:
                totales_manuales_mensuales[clave_periodo]["excluir"] += p.monto
            continue

        key = (p.concepto_id, p.anio, p.mes)
        montos_proyectados_por_concepto_mes[key] = montos_proyectados_por_concepto_mes.get(key, Decimal("0")) + p.monto

        if diferencia_tc_concepto_id and p.concepto_id == diferencia_tc_concepto_id:
            diferencia_tc_valores[clave_periodo] += p.monto
        else:
            if p.concepto.tipo == Concepto.TIPO_INGRESO:
                totales_proyectados_mensuales[clave_periodo]["ingresos"] += p.monto
            elif p.concepto.tipo == Concepto.TIPO_EGRESO:
                totales_proyectados_mensuales[clave_periodo]["egresos"] += p.monto
            elif p.concepto.tipo == Concepto.TIPO_FINANCIAMIENTO:
                totales_proyectados_mensuales[clave_periodo]["financiamiento"] += p.monto
            elif p.concepto.tipo == Concepto.TIPO_EXCLUIR:
                totales_proyectados_mensuales[clave_periodo]["excluir"] += p.monto

        if money_market_concepto_id and p.concepto_id == money_market_concepto_id:
            money_market_proyectado_mensual[clave_periodo] += p.monto

    def construir_filas(conceptos, tipo_fila):
        filas = []

        for concepto in conceptos:
            es_manual = es_concepto_manual(concepto)

            fila = {
                "id": concepto.id,
                "codigo": concepto.codigo,
                "nombre": concepto.nombre,
                "tipo_fila": tipo_fila,
                "es_manual": es_manual,
                "columnas": [],
                "total": Decimal("0"),
            }

            for columna in columnas_flujo:
                if es_manual:
                    monto = montos_manuales_por_concepto_mes.get(
                        (concepto.id, columna["anio"], columna["mes_numero"]),
                        Decimal("0"),
                    )
                elif columna["origen"] == "REAL":
                    monto = montos_reales_por_concepto_mes.get(
                        (concepto.id, columna["anio"], columna["mes_numero"]),
                        Decimal("0"),
                    )
                else:
                    monto = montos_proyectados_por_concepto_mes.get(
                        (concepto.id, columna["anio"], columna["mes_numero"]),
                        Decimal("0"),
                    )

                fila["columnas"].append({
                    "clave": columna["clave"],
                    "anio": columna["anio"],
                    "mes_numero": columna["mes_numero"],
                    "mes_nombre": columna["mes_nombre"],
                    "etiqueta": columna["etiqueta"],
                    "origen": columna["origen"],
                    "es_mes_actual": columna["es_mes_actual"],
                    "monto": monto,
                    "tipo_fila": tipo_fila,
                })
                fila["total"] += monto

            filas.append(fila)

        return filas

    filas_ingresos = construir_filas(conceptos_ingresos, "ingreso")
    filas_egresos = construir_filas(conceptos_egresos, "egreso")
    filas_financiamiento = construir_filas(conceptos_financiamiento, "financiamiento")

    total_ingresos_fila = {"nombre": "TOTAL INGRESOS", "tipo_fila": "ingreso", "columnas": [], "total": Decimal("0")}
    total_egresos_fila = {"nombre": "TOTAL EGRESOS OPERACIONALES", "tipo_fila": "egreso", "columnas": [], "total": Decimal("0")}
    flujo_operacional_fila = {"nombre": "FLUJO OPERACIONAL", "tipo_fila": "resultado", "columnas": [], "total": Decimal("0")}
    flujo_financiamiento_fila = {"nombre": "FLUJO FINANCIAMIENTO", "tipo_fila": "financiamiento", "columnas": [], "total": Decimal("0")}
    total_mes_fila = {"nombre": "TOTAL DEL MES", "tipo_fila": "resultado", "columnas": [], "total": Decimal("0")}
    saldo_inicial_fila = {"nombre": "SALDO INICIAL", "tipo_fila": "saldo_inicial", "columnas": [], "total": Decimal("0")}
    saldo_disponible_banco_fila = {"nombre": "SALDO DISPONIBLE BANCO", "tipo_fila": "saldo_final", "columnas": [], "total": Decimal("0")}
    money_market_acumulado_fila = {"nombre": "MONEY MARKET ACUMULADO", "tipo_fila": "money_market", "columnas": [], "total": Decimal("0")}
    saldo_total_tesoreria_fila = {"nombre": "SALDO TOTAL TESORERÍA", "tipo_fila": "saldo_total", "columnas": [], "total": Decimal("0")}
    fila_diferencia_tc = {"nombre": "DIFERENCIA T/C", "tipo_fila": "saldo", "columnas": [], "total": Decimal("0")}

    saldo_actual = saldo_inicial_base
    money_market_acumulado_actual = money_market_inicial_base

    primer_periodo = meses_base[0][:2]

    for columna in columnas_flujo:
        clave_periodo = (columna["anio"], columna["mes_numero"])

        if columna["origen"] == "REAL":
            ingresos_mes = totales_reales_mensuales[clave_periodo]["ingresos"]
            egresos_mes = totales_reales_mensuales[clave_periodo]["egresos"]
            financiamiento_mes = totales_reales_mensuales[clave_periodo]["financiamiento"]
            money_market_mes = money_market_real_mensual[clave_periodo]
            diferencia_tc_mes = diferencia_tc_valores[clave_periodo]
        else:
            ingresos_mes = totales_proyectados_mensuales[clave_periodo]["ingresos"]
            egresos_mes = totales_proyectados_mensuales[clave_periodo]["egresos"]
            financiamiento_mes = totales_proyectados_mensuales[clave_periodo]["financiamiento"]
            money_market_mes = money_market_proyectado_mensual[clave_periodo]
            diferencia_tc_mes = diferencia_tc_valores[clave_periodo]

        ingresos_mes += totales_manuales_mensuales[clave_periodo]["ingresos"]
        egresos_mes += totales_manuales_mensuales[clave_periodo]["egresos"]
        financiamiento_mes += totales_manuales_mensuales[clave_periodo]["financiamiento"]

        neto_operacional_mes = ingresos_mes + egresos_mes
        neto_financiamiento_mes = financiamiento_mes + diferencia_tc_mes
        neto_total_mes = neto_operacional_mes + neto_financiamiento_mes

        saldo_inicial_mes = saldo_actual
        saldo_disponible_banco_mes = saldo_inicial_mes + neto_total_mes
        saldo_actual = saldo_disponible_banco_mes

        money_market_acumulado_mes = money_market_acumulado_actual + (money_market_mes * Decimal("-1"))
        money_market_acumulado_actual = money_market_acumulado_mes
        saldo_total_tesoreria_mes = saldo_disponible_banco_mes + money_market_acumulado_mes

        fila_diferencia_tc["columnas"].append({
            "clave": columna["clave"],
            "anio": columna["anio"],
            "mes_numero": columna["mes_numero"],
            "mes_nombre": columna["mes_nombre"],
            "etiqueta": columna["etiqueta"],
            "origen": columna["origen"],
            "es_mes_actual": columna["es_mes_actual"],
            "monto": diferencia_tc_mes,
            "tipo_fila": "saldo",
        })
        fila_diferencia_tc["total"] += diferencia_tc_mes

        total_ingresos_fila["columnas"].append({
            "clave": columna["clave"],
            "anio": columna["anio"],
            "mes_numero": columna["mes_numero"],
            "mes_nombre": columna["mes_nombre"],
            "etiqueta": columna["etiqueta"],
            "origen": columna["origen"],
            "es_mes_actual": columna["es_mes_actual"],
            "monto": ingresos_mes,
            "tipo_fila": "ingreso",
        })
        total_ingresos_fila["total"] += ingresos_mes

        total_egresos_fila["columnas"].append({
            "clave": columna["clave"],
            "anio": columna["anio"],
            "mes_numero": columna["mes_numero"],
            "mes_nombre": columna["mes_nombre"],
            "etiqueta": columna["etiqueta"],
            "origen": columna["origen"],
            "es_mes_actual": columna["es_mes_actual"],
            "monto": egresos_mes,
            "tipo_fila": "egreso",
        })
        total_egresos_fila["total"] += egresos_mes

        flujo_operacional_fila["columnas"].append({
            "clave": columna["clave"],
            "anio": columna["anio"],
            "mes_numero": columna["mes_numero"],
            "mes_nombre": columna["mes_nombre"],
            "etiqueta": columna["etiqueta"],
            "origen": columna["origen"],
            "es_mes_actual": columna["es_mes_actual"],
            "monto": neto_operacional_mes,
            "tipo_fila": "resultado",
        })
        flujo_operacional_fila["total"] += neto_operacional_mes

        flujo_financiamiento_fila["columnas"].append({
            "clave": columna["clave"],
            "anio": columna["anio"],
            "mes_numero": columna["mes_numero"],
            "mes_nombre": columna["mes_nombre"],
            "etiqueta": columna["etiqueta"],
            "origen": columna["origen"],
            "es_mes_actual": columna["es_mes_actual"],
            "monto": neto_financiamiento_mes,
            "tipo_fila": "financiamiento",
        })
        flujo_financiamiento_fila["total"] += neto_financiamiento_mes

        total_mes_fila["columnas"].append({
            "clave": columna["clave"],
            "anio": columna["anio"],
            "mes_numero": columna["mes_numero"],
            "mes_nombre": columna["mes_nombre"],
            "etiqueta": columna["etiqueta"],
            "origen": columna["origen"],
            "es_mes_actual": columna["es_mes_actual"],
            "monto": neto_total_mes,
            "tipo_fila": "resultado",
        })
        total_mes_fila["total"] += neto_total_mes

        saldo_inicial_fila["columnas"].append({
            "clave": columna["clave"],
            "anio": columna["anio"],
            "mes_numero": columna["mes_numero"],
            "mes_nombre": columna["mes_nombre"],
            "etiqueta": columna["etiqueta"],
            "origen": columna["origen"],
            "es_mes_actual": columna["es_mes_actual"],
            "monto": saldo_inicial_mes,
            "tipo_fila": "saldo_inicial",
            "es_base_editable": clave_periodo == primer_periodo,
        })

        saldo_disponible_banco_fila["columnas"].append({
            "clave": columna["clave"],
            "anio": columna["anio"],
            "mes_numero": columna["mes_numero"],
            "mes_nombre": columna["mes_nombre"],
            "etiqueta": columna["etiqueta"],
            "origen": columna["origen"],
            "es_mes_actual": columna["es_mes_actual"],
            "monto": saldo_disponible_banco_mes,
            "tipo_fila": "saldo_final",
        })

        money_market_acumulado_fila["columnas"].append({
            "clave": columna["clave"],
            "anio": columna["anio"],
            "mes_numero": columna["mes_numero"],
            "mes_nombre": columna["mes_nombre"],
            "etiqueta": columna["etiqueta"],
            "origen": columna["origen"],
            "es_mes_actual": columna["es_mes_actual"],
            "monto": money_market_acumulado_mes,
            "tipo_fila": "money_market",
            "es_base_editable": clave_periodo == primer_periodo,
        })

        saldo_total_tesoreria_fila["columnas"].append({
            "clave": columna["clave"],
            "anio": columna["anio"],
            "mes_numero": columna["mes_numero"],
            "mes_nombre": columna["mes_nombre"],
            "etiqueta": columna["etiqueta"],
            "origen": columna["origen"],
            "es_mes_actual": columna["es_mes_actual"],
            "monto": saldo_total_tesoreria_mes,
            "tipo_fila": "saldo_total",
        })

    meses_para_template = OrderedDict()
    for anio_columna, mes_numero, mes_nombre in meses_base:
        meses_para_template[f"{anio_columna}-{mes_numero}"] = mes_nombre

    return render(request, "flujo/inicio.html", {
        "movimientos": movimientos,
        "meses": list(meses_para_template.items()),
        "columnas_flujo": columnas_flujo,
        "mes_actual": mes_actual,
        "anio_actual": anio_actual,
        "filas_ingresos": filas_ingresos,
        "filas_egresos": filas_egresos,
        "filas_financiamiento": filas_financiamiento,
        "total_ingresos_fila": total_ingresos_fila,
        "total_egresos_fila": total_egresos_fila,
        "flujo_operacional_fila": flujo_operacional_fila,
        "flujo_financiamiento_fila": flujo_financiamiento_fila,
        "total_mes_fila": total_mes_fila,
        "saldo_inicial_fila": saldo_inicial_fila,
        "saldo_disponible_banco_fila": saldo_disponible_banco_fila,
        "money_market_acumulado_fila": money_market_acumulado_fila,
        "saldo_total_tesoreria_fila": saldo_total_tesoreria_fila,
        "saldo_inicial_base": saldo_inicial_base,
        "money_market_inicial_base": money_market_inicial_base,
        "mes_actual_nombre": "abr-26" if mes_actual == 4 else f"{mes_actual:02d}-26",
        "diferencia_tc_concepto_id": diferencia_tc_concepto_id,
        "fila_diferencia_tc": fila_diferencia_tc,
    })

