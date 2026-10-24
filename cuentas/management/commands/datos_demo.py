from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from cuentas.models import Usuario
from suscripciones.models import Suscripcion


class Command(BaseCommand):
    help = "Crea las cuentas de prueba del portal (las mismas del modo demostración del frontend)."

    def handle(self, *args, **opciones):
        # Contraseñas conocidas: jamás en una base de datos real.
        if not settings.DEBUG:
            raise CommandError("Solo con DEBUG=true: crea cuentas con contraseñas conocidas.")

        hoy = timezone.localdate()
        cuentas = [
            ("maria@demo.com", "María González", "V-12345678", [
                ("Plan Empresa", Suscripcion.Ciclo.MENSUAL, "45", hoy - timedelta(days=9)),
                ("Sucursal adicional", Suscripcion.Ciclo.MENSUAL, "15", hoy + timedelta(days=6)),
            ]),
            ("admin@distribuidora.com", "Distribuidora Ejemplo, C.A.", "J-123456789", [
                ("Plan Empresa", Suscripcion.Ciclo.ANUAL, "450", hoy + timedelta(days=128)),
            ]),
        ]
        for correo, nombre, documento, planes in cuentas:
            usuario, creado = Usuario.objects.get_or_create(
                correo=correo, defaults={"nombre": nombre, "documento": documento}
            )
            if creado:
                usuario.set_password("Demo1234")
                usuario.save()
                for plan, ciclo, monto, vence in planes:
                    Suscripcion.objects.create(
                        usuario=usuario, plan=plan, ciclo=ciclo, monto=Decimal(monto), estado="activa", vence=vence
                    )
            self.stdout.write(f"{'creada' if creado else 'ya existía'}: {correo}")
        self.stdout.write(self.style.SUCCESS("Listo. Contraseña de las dos: Demo1234"))
