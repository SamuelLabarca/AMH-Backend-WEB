from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class GestorUsuarios(BaseUserManager):
    """Crea usuarios con el CORREO como identificador, siempre en minúsculas
    para que "Maria@Demo.com" y "maria@demo.com" sean la misma cuenta."""

    use_in_migrations = True

    @staticmethod
    def normalizar_correo(correo):
        return correo.strip().lower()

    def _crear(self, correo, password, **campos):
        if not correo:
            raise ValueError("El correo es obligatorio.")
        usuario = self.model(correo=self.normalizar_correo(correo), **campos)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, correo, password=None, **campos):
        campos.setdefault("is_staff", False)
        campos.setdefault("is_superuser", False)
        return self._crear(correo, password, **campos)

    def create_superuser(self, correo, password=None, **campos):
        campos.update(is_staff=True, is_superuser=True)
        return self._crear(correo, password, **campos)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """La cuenta del cliente: la MISMA para el portal de pagos y para My
    Business Panel. Se entra con correo; el documento se pide al
    registrarse pero no sirve para entrar, porque es un dato público.

    Tener cuenta no da acceso al Panel: eso lo decide el estado de sus
    suscripciones (ver suscripciones.models)."""

    correo = models.EmailField("correo", unique=True)
    nombre = models.CharField("nombre o razón social", max_length=150)
    documento = models.CharField("cédula o RIF", max_length=16, unique=True, help_text="Formato V-12345678")
    telefono = models.CharField("teléfono", max_length=30, blank=True)

    is_active = models.BooleanField("activo", default=True)
    is_staff = models.BooleanField("equipo de AMH", default=False, help_text="Puede entrar al panel de administración.")
    fecha_registro = models.DateTimeField("registro", default=timezone.now)

    objects = GestorUsuarios()

    USERNAME_FIELD = "correo"
    EMAIL_FIELD = "correo"
    REQUIRED_FIELDS = ["nombre", "documento"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        return f"{self.nombre} ({self.correo})"
