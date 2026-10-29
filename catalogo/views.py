from django.db.models import Prefetch
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import OpcionPago, Producto


class Decimal2Float(serializers.DecimalField):
    """Los importes salen como número (700.0), que es lo que espera el
    frontend; dentro del backend se calcula siempre con Decimal."""

    def to_representation(self, valor):
        return None if valor is None else float(valor)


class OpcionPublica(serializers.ModelSerializer):
    precio = Decimal2Float(max_digits=10, decimal_places=2, allow_null=True)

    class Meta:
        model = OpcionPago
        fields = ["codigo", "nombre", "meses", "precio", "destacado"]


class ProductoPublico(serializers.ModelSerializer):
    iva = Decimal2Float(max_digits=5, decimal_places=2, allow_null=True)
    opciones = OpcionPublica(many=True)

    class Meta:
        model = Producto
        fields = ["codigo", "nombre", "marca", "iva", "opciones"]


class Catalogo(APIView):
    """GET /tienda/catalogo — productos activos con sus opciones activas.

    Público: es lo mismo que se ve en /tienda. Solo precios y ciclos; los
    textos de marketing siguen en el frontend."""

    permission_classes = [AllowAny]

    def get(self, request):
        productos = Producto.objects.filter(activo=True).prefetch_related(
            Prefetch("opciones", queryset=OpcionPago.objects.filter(activa=True))
        )
        return Response({"productos": ProductoPublico(productos, many=True).data})
