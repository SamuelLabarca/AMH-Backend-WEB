from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from cuentas.models import Usuario

from .models import Suscripcion
from .servicios import renovar, sumar_meses

HOY = date(2026, 10, 24)


def usuario(correo, documento):
    return Usuario.objects.create_user(correo, "Segura123", nombre="Cliente", documento=documento)


class EstadoTests(TestCase):
    def sus(self, **campos):
        return Suscripcion(plan="Plan Empresa", monto=Decimal("45"), **campos)

    def test_estados_calculados_por_fecha(self):
        A = Suscripcion.Estado.ACTIVA
        self.assertEqual(self.sus(estado=A, vence=HOY + timedelta(days=30)).estado_actual(HOY), "activa")
        self.assertEqual(self.sus(estado=A, vence=HOY + timedelta(days=5)).estado_actual(HOY), "por-vencer")
        self.assertEqual(self.sus(estado=A, vence=HOY - timedelta(days=1)).estado_actual(HOY), "vencida")
        self.assertEqual(self.sus(estado=Suscripcion.Estado.SUSPENDIDA, vence=HOY).estado_actual(HOY), "suspendida")

    def test_solo_activa_o_por_vencer_dan_acceso_al_panel(self):
        A = Suscripcion.Estado.ACTIVA
        self.assertTrue(self.sus(estado=A, vence=HOY + timedelta(days=3)).da_acceso_al_panel(HOY))
        self.assertFalse(self.sus(estado=A, vence=HOY - timedelta(days=1)).da_acceso_al_panel(HOY))
        self.assertFalse(self.sus(estado=Suscripcion.Estado.PENDIENTE).da_acceso_al_panel(HOY))


class RenovarTests(TestCase):
    def setUp(self):
        self.u = usuario("a@demo.com", "V-11111111")

    def test_sumar_meses_respeta_el_fin_de_mes(self):
        self.assertEqual(sumar_meses(date(2026, 1, 31), 1), date(2026, 2, 28))
        self.assertEqual(sumar_meses(date(2026, 11, 15), 12), date(2027, 11, 15))

    def test_renovar_antes_de_vencer_no_pierde_dias(self):
        s = Suscripcion.objects.create(usuario=self.u, plan="P", monto=1, estado="activa", vence=HOY + timedelta(days=5))
        renovar(s, hoy=HOY)
        self.assertEqual(s.vence, sumar_meses(HOY + timedelta(days=5), 1))

    def test_renovar_vencida_cuenta_desde_hoy(self):
        s = Suscripcion.objects.create(usuario=self.u, plan="P", monto=1, estado="activa", vence=date(2026, 1, 1))
        renovar(s, hoy=HOY)
        self.assertEqual((s.vence, s.estado), (sumar_meses(HOY, 1), "activa"))


class CuentaTests(TestCase):
    def setUp(self):
        self.maria = usuario("maria@demo.com", "V-12345678")
        self.otra = usuario("otra@demo.com", "J-123456789")
        Suscripcion.objects.create(usuario=self.maria, plan="Plan Empresa", monto=45, estado="activa", vence=HOY)
        Suscripcion.objects.create(usuario=self.otra, plan="Plan Ajeno", monto=450)
        self.api = APIClient()

    def test_sin_sesion_responde_401(self):
        self.assertEqual(self.api.get("/portal/cuenta").status_code, 401)

    def test_devuelve_solo_las_suscripciones_propias(self):
        self.api.force_authenticate(self.maria)
        datos = self.api.get("/portal/cuenta").json()["suscripciones"]
        self.assertEqual([s["plan"] for s in datos], ["Plan Empresa"])
        self.assertEqual(datos[0]["ciclo"], "Mensual")
        self.assertEqual(datos[0]["monto"], 45.0)
