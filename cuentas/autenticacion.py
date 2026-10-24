from rest_framework.authentication import SessionAuthentication


class SesionConCsrf(SessionAuthentication):
    """La sesión de Django, con CSRF SIEMPRE.

    La de DRF solo comprueba CSRF cuando ya hay sesión. Eso deja sin
    protección el inicio de sesión y el registro: otra web podría hacer
    que tu navegador entrara con una cuenta del atacante ("login CSRF").
    Aquí se comprueba en toda petición que modifica algo, haya sesión o no.
    Las GET no se ven afectadas: el middleware de CSRF las deja pasar.
    """

    def authenticate(self, request):
        self.enforce_csrf(request)
        usuario = getattr(request._request, "user", None)
        if not usuario or not usuario.is_active:
            return None
        return (usuario, None)
