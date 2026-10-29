from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html, linebreaks, urlize
from django.utils.safestring import mark_safe

from .models import CorreoLocal


class CorreoLocalAdmin(admin.ModelAdmin):
    """La bandeja de desarrollo: como un buzón, de solo lectura. Los enlaces
    del correo (el de recuperar la contraseña, por ejemplo) se pueden abrir
    con un clic."""

    list_display = ["enviado", "para", "asunto"]
    search_fields = ["para", "asunto"]
    readonly_fields = ["enviado", "remitente", "para", "asunto", "mensaje"]
    fields = readonly_fields

    @admin.display(description="mensaje")
    def mensaje(self, correo):
        # `urlize(autoescape=True)` ESCAPA el texto del correo y solo añade sus
        # propios <a>; por eso su resultado se puede marcar como seguro. Sin
        # mark_safe, format_html lo escaparía otra vez y los enlaces se
        # verían como texto.
        cuerpo = mark_safe(linebreaks(urlize(correo.cuerpo, autoescape=True)))
        return format_html('<div style="max-width:70ch;line-height:1.6">{}</div>', cuerpo)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False  # se lee y se borra, no se edita


# Solo aparece en el admin cuando los correos van a la bandeja: en
# producción sería una sección vacía que confunde.
if settings.EMAIL_BACKEND == "notificaciones.correo.BandejaLocal":
    admin.site.register(CorreoLocal, CorreoLocalAdmin)
