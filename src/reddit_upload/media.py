from __future__ import annotations

from pathlib import Path

from reddit_upload.errors import UserError

MAX_MEDIA_BYTES = 20 * 1024 * 1024
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def validate_media(path: Path, *, max_bytes: int = MAX_MEDIA_BYTES) -> Path:
    if not path.is_file():
        raise UserError(f"File not found: {path}")
    extension = path.suffix.lower()
    if extension not in IMAGE_EXTENSIONS:
        allowed = ", ".join(sorted(IMAGE_EXTENSIONS))
        raise UserError(f"Unsupported file type {extension or '(none)'}. Use one of: {allowed}.")

    size = path.stat().st_size
    if size == 0:
        raise UserError(f"{path} is empty.")
    if size > max_bytes:
        raise UserError(
            f"{path.name} is {size} bytes. The limit for this uploader is {max_bytes} bytes."
        )

    header = path.read_bytes()[:16]
    if not _header_matches(extension, header):
        raise UserError(f"{path} does not look like a {extension} file.")
    return path


def _header_matches(extension: str, header: bytes) -> bool:
    if extension in {".jpg", ".jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == ".gif":
        return header.startswith((b"GIF87a", b"GIF89a"))
    if extension == ".webp":
        return len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    return False
