from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from .models import OpcionPago, Producto


class CatalogoTests(TestCase):
    """La migración 0002 ya cargó el catálogo inicial en la base de tests."""

    def setUp(self):
        self.api = APIClient()

    def test_es_publico_y_trae_los_precios_iniciales(self):
        r = self.api.get("/tienda/catalogo")
        self.assertEqual(r.status_code, 200)
        producto = r.json()["productos"][0]
        self.assertEqual(producto["codigo"], "administrativo")
        precios = {o["codigo"]: o["precio"] for o in producto["opciones"]}
        self.assertEqual(precios, {"anual": 700.0, "trimestral": 225.0, "mensual": 100.0})

    def test_respeta_el_orden_del_admin(self):
        opciones = self.api.get("/tienda/catalogo").json()["productos"][0]["opciones"]
        self.assertEqual([o["codigo"] for o in opciones], ["anual", "trimestral", "mensual"])

    def test_un_cambio_de_precio_en_el_admin_se_ve_en_la_api(self):
        OpcionPago.objects.filter(codigo="mensual").update(precio=Decimal("120"))
        opciones = self.api.get("/tienda/catalogo").json()["productos"][0]["opciones"]
        self.assertEqual(next(o["precio"] for o in opciones if o["codigo"] == "mensual"), 120.0)

    def test_oculta_opciones_y_productos_desactivados(self):
        OpcionPago.objects.filter(codigo="trimestral").update(activa=False)
        opciones = self.api.get("/tienda/catalogo").json()["productos"][0]["opciones"]
        self.assertNotIn("trimestral", [o["codigo"] for o in opciones])

        Producto.objects.update(activo=False)
        self.assertEqual(self.api.get("/tienda/catalogo").json()["productos"], [])

    def test_precio_vacio_sale_como_null(self):
        OpcionPago.objects.filter(codigo="anual").update(precio=None)
        opciones = self.api.get("/tienda/catalogo").json()["productos"][0]["opciones"]
        self.assertIsNone(opciones[0]["precio"])
