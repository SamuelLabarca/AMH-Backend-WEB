from django.db import transaction
from django.utils import timezone

from suscripciones.servicios import renovar

from .models import ReportePago


class PagoYaRevisado(Exception):
    """Se intentó aprobar o rechazar un pago que ya no está pendiente."""


@transaction.atomic
def aprobar(reporte_id, revisor, tasa_bcv=None):
    """Aprueba el pago y renueva sus suscripciones, TODO o NADA.

    `select_for_update` bloquea la fila mientras dura la transacción: si
    dos personas del equipo pulsan "aprobar" a la vez, la segunda espera,
    encuentra el pago ya aprobado y no renueva dos veces.
    """
    reporte = ReportePago.objects.select_for_update().get(pk=reporte_id)
    if reporte.estado != ReportePago.Estado.PENDIENTE:
        raise PagoYaRevisado(reporte)

    for suscripcion in reporte.suscripciones.select_for_update():
        renovar(suscripcion)

    reporte.estado = ReportePago.Estado.APROBADO
    reporte.revisado_por = revisor
    reporte.revisado_en = timezone.now()
    if tasa_bcv is not None:
        reporte.tasa_bcv = tasa_bcv
    reporte.save(update_fields=["estado", "revisado_por", "revisado_en", "tasa_bcv"])
    return reporte


@transaction.atomic
def rechazar(reporte_id, revisor, nota=""):
    reporte = ReportePago.objects.select_for_update().get(pk=reporte_id)
    if reporte.estado != ReportePago.Estado.PENDIENTE:
        raise PagoYaRevisado(reporte)
    reporte.estado = ReportePago.Estado.RECHAZADO
    reporte.revisado_por = revisor
    reporte.revisado_en = timezone.now()
    reporte.nota = nota or reporte.nota
    reporte.save(update_fields=["estado", "revisado_por", "revisado_en", "nota"])
    return reporte
