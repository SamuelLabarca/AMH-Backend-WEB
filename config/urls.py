from django.contrib import admin
from django.urls import include, path

# Las rutas siguen el contrato que usa el frontend
# (amh/src/servicios/: autenticacion.js, portalPagos.js y tienda.js).
urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("cuentas.urls")),
    path("tienda/", include("catalogo.urls")),
    path("pagos/", include("pagos.urls_publicas")),
    path("portal/", include("suscripciones.urls")),
    path("portal/", include("pagos.urls")),
]
