from django.contrib import admin

from .models import OpcionPago, Producto


class OpcionesEnLinea(admin.TabularInline):
    """Las opciones se editan dentro de su producto: es como se piensan."""

    model = OpcionPago
    extra = 0
    fields = ["orden", "codigo", "nombre", "meses", "precio", "destacado", "activa"]


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "marca", "codigo", "iva", "activo"]
    inlines = [OpcionesEnLinea]

    def has_delete_permission(self, request, obj=None):
        return False  # se desactiva, no se borra: hay ventas que apuntan a él
