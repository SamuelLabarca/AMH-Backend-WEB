from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from cuentas.errores import ErrorNegocio

from . import servicios
from .models import Orden


class NuevaOrden(serializers.Serializer):
    # SOLO qué se compra. El precio nunca viene del navegador.
    producto = serializers.SlugField()
    opcion = serializers.SlugField()


class OrdenPublica(serializers.ModelSerializer):
    precio = serializers.FloatField()
    iva = serializers.FloatField(allow_null=True)
    impuesto = serializers.FloatField()
    total = serializers.FloatField()

    class Meta:
        model = Orden
        fields = ["id", "producto", "opcion", "meses", "precio", "iva", "impuesto", "total", "estado", "suscripcion"]


class Ordenes(APIView):
    """POST /tienda/ordenes — la compra (requiere sesión).

    201 → { orden } nueva · 200 → { orden } la pendiente que ya existía
    400 → { codigo: "opcion-no-disponible" }"""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ordenes"

    def post(self, request):
        datos = NuevaOrden(data=request.data)
        datos.is_valid(raise_exception=True)
        try:
            orden, nueva = servicios.crear_orden(
                request.user, datos.validated_data["producto"], datos.validated_data["opcion"]
            )
        except servicios.OpcionNoDisponible:
            raise ErrorNegocio(400, "opcion-no-disponible")
        return Response(
            {"orden": OrdenPublica(orden).data}, status=status.HTTP_201_CREATED if nueva else status.HTTP_200_OK
        )
