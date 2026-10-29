from django.contrib import admin, messages

from . import servicios
from .models import DatoCobro, MetodoPago, ReportePago, TasaCambio


class DatosEnLinea(admin.TabularInline):
    model = DatoCobro
    extra = 0
    fields = ["orden", "etiqueta", "valor"]


@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    """Los datos de cobro que ve el cliente. Cambiarlos aquí se refleja en
    la web al instante, sin publicar nada."""

    list_display = ["nombre", "codigo", "moneda", "activo", "orden"]
    list_editable = ["activo", "orden"]
    inlines = [DatosEnLinea]

    def has_delete_permission(self, request, obj=None):
        return False  # se apaga, no se borra: hay reportes que lo usan


@admin.register(TasaCambio)
class TasaCambioAdmin(admin.ModelAdmin):
    list_display = ["fecha", "bs_por_usd", "fuente", "registrada_por"]
    readonly_fields = ["registrada_por", "creada"]
    date_hierarchy = "fecha"

    def save_model(self, request, obj, form, change):
        # Queda quién la cargó: una tasa mal puesta cambia lo que se cobra.
        if not change:
            obj.registrada_por = request.user
        super().save_model(request, obj, form, change)


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
