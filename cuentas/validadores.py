import re

from django.core.exceptions import ValidationError


class LetrasYNumerosValidator:
    """La contraseña tiene que combinar letras y números. Es la misma regla
    que avisa el frontend antes de enviar (validarContrasena)."""

    def validate(self, password, user=None):
        if not re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]", password) or not re.search(r"\d", password):
            raise ValidationError("Debe combinar letras y números.", code="letras_y_numeros")

    def get_help_text(self):
        return "Tu contraseña tiene que combinar letras y números."
