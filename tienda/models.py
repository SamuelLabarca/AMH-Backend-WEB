from django.conf import settings
from django.db import models


class Orden(models.Model):
    """Una compra hecha en la tienda.

    Guarda una FOTO de lo que se compró y a qué precio (`producto`,
    `opcion`, `precio`, `iva`, `total`): si mañana el equipo sube el
    precio en el catálogo, quien compró ayer paga lo que vio. Por eso se
    copian los valores en vez de leerlos del catálogo cada vez.

    Al crearse nace su suscripción en `pendiente`; cuando el pago se
    aprueba, la suscripción se activa y la orden pasa a `pagada`.
    """

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de pago"
        PAGADA = "pagada", "Pagada"
        CANCELADA = "cancelada", "Cancelada"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ordenes")
    opcion_pago = models.ForeignKey("catalogo.OpcionPago", on_delete=models.PROTECT, related_name="ordenes")
    suscripcion = models.OneToOneField(
        "suscripciones.Suscripcion", on_delete=models.PROTECT, related_name="orden", null=True, blank=True
    )

    # La foto del momento de la compra.
    producto = models.CharField(max_length=80)
    opcion = models.CharField(max_length=40)
    meses = models.PositiveSmallIntegerField()
    precio = models.DecimalField("precio (USD)", max_digits=10, decimal_places=2)
    iva = models.DecimalField("IVA (%)", max_digits=5, decimal_places=2, null=True, blank=True)
    impuesto = models.DecimalField("impuesto (USD)", max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField("total (USD)", max_digits=10, decimal_places=2)

    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    creada = models.DateTimeField(auto_now_add=True)
    pagada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "orden"
        verbose_name_plural = "órdenes"
        ordering = ["-creada"]

    def __str__(self):
        return f"#{self.pk} · {self.producto} {self.opcion} · {self.usuario.correo}"
