from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("actualizar-softland/", views.actualizar_softland, name="actualizar_softland"),
    path("guardar-proyeccion/", views.guardar_proyeccion, name="guardar_proyeccion"),
    path("guardar-movimiento-real/", views.guardar_movimiento_real, name="guardar_movimiento_real"),
    path("guardar-configuracion-flujo/", views.guardar_configuracion_flujo, name="guardar_configuracion_flujo"),
    path("generar-proyecciones-json/", views.generar_proyecciones_json, name="generar_proyecciones_json"),
    path("publicar-proyecciones/", views.publicar_proyecciones, name="publicar_proyecciones"),
    path("detalle-movimientos-real/", views.detalle_movimientos_real, name="detalle_movimientos_real"),
]