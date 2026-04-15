from django.contrib import admin

from .models import Concepto, CuentaBanco, Movimiento, Proyeccion


@admin.register(Concepto)
class ConceptoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tipo", "activo")
    list_filter = ("tipo", "activo")
    search_fields = ("codigo", "nombre")
    ordering = ("codigo",)


@admin.register(CuentaBanco)
class CuentaBancoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")
    ordering = ("codigo",)


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = (
        "fecha",
        "anio",
        "mes",
        "cuenta_banco",
        "concepto",
        "mov_debe",
        "mov_haber",
        "monto_calculado",
        "cajcod",
        "descripcion",
    )
    list_filter = ("anio", "mes", "cuenta_banco", "concepto")
    search_fields = ("descripcion", "cajcod", "cpbnum")
    autocomplete_fields = ("cuenta_banco", "concepto")
    ordering = ("-fecha", "-id")

    def monto_calculado(self, obj):
        return obj.monto

    monto_calculado.short_description = "Monto"


@admin.register(Proyeccion)
class ProyeccionAdmin(admin.ModelAdmin):
    list_display = (
        "anio",
        "mes",
        "concepto",
        "monto",
        "descripcion",
        "activo",
    )
    list_filter = ("anio", "mes", "concepto__tipo", "activo")
    search_fields = (
        "concepto__codigo",
        "concepto__nombre",
        "descripcion",
    )
    autocomplete_fields = ("concepto",)
    ordering = ("anio", "mes", "concepto__codigo", "id")