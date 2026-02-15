from datetime import datetime
import logging
from pathlib import Path
from random import choice
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exception_handlers import http_exception_handler as fastapi_http_exception_handler
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from bson.errors import InvalidId
from passlib.hash import bcrypt
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.auth import authenticate_user, create_user
from app.config import settings
from app.db import db, ensure_indexes
from app.email_utils import send_email

app = FastAPI()

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

CONSTRUCTION_IMAGE_URL = "/static/store/page/1768922588.118187_en_construccion_img.png"
CONSTRUCTION_ALLOWED_PATHS = {"/login", "/registro", "/registro/gracias"}

PERMISSION_KEYS = (
    "photos",
    "blog",
    "activities",
    "photos_supervised",
    "blog_supervised",
    "activities_supervised",
)

SUPERVISED_PERMISSION_MAP = {
    "photos": "photos_supervised",
    "blog": "blog_supervised",
    "activities": "activities_supervised",
}


@app.middleware("http")
async def construction_guard(request: Request, call_next: Any) -> Any:
    path = request.url.path
    if path.startswith("/static") or path == "/favicon.ico":
        return await call_next(request)
    if request.session.get("user_email"):
        return await call_next(request)
    if path in CONSTRUCTION_ALLOWED_PATHS:
        return await call_next(request)
    return templates.TemplateResponse(
        "construction.html",
        {"request": request, "image_url": CONSTRUCTION_IMAGE_URL},
    )


app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

SPANISH_MONTHS = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}

ABOUT_PAGE_SLUG = "sobre-nosotros"
DEFAULT_ABOUT_HTML = """
<h1>Sobre nosotros</h1>
<p>
  Cielos Despejados es una asociación astronómica asturiana dedicada a la divulgación, la observación del cielo nocturno y la astrofotografía. Organizamos encuentros, talleres y salidas para compartir la pasión por el cosmos.
</p>
<div class="section-grid">
  <div class="section-media">
    <img src="/static/store/page/CDabout.jpg" alt="Cielos Despejados" />
  </div>
  <div class="section-text">
    <p>
      La asociación astronómica tiene sede en Oviedo, Asturias, y se fundó oficialmente en mayo de 2014, aunque su germen ya llevaba organizando actividades divulgativas y quedadas (g)astronómicas desde mucho antes.
      <br><br>
      Los estatutos de la asociación define los fines de la misma, que son:
    </p>
    <ul class="about-list">
      <li>Adquirir conocimientos más profundos de las Ciencias en general, y la Astronomía en particular; así como facilitar la labor a observadores y estudiosos.</li>
      <li>Promover cuantos temas relativos a las Ciencias en general, y a la Astronomía en particular, se consideren oportunos.</li>
    </ul>
    <p>
      <br>
      Participamos en actividades múltiples en colaboración con instituciones como la Facultad de Ciencias de Oviedo, la Universidad de Oviedo, o el Ayuntamiento de Oviedo. Hacemos actividades de observación para el público, charlas, astrofotografías, y talleres para colegios, público general, o en eventos. Nuestro evento anual por excelencia es la Noche Lunática, que se celebra en septiembre/octubre por la Noche Internacional de la Luna, pero también nos encontrarás en La Hora del Planeta, o en la Noche Europea de los y las investigadores e Investigadoras.
    </p>
  </div>
</div>
<p>
  Podéis contactar con la asociación de las siguientes a través del <a class="inline-link" href="/contacto">formulario de contacto</a> o por correo electrónico a info@cielosdespejados.es. También a través de nuestras redes sociales
</p>
<div class="social-footer">
  <div class="social-links">
    <a class="social-link" href="https://www.facebook.com/cielosdespejados/" target="_blank" rel="noopener" aria-label="Facebook">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M13.5 8.5V7c0-.9.6-1.1 1-1.1h2V3h-2.5C11.9 3 10 4.8 10 6.9v1.6H8v3h2v9h3.5v-9h2.4l.4-3h-2.8z"/>
      </svg>
    </a>
    <a class="social-link" href="https://www.instagram.com/cielosdespejadosasturias/" target="_blank" rel="noopener" aria-label="Instagram">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M7.5 3h9A4.5 4.5 0 0 1 21 7.5v9A4.5 4.5 0 0 1 16.5 21h-9A4.5 4.5 0 0 1 3 16.5v-9A4.5 4.5 0 0 1 7.5 3zm0 2A2.5 2.5 0 0 0 5 7.5v9A2.5 2.5 0 0 0 7.5 19h9a2.5 2.5 0 0 0 2.5-2.5v-9A2.5 2.5 0 0 0 16.5 5h-9z"/>
        <path d="M12 7.5A4.5 4.5 0 1 1 7.5 12 4.5 4.5 0 0 1 12 7.5zm0 2A2.5 2.5 0 1 0 14.5 12 2.5 2.5 0 0 0 12 9.5zm5.25-3.1a1 1 0 1 1-1 1 1 1 0 0 1 1-1z"/>
      </svg>
    </a>
    <a class="social-link" href="https://x.com/CielosDspejados" target="_blank" rel="noopener" aria-label="X">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M18.9 3h3.1l-6.8 7.8 8 10.2h-6.6l-5.1-6.6L5.6 21H2.5l7.3-8.4L2 3h6.8l4.7 6.1L18.9 3zm-1.2 15.1h1.7L8.2 4.8H6.4l11.3 13.3z"/>
      </svg>
    </a>
  </div>
</div>
<div class="about-spacer"></div>
<p>Tras la asamblea de febrero de 2024 la Junta Directiva está formada por:</p>
<ul class="about-list">
  <li>Marcos Suárez, presidente</li>
  <li>María Fernández, vicepresidente</li>
  <li>Julia Menéndez, secretaria/tesorera</li>
  <li>Laura Hermosa, vocal</li>
  <li>Juan F. García, vocal</li>
</ul>
<p><br>La asociación está inscrita en:</p>
<ul class="about-list">
  <li>Registro de Asociaciones del Principado de Asturias, con el nº 11 138</li>
  <li>Número de Identificación Fiscal: G-74 384 165</li>
</ul>
<p><br>¿Te interesa unirte a nosotros? <a class="inline-link" href="/asociate">Hazte socio aquí.</a></p>
""".strip()


@app.on_event("startup")
async def startup() -> None:
    await ensure_indexes()


async def get_current_user(request: Request) -> dict | None:
    user_email = request.session.get("user_email")
    if not user_email:
        return None
    if settings.admin_email and user_email == settings.admin_email:
        return _normalize_user({"email": user_email, "is_admin": True})
    user = await db.users.find_one({"email": user_email})
    return _normalize_user(user) if user else None


async def require_admin(user: dict | None = Depends(get_current_user)) -> dict:
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403)
    return user


def _list_home_images() -> list[str]:
    home_dir = STATIC_DIR / "pics" / "home"
    if not home_dir.exists():
        return []
    return [f"/static/pics/home/{path.name}" for path in home_dir.iterdir() if path.is_file()]


def _store_images_dir(scope: str) -> Path:
    if scope not in {"blog", "activities"}:
        raise HTTPException(status_code=404)
    return STATIC_DIR / "store" / scope


def _list_store_images(scope: str) -> list[str]:
    directory = _store_images_dir(scope)
    if not directory.exists():
        return []
    return sorted(
        [
            f"/static/store/{scope}/{path.name}"
            for path in directory.iterdir()
            if path.is_file()
        ],
        reverse=True,
    )


def _list_not_found_images() -> list[str]:
    directory = STATIC_DIR / "store" / "page"
    if not directory.exists():
        return []
    not_found_images = [
        "NotFound1.jpg",
        "NotFound2.jpg",
        "NotFound3.jpg",
        "NotFound4.jpg",
    ]
    return [
        f"/static/store/page/{image}"
        for image in not_found_images
        if (directory / image).is_file()
    ]


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> Any:
    if exc.status_code != 404:
        return await fastapi_http_exception_handler(request, exc)
    images = _list_not_found_images()
    image_url = choice(images) if images else "/static/store/page/NotFound1.jpg"
    image_position = choice(["left", "right"])
    return templates.TemplateResponse(
        "404.html",
        {"request": request, "image_url": image_url, "image_position": image_position},
        status_code=404,
    )


def _photo_filter(include_hidden: bool) -> dict[str, Any]:
    if include_hidden:
        return {}
    return {"is_hidden": {"$ne": True}}


async def _fetch_recent_photos(limit: int = 6, include_hidden: bool = False) -> list[dict[str, Any]]:
    cursor = db.photos.find(_photo_filter(include_hidden)).sort("uploaded_at", -1).limit(limit)
    return [_serialize_doc(photo) async for photo in cursor]


async def _fetch_about_content() -> str:
    document = await db.page_content.find_one({"slug": ABOUT_PAGE_SLUG})
    if document and document.get("content_html"):
        return document["content_html"]
    return DEFAULT_ABOUT_HTML


def _publication_filter(include_hidden: bool) -> dict[str, Any]:
    if include_hidden:
        return {}
    return {"is_hidden": {"$ne": True}}


def _format_datetime_input(value: Any) -> str:
    if not value:
        return ""
    parsed: datetime | None = None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        cleaned = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(cleaned)
        except ValueError:
            return ""
    if not parsed:
        return ""
    return parsed.strftime("%Y-%m-%dT%H:%M")


async def _fetch_recent_blog_entries(
    limit: int = 3, include_hidden: bool = False
) -> list[dict[str, Any]]:
    cursor = (
        db.blog_entries.find(_publication_filter(include_hidden))
        .sort("published_at", -1)
        .limit(limit)
    )
    return [_prepare_publication_entry(entry) async for entry in cursor]


def _activity_filter(include_hidden: bool, is_upcoming: bool | None = None) -> dict[str, Any]:
    filters = dict(_publication_filter(include_hidden))
    if is_upcoming is not None:
        if is_upcoming:
            filters["is_upcoming"] = True
        else:
            filters["is_upcoming"] = {"$ne": True}
    return filters


async def _fetch_upcoming_activities(
    include_hidden: bool = False,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    cursor = db.activities.find(_activity_filter(include_hidden, is_upcoming=True)).sort(
        "celebration_at", 1
    )
    if limit is not None:
        cursor = cursor.limit(limit)
    return [_prepare_publication_entry(activity) async for activity in cursor]


async def _fetch_recent_past_activities(
    limit: int = 3, include_hidden: bool = False
) -> list[dict[str, Any]]:
    cursor = (
        db.activities.find(_activity_filter(include_hidden, is_upcoming=False))
        .sort("celebration_at", -1)
        .limit(limit)
    )
    return [_prepare_publication_entry(activity) async for activity in cursor]


def _serialize_doc(document: dict[str, Any]) -> dict[str, Any]:
    document["_id"] = str(document.get("_id"))
    return document


def _default_permissions(value: dict[str, Any] | None = None) -> dict[str, bool]:
    permissions = value or {}
    return {key: bool(permissions.get(key)) for key in PERMISSION_KEYS}


def _normalize_user(user: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(user)
    if normalized.get("is_admin"):
        normalized["permissions"] = {key: True for key in PERMISSION_KEYS}
    else:
        normalized["permissions"] = _default_permissions(normalized.get("permissions"))
    return normalized


def _has_permission(user: dict[str, Any] | None, permission: str) -> bool:
    if not user:
        return False
    if user.get("is_admin"):
        return True
    permissions = _default_permissions(user.get("permissions"))
    return permissions.get(permission, False)


def _has_supervised_permission(user: dict[str, Any] | None, permission: str) -> bool:
    supervised_key = SUPERVISED_PERMISSION_MAP.get(permission, "")
    if not supervised_key:
        return False
    return _has_permission(user, supervised_key)


def _has_any_permission(user: dict[str, Any] | None, permission: str) -> bool:
    return _has_permission(user, permission) or _has_supervised_permission(user, permission)


def _can_edit_entry(
    user: dict[str, Any] | None, permission: str, author_email: str | None
) -> bool:
    if not user:
        return False
    if user.get("is_admin") or _has_permission(user, permission):
        return True
    return bool(author_email and author_email == user.get("email"))


def _parse_object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId as exc:
        raise HTTPException(status_code=404) from exc


def _format_spanish_date(value: Any) -> str:
    if not value:
        return ""
    parsed: datetime | None = None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        cleaned = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(cleaned)
        except ValueError:
            return value
    if not parsed:
        return str(value)
    month_name = SPANISH_MONTHS.get(parsed.month, "")
    return f"{parsed.day:02d} de {month_name} de {parsed.year}"


def _prepare_publication_entry(document: dict[str, Any]) -> dict[str, Any]:
    serialized = _serialize_doc(document)
    serialized["published_at_display"] = _format_spanish_date(serialized.get("published_at"))
    serialized["published_at_input"] = _format_datetime_input(serialized.get("published_at"))
    celebration_at = serialized.get("celebration_at") or serialized.get("published_at")
    serialized["celebration_at_display"] = _format_spanish_date(celebration_at)
    serialized["celebration_at_input"] = _format_datetime_input(celebration_at)
    serialized["author_name"] = (serialized.get("author_name") or "").strip()
    serialized["show_author"] = bool(serialized.get("show_author", True))
    serialized["show_image"] = bool(serialized.get("show_image", True))
    serialized["is_hidden"] = bool(serialized.get("is_hidden", False))
    serialized["is_upcoming"] = bool(serialized.get("is_upcoming", False))
    return serialized


def _user_display_name(user: dict | None) -> str:
    if not user:
        return ""
    return user.get("full_name", "")


def _can_manage_scope(user: dict[str, Any] | None, scope: str) -> bool:
    if not user:
        return False
    if user.get("is_admin"):
        return True
    return _has_permission(user, scope)


async def _ensure_user_profile(user: dict) -> dict[str, Any]:
    profile = await db.users.find_one({"email": user["email"]})
    if not profile:
        profile = {
            "email": user["email"],
            "full_name": "",
            "location": "",
            "bio": "",
            "equipment_notes": "",
            "is_admin": bool(user.get("is_admin")),
            "permissions": _default_permissions(),
        }
    return _normalize_user(profile)


@app.get("/")
async def index(request: Request, user: dict | None = Depends(get_current_user)) -> Any:
    context = {
        "request": request,
        "home_images": _list_home_images(),
        "photos": await _fetch_recent_photos(include_hidden=bool(user)),
        "upcoming_activities": await _fetch_upcoming_activities(
            include_hidden=False, limit=3
        ),
        "recent_activities": await _fetch_recent_past_activities(include_hidden=False),
        "blog_entries": await _fetch_recent_blog_entries(include_hidden=False),
        "user": user,
    }
    return templates.TemplateResponse("index.html", context)


@app.get("/sobre-nosotros")
async def about(request: Request, user: dict | None = Depends(get_current_user)) -> Any:
    context = {
        "request": request,
        "content_html": await _fetch_about_content(),
        "user": user,
    }
    return templates.TemplateResponse("about.html", context)


@app.post("/sobre-nosotros")
async def about_update(
    content_html: str = Form(...),
    user: dict = Depends(require_admin),
) -> Any:
    cleaned = content_html.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="El contenido es obligatorio.")
    await db.page_content.update_one(
        {"slug": ABOUT_PAGE_SLUG},
        {"$set": {"content_html": cleaned, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    return RedirectResponse("/sobre-nosotros", status_code=303)


@app.get("/asociate")
async def associate(request: Request) -> Any:
    return templates.TemplateResponse(
        "associate.html",
        {"request": request, "contact_email": settings.contact_email},
    )


@app.post("/asociate")
async def associate_submit(
    request: Request,
    full_name: str = Form(...),
    dni: str | None = Form(None),
    email: str = Form(...),
    phone: str | None = Form(None),
    city: str | None = Form(None),
    interests: str | None = Form(None),
    experience: str | None = Form(None),
    payment_receipt: UploadFile | None = File(None),
    data_policy: bool = Form(...),
) -> Any:
    payload = {
        "full_name": full_name,
        "dni": dni,
        "email": email,
        "phone": phone,
        "city": city,
        "interests": interests,
        "experience": experience,
        "payment_receipt_filename": payment_receipt.filename if payment_receipt else None,
        "payment_receipt_content_type": payment_receipt.content_type
        if payment_receipt
        else None,
        "data_policy": data_policy,
        "submitted_at": datetime.utcnow(),
    }
    attachments: list[tuple[str, bytes, str]] = []
    if payment_receipt and payment_receipt.filename:
        attachments.append(
            (
                payment_receipt.filename,
                await payment_receipt.read(),
                payment_receipt.content_type or "application/octet-stream",
            )
        )
    await db.membership_requests.insert_one(payload)
    send_email(
        "Nueva solicitud de asociación",
        f"Se ha recibido una solicitud de {full_name} ({email}).",
        settings.contact_email,
        attachments=attachments,
    )
    return templates.TemplateResponse(
        "associate.html",
        {
            "request": request,
            "contact_email": settings.contact_email,
            "success": True,
        },
    )


@app.get("/astrofotos")
async def astrofotos(request: Request, user: dict | None = Depends(get_current_user)) -> Any:
    photos = await _fetch_recent_photos(limit=50, include_hidden=bool(user))
    authors: set[str] = set()
    for photo in photos:
        photo["uploaded_at_display"] = _format_spanish_date(photo.get("uploaded_at"))
        uploaded_at = photo.get("uploaded_at")
        if isinstance(uploaded_at, datetime):
            photo["uploaded_at_iso"] = uploaded_at.date().isoformat()
        elif isinstance(uploaded_at, str):
            photo["uploaded_at_iso"] = uploaded_at.split("T")[0]
        else:
            photo["uploaded_at_iso"] = ""
        author_name = (photo.get("author") or "").strip()
        if author_name:
            authors.add(author_name)
    author_default = _user_display_name(user)
    return templates.TemplateResponse(
        "astrofotos.html",
        {
            "request": request,
            "photos": photos,
            "authors": sorted(authors),
            "user": user,
            "author_default": author_default,
        },
    )


@app.get("/astrofotos/{photo_id}")
async def astrofoto_detail(
    request: Request, photo_id: str, user: dict | None = Depends(get_current_user)
) -> Any:
    photo = await db.photos.find_one({"_id": photo_id})
    if not photo:
        raise HTTPException(status_code=404)
    if photo.get("is_hidden") and not user:
        raise HTTPException(status_code=404)
    serialized = _serialize_doc(photo)
    serialized["uploaded_at_display"] = _format_spanish_date(serialized.get("uploaded_at"))
    return templates.TemplateResponse(
        "astrofoto_detail.html",
        {
            "request": request,
            "photo": serialized,
            "user": user,
            "can_edit": bool(
                user
                and _has_any_permission(user, "photos")
                and _can_edit_entry(user, "photos", photo.get("uploaded_by"))
            ),
        },
    )


@app.post("/astrofotos")
async def astrofotos_upload(
    request: Request,
    name: str = Form(...),
    characteristics: str | None = Form(None),
    equipment: str | None = Form(None),
    description: str | None = Form(None),
    author: str | None = Form(None),
    photo_file: UploadFile = Form(...),
    version_descriptions: list[str] = Form(default=[]),
    version_files: list[UploadFile] = File(default=[]),
    submission_action: str | None = Form(None),
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user or not _has_any_permission(user, "photos"):
        raise HTTPException(status_code=403)
    filename = f"{datetime.utcnow().timestamp()}_{photo_file.filename}"
    file_path = STATIC_DIR / "store" / "pics" / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    contents = await photo_file.read()
    file_path.write_bytes(contents)
    author_value = author.strip() if author else ""
    if not author_value:
        author_value = _user_display_name(user)
    versions: list[dict[str, str]] = []
    for index, version_file in enumerate(version_files or []):
        if not version_file.filename:
            continue
        version_filename = f"{datetime.utcnow().timestamp()}_{version_file.filename}"
        version_path = STATIC_DIR / "store" / "pics" / version_filename
        version_path.write_bytes(await version_file.read())
        version_description = ""
        if index < len(version_descriptions):
            version_description = version_descriptions[index].strip()
        versions.append(
            {
                "image_url": f"/static/store/pics/{version_filename}",
                "description": version_description,
            }
        )
    should_publish = bool(
        submission_action != "review" and _has_permission(user, "photos")
    )
    payload = {
        "_id": filename,
        "name": name,
        "uploaded_at": datetime.utcnow(),
        "characteristics": (characteristics or "").strip(),
        "equipment": (equipment or "").strip(),
        "description": (description or "").strip(),
        "author": author_value,
        "uploaded_by": user.get("email", ""),
        "image_url": f"/static/store/pics/{filename}",
        "versions": versions,
        "is_hidden": not should_publish,
    }
    await db.photos.insert_one(payload)
    return RedirectResponse("/astrofotos", status_code=303)


@app.get("/astrofotos/{photo_id}/editar")
async def astrofotos_edit(
    request: Request,
    photo_id: str,
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    photo = await db.photos.find_one({"_id": photo_id})
    if not photo:
        raise HTTPException(status_code=404)
    if not _has_any_permission(user, "photos"):
        raise HTTPException(status_code=403)
    if not _can_edit_entry(user, "photos", photo.get("uploaded_by")):
        raise HTTPException(status_code=403)
    serialized = _serialize_doc(photo)
    serialized["uploaded_at_display"] = _format_spanish_date(serialized.get("uploaded_at"))
    return templates.TemplateResponse(
        "astrofoto_edit.html",
        {"request": request, "photo": serialized, "user": user},
    )


@app.post("/astrofotos/{photo_id}/editar")
async def astrofotos_edit_submit(
    request: Request,
    photo_id: str,
    name: str = Form(...),
    characteristics: str | None = Form(None),
    equipment: str | None = Form(None),
    description: str | None = Form(None),
    author: str | None = Form(None),
    is_hidden: str | None = Form(None),
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    photo = await db.photos.find_one({"_id": photo_id})
    if not photo:
        raise HTTPException(status_code=404)
    if not _has_any_permission(user, "photos"):
        raise HTTPException(status_code=403)
    if not _can_edit_entry(user, "photos", photo.get("uploaded_by")):
        raise HTTPException(status_code=403)
    updates = {
        "name": name,
        "characteristics": (characteristics or "").strip(),
        "equipment": (equipment or "").strip(),
        "description": (description or "").strip(),
        "author": (author or "").strip(),
    }
    if _has_permission(user, "photos"):
        updates["is_hidden"] = is_hidden == "on"
    await db.photos.update_one({"_id": photo_id}, {"$set": updates})
    return RedirectResponse(f"/astrofotos/{photo_id}", status_code=303)


@app.get("/blog")
async def blog(request: Request, page: int = 1, user: dict | None = Depends(get_current_user)) -> Any:
    per_page = 5
    skip = (page - 1) * per_page
    entries_cursor = (
        db.blog_entries.find(_publication_filter(False))
        .sort("published_at", -1)
        .skip(skip)
        .limit(per_page)
    )
    entries = [_prepare_publication_entry(entry) async for entry in entries_cursor]
    total_entries = await db.blog_entries.count_documents(_publication_filter(False))
    total_pages = max(1, (total_entries + per_page - 1) // per_page)
    latest_entries = await _fetch_recent_blog_entries(limit=3, include_hidden=False)
    can_manage_drafts = bool(user and _has_permission(user, "blog"))
    draft_entries: list[dict[str, Any]] = []
    if user:
        draft_filter: dict[str, Any] = {"is_hidden": True}
        if not can_manage_drafts:
            draft_filter["author_email"] = user.get("email")
        drafts_cursor = db.blog_entries.find(draft_filter).sort("published_at", -1)
        draft_entries = [_prepare_publication_entry(entry) async for entry in drafts_cursor]
    return templates.TemplateResponse(
        "blog.html",
        {
            "request": request,
            "entries": entries,
            "latest_entries": latest_entries,
            "draft_entries": draft_entries,
            "page": page,
            "total_pages": total_pages,
            "user": user,
            "can_manage_drafts": can_manage_drafts,
        },
    )


@app.get("/blog/nueva")
async def blog_new(request: Request, user: dict | None = Depends(get_current_user)) -> Any:
    if not user or not _has_any_permission(user, "blog"):
        raise HTTPException(status_code=403)
    return templates.TemplateResponse(
        "blog_new.html",
        {"request": request, "user": user, "author_default": _user_display_name(user)},
    )


@app.get("/media/{scope}/list")
async def media_list(scope: str, user: dict | None = Depends(get_current_user)) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    if scope == "blog" and not _has_any_permission(user, "blog"):
        raise HTTPException(status_code=403)
    if scope == "activities" and not _has_any_permission(user, "activities"):
        raise HTTPException(status_code=403)
    return {"images": _list_store_images(scope)}


@app.post("/media/{scope}/upload")
async def media_upload(
    scope: str,
    files: list[UploadFile] = File(...),
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    if scope == "blog" and not _has_any_permission(user, "blog"):
        raise HTTPException(status_code=403)
    if scope == "activities" and not _has_any_permission(user, "activities"):
        raise HTTPException(status_code=403)
    directory = _store_images_dir(scope)
    directory.mkdir(parents=True, exist_ok=True)
    for image in files:
        if not image.filename:
            continue
        filename = f"{datetime.utcnow().timestamp()}_{image.filename}"
        file_path = directory / filename
        file_path.write_bytes(await image.read())
    return {"images": _list_store_images(scope)}


@app.post("/media/{scope}/delete")
async def media_delete(
    scope: str,
    request: Request,
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    if scope == "blog" and not _has_any_permission(user, "blog"):
        raise HTTPException(status_code=403)
    if scope == "activities" and not _has_any_permission(user, "activities"):
        raise HTTPException(status_code=403)
    payload = await request.json()
    url = (payload or {}).get("url", "")
    filename = Path(url).name if url else ""
    if not filename:
        raise HTTPException(status_code=400)
    directory = _store_images_dir(scope).resolve()
    target = (directory / filename).resolve()
    if directory not in target.parents and target != directory:
        raise HTTPException(status_code=400)
    if target.exists():
        target.unlink()
    return {"images": _list_store_images(scope)}


@app.post("/blog/nueva")
async def blog_new_submit(
    request: Request,
    title: str = Form(...),
    summary: str = Form(...),
    content_html: str = Form(...),
    author_name: str | None = Form(None),
    show_image: str | None = Form(None),
    image: UploadFile | None = Form(None),
    submission_action: str | None = Form(None),
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user or not _has_any_permission(user, "blog"):
        raise HTTPException(status_code=403)
    image_url = ""
    if image and image.filename:
        filename = f"{datetime.utcnow().timestamp()}_{image.filename}"
        file_path = STATIC_DIR / "store" / "blog" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(await image.read())
        image_url = f"/static/store/blog/{filename}"
    entry_id = f"entry-{datetime.utcnow().timestamp()}"
    should_publish = bool(
        submission_action != "review" and _has_permission(user, "blog")
    )
    payload = {
        "_id": entry_id,
        "title": title,
        "summary": summary,
        "content_html": content_html,
        "image_url": image_url,
        "published_at": datetime.utcnow(),
        "author_name": (author_name or "").strip(),
        "author_email": user.get("email", ""),
        "show_author": True,
        "show_image": show_image == "on",
        "is_hidden": not should_publish,
    }
    await db.blog_entries.insert_one(payload)
    return RedirectResponse("/blog", status_code=303)


@app.get("/blog/{entry_id}")
async def blog_detail(
    request: Request,
    entry_id: str,
    user: dict | None = Depends(get_current_user),
) -> Any:
    entry = await db.blog_entries.find_one({"_id": entry_id})
    if not entry:
        raise HTTPException(status_code=404)
    if entry.get("is_hidden"):
        can_manage = bool(user and _has_permission(user, "blog"))
        is_owner = bool(user and entry.get("author_email") == user.get("email"))
        if not (can_manage or is_owner):
            raise HTTPException(status_code=404)
    can_edit = bool(
        user
        and _has_any_permission(user, "blog")
        and _can_edit_entry(user, "blog", entry.get("author_email"))
    )
    return templates.TemplateResponse(
        "blog_detail.html",
        {
            "request": request,
            "entry": _prepare_publication_entry(entry),
            "user": user,
            "can_edit": can_edit,
        },
    )


@app.get("/blog/{entry_id}/editar")
async def blog_edit(
    request: Request,
    entry_id: str,
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    entry = await db.blog_entries.find_one({"_id": entry_id})
    if not entry:
        raise HTTPException(status_code=404)
    if not _has_any_permission(user, "blog"):
        raise HTTPException(status_code=403)
    if not _can_edit_entry(user, "blog", entry.get("author_email")):
        raise HTTPException(status_code=403)
    return templates.TemplateResponse(
        "blog_edit.html",
        {"request": request, "entry": _prepare_publication_entry(entry), "user": user},
    )


@app.post("/blog/{entry_id}/editar")
async def blog_edit_submit(
    request: Request,
    entry_id: str,
    title: str = Form(...),
    summary: str = Form(...),
    content_html: str = Form(...),
    author_name: str | None = Form(None),
    show_author: str | None = Form(None),
    show_image: str | None = Form(None),
    is_hidden: str | None = Form(None),
    published_at: str | None = Form(None),
    image: UploadFile | None = File(None),
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    entry = await db.blog_entries.find_one({"_id": entry_id})
    if not entry:
        raise HTTPException(status_code=404)
    if not _has_any_permission(user, "blog"):
        raise HTTPException(status_code=403)
    if not _can_edit_entry(user, "blog", entry.get("author_email")):
        raise HTTPException(status_code=403)
    updates = {
        "title": title,
        "summary": summary,
        "content_html": content_html,
        "author_name": (author_name or "").strip(),
        "show_author": show_author == "on",
        "show_image": show_image == "on",
    }
    if _has_permission(user, "blog"):
        updates["is_hidden"] = is_hidden == "on"
    else:
        updates["is_hidden"] = True
    if image and image.filename:
        filename = f"{datetime.utcnow().timestamp()}_{image.filename}"
        file_path = STATIC_DIR / "store" / "blog" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(await image.read())
        updates["image_url"] = f"/static/store/blog/{filename}"
    if user.get("is_admin") and published_at:
        try:
            updates["published_at"] = datetime.fromisoformat(published_at)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Fecha inválida.") from exc
    await db.blog_entries.update_one(
        {"_id": entry_id},
        {
            "$set": updates,
        },
    )
    return RedirectResponse(f"/blog/{entry_id}", status_code=303)


@app.post("/blog/{entry_id}/eliminar")
async def blog_delete(
    entry_id: str,
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    entry = await db.blog_entries.find_one({"_id": entry_id})
    if not entry:
        raise HTTPException(status_code=404)
    if not _has_any_permission(user, "blog"):
        raise HTTPException(status_code=403)
    if not _can_edit_entry(user, "blog", entry.get("author_email")):
        raise HTTPException(status_code=403)
    await db.blog_entries.delete_one({"_id": entry_id})
    return RedirectResponse("/blog", status_code=303)


@app.post("/blog/{entry_id}/publicar")
async def blog_publish(
    entry_id: str,
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user or not _has_permission(user, "blog"):
        raise HTTPException(status_code=403)
    await db.blog_entries.update_one(
        {"_id": entry_id},
        {"$set": {"is_hidden": False}},
    )
    return RedirectResponse("/blog", status_code=303)


@app.get("/actividades")
async def activities(
    request: Request,
    page: int = 1,
    user: dict | None = Depends(get_current_user),
) -> Any:
    per_page = 5
    skip = (page - 1) * per_page
    activities_cursor = (
        db.activities.find(_activity_filter(False, is_upcoming=False))
        .sort("celebration_at", -1)
        .skip(skip)
        .limit(per_page)
    )
    activity_entries = [_prepare_publication_entry(activity) async for activity in activities_cursor]
    total_entries = await db.activities.count_documents(
        _activity_filter(False, is_upcoming=False)
    )
    total_pages = max(1, (total_entries + per_page - 1) // per_page)
    upcoming_entries = await _fetch_upcoming_activities(include_hidden=False)
    can_manage_drafts = bool(user and _has_permission(user, "activities"))
    draft_entries: list[dict[str, Any]] = []
    if user:
        draft_filter: dict[str, Any] = {"is_hidden": True}
        if not can_manage_drafts:
            draft_filter["author_email"] = user.get("email")
        drafts_cursor = db.activities.find(draft_filter).sort("celebration_at", -1)
        draft_entries = [
            _prepare_publication_entry(activity) async for activity in drafts_cursor
        ]
    return templates.TemplateResponse(
        "activities.html",
        {
            "request": request,
            "entries": activity_entries,
            "upcoming_entries": upcoming_entries,
            "draft_entries": draft_entries,
            "page": page,
            "total_pages": total_pages,
            "user": user,
            "can_manage_drafts": can_manage_drafts,
        },
    )


@app.get("/actividades/nueva")
async def activities_new(request: Request, user: dict | None = Depends(get_current_user)) -> Any:
    if not user or not _has_any_permission(user, "activities"):
        raise HTTPException(status_code=403)
    return templates.TemplateResponse(
        "activities_new.html",
        {"request": request, "user": user, "author_default": _user_display_name(user)},
    )


@app.post("/actividades/nueva")
async def activities_new_submit(
    request: Request,
    title: str = Form(...),
    summary: str = Form(...),
    content_html: str = Form(...),
    celebration_at: str = Form(...),
    is_upcoming: str = Form(...),
    author_name: str | None = Form(None),
    show_image: str | None = Form(None),
    image: UploadFile | None = Form(None),
    submission_action: str | None = Form(None),
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user or not _has_any_permission(user, "activities"):
        raise HTTPException(status_code=403)
    image_url = ""
    if image and image.filename:
        filename = f"{datetime.utcnow().timestamp()}_{image.filename}"
        file_path = STATIC_DIR / "store" / "activities" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(await image.read())
        image_url = f"/static/store/activities/{filename}"
    entry_id = f"activity-{datetime.utcnow().timestamp()}"
    try:
        celebration_date = datetime.fromisoformat(celebration_at)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Fecha inválida.") from exc
    should_publish = bool(
        submission_action != "review" and _has_permission(user, "activities")
    )
    payload = {
        "_id": entry_id,
        "title": title,
        "summary": summary,
        "content_html": content_html,
        "image_url": image_url,
        "published_at": datetime.utcnow(),
        "celebration_at": celebration_date,
        "author_name": (author_name or "").strip(),
        "author_email": user.get("email", ""),
        "show_author": True,
        "show_image": show_image == "on",
        "is_hidden": not should_publish,
        "is_upcoming": is_upcoming == "future",
    }
    await db.activities.insert_one(payload)
    return RedirectResponse("/actividades", status_code=303)


@app.get("/actividades/{activity_id}")
async def activities_detail(
    request: Request,
    activity_id: str,
    user: dict | None = Depends(get_current_user),
) -> Any:
    activity = await db.activities.find_one({"_id": activity_id})
    if not activity:
        raise HTTPException(status_code=404)
    if activity.get("is_hidden"):
        can_manage = bool(user and _has_permission(user, "activities"))
        is_owner = bool(user and activity.get("author_email") == user.get("email"))
        if not (can_manage or is_owner):
            raise HTTPException(status_code=404)
    can_edit = bool(
        user
        and _has_any_permission(user, "activities")
        and _can_edit_entry(user, "activities", activity.get("author_email"))
    )
    return templates.TemplateResponse(
        "activities_detail.html",
        {
            "request": request,
            "activity": _prepare_publication_entry(activity),
            "user": user,
            "can_edit": can_edit,
        },
    )


@app.get("/actividades/{activity_id}/editar")
async def activities_edit(
    request: Request,
    activity_id: str,
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    activity = await db.activities.find_one({"_id": activity_id})
    if not activity:
        raise HTTPException(status_code=404)
    if not _has_any_permission(user, "activities"):
        raise HTTPException(status_code=403)
    if not _can_edit_entry(user, "activities", activity.get("author_email")):
        raise HTTPException(status_code=403)
    return templates.TemplateResponse(
        "activities_edit.html",
        {"request": request, "activity": _prepare_publication_entry(activity), "user": user},
    )


@app.post("/actividades/{activity_id}/editar")
async def activities_edit_submit(
    request: Request,
    activity_id: str,
    title: str = Form(...),
    summary: str = Form(...),
    content_html: str = Form(...),
    celebration_at: str = Form(...),
    is_upcoming: str = Form(...),
    author_name: str | None = Form(None),
    show_author: str | None = Form(None),
    show_image: str | None = Form(None),
    is_hidden: str | None = Form(None),
    published_at: str | None = Form(None),
    image: UploadFile | None = File(None),
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    activity = await db.activities.find_one({"_id": activity_id})
    if not activity:
        raise HTTPException(status_code=404)
    if not _has_any_permission(user, "activities"):
        raise HTTPException(status_code=403)
    if not _can_edit_entry(user, "activities", activity.get("author_email")):
        raise HTTPException(status_code=403)
    updates = {
        "title": title,
        "summary": summary,
        "content_html": content_html,
        "author_name": (author_name or "").strip(),
        "show_author": show_author == "on",
        "show_image": show_image == "on",
        "is_upcoming": is_upcoming == "future",
    }
    if _has_permission(user, "activities"):
        updates["is_hidden"] = is_hidden == "on"
    else:
        updates["is_hidden"] = True
    try:
        updates["celebration_at"] = datetime.fromisoformat(celebration_at)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Fecha inválida.") from exc
    if image and image.filename:
        filename = f"{datetime.utcnow().timestamp()}_{image.filename}"
        file_path = STATIC_DIR / "store" / "activities" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(await image.read())
        updates["image_url"] = f"/static/store/activities/{filename}"
    if user.get("is_admin") and published_at:
        try:
            updates["published_at"] = datetime.fromisoformat(published_at)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Fecha inválida.") from exc
    await db.activities.update_one(
        {"_id": activity_id},
        {
            "$set": updates,
        },
    )
    return RedirectResponse(f"/actividades/{activity_id}", status_code=303)


@app.post("/actividades/{activity_id}/eliminar")
async def activities_delete(
    activity_id: str,
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    activity = await db.activities.find_one({"_id": activity_id})
    if not activity:
        raise HTTPException(status_code=404)
    if not _has_any_permission(user, "activities"):
        raise HTTPException(status_code=403)
    if not _can_edit_entry(user, "activities", activity.get("author_email")):
        raise HTTPException(status_code=403)
    await db.activities.delete_one({"_id": activity_id})
    return RedirectResponse("/actividades", status_code=303)


@app.post("/actividades/{activity_id}/publicar")
async def activities_publish(
    activity_id: str,
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user or not _has_permission(user, "activities"):
        raise HTTPException(status_code=403)
    await db.activities.update_one(
        {"_id": activity_id},
        {"$set": {"is_hidden": False}},
    )
    return RedirectResponse("/actividades", status_code=303)


@app.get("/contacto")
async def contact(request: Request) -> Any:
    return templates.TemplateResponse("contact.html", {"request": request})


@app.get("/perfil")
async def profile(request: Request, user: dict | None = Depends(get_current_user)) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    profile_data = await _ensure_user_profile(user)
    profile_data.setdefault("equipment_notes", "")
    user_photos_cursor = db.photos.find({"uploaded_by": user["email"]}).sort("uploaded_at", -1)
    user_photos = [_serialize_doc(photo) async for photo in user_photos_cursor]
    blog_entries_cursor = db.blog_entries.find({"author_email": user["email"]}).sort(
        "published_at", -1
    )
    blog_entries = [_prepare_publication_entry(entry) async for entry in blog_entries_cursor]
    activities_cursor = db.activities.find({"author_email": user["email"]}).sort(
        "published_at", -1
    )
    activity_entries = [_prepare_publication_entry(entry) async for entry in activities_cursor]
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": user,
            "profile": profile_data,
            "user_photos": user_photos,
            "blog_entries": blog_entries,
            "activity_entries": activity_entries,
        },
    )


@app.post("/perfil")
async def profile_update(
    request: Request,
    full_name: str = Form(""),
    location: str = Form(""),
    bio: str = Form(""),
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    await db.users.update_one(
        {"email": user["email"]},
        {
            "$set": {
                "full_name": full_name.strip(),
                "location": location.strip(),
                "bio": bio.strip(),
            },
            "$setOnInsert": {"is_admin": bool(user.get("is_admin"))},
        },
        upsert=True,
    )
    return RedirectResponse("/perfil", status_code=303)


@app.post("/perfil/equipos")
async def profile_update_equipment(
    equipment_notes: str = Form(""),
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    notes = equipment_notes.strip()
    if len(notes) > 500:
        notes = notes[:500]
    await db.users.update_one(
        {"email": user["email"]},
        {
            "$set": {"equipment_notes": notes},
            "$setOnInsert": {"is_admin": bool(user.get("is_admin"))},
        },
        upsert=True,
    )
    return RedirectResponse("/perfil", status_code=303)


def _content_sort_key(item: dict[str, Any]) -> datetime:
    value = item.get("sort_date")
    if isinstance(value, datetime):
        return value
    return datetime.min


@app.get("/gestion-contenidos")
async def content_management(
    request: Request,
    page: int = 1,
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user or not (
        user.get("is_admin")
        or any(_has_permission(user, scope) for scope in ("photos", "blog", "activities"))
    ):
        raise HTTPException(status_code=403)

    allowed_scopes = {
        scope
        for scope in ("photos", "blog", "activities")
        if _can_manage_scope(user, scope)
    }
    if user.get("is_admin"):
        allowed_scopes = {"photos", "blog", "activities"}

    hidden_items: list[dict[str, Any]] = []
    published_items: list[dict[str, Any]] = []

    if "photos" in allowed_scopes:
        async for photo in db.photos.find({"is_hidden": True}).sort("uploaded_at", -1):
            hidden_items.append(
                {
                    "scope": "photos",
                    "id": photo["_id"],
                    "title": photo.get("name", ""),
                    "author": photo.get("author", ""),
                    "status_label": "Astrofotografía",
                    "sort_date": photo.get("uploaded_at"),
                    "date_display": _format_spanish_date(photo.get("uploaded_at")),
                    "edit_url": f"/astrofotos/{photo['_id']}/editar",
                }
            )
        async for photo in db.photos.find({"is_hidden": {"$ne": True}}).sort(
            "uploaded_at", -1
        ):
            published_items.append(
                {
                    "scope": "photos",
                    "id": photo["_id"],
                    "title": photo.get("name", ""),
                    "author": photo.get("author", ""),
                    "status_label": "Astrofotografía",
                    "sort_date": photo.get("uploaded_at"),
                    "date_display": _format_spanish_date(photo.get("uploaded_at")),
                    "edit_url": f"/astrofotos/{photo['_id']}/editar",
                }
            )

    if "blog" in allowed_scopes:
        async for entry in db.blog_entries.find({"is_hidden": True}).sort("published_at", -1):
            hidden_items.append(
                {
                    "scope": "blog",
                    "id": entry["_id"],
                    "title": entry.get("title", ""),
                    "author": entry.get("author_name") or entry.get("author_email", ""),
                    "status_label": "Blog",
                    "sort_date": entry.get("published_at"),
                    "date_display": _format_spanish_date(entry.get("published_at")),
                    "edit_url": f"/blog/{entry['_id']}/editar",
                }
            )
        async for entry in db.blog_entries.find({"is_hidden": {"$ne": True}}).sort(
            "published_at", -1
        ):
            published_items.append(
                {
                    "scope": "blog",
                    "id": entry["_id"],
                    "title": entry.get("title", ""),
                    "author": entry.get("author_name") or entry.get("author_email", ""),
                    "status_label": "Blog",
                    "sort_date": entry.get("published_at"),
                    "date_display": _format_spanish_date(entry.get("published_at")),
                    "edit_url": f"/blog/{entry['_id']}/editar",
                }
            )

    if "activities" in allowed_scopes:
        async for activity in db.activities.find({"is_hidden": True}).sort("published_at", -1):
            hidden_items.append(
                {
                    "scope": "activities",
                    "id": activity["_id"],
                    "title": activity.get("title", ""),
                    "author": activity.get("author_name") or activity.get("author_email", ""),
                    "status_label": "Noticias",
                    "sort_date": activity.get("published_at"),
                    "date_display": _format_spanish_date(activity.get("published_at")),
                    "edit_url": f"/actividades/{activity['_id']}/editar",
                }
            )
        async for activity in db.activities.find({"is_hidden": {"$ne": True}}).sort(
            "published_at", -1
        ):
            published_items.append(
                {
                    "scope": "activities",
                    "id": activity["_id"],
                    "title": activity.get("title", ""),
                    "author": activity.get("author_name") or activity.get("author_email", ""),
                    "status_label": "Noticias",
                    "sort_date": activity.get("published_at"),
                    "date_display": _format_spanish_date(activity.get("published_at")),
                    "edit_url": f"/actividades/{activity['_id']}/editar",
                }
            )

    hidden_items.sort(key=_content_sort_key, reverse=True)
    published_items.sort(key=_content_sort_key, reverse=True)

    per_page = 10
    total_pages = max(1, (len(published_items) + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start_index = (page - 1) * per_page
    paginated_published = published_items[start_index : start_index + per_page]

    return templates.TemplateResponse(
        "content_management.html",
        {
            "request": request,
            "user": user,
            "hidden_items": hidden_items,
            "published_items": paginated_published,
            "page": page,
            "total_pages": total_pages,
        },
    )


@app.post("/gestion-contenidos/{scope}/{entry_id}/visibilidad")
async def content_toggle_visibility(
    scope: str,
    entry_id: str,
    visibility: str = Form(...),
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not _can_manage_scope(user, scope):
        raise HTTPException(status_code=403)
    is_hidden = visibility == "hide"
    if scope == "photos":
        await db.photos.update_one({"_id": entry_id}, {"$set": {"is_hidden": is_hidden}})
    elif scope == "blog":
        updates = {"is_hidden": is_hidden}
        if not is_hidden:
            updates["published_at"] = datetime.utcnow()
        await db.blog_entries.update_one({"_id": entry_id}, {"$set": updates})
    elif scope == "activities":
        updates = {"is_hidden": is_hidden}
        if not is_hidden:
            updates["published_at"] = datetime.utcnow()
        await db.activities.update_one({"_id": entry_id}, {"$set": updates})
    else:
        raise HTTPException(status_code=404)
    return RedirectResponse("/gestion-contenidos", status_code=303)


@app.post("/gestion-contenidos/{scope}/{entry_id}/eliminar")
async def content_delete(
    scope: str,
    entry_id: str,
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not _can_manage_scope(user, scope):
        raise HTTPException(status_code=403)
    if scope == "photos":
        await db.photos.delete_one({"_id": entry_id})
    elif scope == "blog":
        await db.blog_entries.delete_one({"_id": entry_id})
    elif scope == "activities":
        await db.activities.delete_one({"_id": entry_id})
    else:
        raise HTTPException(status_code=404)
    return RedirectResponse("/gestion-contenidos", status_code=303)


@app.post("/contacto")
async def contact_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...),
) -> Any:
    send_email(
        "Nuevo mensaje de contacto",
        f"Mensaje de {name} ({email}):\n\n{message}",
        settings.contact_email,
    )
    return templates.TemplateResponse("contact.html", {"request": request, "success": True})


@app.get("/login")
async def login(request: Request) -> Any:
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
) -> Any:
    user = await authenticate_user(email, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Credenciales inválidas."},
        )
    request.session["user_email"] = user["email"]
    request.session["is_admin"] = bool(user.get("is_admin"))
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
async def logout(request: Request) -> Any:
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.post("/registro")
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
) -> Any:
    if password != password_confirm:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "register_error": "Las contraseñas no coinciden."},
        )
    existing = await db.pending_registrations.find_one({"email": email})
    if existing:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "register_error": "Solicitud ya enviada."},
        )
    request_id = f"req-{datetime.utcnow().timestamp()}"
    password_hash = bcrypt.hash(password)
    await db.pending_registrations.insert_one(
        {
            "_id": request_id,
            "email": email,
            "password_hash": password_hash,
            "requested_at": datetime.utcnow(),
        }
    )
    send_email(
        "Solicitud de registro",
        f"Nuevo registro pendiente para {email}.",
        settings.contact_email,
    )
    return RedirectResponse("/registro/gracias", status_code=303)


@app.get("/registro/gracias")
async def register_thanks(request: Request) -> Any:
    return templates.TemplateResponse("register_thanks.html", {"request": request})


@app.get("/admin/solicitudes")
async def admin_requests(request: Request, user: dict = Depends(require_admin)) -> Any:
    requests_cursor = db.pending_registrations.find().sort("requested_at", -1)
    requests_list = [_serialize_doc(req) async for req in requests_cursor]
    users_cursor = db.users.find().sort("email", 1)
    users_list = [
        _serialize_doc(_normalize_user(user_doc)) async for user_doc in users_cursor
    ]
    return templates.TemplateResponse(
        "admin_requests.html",
        {
            "request": request,
            "requests": requests_list,
            "users": users_list,
            "user": user,
        },
    )


@app.post("/admin/solicitudes/{request_id}/aprobar")
async def admin_approve(request_id: str, user: dict = Depends(require_admin)) -> Any:
    pending = await db.pending_registrations.find_one({"_id": request_id})
    if pending:
        password_hash = pending.get("password_hash")
        if password_hash:
            await db.users.insert_one(
                {
                    "email": pending["email"],
                    "password_hash": password_hash,
                    "is_admin": False,
                    "permissions": _default_permissions(),
                }
            )
            send_email(
                "Cuenta aprobada",
                "Tu cuenta ha sido aprobada. Ya puedes acceder con la contraseña que registraste.",
                pending["email"],
            )
        else:
            logger.warning(
                "Pending registration %s missing password hash; assigning temporary password.",
                request_id,
            )
            temp_password = "temporal"
            await create_user(pending["email"], temp_password)
            send_email(
                "Cuenta aprobada",
                "Tu cuenta ha sido aprobada. Usa la contraseña temporal 'temporal' y cámbiala al acceder.",
                pending["email"],
            )
        await db.pending_registrations.delete_one({"_id": request_id})
    return RedirectResponse("/admin/solicitudes", status_code=303)


@app.post("/admin/solicitudes/{request_id}/eliminar")
async def admin_delete(request_id: str, user: dict = Depends(require_admin)) -> Any:
    await db.pending_registrations.delete_one({"_id": request_id})
    return RedirectResponse("/admin/solicitudes", status_code=303)


@app.post("/admin/usuarios/{user_id}/permisos")
async def admin_update_permissions(
    user_id: str,
    photos: str | None = Form(None),
    photos_supervised: str | None = Form(None),
    blog: str | None = Form(None),
    blog_supervised: str | None = Form(None),
    activities: str | None = Form(None),
    activities_supervised: str | None = Form(None),
    user: dict = Depends(require_admin),
) -> Any:
    permissions = {
        "photos": photos == "on",
        "photos_supervised": photos_supervised == "on",
        "blog": blog == "on",
        "blog_supervised": blog_supervised == "on",
        "activities": activities == "on",
        "activities_supervised": activities_supervised == "on",
    }
    await db.users.update_one(
        {"_id": _parse_object_id(user_id)},
        {"$set": {"permissions": permissions}},
    )
    return RedirectResponse("/admin/solicitudes", status_code=303)


@app.post("/admin/usuarios/{user_id}/eliminar")
async def admin_user_delete(user_id: str, user: dict = Depends(require_admin)) -> Any:
    await db.users.delete_one({"_id": _parse_object_id(user_id)})
    return RedirectResponse("/admin/solicitudes", status_code=303)
