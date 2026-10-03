from pathlib import Path

import pytest

from reddit_upload.errors import UserError
from reddit_upload.media import validate_media

PNG = b"\x89PNG\r\n\x1a\n" + b"rest"
GIF = b"GIF89a" + b"rest"
JPEG = b"\xff\xd8\xff" + b"rest"
WEBP = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"rest"


@pytest.mark.parametrize(
    ("name", "payload"),
    [("photo.png", PNG), ("anim.gif", GIF), ("photo.jpg", JPEG), ("photo.jpeg", JPEG), ("photo.webp", WEBP)],
)
def test_validate_media_accepts_real_headers(tmp_path: Path, name: str, payload: bytes):
    path = tmp_path / name
    path.write_bytes(payload)
    assert validate_media(path) == path


def test_validate_media_rejects_mismatched_contents(tmp_path: Path):
    path = tmp_path / "clip.gif"
    path.write_bytes(PNG)
    with pytest.raises(UserError, match="does not look like"):
        validate_media(path)


def test_validate_media_rejects_type_size_and_missing(tmp_path: Path):
    text = tmp_path / "notes.txt"
    text.write_text("hello", encoding="utf-8")
    with pytest.raises(UserError, match="Unsupported"):
        validate_media(text)

    empty = tmp_path / "empty.png"
    empty.write_bytes(b"")
    with pytest.raises(UserError, match="empty"):
        validate_media(empty)

    big = tmp_path / "big.png"
    big.write_bytes(PNG)
    with pytest.raises(UserError, match="limit"):
        validate_media(big, max_bytes=4)

    with pytest.raises(UserError, match="not found"):
        validate_media(tmp_path / "missing.png")
