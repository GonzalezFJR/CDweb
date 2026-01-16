from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.auth import authenticate_user, create_user
from app.config import settings
from app.db import db, ensure_indexes
from app.email_utils import send_email

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

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


@app.on_event("startup")
async def startup() -> None:
    await ensure_indexes()


async def get_current_user(request: Request) -> dict | None:
    user_email = request.session.get("user_email")
    if not user_email:
        return None
    if settings.admin_email and user_email == settings.admin_email:
        return {"email": user_email, "is_admin": True}
    return await db.users.find_one({"email": user_email})


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
        ]
    )


async def _fetch_recent_photos(limit: int = 6) -> list[dict[str, Any]]:
    cursor = db.photos.find().sort("uploaded_at", -1).limit(limit)
    return [_serialize_doc(photo) async for photo in cursor]


async def _fetch_recent_blog_entries(limit: int = 3) -> list[dict[str, Any]]:
    cursor = db.blog_entries.find().sort("published_at", -1).limit(limit)
    return [_prepare_publication_entry(entry) async for entry in cursor]


async def _fetch_recent_activities(limit: int = 3) -> list[dict[str, Any]]:
    cursor = db.activities.find().sort("published_at", -1).limit(limit)
    return [_prepare_publication_entry(activity) async for activity in cursor]


def _serialize_doc(document: dict[str, Any]) -> dict[str, Any]:
    document["_id"] = str(document.get("_id"))
    return document


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
    serialized["author_name"] = (serialized.get("author_name") or "").strip()
    serialized["show_author"] = bool(serialized.get("show_author", True))
    serialized["show_image"] = bool(serialized.get("show_image", True))
    return serialized


def _user_display_name(user: dict | None) -> str:
    if not user:
        return ""
    return user.get("full_name", "")


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
        }
    return profile


@app.get("/")
async def index(request: Request) -> Any:
    context = {
        "request": request,
        "home_images": _list_home_images(),
        "photos": await _fetch_recent_photos(),
        "activities": await _fetch_recent_activities(),
        "blog_entries": await _fetch_recent_blog_entries(),
    }
    return templates.TemplateResponse("index.html", context)


@app.get("/sobre-nosotros")
async def about(request: Request) -> Any:
    return templates.TemplateResponse("about.html", {"request": request})


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
    email: str = Form(...),
    phone: str = Form(...),
    city: str = Form(...),
    favorite: str = Form(...),
    has_telescope: str = Form(...),
    astro_experience: str = Form(...),
) -> Any:
    payload = {
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "city": city,
        "favorite": favorite,
        "has_telescope": has_telescope,
        "astro_experience": astro_experience,
        "submitted_at": datetime.utcnow(),
    }
    await db.membership_requests.insert_one(payload)
    send_email(
        "Nueva solicitud de asociación",
        f"Se ha recibido una solicitud de {full_name} ({email}).",
        settings.contact_email,
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
    photos = await _fetch_recent_photos(limit=50)
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
async def astrofoto_detail(request: Request, photo_id: str) -> Any:
    photo = await db.photos.find_one({"_id": photo_id})
    if not photo:
        raise HTTPException(status_code=404)
    serialized = _serialize_doc(photo)
    serialized["uploaded_at_display"] = _format_spanish_date(serialized.get("uploaded_at"))
    return templates.TemplateResponse(
        "astrofoto_detail.html",
        {"request": request, "photo": serialized},
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
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
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
    }
    await db.photos.insert_one(payload)
    return RedirectResponse("/astrofotos", status_code=303)


@app.get("/blog")
async def blog(request: Request, page: int = 1, user: dict | None = Depends(get_current_user)) -> Any:
    per_page = 5
    skip = (page - 1) * per_page
    entries_cursor = db.blog_entries.find().sort("published_at", -1).skip(skip).limit(per_page)
    entries = [_prepare_publication_entry(entry) async for entry in entries_cursor]
    total_entries = await db.blog_entries.count_documents({})
    total_pages = max(1, (total_entries + per_page - 1) // per_page)
    latest_entries = await _fetch_recent_blog_entries(limit=3)
    return templates.TemplateResponse(
        "blog.html",
        {
            "request": request,
            "entries": entries,
            "latest_entries": latest_entries,
            "page": page,
            "total_pages": total_pages,
            "user": user,
        },
    )


@app.get("/blog/nueva")
async def blog_new(request: Request, user: dict | None = Depends(get_current_user)) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    return templates.TemplateResponse(
        "blog_new.html",
        {"request": request, "user": user, "author_default": _user_display_name(user)},
    )


@app.get("/media/{scope}/list")
async def media_list(scope: str, user: dict | None = Depends(get_current_user)) -> Any:
    if not user:
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
    directory = _store_images_dir(scope)
    directory.mkdir(parents=True, exist_ok=True)
    for image in files:
        if not image.filename:
            continue
        filename = f"{datetime.utcnow().timestamp()}_{image.filename}"
        file_path = directory / filename
        file_path.write_bytes(await image.read())
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
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    image_url = ""
    if image and image.filename:
        filename = f"{datetime.utcnow().timestamp()}_{image.filename}"
        file_path = STATIC_DIR / "store" / "blog" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(await image.read())
        image_url = f"/static/store/blog/{filename}"
    entry_id = f"entry-{datetime.utcnow().timestamp()}"
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
    }
    await db.blog_entries.insert_one(payload)
    return RedirectResponse("/blog", status_code=303)


@app.get("/blog/{entry_id}")
async def blog_detail(request: Request, entry_id: str) -> Any:
    entry = await db.blog_entries.find_one({"_id": entry_id})
    if not entry:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        "blog_detail.html", {"request": request, "entry": _prepare_publication_entry(entry)}
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
    if entry.get("author_email") != user.get("email") and not user.get("is_admin"):
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
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    entry = await db.blog_entries.find_one({"_id": entry_id})
    if not entry:
        raise HTTPException(status_code=404)
    if entry.get("author_email") != user.get("email") and not user.get("is_admin"):
        raise HTTPException(status_code=403)
    await db.blog_entries.update_one(
        {"_id": entry_id},
        {
            "$set": {
                "title": title,
                "summary": summary,
                "content_html": content_html,
                "author_name": (author_name or "").strip(),
                "show_author": show_author == "on",
                "show_image": show_image == "on",
            }
        },
    )
    return RedirectResponse(f"/blog/{entry_id}", status_code=303)


@app.get("/actividades")
async def activities(
    request: Request,
    page: int = 1,
    user: dict | None = Depends(get_current_user),
) -> Any:
    per_page = 5
    skip = (page - 1) * per_page
    activities_cursor = (
        db.activities.find().sort("published_at", -1).skip(skip).limit(per_page)
    )
    activity_entries = [_prepare_publication_entry(activity) async for activity in activities_cursor]
    total_entries = await db.activities.count_documents({})
    total_pages = max(1, (total_entries + per_page - 1) // per_page)
    latest_entries = await _fetch_recent_activities(limit=3)
    return templates.TemplateResponse(
        "activities.html",
        {
            "request": request,
            "entries": activity_entries,
            "latest_entries": latest_entries,
            "page": page,
            "total_pages": total_pages,
            "user": user,
        },
    )


@app.get("/actividades/nueva")
async def activities_new(request: Request, user: dict | None = Depends(get_current_user)) -> Any:
    if not user:
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
    author_name: str | None = Form(None),
    show_image: str | None = Form(None),
    image: UploadFile | None = Form(None),
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    image_url = ""
    if image and image.filename:
        filename = f"{datetime.utcnow().timestamp()}_{image.filename}"
        file_path = STATIC_DIR / "store" / "activities" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(await image.read())
        image_url = f"/static/store/activities/{filename}"
    entry_id = f"activity-{datetime.utcnow().timestamp()}"
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
    }
    await db.activities.insert_one(payload)
    return RedirectResponse("/actividades", status_code=303)


@app.get("/actividades/{activity_id}")
async def activities_detail(request: Request, activity_id: str) -> Any:
    activity = await db.activities.find_one({"_id": activity_id})
    if not activity:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        "activities_detail.html",
        {"request": request, "activity": _prepare_publication_entry(activity)},
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
    if activity.get("author_email") != user.get("email") and not user.get("is_admin"):
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
    author_name: str | None = Form(None),
    show_author: str | None = Form(None),
    show_image: str | None = Form(None),
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    activity = await db.activities.find_one({"_id": activity_id})
    if not activity:
        raise HTTPException(status_code=404)
    if activity.get("author_email") != user.get("email") and not user.get("is_admin"):
        raise HTTPException(status_code=403)
    await db.activities.update_one(
        {"_id": activity_id},
        {
            "$set": {
                "title": title,
                "summary": summary,
                "content_html": content_html,
                "author_name": (author_name or "").strip(),
                "show_author": show_author == "on",
                "show_image": show_image == "on",
            }
        },
    )
    return RedirectResponse(f"/actividades/{activity_id}", status_code=303)


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
    await db.pending_registrations.insert_one(
        {"_id": request_id, "email": email, "requested_at": datetime.utcnow()}
    )
    send_email(
        "Solicitud de registro",
        f"Nuevo registro pendiente para {email}.",
        settings.contact_email,
    )
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "register_success": True},
    )


@app.get("/admin/solicitudes")
async def admin_requests(request: Request, user: dict = Depends(require_admin)) -> Any:
    requests_cursor = db.pending_registrations.find().sort("requested_at", -1)
    requests_list = [_serialize_doc(req) async for req in requests_cursor]
    return templates.TemplateResponse(
        "admin_requests.html",
        {"request": request, "requests": requests_list, "user": user},
    )


@app.post("/admin/solicitudes/{request_id}/aprobar")
async def admin_approve(request_id: str, user: dict = Depends(require_admin)) -> Any:
    pending = await db.pending_registrations.find_one({"_id": request_id})
    if pending:
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
