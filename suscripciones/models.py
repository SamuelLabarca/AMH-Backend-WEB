from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Suscripcion(models.Model):
    """Un plan contratado por un usuario.

    Se GUARDA solo lo que decide una persona o un pago: pendiente, activa,
    suspendida o cancelada. "Vencida" y "por vencer" NO se guardan: se
    calculan con la fecha de `vence` cada vez que se consulta. Guardarlas
    obligaría a una tarea diaria que las actualice, y si esa tarea falla
    un día, el estado miente.
    """

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de pago"
        ACTIVA = "activa", "Activa"
        SUSPENDIDA = "suspendida", "Suspendida"
        CANCELADA = "cancelada", "Cancelada"

    class Ciclo(models.IntegerChoices):
        MENSUAL = 1, "Mensual"
        TRIMESTRAL = 3, "Trimestral"
        ANUAL = 12, "Anual"

    # Cuántos días antes del vencimiento se avisa "por vencer".
    AVISO_DIAS = 7

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="suscripciones")
    producto = models.CharField(max_length=80, default="My Business Panel")
    plan = models.CharField(max_length=80)
    ciclo = models.PositiveSmallIntegerField(choices=Ciclo.choices, default=Ciclo.MENSUAL)
    monto = models.DecimalField("monto (USD)", max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    vence = models.DateField(null=True, blank=True, help_text="Vacío hasta el primer pago.")
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "suscripción"
        verbose_name_plural = "suscripciones"
        ordering = ["vence", "id"]

    def __str__(self):
        return f"{self.plan} · {self.usuario.nombre}"

    def estado_actual(self, hoy=None):
        """El estado que ve el cliente, con vencida / por-vencer calculados."""
        # La fecha en Caracas (TIME_ZONE), no la del servidor.
        hoy = hoy or timezone.localdate()
        if self.estado != self.Estado.ACTIVA:
            return self.estado
        if self.vence is None or self.vence < hoy:
            return "vencida"
        if self.vence - hoy <= timedelta(days=self.AVISO_DIAS):
            return "por-vencer"
        return "activa"

    def da_acceso_al_panel(self, hoy=None):
        """Lo que consultará My Business Panel al iniciar sesión."""
        return self.estado_actual(hoy) in ("activa", "por-vencer")
