from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Suscripcion


class SuscripcionPublica(serializers.ModelSerializer):
    """La forma que espera el portal (amh/src/servicios/portalPagos.js)."""

    ciclo = serializers.CharField(source="get_ciclo_display")
    estado = serializers.SerializerMethodField()
    monto = serializers.FloatField()

    class Meta:
        model = Suscripcion
        fields = ["id", "producto", "plan", "ciclo", "monto", "estado", "vence"]

    def get_estado(self, suscripcion):
        return suscripcion.estado_actual()


class Cuenta(APIView):
    """GET /portal/cuenta — las suscripciones del usuario CON SESIÓN.

    No recibe ningún dato del cliente: quién es sale de la cookie de
    sesión, así que no hay forma de pedir las de otro."""

    def get(self, request):
        suscripciones = request.user.suscripciones.exclude(estado=Suscripcion.Estado.CANCELADA)
        return Response({"suscripciones": SuscripcionPublica(suscripciones, many=True).data})
