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

from .models import Movimiento, Concepto, Proyeccion


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

        if not concepto_id or not mes:
            return JsonResponse({"ok": False, "error": "Faltan datos"}, status=400)

        concepto = Concepto.objects.get(id=int(concepto_id))

        proyeccion, _ = Proyeccion.objects.get_or_create(
            concepto=concepto,
            anio=2026,
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
                "monto": str(monto),
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
    saldo_inicial_enero = Decimal("143498696")
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

    movimientos_2026 = Movimiento.objects.select_related("concepto").filter(
        anio=anio_actual
    ).exclude(cajcod="0000000000").order_by("fecha", "id")

    proyecciones_2026 = Proyeccion.objects.select_related("concepto").filter(
        anio=anio_actual,
        activo=True,
    ).order_by("mes", "concepto__codigo", "id")

    meses_base = OrderedDict([
        (1, "ene-26"),
        (2, "feb-26"),
        (3, "mar-26"),
        (4, "abr-26"),
        (5, "may-26"),
        (6, "jun-26"),
        (7, "jul-26"),
        (8, "ago-26"),
        (9, "sep-26"),
        (10, "oct-26"),
        (11, "nov-26"),
        (12, "dic-26"),
    ])

    columnas_flujo = []
    for mes_numero, mes_nombre in meses_base.items():
        if mes_numero < mes_actual:
            columnas_flujo.append({
                "clave": f"{mes_numero}_real",
                "mes_numero": mes_numero,
                "mes_nombre": mes_nombre,
                "etiqueta": "REAL",
                "origen": "REAL",
                "es_mes_actual": False,
            })
        elif mes_numero == mes_actual:
            columnas_flujo.append({
                "clave": f"{mes_numero}_real",
                "mes_numero": mes_numero,
                "mes_nombre": mes_nombre,
                "etiqueta": "REAL",
                "origen": "REAL",
                "es_mes_actual": True,
            })
            columnas_flujo.append({
                "clave": f"{mes_numero}_proyectado",
                "mes_numero": mes_numero,
                "mes_nombre": mes_nombre,
                "etiqueta": "PROY.",
                "origen": "PROYECTADO",
                "es_mes_actual": True,
            })
        else:
            columnas_flujo.append({
                "clave": f"{mes_numero}_proyectado",
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
        ).order_by("codigo")
    )

    money_market_concepto = Concepto.objects.filter(codigo="800010").first()
    money_market_concepto_id = money_market_concepto.id if money_market_concepto else None

    montos_reales_por_concepto_mes = {}
    montos_proyectados_por_concepto_mes = {}

    totales_reales_mensuales = {}
    totales_proyectados_mensuales = {}

    money_market_real_mensual = {}
    money_market_proyectado_mensual = {}

    for mes in meses_base:
        totales_reales_mensuales[mes] = {
            "ingresos": Decimal("0"),
            "egresos": Decimal("0"),
            "financiamiento": Decimal("0"),
            "excluir": Decimal("0"),
        }
        totales_proyectados_mensuales[mes] = {
            "ingresos": Decimal("0"),
            "egresos": Decimal("0"),
            "financiamiento": Decimal("0"),
            "excluir": Decimal("0"),
        }
        money_market_real_mensual[mes] = Decimal("0")
        money_market_proyectado_mensual[mes] = Decimal("0")

    for m in movimientos_2026:
        if not m.concepto or m.mes not in meses_base:
            continue

        key = (m.concepto_id, m.mes)
        montos_reales_por_concepto_mes[key] = montos_reales_por_concepto_mes.get(key, Decimal("0")) + m.monto

        if m.concepto.tipo == Concepto.TIPO_INGRESO:
            totales_reales_mensuales[m.mes]["ingresos"] += m.monto
        elif m.concepto.tipo == Concepto.TIPO_EGRESO:
            totales_reales_mensuales[m.mes]["egresos"] += m.monto
        elif m.concepto.tipo == Concepto.TIPO_FINANCIAMIENTO:
            totales_reales_mensuales[m.mes]["financiamiento"] += m.monto
        elif m.concepto.tipo == Concepto.TIPO_EXCLUIR:
            totales_reales_mensuales[m.mes]["excluir"] += m.monto

        if money_market_concepto_id and m.concepto_id == money_market_concepto_id:
            money_market_real_mensual[m.mes] += m.monto

    for p in proyecciones_2026:
        if not p.concepto or p.mes not in meses_base:
            continue

        key = (p.concepto_id, p.mes)
        montos_proyectados_por_concepto_mes[key] = montos_proyectados_por_concepto_mes.get(key, Decimal("0")) + p.monto

        if p.concepto.tipo == Concepto.TIPO_INGRESO:
            totales_proyectados_mensuales[p.mes]["ingresos"] += p.monto
        elif p.concepto.tipo == Concepto.TIPO_EGRESO:
            totales_proyectados_mensuales[p.mes]["egresos"] += p.monto
        elif p.concepto.tipo == Concepto.TIPO_FINANCIAMIENTO:
            totales_proyectados_mensuales[p.mes]["financiamiento"] += p.monto
        elif p.concepto.tipo == Concepto.TIPO_EXCLUIR:
            totales_proyectados_mensuales[p.mes]["excluir"] += p.monto

        if money_market_concepto_id and p.concepto_id == money_market_concepto_id:
            money_market_proyectado_mensual[p.mes] += p.monto

    def construir_filas(conceptos, tipo_fila):
        filas = []

        for concepto in conceptos:
            fila = {
                "id": concepto.id,
                "codigo": concepto.codigo,
                "nombre": concepto.nombre,
                "tipo_fila": tipo_fila,
                "columnas": [],
                "total": Decimal("0"),
            }

            for columna in columnas_flujo:
                if columna["origen"] == "REAL":
                    monto = montos_reales_por_concepto_mes.get(
                        (concepto.id, columna["mes_numero"]),
                        Decimal("0"),
                    )
                else:
                    monto = montos_proyectados_por_concepto_mes.get(
                        (concepto.id, columna["mes_numero"]),
                        Decimal("0"),
                    )

                fila["columnas"].append({
                    "clave": columna["clave"],
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

    saldo_actual = saldo_inicial_enero
    money_market_acumulado_actual = Decimal("0")

    for columna in columnas_flujo:
        mes_numero = columna["mes_numero"]

        if columna["origen"] == "REAL":
            ingresos_mes = totales_reales_mensuales[mes_numero]["ingresos"]
            egresos_mes = totales_reales_mensuales[mes_numero]["egresos"]
            financiamiento_mes = totales_reales_mensuales[mes_numero]["financiamiento"]
            money_market_mes = money_market_real_mensual[mes_numero]
        else:
            ingresos_mes = totales_proyectados_mensuales[mes_numero]["ingresos"]
            egresos_mes = totales_proyectados_mensuales[mes_numero]["egresos"]
            financiamiento_mes = totales_proyectados_mensuales[mes_numero]["financiamiento"]
            money_market_mes = money_market_proyectado_mensual[mes_numero]

        neto_operacional_mes = ingresos_mes + egresos_mes
        neto_financiamiento_mes = financiamiento_mes
        neto_total_mes = neto_operacional_mes + neto_financiamiento_mes

        saldo_inicial_mes = saldo_actual
        saldo_disponible_banco_mes = saldo_inicial_mes + neto_total_mes
        saldo_actual = saldo_disponible_banco_mes

        money_market_acumulado_actual += (money_market_mes * Decimal("-1"))
        saldo_total_tesoreria_mes = saldo_disponible_banco_mes + money_market_acumulado_actual

        total_ingresos_fila["columnas"].append({
            "clave": columna["clave"],
            "mes_numero": mes_numero,
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
            "mes_numero": mes_numero,
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
            "mes_numero": mes_numero,
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
            "mes_numero": mes_numero,
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
            "mes_numero": mes_numero,
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
            "mes_numero": mes_numero,
            "mes_nombre": columna["mes_nombre"],
            "etiqueta": columna["etiqueta"],
            "origen": columna["origen"],
            "es_mes_actual": columna["es_mes_actual"],
            "monto": saldo_inicial_mes,
            "tipo_fila": "saldo_inicial",
        })

        saldo_disponible_banco_fila["columnas"].append({
            "clave": columna["clave"],
            "mes_numero": mes_numero,
            "mes_nombre": columna["mes_nombre"],
            "etiqueta": columna["etiqueta"],
            "origen": columna["origen"],
            "es_mes_actual": columna["es_mes_actual"],
            "monto": saldo_disponible_banco_mes,
            "tipo_fila": "saldo_final",
        })

        money_market_acumulado_fila["columnas"].append({
            "clave": columna["clave"],
            "mes_numero": mes_numero,
            "mes_nombre": columna["mes_nombre"],
            "etiqueta": columna["etiqueta"],
            "origen": columna["origen"],
            "es_mes_actual": columna["es_mes_actual"],
            "monto": money_market_acumulado_actual,
            "tipo_fila": "money_market",
        })

        saldo_total_tesoreria_fila["columnas"].append({
            "clave": columna["clave"],
            "mes_numero": mes_numero,
            "mes_nombre": columna["mes_nombre"],
            "etiqueta": columna["etiqueta"],
            "origen": columna["origen"],
            "es_mes_actual": columna["es_mes_actual"],
            "monto": saldo_total_tesoreria_mes,
            "tipo_fila": "saldo_total",
        })

    return render(request, "flujo/inicio.html", {
        "movimientos": movimientos,
        "meses": list(meses_base.items()),
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
        "saldo_inicial_enero": saldo_inicial_enero,
        "mes_actual_nombre": meses_base[mes_actual],
    })