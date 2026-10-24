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

En el frontend, `VITE_API_URL=http://localhost:8000` en su `.env` y el
portal deja el modo demostración.

## Las tres apps

| App | Qué hace |
|---|---|
| `cuentas` | Usuario (se entra con correo), sesión, registro y recuperación de contraseña |
| `suscripciones` | Los planes de cada usuario y su estado (`GET /portal/cuenta`) |
| `pagos` | El cliente reporta un pago; el equipo lo aprueba en `/admin` y eso renueva las suscripciones |

La lógica de negocio vive en `servicios.py` de cada app, no en las vistas
ni en el admin: aprobar un pago desde el admin, desde un webhook de Celebry
o desde un test pasa por la misma función (`pagos.servicios.aprobar`).

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
| POST | `/portal/pagos` | `{ metodo, referencia, fecha, monto, banco, suscripciones }` → 201 · 409 `referencia-usada` |

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
