"""Las reglas de las suscripciones. Las otras apps (tienda, pagos) llaman
a estas funciones en vez de leer o escribir el modelo Suscripcion: así,
"cuándo se puede pagar" o "cómo nace una suscripción" se lee en un solo
archivo."""

from django.utils import timezone

from .models import Suscripcion


def crear_pendiente(usuario, *, producto, plan, ciclo, monto):
    """Una suscripción recién comprada: existe, pero no da acceso hasta que
    se apruebe su pago (ver renovar)."""
    return Suscripcion.objects.create(
        usuario=usuario,
        producto=producto,
        plan=plan,
        ciclo=ciclo,
        monto=monto,
        estado=Suscripcion.Estado.PENDIENTE,
    )


def cancelar_pendiente(suscripcion):
    """Cancela una suscripción que nunca se pagó. Si ya está activa (se
    pagó) no la toca: cancelar una compra no puede quitar un acceso pagado."""
    if suscripcion.estado != Suscripcion.Estado.PENDIENTE:
        return False
    suscripcion.estado = Suscripcion.Estado.CANCELADA
    suscripcion.save(update_fields=["estado"])
    return True


def pagables(usuario, ids):
    """Las suscripciones de `usuario` con esos ids que se pueden pagar, o
    None si alguna no existe, no es suya o está cancelada.

    Todo o nada a propósito: quien llama no debe saber CUÁL falló, para no
    confirmar que existe una suscripción ajena con ese id."""
    ids = set(ids)
    encontradas = list(
        usuario.suscripciones.filter(pk__in=ids).exclude(estado=Suscripcion.Estado.CANCELADA)
    )
    return encontradas if len(encontradas) == len(ids) else None


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
