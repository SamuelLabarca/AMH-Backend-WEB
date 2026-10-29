from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from catalogo.models import OpcionPago, Producto
from cuentas.models import Usuario
from pagos import servicios as pagos
from pagos.models import ReportePago
from suscripciones.models import Suscripcion

from .models import Orden
from .servicios import calcular


class Base(TestCase):
    """La migración de catalogo ya cargó: anual 700, trimestral 225, mensual 100."""

    def setUp(self):
        cache.clear()
        self.maria = Usuario.objects.create_user("maria@demo.com", "Segura123", nombre="María", documento="V-12345678")
        self.api = APIClient()
        self.api.force_authenticate(self.maria)

    def comprar(self, opcion="anual", **extra):
        return self.api.post("/tienda/ordenes", {"producto": "administrativo", "opcion": opcion, **extra}, format="json")


class CrearOrdenTests(Base):
    def test_sin_sesion_responde_401(self):
        r = APIClient().post("/tienda/ordenes", {"producto": "administrativo", "opcion": "anual"}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_crea_la_orden_y_su_suscripcion_pendiente(self):
        r = self.comprar()
        self.assertEqual(r.status_code, 201)
        orden = r.json()["orden"]
        self.assertEqual((orden["total"], orden["meses"], orden["estado"]), (700.0, 12, "pendiente"))

        sus = Suscripcion.objects.get(pk=orden["suscripcion"])
        self.assertEqual((sus.estado, sus.ciclo, sus.monto, sus.usuario), ("pendiente", 12, Decimal("700"), self.maria))

    def test_el_precio_lo_pone_el_servidor_aunque_el_cliente_mande_otro(self):
        orden = self.comprar(precio=1, total=1).json()["orden"]
        self.assertEqual(orden["total"], 700.0)

    def test_suma_el_iva_del_producto(self):
        Producto.objects.update(iva=Decimal("16"))
        orden = self.comprar("trimestral").json()["orden"]
        self.assertEqual((orden["impuesto"], orden["total"]), (36.0, 261.0))

    def test_la_orden_congela_el_precio(self):
        orden_id = self.comprar("mensual").json()["orden"]["id"]
        OpcionPago.objects.filter(codigo="mensual").update(precio=Decimal("150"))
        self.assertEqual(Orden.objects.get(pk=orden_id).total, Decimal("100"))

    def test_repetir_la_misma_compra_devuelve_la_pendiente(self):
        primera = self.comprar().json()["orden"]
        r = self.comprar()
        self.assertEqual((r.status_code, r.json()["orden"]["id"]), (200, primera["id"]))
        self.assertEqual(Orden.objects.count(), 1)

    def test_cambiar_de_opcion_cancela_la_anterior(self):
        anterior = self.comprar("anual").json()["orden"]
        nueva = self.comprar("mensual").json()["orden"]
        self.assertNotEqual(anterior["id"], nueva["id"])
        self.assertEqual(Orden.objects.get(pk=anterior["id"]).estado, "cancelada")
        self.assertEqual(Suscripcion.objects.get(pk=anterior["suscripcion"]).estado, "cancelada")

    def test_no_vende_una_opcion_apagada_o_sin_precio(self):
        OpcionPago.objects.filter(codigo="trimestral").update(activa=False)
        OpcionPago.objects.filter(codigo="mensual").update(precio=None)
        for opcion in ("trimestral", "mensual", "no-existe"):
            r = self.comprar(opcion)
            self.assertEqual((r.status_code, r.json()["codigo"]), (400, "opcion-no-disponible"))
        self.assertFalse(Orden.objects.exists())


class PagarOrdenTests(Base):
    def test_aprobar_el_pago_activa_la_suscripcion_y_paga_la_orden(self):
        orden = self.comprar("mensual").json()["orden"]
        self.api.post(
            "/portal/pagos",
            {
                "metodo": "zelle",
                "referencia": "ZL-1001",
                "fecha": str(timezone.localdate()),
                "monto": "100",
                "suscripciones": [orden["suscripcion"]],
            },
            format="json",
        )
        equipo = Usuario.objects.create_superuser("e@amh.com", "Segura123", nombre="E", documento="V-1000000")
        pagos.aprobar(ReportePago.objects.get().pk, equipo)

        self.assertEqual(Orden.objects.get(pk=orden["id"]).estado, "pagada")
        sus = Suscripcion.objects.get(pk=orden["suscripcion"])
        self.assertEqual(sus.estado_actual(), "activa")
        self.assertTrue(sus.da_acceso_al_panel())


class CalcularTests(TestCase):
    def test_redondea_al_centimo(self):
        self.assertEqual(calcular(Decimal("99.99"), Decimal("16")), (Decimal("16.00"), Decimal("115.99")))
        self.assertEqual(calcular(Decimal("100"), None), (Decimal("0"), Decimal("100")))
