from .models import OpcionPago


def opcion_vendible(producto_codigo, opcion_codigo):
    """La opción que se puede COMPRAR en línea ahora mismo, o None.

    Es la regla de "qué se vende" en un solo sitio: producto activo,
    opción activa y con precio (sin precio es "a consultar"). Las otras
    apps preguntan aquí en vez de filtrar los modelos del catálogo."""
    return (
        OpcionPago.objects.select_related("producto")
        .filter(
            producto__codigo=producto_codigo,
            producto__activo=True,
            codigo=opcion_codigo,
            activa=True,
            precio__isnull=False,
        )
        .first()
    )
