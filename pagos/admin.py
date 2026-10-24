from django.contrib import admin, messages

from . import servicios
from .models import ReportePago


@admin.register(ReportePago)
class ReportePagoAdmin(admin.ModelAdmin):
    """La bandeja del equipo: los pagos reportados, los pendientes primero.

    Aprobar y rechazar pasan por `pagos.servicios`, nunca editando el campo
    `estado` a mano: así aprobar SIEMPRE renueva las suscripciones."""

    list_display = ["creado", "usuario", "metodo", "referencia", "monto", "moneda", "total_usd", "estado"]
    list_filter = ["estado", "metodo"]
    search_fields = ["referencia", "usuario__correo", "usuario__nombre", "usuario__documento"]
    date_hierarchy = "creado"
    actions = ["aprobar_seleccionados", "rechazar_seleccionados"]
    filter_horizontal = ["suscripciones"]

    # El estado y la revisión no se editan a mano: solo con las acciones.
    readonly_fields = [
        "usuario",
        "suscripciones",
        "metodo",
        "referencia",
        "fecha_pago",
        "banco_origen",
        "monto",
        "moneda",
        "total_usd",
        "estado",
        "creado",
        "revisado_en",
        "revisado_por",
    ]
    fields = readonly_fields[:9] + ["tasa_bcv", "nota"] + readonly_fields[9:]

    def has_add_permission(self, request):
        return False  # los reporta el cliente desde el portal

    def has_delete_permission(self, request, obj=None):
        return False  # un pago no se borra: se rechaza, y queda el rastro

    @admin.action(description="Aprobar (activa las suscripciones)")
    def aprobar_seleccionados(self, request, queryset):
        self._revisar(request, queryset, lambda r: servicios.aprobar(r.pk, request.user), "aprobado")

    @admin.action(description="Rechazar")
    def rechazar_seleccionados(self, request, queryset):
        self._revisar(request, queryset, lambda r: servicios.rechazar(r.pk, request.user), "rechazado")

    def _revisar(self, request, queryset, accion, verbo):
        hechos, saltados = 0, 0
        for reporte in queryset:
            try:
                accion(reporte)
                hechos += 1
            except servicios.PagoYaRevisado:
                saltados += 1
        if hechos:
            self.message_user(request, f"{hechos} pago(s) {verbo}(s).", messages.SUCCESS)
        if saltados:
            self.message_user(request, f"{saltados} ya estaban revisados y no se tocaron.", messages.WARNING)
