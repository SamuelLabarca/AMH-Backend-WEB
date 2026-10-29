"""Carga los métodos de cobro que hasta ahora vivían en el frontend
(contenido.js → METODOS_PAGO), con los datos VACÍOS: la web los muestra
como "Por confirmar" hasta que el equipo los complete en el admin.

La tasa BCV no se carga: un valor inventado acabaría cobrándose."""

from django.db import migrations

METODOS = [
    # codigo, nombre, moneda, orden, etiquetas de los datos
    ("pago-movil", "Pago Móvil", "Bs", 1, ["Banco", "Teléfono", "RIF"]),
    ("transferencia", "Transferencia", "Bs", 2, ["Banco", "Cuenta", "Titular", "RIF"]),
    ("zelle", "Zelle", "USD", 3, ["Correo", "Titular"]),
]


def cargar(apps, schema_editor):
    MetodoPago = apps.get_model("pagos", "MetodoPago")
    DatoCobro = apps.get_model("pagos", "DatoCobro")
    for codigo, nombre, moneda, orden, etiquetas in METODOS:
        metodo, creado = MetodoPago.objects.get_or_create(
            codigo=codigo, defaults={"nombre": nombre, "moneda": moneda, "orden": orden}
        )
        if creado:
            for i, etiqueta in enumerate(etiquetas):
                DatoCobro.objects.create(metodo=metodo, etiqueta=etiqueta, orden=i)


def quitar(apps, schema_editor):
    apps.get_model("pagos", "MetodoPago").objects.filter(codigo__in=[m[0] for m in METODOS]).delete()


class Migration(migrations.Migration):
    dependencies = [("pagos", "0002_metodopago_datocobro_tasacambio")]
    operations = [migrations.RunPython(cargar, quitar)]
