from django.urls import path

from . import views

# Rutas públicas de pagos (sin sesión): a dónde pagar y la tasa del día.
# El reporte, que sí necesita sesión, está en urls.py bajo /portal/.
urlpatterns = [
    path("metodos", views.Metodos.as_view()),
    path("tasa", views.Tasa.as_view()),
]
