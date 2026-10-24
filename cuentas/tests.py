import re

from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Usuario

DATOS = {
    "nombre": "María González",
    "documento": "V-12345678",
    "correo": "Maria@Demo.com",
    "telefono": "+58 412 1234567",
    "contrasena": "Segura123",
}


class Base(TestCase):
    def setUp(self):
        cache.clear()  # los límites de intentos viven en la caché
        # Con CSRF de verdad, como el navegador.
        self.api = APIClient(enforce_csrf_checks=True)
        self.api.get("/auth/csrf")

    def post(self, ruta, datos):
        token = self.api.cookies["csrftoken"].value
        return self.api.post(ruta, datos, format="json", HTTP_X_CSRFTOKEN=token)

    def delete(self, ruta):
        return self.api.delete(ruta, HTTP_X_CSRFTOKEN=self.api.cookies["csrftoken"].value)

    def crear(self, **cambios):
        d = {**DATOS, **cambios}
        return Usuario.objects.create_user(d["correo"], d["contrasena"], nombre=d["nombre"], documento=d["documento"])


class RegistroTests(Base):
    def test_crea_la_cuenta_abre_sesion_y_no_devuelve_la_contrasena(self):
        r = self.post("/auth/registro", DATOS)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["usuario"]["correo"], "maria@demo.com")
        self.assertNotIn("contrasena", r.json()["usuario"])
        self.assertEqual(self.api.get("/auth/sesion").status_code, 200)

    def test_guarda_la_contrasena_con_argon2(self):
        self.post("/auth/registro", DATOS)
        self.assertTrue(Usuario.objects.get().password.startswith("argon2"))

    def test_correo_o_documento_repetido_da_el_mismo_error(self):
        self.crear()
        r1 = self.post("/auth/registro", {**DATOS, "documento": "V-99999999"})
        r2 = self.post("/auth/registro", {**DATOS, "correo": "otra@demo.com"})
        self.assertEqual((r1.status_code, r1.json()["codigo"]), (409, "cuenta-existente"))
        self.assertEqual((r2.status_code, r2.json()["codigo"]), (409, "cuenta-existente"))

    def test_rechaza_contrasena_sin_numeros(self):
        r = self.post("/auth/registro", {**DATOS, "contrasena": "sololetrasaqui"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("contrasena", r.json()["campos"])

    def test_sin_token_csrf_no_registra(self):
        r = self.api.post("/auth/registro", DATOS, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Usuario.objects.exists())


class SesionTests(Base):
    def test_sin_sesion_responde_401(self):
        r = self.api.get("/auth/sesion")
        self.assertEqual((r.status_code, r.json()["codigo"]), (401, "sin-sesion"))

    def test_entra_con_correo_en_cualquier_mayuscula(self):
        self.crear()
        r = self.post("/auth/sesion", {"correo": "MARIA@demo.com", "contrasena": "Segura123"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["usuario"]["documento"], "V-12345678")

    def test_credenciales_incorrectas_no_dicen_cual_fallo(self):
        self.crear()
        mala_clave = self.post("/auth/sesion", {"correo": "maria@demo.com", "contrasena": "Otra1234"})
        sin_cuenta = self.post("/auth/sesion", {"correo": "nadie@demo.com", "contrasena": "Otra1234"})
        self.assertEqual(mala_clave.json(), sin_cuenta.json())
        self.assertEqual(mala_clave.status_code, 401)

    def test_la_cookie_de_sesion_es_httponly(self):
        self.crear()
        self.post("/auth/sesion", {"correo": "maria@demo.com", "contrasena": "Segura123"})
        self.assertTrue(self.api.cookies["sessionid"]["httponly"])

    def test_salir_cierra_la_sesion(self):
        self.crear()
        self.post("/auth/sesion", {"correo": "maria@demo.com", "contrasena": "Segura123"})
        self.assertEqual(self.delete("/auth/sesion").status_code, 204)
        self.assertEqual(self.api.get("/auth/sesion").status_code, 401)

    def test_frena_la_fuerza_bruta(self):
        self.crear()
        codigos = [
            self.post("/auth/sesion", {"correo": "maria@demo.com", "contrasena": f"Mala{i}xx"}).status_code
            for i in range(11)
        ]
        self.assertEqual(codigos[-1], 429)


class RecuperacionTests(Base):
    def pedir(self, correo):
        return self.post("/auth/recuperacion", {"correo": correo})

    def token_del_correo(self):
        return re.search(r"token=([\w.-]+)", mail.outbox[-1].body).group(1)

    def test_responde_igual_exista_o_no_el_correo(self):
        self.crear()
        self.assertEqual(self.pedir("maria@demo.com").status_code, 202)
        self.assertEqual(self.pedir("nadie@demo.com").status_code, 202)
        self.assertEqual(len(mail.outbox), 1)  # solo al que existe

    def test_cambia_la_contrasena_y_el_enlace_es_de_un_solo_uso(self):
        self.crear()
        self.pedir("maria@demo.com")
        token = self.token_del_correo()

        r = self.post("/auth/recuperacion/confirmar", {"token": token, "contrasena": "Nueva1234"})
        self.assertEqual(r.status_code, 204)
        self.assertTrue(Usuario.objects.get().check_password("Nueva1234"))

        otra = self.post("/auth/recuperacion/confirmar", {"token": token, "contrasena": "Otra12345"})
        self.assertEqual((otra.status_code, otra.json()["codigo"]), (400, "token-invalido"))

    def test_cambiar_la_contrasena_cierra_las_otras_sesiones(self):
        self.crear()
        otro = APIClient()
        otro.login(username="maria@demo.com", password="Segura123")
        self.assertEqual(otro.get("/auth/sesion").status_code, 200)

        self.pedir("maria@demo.com")
        self.post("/auth/recuperacion/confirmar", {"token": self.token_del_correo(), "contrasena": "Nueva1234"})
        self.assertEqual(otro.get("/auth/sesion").status_code, 401)

    def test_token_inventado(self):
        r = self.post("/auth/recuperacion/confirmar", {"token": "abc.def", "contrasena": "Nueva1234"})
        self.assertEqual(r.json()["codigo"], "token-invalido")
