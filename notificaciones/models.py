from django.db import models


class CorreoLocal(models.Model):
    """Un correo que la API "envió" en DESARROLLO.

    En local no hay servidor de correo: en vez de imprimirse en la consola
    (donde se pierde entre los logs), cada correo se guarda aquí y se lee en
    el admin, con sus enlaces listos para abrir. Así se prueba la
    recuperación de contraseña sin configurar nada.

    En producción esta tabla queda vacía: el correo sale por SMTP (Resend o
    Brevo) y nunca pasa por aquí. Ver notificaciones/correo.py.
    """

    para = models.CharField(max_length=500)
    asunto = models.CharField(max_length=300)
    cuerpo = models.TextField()
    html = models.TextField(blank=True)
    remitente = models.CharField(max_length=300)
    enviado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "correo (bandeja local)"
        verbose_name_plural = "bandeja de correos (local)"
        ordering = ["-enviado"]

    def __str__(self):
        return f"{self.asunto} → {self.para}"
