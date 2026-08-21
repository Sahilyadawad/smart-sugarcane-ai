"""Validated image upload storage."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.config import settings

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/tiff",
}
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


async def read_image_upload(upload: UploadFile) -> bytes:
    """Read an upload, enforcing type and size limits, and verify it decodes."""
    if upload is None or not upload.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No image file was uploaded.")

    suffix = Path(upload.filename).suffix.lower()
    content_type = (upload.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES and suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type '{content_type or suffix}'. Upload a JPG, PNG or WEBP photo.",
        )

    data = await upload.read()
    await upload.close()

    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image is larger than the {settings.MAX_UPLOAD_MB} MB limit.",
        )

    # Verify the bytes really are a decodable image before anything else touches them.
    try:
        from io import BytesIO

        with Image.open(BytesIO(data)) as probe:
            probe.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That file could not be read as an image. Please upload a valid photo.",
        ) from None

    return data


def save_image(data: bytes, category: str, user_id: int, original_name: str | None = None) -> tuple[str, str]:
    """Persist bytes under ``uploads/<category>/`` and return (absolute path, public URL)."""
    if category not in {"plants", "soil"}:
        raise ValueError(f"Unknown upload category: {category}")

    suffix = Path(original_name or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        suffix = ".jpg"

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"u{user_id}-{stamp}-{secrets.token_hex(4)}{suffix}"

    directory: Path = settings.upload_path / category
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / filename
    destination.write_bytes(data)

    return str(destination), f"/uploads/{category}/{filename}"


def delete_image(absolute_path: str | None) -> None:
    """Best-effort cleanup when a history entry is deleted."""
    if not absolute_path:
        return
    try:
        path = Path(absolute_path)
        # Only ever delete inside the configured upload directory.
        if path.is_file() and settings.upload_path in path.resolve().parents:
            path.unlink()
    except OSError:
        pass
