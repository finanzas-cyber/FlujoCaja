from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("actualizar-softland/", views.actualizar_softland, name="actualizar_softland"),
    path("guardar-proyeccion/", views.guardar_proyeccion, name="guardar_proyeccion"),
    path("generar-proyecciones-json/", views.generar_proyecciones_json, name="generar_proyecciones_json"),
]