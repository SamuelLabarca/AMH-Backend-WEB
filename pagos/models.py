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

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pagos")
    suscripciones = models.ManyToManyField("suscripciones.Suscripcion", related_name="pagos")
    metodo = models.CharField(max_length=16, choices=Metodo.choices)
    referencia = models.CharField(max_length=40)
    fecha_pago = models.DateField("fecha del pago")
    banco_origen = models.CharField(max_length=60, blank=True)
    monto = models.DecimalField("monto pagado", max_digits=14, decimal_places=2)
    moneda = models.CharField(max_length=3)
    total_usd = models.DecimalField("total de los planes (USD)", max_digits=10, decimal_places=2)
    # La tasa BCV de un pago en bolívares. Se copia la vigente al reportar
    # y quien aprueba puede corregirla: sin ella no se puede conciliar ese
    # pago meses después.
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


class MetodoPago(models.Model):
    """A dónde paga el cliente: los datos de cobro que ve en el último paso.

    Viven aquí y no en el código del frontend para cambiarlos desde el
    admin (otra cuenta, otro teléfono) sin publicar la web de nuevo, y
    para apagar un método sin tocar nada más."""

    class Moneda(models.TextChoices):
        BOLIVARES = "Bs", "Bolívares"
        DOLARES = "USD", "Dólares"

    codigo = models.CharField(max_length=16, choices=ReportePago.Metodo.choices, unique=True)
    nombre = models.CharField(max_length=40)
    moneda = models.CharField(max_length=3, choices=Moneda.choices)
    activo = models.BooleanField(default=True, help_text="Apagado deja de ofrecerse y de aceptarse en reportes nuevos.")
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "método de cobro"
        verbose_name_plural = "métodos de cobro"
        ordering = ["orden", "id"]

    def __str__(self):
        return self.nombre


class DatoCobro(models.Model):
    """Un renglón de los datos de cobro: "Banco: Banesco", "Teléfono: …".
    Vacío se muestra como "Por confirmar"."""

    metodo = models.ForeignKey(MetodoPago, on_delete=models.CASCADE, related_name="datos")
    etiqueta = models.CharField(max_length=40)
    valor = models.CharField(max_length=120, blank=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "dato de cobro"
        verbose_name_plural = "datos de cobro"
        ordering = ["orden", "id"]

    def __str__(self):
        return f"{self.etiqueta}: {self.valor or 'por confirmar'}"


class TasaCambio(models.Model):
    """La tasa oficial del BCV (bolívares por dólar) de un día.

    Se carga a mano desde el admin; más adelante, un comando diario podrá
    traerla sola. Vale la ÚLTIMA cargada con fecha de hoy o anterior: si
    un día nadie la carga, sigue valiendo la del día hábil anterior, que
    es exactamente cómo publica el BCV."""

    fecha = models.DateField(unique=True)
    bs_por_usd = models.DecimalField("Bs por USD", max_digits=12, decimal_places=4)
    fuente = models.CharField(max_length=40, default="BCV (manual)")
    registrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "tasa de cambio"
        verbose_name_plural = "tasas de cambio"
        ordering = ["-fecha"]
        constraints = [models.CheckConstraint(condition=models.Q(bs_por_usd__gt=0), name="tasa_positiva")]

    def __str__(self):
        return f"{self.fecha}: Bs {self.bs_por_usd}"
