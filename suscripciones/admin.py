from django.contrib import admin

from .models import Suscripcion


@admin.register(Suscripcion)
class SuscripcionAdmin(admin.ModelAdmin):
    list_display = ["plan", "usuario", "ciclo", "monto", "estado", "estado_cliente", "vence"]
    list_filter = ["estado", "ciclo", "plan"]
    search_fields = ["usuario__correo", "usuario__nombre", "usuario__documento", "plan"]
    autocomplete_fields = ["usuario"]
    readonly_fields = ["creada"]

    @admin.display(description="lo que ve el cliente")
    def estado_cliente(self, suscripcion):
        return suscripcion.estado_actual()
