from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from cuentas.errores import ErrorNegocio
from suscripciones.models import Suscripcion

from .models import ReportePago


class NuevoReporte(serializers.Serializer):
    metodo = serializers.ChoiceField(choices=ReportePago.Metodo.choices)
    referencia = serializers.RegexField(r"^[A-Za-z0-9-]{4,40}$")
    fecha = serializers.DateField()
    banco = serializers.CharField(max_length=60, required=False, allow_blank=True)
    monto = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    suscripciones = serializers.ListField(child=serializers.IntegerField(), min_length=1)

    def validate_fecha(self, fecha):
        if fecha > timezone.localdate():
            raise serializers.ValidationError("La fecha del pago no puede ser futura.")
        return fecha


class Pagos(APIView):
    """POST /portal/pagos — el cliente reporta un pago.

    Queda PENDIENTE: nada se activa hasta que alguien del equipo lo verifica
    en el banco y lo aprueba desde el admin."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "pagos"

    def post(self, request):
        datos = NuevoReporte(data=request.data)
        datos.is_valid(raise_exception=True)
        d = datos.validated_data

        # Solo suscripciones PROPIAS. Si alguna no lo es, se rechaza todo
        # sin decir cuál: no se confirma que exista una suscripción ajena.
        ids = set(d["suscripciones"])
        suscripciones = list(request.user.suscripciones.filter(pk__in=ids).exclude(estado=Suscripcion.Estado.CANCELADA))
        if len(suscripciones) != len(ids):
            raise ErrorNegocio(400, "suscripcion-invalida")

        try:
            with transaction.atomic():
                reporte = ReportePago.objects.create(
                    usuario=request.user,
                    metodo=d["metodo"],
                    referencia=d["referencia"],
                    fecha_pago=d["fecha"],
                    banco_origen=d.get("banco", ""),
                    monto=d["monto"],
                    moneda=ReportePago.MONEDA[d["metodo"]],
                    total_usd=sum((s.monto for s in suscripciones), Decimal("0")),
                )
                reporte.suscripciones.set(suscripciones)
        except IntegrityError:
            raise ErrorNegocio(409, "referencia-usada")

        return Response({"id": reporte.id, "estado": reporte.estado}, status=status.HTTP_201_CREATED)
