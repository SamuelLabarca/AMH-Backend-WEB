from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

# Las otras apps, solo por sus servicios: nunca sus modelos.
from catalogo import servicios as catalogo
from suscripciones import servicios as suscripciones

from .models import Orden

CENTIMO = Decimal("0.01")


class OpcionNoDisponible(Exception):
    """La opción no existe, está apagada o no tiene precio para venderse en línea."""


def calcular(precio, iva):
    """Precio + IVA, redondeado al céntimo como en una factura."""
    impuesto = (precio * iva / 100).quantize(CENTIMO, ROUND_HALF_UP) if iva else Decimal("0")
    return impuesto, precio + impuesto


@transaction.atomic
def crear_orden(usuario, producto_codigo, opcion_codigo):
    """Crea la orden y su suscripción pendiente, TODO o NADA.

    El precio sale del catálogo en ESTE momento, nunca de la petición.

    Una sola orden pendiente por producto y usuario: si ya tenía una con la
    misma opción se devuelve esa (volver atrás o hacer doble clic no crea
    duplicados); si era de otra opción, se cancela y se crea la nueva.
    """
    opcion = catalogo.opcion_vendible(producto_codigo, opcion_codigo)
    if opcion is None:
        raise OpcionNoDisponible(opcion_codigo)
    producto = opcion.producto

    pendientes = Orden.objects.select_for_update().filter(
        usuario=usuario, estado=Orden.Estado.PENDIENTE, opcion_pago__producto=producto
    )
    for anterior in pendientes:
        if anterior.opcion_pago_id == opcion.id:
            return anterior, False
        cancelar(anterior)

    impuesto, total = calcular(opcion.precio, producto.iva)
    suscripcion = suscripciones.crear_pendiente(
        usuario, producto=producto.marca, plan=producto.nombre, ciclo=opcion.meses, monto=total
    )
    orden = Orden.objects.create(
        usuario=usuario,
        opcion_pago=opcion,
        suscripcion=suscripcion,
        producto=f"{producto.marca} · {producto.nombre}",
        opcion=opcion.nombre,
        meses=opcion.meses,
        precio=opcion.precio,
        iva=producto.iva,
        impuesto=impuesto,
        total=total,
    )
    return orden, True


def cancelar(orden):
    """Cancela una orden pendiente y su suscripción, que nunca llegó a pagarse."""
    orden.estado = Orden.Estado.CANCELADA
    orden.save(update_fields=["estado"])
    if orden.suscripcion:
        suscripciones.cancelar_pendiente(orden.suscripcion)


def marcar_pagadas(renovadas):
    """Lo llama pagos.servicios.aprobar: las órdenes pendientes de esas
    suscripciones pasan a pagadas. Una renovación no tiene orden y no
    hace nada aquí."""
    Orden.objects.filter(suscripcion__in=renovadas, estado=Orden.Estado.PENDIENTE).update(
        estado=Orden.Estado.PAGADA, pagada_en=timezone.now()
    )
