from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from cuentas.models import Usuario
from suscripciones.models import Suscripcion

from . import servicios
from .models import ReportePago


class Base(TestCase):
    def setUp(self):
        cache.clear()
        self.maria = Usuario.objects.create_user("maria@demo.com", "Segura123", nombre="María", documento="V-12345678")
        self.otra = Usuario.objects.create_user("otra@demo.com", "Segura123", nombre="Otra", documento="V-87654321")
        self.equipo = Usuario.objects.create_superuser("equipo@amh.com", "Segura123", nombre="Equipo", documento="V-1000000")
        self.sus = Suscripcion.objects.create(usuario=self.maria, plan="Plan Empresa", monto=Decimal("45"))
        self.ajena = Suscripcion.objects.create(usuario=self.otra, plan="Plan Ajeno", monto=Decimal("15"))
        self.api = APIClient()
        self.api.force_authenticate(self.maria)

    def reportar(self, **cambios):
        datos = {
            "metodo": "pago-movil",
            "referencia": "00123456",
            "fecha": str(timezone.localdate()),
            "banco": "Banesco",
            "monto": "1800.50",
            "suscripciones": [self.sus.id],
            **cambios,
        }
        return self.api.post("/portal/pagos", datos, format="json")


class ReportarTests(Base):
    def test_queda_pendiente_con_la_moneda_del_metodo(self):
        r = self.reportar()
        self.assertEqual(r.status_code, 201)
        pago = ReportePago.objects.get()
        self.assertEqual((pago.estado, pago.moneda, pago.total_usd), ("pendiente", "Bs", Decimal("45")))
        self.sus.refresh_from_db()
        self.assertEqual(self.sus.estado, "pendiente")  # reportar NO activa nada

    def test_no_se_puede_reusar_una_referencia(self):
        self.reportar()
        r = self.reportar()
        self.assertEqual((r.status_code, r.json()["codigo"]), (409, "referencia-usada"))

    def test_no_se_puede_pagar_una_suscripcion_ajena(self):
        r = self.reportar(suscripciones=[self.sus.id, self.ajena.id])
        self.assertEqual((r.status_code, r.json()["codigo"]), (400, "suscripcion-invalida"))
        self.assertFalse(ReportePago.objects.exists())

    def test_fecha_futura_no_vale(self):
        r = self.reportar(fecha=str(timezone.localdate() + timedelta(days=1)))
        self.assertEqual(r.status_code, 400)


class AprobarTests(Base):
    def test_aprobar_activa_y_renueva_la_suscripcion(self):
        self.reportar()
        servicios.aprobar(ReportePago.objects.get().pk, self.equipo, tasa_bcv=Decimal("40.01"))
        self.sus.refresh_from_db()
        self.assertEqual(self.sus.estado_actual(), "activa")
        self.assertGreater(self.sus.vence, timezone.localdate())
        self.assertEqual(ReportePago.objects.get().revisado_por, self.equipo)

    def test_no_se_aprueba_dos_veces(self):
        self.reportar()
        pk = ReportePago.objects.get().pk
        servicios.aprobar(pk, self.equipo)
        vence = Suscripcion.objects.get(pk=self.sus.pk).vence
        with self.assertRaises(servicios.PagoYaRevisado):
            servicios.aprobar(pk, self.equipo)
        self.assertEqual(Suscripcion.objects.get(pk=self.sus.pk).vence, vence)

    def test_rechazar_no_toca_la_suscripcion(self):
        self.reportar()
        servicios.rechazar(ReportePago.objects.get().pk, self.equipo, "No aparece en el banco")
        self.sus.refresh_from_db()
        self.assertEqual(self.sus.estado, "pendiente")
