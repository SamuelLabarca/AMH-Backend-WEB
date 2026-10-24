from django.conf import settings
from django.db import models


class ReportePago(models.Model):
    """Un pago que el cliente REPORTA desde el portal (Pago Móvil,
    transferencia o Zelle) y que alguien del equipo verifica en su banco.

    Nace `pendiente`. Solo `pagos.servicios.aprobar` lo pasa a `aprobado`,
    y es eso lo que activa las suscripciones: el puente entre pagar y
    tener acceso al Panel. Cuando exista la verificación automática
    (Celebry), será otro camino hacia el mismo `aprobar`.
    """

    class Metodo(models.TextChoices):
        PAGO_MOVIL = "pago-movil", "Pago Móvil"
        TRANSFERENCIA = "transferencia", "Transferencia"
        ZELLE = "zelle", "Zelle"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de verificar"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"

    MONEDA = {Metodo.PAGO_MOVIL: "Bs", Metodo.TRANSFERENCIA: "Bs", Metodo.ZELLE: "USD"}

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pagos")
    suscripciones = models.ManyToManyField("suscripciones.Suscripcion", related_name="pagos")
    metodo = models.CharField(max_length=16, choices=Metodo.choices)
    referencia = models.CharField(max_length=40)
    fecha_pago = models.DateField("fecha del pago")
    banco_origen = models.CharField(max_length=60, blank=True)
    monto = models.DecimalField("monto pagado", max_digits=14, decimal_places=2)
    moneda = models.CharField(max_length=3)
    total_usd = models.DecimalField("total de los planes (USD)", max_digits=10, decimal_places=2)
    # La tasa BCV con la que se verificó un pago en bolívares. La pone quien
    # aprueba: sin ella no se puede conciliar ese pago meses después.
    tasa_bcv = models.DecimalField("tasa BCV", max_digits=12, decimal_places=4, null=True, blank=True)

    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    nota = models.TextField(blank=True, help_text="Motivo del rechazo u observaciones.")
    creado = models.DateTimeField(auto_now_add=True)
    revisado_en = models.DateTimeField(null=True, blank=True)
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "reporte de pago"
        verbose_name_plural = "reportes de pago"
        ordering = ["-creado"]
        constraints = [
            # Una referencia bancaria solo se puede reportar una vez por
            # método: es la defensa contra reusar el mismo comprobante.
            models.UniqueConstraint(fields=["metodo", "referencia"], name="referencia_unica_por_metodo"),
        ]

    def __str__(self):
        return f"{self.get_metodo_display()} {self.referencia} · {self.usuario.nombre}"
