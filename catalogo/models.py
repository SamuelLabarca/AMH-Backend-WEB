from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from suscripciones.models import Suscripcion


class Producto(models.Model):
    """Lo que se vende en la tienda (hoy, My Business Panel · Administrativo).

    Solo lo que decide CUÁNTO se cobra vive aquí. Los textos de marketing
    (titulares, "incluye", fotos) siguen en el frontend: cambiarlos no
    debería requerir tocar la base de datos, y no tienen riesgo."""

    codigo = models.SlugField(unique=True, help_text="El mismo `id` que usa el frontend, p. ej. administrativo.")
    nombre = models.CharField(max_length=80)
    marca = models.CharField(max_length=80, default="My Business Panel")
    # IVA en porcentaje (16 = 16 %). Vacío: los precios ya lo incluyen o no aplica.
    iva = models.DecimalField(
        "IVA (%)",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    activo = models.BooleanField(default=True, help_text="Desactivado deja de venderse; lo ya vendido sigue igual.")

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"

    def __str__(self):
        return f"{self.marca} · {self.nombre}"


class OpcionPago(models.Model):
    """Cada cuánto se paga un producto y a qué precio (anual, trimestral…).

    ⚠️ El precio que se COBRA sale siempre de aquí, nunca del navegador:
    si el monto lo mandara el cliente, cualquiera lo cambiaría con las
    herramientas del navegador. Cambiarlo aquí NO cambia lo ya vendido:
    la orden guarda el precio del momento (fase 2)."""

    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="opciones")
    codigo = models.SlugField(help_text="anual, trimestral, mensual…")
    nombre = models.CharField(max_length=40)
    meses = models.PositiveSmallIntegerField(choices=Suscripcion.Ciclo.choices)
    precio = models.DecimalField(
        "precio (USD)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Vacío = 'a consultar': se muestra, pero no se puede comprar en línea.",
    )
    destacado = models.CharField(max_length=60, blank=True, help_text="Sello, p. ej. 'El plan más solicitado'.")
    orden = models.PositiveSmallIntegerField(default=0, help_text="Menor va primero.")
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "opción de pago"
        verbose_name_plural = "opciones de pago"
        ordering = ["producto", "orden", "id"]
        constraints = [models.UniqueConstraint(fields=["producto", "codigo"], name="opcion_unica_por_producto")]

    def __str__(self):
        return f"{self.producto.nombre} · {self.nombre}"
