# Cielos Despejados

Web oficial de la Asociación Cielos Despejados, construida con FastAPI, Jinja templates y MongoDB.

## Requisitos

- Docker y Docker Compose

## Variables de entorno

Copia el archivo `.env.example` a `.env` y ajusta los valores:

- `MONGO_URI`: URI de conexión a MongoDB (por defecto `mongodb://mongo:27017`).
- `MONGO_DB`: nombre de base de datos.
- `SECRET_KEY`: clave para sesiones.
- `CONTACT_EMAIL`: correo destino para formularios.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`: credenciales SMTP para envío de emails.
- `ADMIN_EMAIL`, `ADMIN_PASSWORD`: credenciales del administrador que puede acceder al panel de gestión.

## Puesta en marcha con Docker

```bash
cp .env.example .env

docker compose up --build
```

La aplicación estará disponible en `http://localhost:8000`.

El servicio de MongoDB se inicia automáticamente en un contenedor con un volumen persistente
(`mongo_data`) para conservar los datos entre reinicios.

## Estructura principal

- `app/main.py`: rutas FastAPI y lógica principal.
- `app/templates/`: templates Jinja (incluye `base.html`).
- `app/static/`: estilos, scripts y recursos estáticos.
- `app/static/store/pics/`: almacén de astrofotografías.
- `app/static/store/blog/`: almacén de imágenes del blog.

## Datos iniciales

- Las imágenes del banner principal deben colocarse en `app/static/pics/home/`.
- Los metadatos de astrofotos y entradas de blog se guardan en MongoDB.
- Para convertir un usuario en administrador, actualiza el campo `is_admin` a `true` en la colección `users` o usa las variables `ADMIN_EMAIL` y `ADMIN_PASSWORD`.

## Scripts

Para crear un usuario manualmente en MongoDB:

```bash
python scripts/add_user_mongo.py my_user_name my_secret_password --email a_email@gmail.com
```
