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


class MetodosTests(TestCase):
    """La migración 0003 cargó los tres métodos con sus datos vacíos."""

    def test_publicos_con_datos_por_confirmar(self):
        r = APIClient().get("/pagos/metodos")
        self.assertEqual(r.status_code, 200)
        metodos = r.json()["metodos"]
        self.assertEqual([m["id"] for m in metodos], ["pago-movil", "transferencia", "zelle"])
        self.assertEqual(metodos[2]["moneda"], "USD")
        self.assertIsNone(metodos[0]["datos"][0]["valor"])  # el frontend pinta "Por confirmar"

    def test_un_dato_cargado_en_el_admin_se_publica(self):
        from .models import DatoCobro

        DatoCobro.objects.filter(metodo__codigo="zelle", etiqueta="Correo").update(valor="pagos@amh.com")
        zelle = APIClient().get("/pagos/metodos").json()["metodos"][2]
        self.assertEqual(zelle["datos"][0], {"etiqueta": "Correo", "valor": "pagos@amh.com"})

    def test_apagado_no_se_ofrece(self):
        from .models import MetodoPago

        MetodoPago.objects.filter(codigo="transferencia").update(activo=False)
        ids = [m["id"] for m in APIClient().get("/pagos/metodos").json()["metodos"]]
        self.assertNotIn("transferencia", ids)


class TasaTests(TestCase):
    def setUp(self):
        from .models import TasaCambio

        self.Tasa = TasaCambio
        self.hoy = timezone.localdate()

    def test_sin_tasa_cargada_responde_404(self):
        r = APIClient().get("/pagos/tasa")
        self.assertEqual((r.status_code, r.json()["codigo"]), (404, "sin-tasa"))

    def test_vale_la_ultima_cargada_hasta_hoy(self):
        self.Tasa.objects.create(fecha=self.hoy - timedelta(days=3), bs_por_usd=Decimal("39.5"))
        self.Tasa.objects.create(fecha=self.hoy - timedelta(days=1), bs_por_usd=Decimal("40.25"))
        self.Tasa.objects.create(fecha=self.hoy + timedelta(days=1), bs_por_usd=Decimal("99"))  # futura: no vale
        self.assertEqual(APIClient().get("/pagos/tasa").json()["bs_por_usd"], 40.25)

    def test_el_reporte_en_bolivares_guarda_la_tasa_del_dia_del_pago(self):
        self.Tasa.objects.create(fecha=self.hoy - timedelta(days=5), bs_por_usd=Decimal("38"))
        self.Tasa.objects.create(fecha=self.hoy, bs_por_usd=Decimal("41"))
        u = Usuario.objects.create_user("t@demo.com", "Segura123", nombre="T", documento="V-22222222")
        s = Suscripcion.objects.create(usuario=u, plan="P", monto=Decimal("100"))
        api = APIClient()
        api.force_authenticate(u)
        hace_3 = str(self.hoy - timedelta(days=3))
        api.post(
            "/portal/pagos",
            {"metodo": "pago-movil", "referencia": "5555", "fecha": hace_3, "monto": "3800", "suscripciones": [s.id]},
            format="json",
        )
        self.assertEqual(ReportePago.objects.get().tasa_bcv, Decimal("38"))


class MetodoApagadoTests(Base):
    def test_no_acepta_reportes_de_un_metodo_apagado(self):
        from .models import MetodoPago

        MetodoPago.objects.filter(codigo="zelle").update(activo=False)
        r = self.reportar(metodo="zelle")
        self.assertEqual((r.status_code, r.json()["codigo"]), (400, "metodo-no-disponible"))

    def test_zelle_guarda_dolares_y_sin_tasa(self):
        self.reportar(metodo="zelle", monto="45")
        pago = ReportePago.objects.get()
        self.assertEqual((pago.moneda, pago.tasa_bcv), ("USD", None))
