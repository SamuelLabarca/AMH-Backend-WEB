# AMH API — portal de pagos de My Business Panel

API del portal de pagos. **Django 5.2 (LTS) + Django REST Framework**. El
frontend vive en el repositorio `amh` (`src/pages/portal/`).

## Arrancar

Requiere [uv](https://docs.astral.sh/uv/). Él instala Python 3.13 solo.

```bash
cp .env.example .env          # y rellénalo
uv sync
uv run python manage.py migrate
uv run python manage.py datos_demo        # cuentas de prueba (solo DEBUG)
uv run python manage.py createsuperuser   # tu usuario del admin
uv run python manage.py runserver         # http://localhost:8000
uv run python manage.py test
```

En el frontend, `npm run dev:api` (usa `VITE_API_URL=http://localhost:8000`)
y el portal deja el modo demostración.

**Los correos en local** no se envían: van a la bandeja de desarrollo, en
`/admin` → **Bandeja de correos (local)**. Ahí se ve, por ejemplo, el enlace
de recuperación de contraseña, listo para abrir. En producción salen por SMTP
(ver `.env.example`).

## Las apps

| App | Qué hace |
|---|---|
| `cuentas` | Usuario (se entra con correo), sesión, registro y recuperación de contraseña |
| `catalogo` | Productos y opciones de pago (anual, trimestral, mensual) con su precio. Se editan en `/admin` |
| `tienda` | Órdenes: la compra guarda el precio del momento y crea la suscripción `pendiente`; aprobar su pago la deja `pagada` |
| `suscripciones` | Los planes de cada usuario y su estado (`GET /portal/cuenta`) |
| `pagos` | Métodos de cobro, tasa BCV y reportes de pago; el equipo aprueba en `/admin` y eso renueva las suscripciones |
| `notificaciones` | Correos. En desarrollo, la bandeja local (`notificaciones.correo.BandejaLocal`) |

**Lo que se edita en el admin sin publicar la web:** precios y opciones
(Catálogo → Productos), datos de cobro y métodos activos (Pagos → Métodos de
cobro) y la tasa BCV del día (Pagos → Tasas de cambio). Sin una tasa cargada,
`/pagos/tasa` responde 404 y el portal no puede convertir a bolívares.

## Las capas de cada app

Todas las apps tienen los mismos archivos, con el mismo papel:

| Archivo | Capa | Pregunta que responde |
|---|---|---|
| `models.py` | Datos | ¿Qué se guarda? |
| `servicios.py` | **Reglas de negocio** | ¿Qué pasa cuando…? (aprobar un pago, crear una orden) |
| `views.py` | Entrada HTTP | ¿Qué recibe y qué responde la API? |
| `admin.py` | Pantalla interna | ¿Qué ve y qué hace el equipo? |
| `tests.py` | Pruebas | ¿Cómo sé que funciona? |

**Reglas:**

1. **Las vistas y el admin no deciden nada**: llaman a `servicios.py`. Por eso
   aprobar un pago desde el admin, desde un webhook de PagoFlash o desde un test
   pasa por la misma función (`pagos.servicios.aprobar`).
2. **Una app habla con otra SOLO por su `servicios.py`**, nunca leyendo o
   escribiendo sus modelos. Ejemplo: la tienda no crea una `Suscripcion`, llama a
   `suscripciones.servicios.crear_pendiente()`. Así cada regla ("qué se puede
   pagar", "qué se vende") se lee en un único archivo.

   Se importa con un alias que dice de dónde viene:
   `from suscripciones import servicios as suscripciones`.

   Única excepción: `catalogo/models.py` usa `Suscripcion.Ciclo` (mensual,
   trimestral, anual), que es una lista de valores sin lógica. Los tests y las
   migraciones también pueden usar modelos ajenos para preparar datos.

## Contrato

| Método | Ruta | Respuesta |
|---|---|---|
| GET | `/auth/csrf` | `{ csrf }` — mandarlo en `X-CSRFToken` en todo POST/DELETE |
| GET | `/auth/sesion` | `{ usuario }` · 401 |
| POST | `/auth/sesion` | `{ correo, contrasena }` → `{ usuario }` · 401 `credenciales-invalidas` |
| DELETE | `/auth/sesion` | 204 |
| POST | `/auth/registro` | → 201 `{ usuario }` · 409 `cuenta-existente` |
| POST | `/auth/recuperacion` | `{ correo }` → 202 siempre |
| POST | `/auth/recuperacion/confirmar` | `{ token, contrasena }` → 204 · 400 `token-invalido` |
| GET | `/portal/cuenta` | `{ suscripciones: [...] }` |
| POST | `/portal/pagos` | `{ metodo, referencia, fecha, monto, banco, suscripciones }` → 201 · 409 `referencia-usada` · 400 `metodo-no-disponible` |
| POST | `/tienda/ordenes` | `{ producto, opcion }` (con sesión) → 201 `{ orden }` nueva · 200 la pendiente que ya existía · 400 `opcion-no-disponible`. El precio lo pone el servidor |
| GET | `/tienda/catalogo` | `{ productos: [{ codigo, nombre, marca, iva, opciones: [{ codigo, nombre, meses, precio, destacado }] }] }` (público) |
| GET | `/pagos/metodos` | `{ metodos: [{ id, nombre, moneda, datos: [{ etiqueta, valor }] }] }` (público) |
| GET | `/pagos/tasa` | `{ fecha, bs_por_usd }` · 404 `sin-tasa` (público) |

Errores siempre como `{ codigo, mensaje }`.

## Seguridad

- Contraseñas con **argon2**. Mínimo 8 caracteres, letras y números, y no de las comunes.
- Sesión en cookie **HttpOnly**, `SameSite=Lax`, `Secure` en producción.
- **CSRF en todas** las peticiones que modifican algo, también entrar y registrarse.
- **Límite de intentos**: 10/min al entrar, 5/hora en recuperación.
  En producción con varias instancias, la caché tiene que ser Redis.
- Recuperación: responde igual exista o no el correo; el enlace vence a
  los 30 minutos, es de un solo uso y cierra las demás sesiones.
- `/portal/cuenta` no recibe ningún identificador: el usuario sale de la sesión.
- Una referencia bancaria no se puede reportar dos veces.

## PostgreSQL local

Crea el usuario y la base (desde `psql` como `postgres`), con una contraseña
tuya:

```sql
CREATE ROLE amh LOGIN PASSWORD 'elige-una' CREATEDB;
CREATE DATABASE amh OWNER amh;
```

Y en `.env`: `DATABASE_URL=postgres://amh:elige-una@localhost:5432/amh`.
`CREATEDB` es para que los tests puedan crear su base temporal.
