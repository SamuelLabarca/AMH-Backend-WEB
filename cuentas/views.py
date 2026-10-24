from django.conf import settings
from django.contrib.auth import authenticate, login, logout, password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import serializers as s
from .errores import ErrorNegocio
from .models import Usuario


class SoloPostLimitado(APIView):
    """Limita los intentos SOLO en los POST: la consulta de sesión (GET)
    se hace en cada visita y no tiene que gastar intentos."""

    throttle_classes = [ScopedRateThrottle]

    def get_throttles(self):
        return super().get_throttles() if self.request.method == "POST" else []


@method_decorator(ensure_csrf_cookie, name="dispatch")
class Csrf(APIView):
    """GET /auth/csrf — deja la cookie `csrftoken` y devuelve el token.

    El frontend lo pide una vez y lo manda en la cabecera X-CSRFToken.
    Se devuelve también en el cuerpo porque en producción el frontend y
    la API viven en subdominios distintos y el JavaScript del portal no
    puede leer una cookie de otro subdominio."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrf": get_token(request)})


class Sesion(SoloPostLimitado):
    """GET quién soy · POST entrar · DELETE salir."""

    permission_classes = [AllowAny]
    throttle_scope = "sesion"

    def get(self, request):
        if not request.user.is_authenticated:
            raise ErrorNegocio(401, "sin-sesion")
        return Response({"usuario": s.UsuarioPublico(request.user).data})

    def post(self, request):
        datos = s.InicioSesion(data=request.data)
        datos.is_valid(raise_exception=True)
        usuario = authenticate(
            request,
            username=Usuario.objects.normalizar_correo(datos.validated_data["correo"]),
            password=datos.validated_data["contrasena"],
        )
        # El mismo error si falla el correo o la contraseña: no se revela cuál.
        if usuario is None:
            raise ErrorNegocio(401, "credenciales-invalidas")
        login(request, usuario)  # rota la sesión: evita la fijación de sesión
        return Response({"usuario": s.UsuarioPublico(usuario).data})

    def delete(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class Registro(SoloPostLimitado):
    """POST /auth/registro — crea la cuenta y abre la sesión."""

    permission_classes = [AllowAny]
    throttle_scope = "registro"

    def post(self, request):
        datos = s.Registro(data=request.data)
        datos.is_valid(raise_exception=True)
        d = datos.validated_data
        try:
            with transaction.atomic():
                usuario = Usuario.objects.create_user(
                    d["correo"],
                    d["contrasena"],
                    nombre=d["nombre"],
                    documento=d["documento"],
                    telefono=d.get("telefono", ""),
                )
        except IntegrityError:
            # Correo o documento repetidos: un solo mensaje para los dos.
            raise ErrorNegocio(409, "cuenta-existente")
        login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"usuario": s.UsuarioPublico(usuario).data}, status=status.HTTP_201_CREATED)


class Recuperacion(SoloPostLimitado):
    """POST /auth/recuperacion — envía el enlace por correo.

    Responde 202 SIEMPRE, exista o no la cuenta: si dijera "ese correo no
    existe", serviría para averiguar quién es cliente."""

    permission_classes = [AllowAny]
    throttle_scope = "recuperacion"

    def post(self, request):
        datos = s.PedirRecuperacion(data=request.data)
        datos.is_valid(raise_exception=True)
        correo = Usuario.objects.normalizar_correo(datos.validated_data["correo"])
        usuario = Usuario.objects.filter(correo=correo, is_active=True).first()
        if usuario:
            enviar_enlace_recuperacion(usuario)
        return Response(status=status.HTTP_202_ACCEPTED)


class ConfirmarRecuperacion(SoloPostLimitado):
    """POST /auth/recuperacion/confirmar — cambia la contraseña con el token.

    El token de Django vence a los 30 min (PASSWORD_RESET_TIMEOUT) y deja de
    servir en cuanto cambia la contraseña: es de un solo uso. Cambiarla
    además invalida las demás sesiones abiertas del usuario."""

    permission_classes = [AllowAny]
    throttle_scope = "recuperacion"

    def post(self, request):
        datos = s.ConfirmarRecuperacion(data=request.data)
        datos.is_valid(raise_exception=True)
        usuario = usuario_del_token(datos.validated_data["token"])
        if usuario is None:
            raise ErrorNegocio(400, "token-invalido")

        contrasena = datos.validated_data["contrasena"]
        try:
            password_validation.validate_password(contrasena, usuario)
        except ValidationError as e:
            raise ErrorNegocio(400, "contrasena-invalida", " ".join(e.messages))

        usuario.set_password(contrasena)
        usuario.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# El token del enlace: "<id en base64>.<token de Django>". El frontend lo
# trata como una sola cadena (?token=...), no necesita saber que son dos.
# ---------------------------------------------------------------------------
def crear_token(usuario):
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    return f"{uid}.{default_token_generator.make_token(usuario)}"


def usuario_del_token(token):
    try:
        uid, firma = token.split(".", 1)
        usuario = Usuario.objects.get(pk=force_str(urlsafe_base64_decode(uid)), is_active=True)
    except (ValueError, TypeError, OverflowError, Usuario.DoesNotExist):
        return None
    return usuario if default_token_generator.check_token(usuario, firma) else None


def enviar_enlace_recuperacion(usuario):
    enlace = f"{settings.URL_PORTAL}/restablecer?token={crear_token(usuario)}"
    send_mail(
        subject="Crea tu contraseña nueva · My Business Panel",
        message=(
            f"Hola, {usuario.nombre}:\n\n"
            "Pediste cambiar la contraseña de tu cuenta. Entra en este enlace para crear una nueva:\n\n"
            f"{enlace}\n\n"
            "El enlace vence en 30 minutos y solo se puede usar una vez.\n"
            "Si no fuiste tú, ignora este correo: tu contraseña no cambia.\n\n"
            "AMH Solutions"
        ),
        from_email=None,  # DEFAULT_FROM_EMAIL
        recipient_list=[usuario.correo],
    )
