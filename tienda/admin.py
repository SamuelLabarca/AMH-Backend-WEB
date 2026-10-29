from django.contrib import admin

from .models import Orden


@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    """Solo lectura: una orden es el registro de lo que se vendió. Se paga
    aprobando su pago en Reportes de pago, no editándola aquí."""

    list_display = ["id", "creada", "usuario", "producto", "opcion", "total", "estado"]
    list_filter = ["estado", "opcion"]
    search_fields = ["usuario__correo", "usuario__nombre", "usuario__documento"]
    date_hierarchy = "creada"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
