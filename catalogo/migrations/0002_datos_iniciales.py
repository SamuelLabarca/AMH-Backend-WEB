"""Carga el catálogo que hasta ahora vivía en el frontend (contenido.js →
TIENDA). Desde aquí, los precios se cambian en el admin."""

from decimal import Decimal

from django.db import migrations

OPCIONES = [
    # codigo, nombre, meses, precio, destacado, orden
    ("anual", "Anual", 12, Decimal("700"), "El plan más solicitado", 1),
    ("trimestral", "Trimestral", 3, Decimal("225"), "", 2),
    ("mensual", "Mensual", 1, Decimal("100"), "", 3),
]


def cargar(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    OpcionPago = apps.get_model("catalogo", "OpcionPago")
    producto, _ = Producto.objects.get_or_create(
        codigo="administrativo", defaults={"nombre": "Administrativo", "marca": "My Business Panel"}
    )
    for codigo, nombre, meses, precio, destacado, orden in OPCIONES:
        OpcionPago.objects.get_or_create(
            producto=producto,
            codigo=codigo,
            defaults={"nombre": nombre, "meses": meses, "precio": precio, "destacado": destacado, "orden": orden},
        )


def quitar(apps, schema_editor):
    apps.get_model("catalogo", "Producto").objects.filter(codigo="administrativo").delete()


class Migration(migrations.Migration):
    dependencies = [("catalogo", "0001_initial")]
    operations = [migrations.RunPython(cargar, quitar)]
