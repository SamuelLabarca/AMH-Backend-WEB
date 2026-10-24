from django.contrib import admin
from django.urls import include, path

# Las rutas siguen el contrato que ya usa el frontend
# (amh/src/servicios/autenticacion.js y portalPagos.js).
urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("cuentas.urls")),
    path("portal/", include("suscripciones.urls")),
    path("portal/", include("pagos.urls")),
]
