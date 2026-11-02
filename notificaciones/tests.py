import re

from django.contrib.admin.sites import site
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from cuentas.models import Usuario

from .admin import CorreoLocalAdmin
from .models import CorreoLocal

BANDEJA = "notificaciones.correo.BandejaLocal"


@override_settings(EMAIL_BACKEND=BANDEJA)
class BandejaLocalTests(TestCase):
    def test_guarda_el_correo_en_vez_de_enviarlo(self):
        enviados = mail.send_mail("Hola", "Cuerpo del correo", "amh@local", ["a@demo.com", "b@demo.com"])
        self.assertEqual(enviados, 1)
        correo = CorreoLocal.objects.get()
        self.assertEqual((correo.asunto, correo.para, correo.cuerpo), ("Hola", "a@demo.com, b@demo.com", "Cuerpo del correo"))

    def test_guarda_tambien_la_version_html(self):
        mensaje = mail.EmailMultiAlternatives("Con HTML", "texto", "amh@local", ["a@demo.com"])
        mensaje.attach_alternative("<p>html</p>", "text/html")
        mensaje.send()
        self.assertEqual(CorreoLocal.objects.get().html, "<p>html</p>")

    def test_el_correo_de_recuperacion_llega_a_la_bandeja_con_su_enlace(self):
        cache.clear()
        Usuario.objects.create_user("maria@demo.com", "Segura123", nombre="María", documento="V-12345678")
        api = APIClient(enforce_csrf_checks=True)
        token = api.get("/auth/csrf").json()["csrf"]
        api.post("/auth/recuperacion", {"correo": "maria@demo.com"}, format="json", HTTP_X_CSRFTOKEN=token)

        correo = CorreoLocal.objects.get()
        self.assertEqual(correo.para, "maria@demo.com")
        self.assertRegex(correo.cuerpo, r"/portal-de-pagos/restablecer\?token=")

    def test_el_admin_muestra_los_enlaces_como_enlaces(self):
        correo = CorreoLocal.objects.create(
            para="a@demo.com", asunto="x", cuerpo="Entra en http://localhost:5173/x?token=abc", remitente="amh"
        )
        html = CorreoLocalAdmin(CorreoLocal, site).mensaje(correo)
        self.assertTrue(re.search(r'<a href="http://localhost:5173/x\?token=abc"', html))

    def test_el_admin_escapa_el_html_del_cuerpo(self):
        correo = CorreoLocal.objects.create(para="a", asunto="x", cuerpo="<script>alert(1)</script>", remitente="amh")
        html = CorreoLocalAdmin(CorreoLocal, site).mensaje(correo)
        self.assertNotIn("<script>", html)
