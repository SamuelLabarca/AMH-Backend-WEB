from django.core.mail.backends.base import BaseEmailBackend


class BandejaLocal(BaseEmailBackend):
    """Backend de correo de DESARROLLO: guarda cada correo en la base
    (CorreoLocal) en lugar de enviarlo. Se lee en /admin → Bandeja de correos.

    Es el que usa DEBUG=true si no se configura otro (ver settings). No
    sirve en producción: los correos no le llegarían a nadie.
    """

    def send_messages(self, mensajes):
        # Import aquí: el backend se carga antes de que las apps estén listas.
        from .models import CorreoLocal

        enviados = 0
        for mensaje in mensajes or []:
            html = next((contenido for contenido, tipo in getattr(mensaje, "alternatives", []) if tipo == "text/html"), "")
            CorreoLocal.objects.create(
                para=", ".join(mensaje.recipients()),
                asunto=mensaje.subject,
                cuerpo=mensaje.body,
                html=html,
                remitente=mensaje.from_email,
            )
            enviados += 1
        return enviados
