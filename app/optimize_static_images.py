#!/usr/bin/env python3
# optimize_static_images.py
"""
Diagnostica y (opcionalmente) optimiza imágenes en una carpeta (por defecto: static/).

- Modo por defecto: solo lista/diagnostica.
- Modo --resize: guarda copia *_orig.<ext> y convierte/redimensiona a JPG (misma ruta, .jpg).

Notas:
- Si el archivo original ya era .jpg/.jpeg, también puede recomprimir/redimensionar (según flags).
- Transparencias (PNG con alpha) se aplanan sobre fondo blanco al convertir a JPG.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple, List

from PIL import Image, ImageOps

# Extensiones consideradas imagen (entrada)
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}

# Formatos típicamente "pesados" o menos web-friendly en bruto
HEAVY_FORMAT_EXTS = {".png", ".bmp", ".tif", ".tiff"}


@dataclass
class ImgInfo:
    path: Path
    size_bytes: int
    ext: str
    mode: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    has_alpha: Optional[bool] = None


def human_bytes(n: int) -> str:
    # Formato simple KB/MB/GB
    units = ["B", "KB", "MB", "GB", "TB"]
    f = float(n)
    for u in units:
        if f < 1024.0 or u == units[-1]:
            return f"{f:.1f} {u}" if u != "B" else f"{int(f)} B"
        f /= 1024.0
    return f"{n} B"


def iter_images(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            yield p


def get_img_info(p: Path) -> ImgInfo:
    size = p.stat().st_size
    ext = p.suffix.lower()
    info = ImgInfo(path=p, size_bytes=size, ext=ext)
    try:
        with Image.open(p) as im:
            info.mode = im.mode
            info.width, info.height = im.size
            # Alpha: modos típicos RGBA/LA o paleta con transparencia
            info.has_alpha = ("A" in im.getbands()) or (im.mode == "P" and "transparency" in im.info)
    except Exception:
        # Si PIL no puede abrirla, dejamos campos None y seguimos
        pass
    return info


def print_report(
    infos: List[ImgInfo],
    top: int,
    heavy_threshold_kb: int,
    only_heavy_exts: bool,
) -> None:
    heavy_threshold_bytes = heavy_threshold_kb * 1024

    # Top N por tamaño
    infos_sorted = sorted(infos, key=lambda x: x.size_bytes, reverse=True)
    print(f"\n=== Top {min(top, len(infos_sorted))} imágenes más pesadas ===")
    for i, inf in enumerate(infos_sorted[:top], start=1):
        flags = []
        if inf.ext in HEAVY_FORMAT_EXTS:
            flags.append("HEAVY_FMT")
        if inf.size_bytes >= heavy_threshold_bytes:
            flags.append(f">={heavy_threshold_kb}KB")
        if inf.has_alpha:
            flags.append("ALPHA")
        dim = f"{inf.width}x{inf.height}" if inf.width and inf.height else "?"
        mode = inf.mode or "?"
        flag_str = f" [{' '.join(flags)}]" if flags else ""
        print(f"{i:>2}. {human_bytes(inf.size_bytes):>10}  {dim:>10}  {mode:>4}  {inf.ext:>5}  {inf.path}{flag_str}")

    # Lista “problemáticas” por formato / tamaño
    print("\n=== Candidatas típicas a optimizar ===")
    candidates = []
    for inf in infos:
        if only_heavy_exts:
            if inf.ext in HEAVY_FORMAT_EXTS:
                candidates.append(inf)
        else:
            if inf.ext in HEAVY_FORMAT_EXTS or inf.size_bytes >= heavy_threshold_bytes:
                candidates.append(inf)

    candidates = sorted(candidates, key=lambda x: x.size_bytes, reverse=True)
    if not candidates:
        print("No se encontraron candidatas según los criterios actuales.")
        return

    for inf in candidates:
        flags = []
        if inf.ext in HEAVY_FORMAT_EXTS:
            flags.append("HEAVY_FMT")
        if inf.size_bytes >= heavy_threshold_bytes:
            flags.append(f">={heavy_threshold_kb}KB")
        if inf.has_alpha:
            flags.append("ALPHA")
        dim = f"{inf.width}x{inf.height}" if inf.width and inf.height else "?"
        mode = inf.mode or "?"
        print(f"- {human_bytes(inf.size_bytes):>10}  {dim:>10}  {mode:>4}  {inf.ext:>5}  {inf.path} [{' '.join(flags)}]")


def safe_backup_with_suffix(p: Path, suffix: str = "_orig") -> Path:
    """
    Renombra foo.png -> foo_orig.png
    Si ya existe foo_orig.png, añade contador foo_orig_2.png, etc.
    """
    orig = p
    stem = orig.stem
    ext = orig.suffix
    parent = orig.parent

    candidate = parent / f"{stem}{suffix}{ext}"
    if not candidate.exists():
        orig.rename(candidate)
        return candidate

    # Busca nombre libre
    k = 2
    while True:
        candidate_k = parent / f"{stem}{suffix}_{k}{ext}"
        if not candidate_k.exists():
            orig.rename(candidate_k)
            return candidate_k
        k += 1


def flatten_alpha_to_rgb(im: Image.Image, background=(255, 255, 255)) -> Image.Image:
    """
    Convierte imágenes con alpha a RGB, aplanando sobre fondo blanco (por defecto).
    """
    if im.mode in ("RGBA", "LA") or ("A" in im.getbands()):
        bg = Image.new("RGB", im.size, background)
        # Convertimos a RGBA para asegurar canal alpha
        rgba = im.convert("RGBA")
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    if im.mode == "P":
        # paleta puede tener transparencia
        if "transparency" in im.info:
            rgba = im.convert("RGBA")
            bg = Image.new("RGB", im.size, background)
            bg.paste(rgba, mask=rgba.split()[-1])
            return bg
        return im.convert("RGB")
    if im.mode != "RGB":
        return im.convert("RGB")
    return im


def resize_to_max_width(im: Image.Image, max_width: int) -> Tuple[Image.Image, bool]:
    """
    Redimensiona manteniendo aspecto si width > max_width.
    Devuelve (imagen, changed)
    """
    w, h = im.size
    if max_width <= 0 or w <= max_width:
        return im, False
    new_h = int(round(h * (max_width / w)))
    # LANCZOS: buena calidad para downscale
    im2 = im.resize((max_width, new_h), Image.Resampling.LANCZOS)
    return im2, True


def optimize_one(
    path: Path,
    max_width: int,
    quality: int,
    progressive: bool,
    strip_exif: bool,
    dry_run: bool,
    convert_png_only: bool,
    min_size_kb: int,
) -> None:
    """
    Optimiza una imagen:
    - Si convert_png_only=True, solo procesa PNG/BMP/TIFF (los de HEAVY_FORMAT_EXTS).
    - Si min_size_kb>0, solo procesa si tamaño >= ese umbral.
    - Hace backup con _orig y crea JPG con mismo nombre base (.jpg).
    """
    ext = path.suffix.lower()
    size_bytes = path.stat().st_size
    if convert_png_only and ext not in HEAVY_FORMAT_EXTS:
        return
    if min_size_kb > 0 and size_bytes < min_size_kb * 1024:
        return

    # Abrimos
    try:
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)  # respeta orientación EXIF
            im = flatten_alpha_to_rgb(im)

            im_resized, resized = resize_to_max_width(im, max_width=max_width)

            # destino: mismo nombre base pero .jpg
            dst_jpg = path.with_suffix(".jpg")

            action = []
            if resized:
                action.append(f"resize->w{max_width}")
            action.append(f"jpg(q={quality})")

            # Si el destino es el mismo archivo (ya era .jpg) y queremos preservar _orig, también aplica:
            # guardamos backup del archivo original y luego escribimos destino.
            if dry_run:
                print(f"[DRY] {path} -> backup *_orig + write {dst_jpg} ({', '.join(action)})")
                return

    except Exception as e:
        print(f"[WARN] No se pudo abrir/procesar: {path} ({e})", file=sys.stderr)
        return

    # En modo real: hacemos backup del original y escribimos el nuevo JPG
    # Importante: si path ya es .jpg y dst_jpg == path, la secuencia:
    # 1) renombrar a *_orig.jpg
    # 2) escribir nuevo .jpg con el nombre original
    try:
        # Renombrar original a *_orig.<ext>
        backed_up = safe_backup_with_suffix(path, suffix="_orig")

        # Volver a abrir desde backup (porque path ya no existe con el nombre original)
        with Image.open(backed_up) as im2:
            im2 = ImageOps.exif_transpose(im2)
            im2 = flatten_alpha_to_rgb(im2)
            im2, _ = resize_to_max_width(im2, max_width=max_width)

            save_kwargs = {
                "format": "JPEG",
                "quality": int(quality),
                "optimize": True,
                "progressive": bool(progressive),
            }
            if strip_exif:
                # No pasamos exif -> se elimina metadata
                pass
            else:
                # Intentamos preservar EXIF si existe (no siempre es crítico)
                exif = im2.info.get("exif")
                if exif:
                    save_kwargs["exif"] = exif

            # Guardar JPG destino
            im2.save(dst_jpg, **save_kwargs)

        old_size = backed_up.stat().st_size
        new_size = dst_jpg.stat().st_size
        delta = old_size - new_size
        print(
            f"[OK] {dst_jpg}  {human_bytes(old_size)} -> {human_bytes(new_size)}  "
            f"({human_bytes(delta)} menos)  backup: {backed_up.name}"
        )

        # Si el original NO era jpg y el destino .jpg tiene distinto nombre,
        # el archivo original ya fue renombrado a *_orig.<ext> y queda ahí.
        # Si el original era .jpg, el backup es *_orig.jpg y el nuevo reescribe el nombre original.

    except Exception as e:
        print(f"[ERROR] Falló optimización para {path}: {e}", file=sys.stderr)
        return


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Diagnostica y optimiza imágenes dentro de una carpeta (por defecto: static/)."
    )
    ap.add_argument(
        "--root",
        type=Path,
        default=Path("static"),
        help="Carpeta raíz a escanear (por defecto: static).",
    )
    ap.add_argument(
        "--top",
        type=int,
        default=20,
        help="Número de imágenes más pesadas a mostrar (por defecto: 20).",
    )
    ap.add_argument(
        "--heavy-threshold-kb",
        type=int,
        default=300,
        help="Umbral (KB) para marcar como 'pesada' en diagnóstico (por defecto: 300KB).",
    )
    ap.add_argument(
        "--only-heavy-exts",
        action="store_true",
        help="En la lista de candidatas, muestra solo formatos pesados (png/bmp/tiff), ignorando el umbral por tamaño.",
    )

    # Acción de optimización
    ap.add_argument(
        "--resize",
        action="store_true",
        help="Además de diagnosticar, optimiza: backup *_orig + redimensiona/comprime a JPG.",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Con --resize, no modifica nada; solo imprime lo que haría.",
    )
    ap.add_argument(
        "--max-width",
        type=int,
        default=1600,
        help="Ancho máximo en píxeles. Si la imagen es más ancha, se reduce manteniendo aspecto. (por defecto: 1600)",
    )
    ap.add_argument(
        "--quality",
        type=int,
        default=82,
        help="Calidad JPEG (1-95). Recomendado 70-85 para web. (por defecto: 82)",
    )
    ap.add_argument(
        "--progressive",
        action="store_true",
        help="Guarda JPG como progressive (suele ir bien en web).",
    )
    ap.add_argument(
        "--strip-exif",
        action="store_true",
        help="Elimina metadata/EXIF al guardar (menos peso, más privacidad).",
    )
    ap.add_argument(
        "--convert-png-only",
        action="store_true",
        help="En modo --resize, solo procesa png/bmp/tiff (formatos pesados).",
    )
    ap.add_argument(
        "--min-size-kb",
        type=int,
        default=0,
        help="En modo --resize, solo procesa imágenes con tamaño >= este umbral (KB). 0 = sin umbral.",
    )

    args = ap.parse_args()

    root: Path = args.root
    if not root.exists() or not root.is_dir():
        print(f"[ERROR] No existe carpeta raíz: {root}", file=sys.stderr)
        return 2

    # Escaneo + info
    paths = list(iter_images(root))
    if not paths:
        print(f"No se encontraron imágenes en {root.resolve()}")
        return 0

    infos = [get_img_info(p) for p in paths]
    total_bytes = sum(i.size_bytes for i in infos)
    print(f"Encontradas {len(infos)} imágenes en {root.resolve()}")
    print(f"Tamaño total: {human_bytes(total_bytes)}")

    # Diagnóstico
    print_report(
        infos=infos,
        top=args.top,
        heavy_threshold_kb=args.heavy_threshold_kb,
        only_heavy_exts=args.only_heavy_exts,
    )

    # Acción
    if args.resize:
        print("\n=== Optimización (backup *_orig + JPG) ===")
        # Procesamos en orden de mayor a menor, para atacar “lo gordo” primero
        infos_sorted = sorted(infos, key=lambda x: x.size_bytes, reverse=True)
        for inf in infos_sorted:
            optimize_one(
                path=inf.path,
                max_width=args.max_width,
                quality=args.quality,
                progressive=args.progressive,
                strip_exif=args.strip_exif,
                dry_run=args.dry_run,
                convert_png_only=args.convert_png_only,
                min_size_kb=args.min_size_kb,
            )
    else:
        print("\n(Solo diagnóstico. Usa --resize para redimensionar/comprimir.)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

