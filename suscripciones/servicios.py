from django.utils import timezone

from .models import Suscripcion


def sumar_meses(fecha, meses):
    """Suma meses calendario. Si el día no existe en el mes destino (31 de
    enero + 1 mes) se queda en el último día de ese mes."""
    indice = fecha.month - 1 + meses
    anio, mes = fecha.year + indice // 12, indice % 12 + 1
    for dia in (fecha.day, 30, 29, 28):
        try:
            return fecha.replace(year=anio, month=mes, day=dia)
        except ValueError:
            continue
    raise ValueError("Fecha imposible")


def renovar(suscripcion, hoy=None):
    """Extiende la suscripción un ciclo y la deja activa.

    Si todavía no venció, el ciclo nuevo se suma DESPUÉS del vencimiento:
    quien renueva antes no pierde días. Si ya venció, cuenta desde hoy.
    """
    hoy = hoy or timezone.localdate()
    base = suscripcion.vence if suscripcion.vence and suscripcion.vence > hoy else hoy
    suscripcion.vence = sumar_meses(base, suscripcion.ciclo)
    suscripcion.estado = Suscripcion.Estado.ACTIVA
    suscripcion.save(update_fields=["vence", "estado"])
    return suscripcion
