from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Form, HTTPException, Request, UploadFile
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


@app.on_event("startup")
async def startup() -> None:
    await ensure_indexes()


async def get_current_user(request: Request) -> dict | None:
    user_email = request.session.get("user_email")
    if not user_email:
        return None
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


async def _fetch_recent_photos(limit: int = 6) -> list[dict[str, Any]]:
    cursor = db.photos.find().sort("uploaded_at", -1).limit(limit)
    return [_serialize_doc(photo) async for photo in cursor]


async def _fetch_recent_blog_entries(limit: int = 3) -> list[dict[str, Any]]:
    cursor = db.blog_entries.find().sort("published_at", -1).limit(limit)
    return [_serialize_doc(entry) async for entry in cursor]


def _serialize_doc(document: dict[str, Any]) -> dict[str, Any]:
    document["_id"] = str(document.get("_id"))
    return document


@app.get("/")
async def index(request: Request) -> Any:
    context = {
        "request": request,
        "home_images": _list_home_images(),
        "photos": await _fetch_recent_photos(),
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
    return templates.TemplateResponse(
        "astrofotos.html",
        {"request": request, "photos": photos, "user": user},
    )


@app.get("/astrofotos/{photo_id}")
async def astrofoto_detail(request: Request, photo_id: str) -> Any:
    photo = await db.photos.find_one({"_id": photo_id})
    if not photo:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        "astrofoto_detail.html",
        {"request": request, "photo": _serialize_doc(photo)},
    )


@app.post("/astrofotos")
async def astrofotos_upload(
    request: Request,
    name: str = Form(...),
    exposure_time: str = Form(...),
    equipment: str = Form(...),
    description: str = Form(...),
    author: str = Form(...),
    photo_file: UploadFile = Form(...),
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    filename = f"{datetime.utcnow().timestamp()}_{photo_file.filename}"
    file_path = STATIC_DIR / "store" / "pics" / filename
    contents = await photo_file.read()
    file_path.write_bytes(contents)
    payload = {
        "_id": filename,
        "name": name,
        "uploaded_at": datetime.utcnow(),
        "exposure_time": exposure_time,
        "equipment": equipment,
        "description": description,
        "author": author,
        "image_url": f"/static/store/pics/{filename}",
    }
    await db.photos.insert_one(payload)
    return RedirectResponse("/astrofotos", status_code=303)


@app.get("/blog")
async def blog(request: Request, page: int = 1, user: dict | None = Depends(get_current_user)) -> Any:
    per_page = 5
    skip = (page - 1) * per_page
    entries_cursor = db.blog_entries.find().sort("published_at", -1).skip(skip).limit(per_page)
    entries = [_serialize_doc(entry) async for entry in entries_cursor]
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
    return templates.TemplateResponse("blog_new.html", {"request": request, "user": user})


@app.post("/blog/nueva")
async def blog_new_submit(
    request: Request,
    title: str = Form(...),
    summary: str = Form(...),
    content_html: str = Form(...),
    image: UploadFile | None = Form(None),
    user: dict | None = Depends(get_current_user),
) -> Any:
    if not user:
        raise HTTPException(status_code=403)
    image_url = ""
    if image and image.filename:
        filename = f"{datetime.utcnow().timestamp()}_{image.filename}"
        file_path = STATIC_DIR / "store" / "blog" / filename
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
    }
    await db.blog_entries.insert_one(payload)
    return RedirectResponse("/blog", status_code=303)


@app.get("/blog/{entry_id}")
async def blog_detail(request: Request, entry_id: str) -> Any:
    entry = await db.blog_entries.find_one({"_id": entry_id})
    if not entry:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        "blog_detail.html", {"request": request, "entry": _serialize_doc(entry)}
    )


@app.get("/contacto")
async def contact(request: Request) -> Any:
    return templates.TemplateResponse("contact.html", {"request": request})


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
