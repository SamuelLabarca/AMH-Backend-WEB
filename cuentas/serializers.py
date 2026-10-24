from django.contrib.auth import password_validation
from rest_framework import serializers

from .models import Usuario


class UsuarioPublico(serializers.ModelSerializer):
    """Lo único que sale de la API sobre un usuario. Nunca la contraseña,
    el hash ni los permisos."""

    class Meta:
        model = Usuario
        fields = ["id", "nombre", "documento", "correo"]


class Registro(serializers.Serializer):
    nombre = serializers.CharField(max_length=150, trim_whitespace=True)
    # Llega ya normalizado por el frontend (normalizarDocumento): V-12345678.
    documento = serializers.RegexField(r"^[VEJGP]-\d{5,10}$", max_length=16)
    correo = serializers.EmailField()
    telefono = serializers.CharField(max_length=30, allow_blank=True, required=False)
    contrasena = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_correo(self, correo):
        return Usuario.objects.normalizar_correo(correo)

    def validate(self, datos):
        # Los validadores de settings.AUTH_PASSWORD_VALIDATORS, con los datos
        # del usuario para rechazar contraseñas parecidas a su correo.
        provisional = Usuario(correo=datos["correo"], nombre=datos["nombre"], documento=datos["documento"])
        try:
            password_validation.validate_password(datos["contrasena"], provisional)
        except Exception as e:  # ValidationError de Django → de DRF
            raise serializers.ValidationError({"contrasena": list(getattr(e, "messages", [str(e)]))})
        return datos


class InicioSesion(serializers.Serializer):
    correo = serializers.EmailField()
    contrasena = serializers.CharField(trim_whitespace=False)


class PedirRecuperacion(serializers.Serializer):
    correo = serializers.EmailField()


class ConfirmarRecuperacion(serializers.Serializer):
    token = serializers.CharField()
    contrasena = serializers.CharField(trim_whitespace=False)
