from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from cuentas.errores import ErrorNegocio
from suscripciones.models import Suscripcion

from .models import DatoCobro, MetodoPago, ReportePago
from .servicios import tasa_vigente


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

        # Solo métodos encendidos en el admin: apagar uno corta también
        # los reportes nuevos, no solo deja de mostrarse.
        metodo = MetodoPago.objects.filter(codigo=d["metodo"], activo=True).first()
        if metodo is None:
            raise ErrorNegocio(400, "metodo-no-disponible")

        # Solo suscripciones PROPIAS. Si alguna no lo es, se rechaza todo
        # sin decir cuál: no se confirma que exista una suscripción ajena.
        ids = set(d["suscripciones"])
        suscripciones = list(request.user.suscripciones.filter(pk__in=ids).exclude(estado=Suscripcion.Estado.CANCELADA))
        if len(suscripciones) != len(ids):
            raise ErrorNegocio(400, "suscripcion-invalida")

        # Pago en bolívares: se copia la tasa del día del PAGO (no la de hoy),
        # que es con la que el cliente calculó el monto.
        tasa = tasa_vigente(d["fecha"]) if metodo.moneda == MetodoPago.Moneda.BOLIVARES else None

        try:
            with transaction.atomic():
                reporte = ReportePago.objects.create(
                    usuario=request.user,
                    metodo=metodo.codigo,
                    referencia=d["referencia"],
                    fecha_pago=d["fecha"],
                    banco_origen=d.get("banco", ""),
                    monto=d["monto"],
                    moneda=metodo.moneda,
                    total_usd=sum((s.monto for s in suscripciones), Decimal("0")),
                    tasa_bcv=tasa.bs_por_usd if tasa else None,
                )
                reporte.suscripciones.set(suscripciones)
        except IntegrityError:
            raise ErrorNegocio(409, "referencia-usada")

        return Response({"id": reporte.id, "estado": reporte.estado}, status=status.HTTP_201_CREATED)


class Metodos(APIView):
    """GET /pagos/metodos — los métodos de cobro activos con sus datos.

    Público a propósito: son los datos que se le dan a cualquiera que va a
    pagar (como un número de cuenta en una factura). Por eso aquí NUNCA va
    nada que no se pueda publicar."""

    permission_classes = [AllowAny]

    def get(self, request):
        metodos = MetodoPago.objects.filter(activo=True).prefetch_related(
            Prefetch("datos", queryset=DatoCobro.objects.order_by("orden", "id"))
        )
        return Response(
            {
                "metodos": [
                    {
                        "id": m.codigo,
                        "nombre": m.nombre,
                        "moneda": m.moneda,
                        "datos": [{"etiqueta": d.etiqueta, "valor": d.valor or None} for d in m.datos.all()],
                    }
                    for m in metodos
                ]
            }
        )


class Tasa(APIView):
    """GET /pagos/tasa — la tasa BCV vigente.
    200 → { fecha, bs_por_usd } · 404 { codigo: "sin-tasa" } si nunca se cargó."""

    permission_classes = [AllowAny]

    def get(self, request):
        tasa = tasa_vigente()
        if tasa is None:
            raise ErrorNegocio(404, "sin-tasa")
        return Response({"fecha": tasa.fecha, "bs_por_usd": float(tasa.bs_por_usd)})
