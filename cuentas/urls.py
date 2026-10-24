from django.urls import path

from . import views

urlpatterns = [
    path("csrf", views.Csrf.as_view()),
    path("sesion", views.Sesion.as_view()),
    path("registro", views.Registro.as_view()),
    path("recuperacion", views.Recuperacion.as_view()),
    path("recuperacion/confirmar", views.ConfirmarRecuperacion.as_view()),
]
