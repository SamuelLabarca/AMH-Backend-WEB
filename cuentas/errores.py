from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler


class ErrorNegocio(exceptions.APIException):
    """Un error con `codigo` para que el frontend elija el mensaje sin
    depender del texto (ver amh/src/pages/portal/rutas.js)."""

    def __init__(self, estado, codigo, mensaje=""):
        self.status_code = estado
        self.codigo = codigo
        super().__init__(mensaje or codigo)


def manejar_error(exc, contexto):
    """Todas las respuestas de error con la misma forma: { codigo, mensaje }.
    Nunca se devuelve el detalle interno de una excepción inesperada."""

    if isinstance(exc, ErrorNegocio):
        return Response({"codigo": exc.codigo, "mensaje": str(exc.detail)}, status=exc.status_code)

    # Sin sesión es 401, no 403: el frontend lo usa para volver a pedir entrar.
    if isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
        return Response({"codigo": "sin-sesion", "mensaje": "Inicia sesión para continuar."}, status=401)

    respuesta = exception_handler(exc, contexto)
    if respuesta is None:
        return None

    if isinstance(exc, exceptions.Throttled):
        respuesta.data = {"codigo": "demasiados-intentos", "mensaje": "Demasiados intentos. Espera unos minutos."}
    elif isinstance(exc, exceptions.ValidationError):
        respuesta.data = {"codigo": "datos-invalidos", "mensaje": "Revisa los datos.", "campos": exc.detail}
    elif respuesta.status_code == status.HTTP_403_FORBIDDEN:
        # Incluye el fallo de CSRF.
        respuesta.data = {"codigo": "sin-permiso", "mensaje": "No puedes hacer esto."}
    else:
        respuesta.data = {"codigo": "error", "mensaje": str(getattr(exc, "detail", "Error"))}
    return respuesta
