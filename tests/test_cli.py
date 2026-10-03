import json
from pathlib import Path

from reddit_upload.cli import main

PNG = b"\x89PNG\r\n\x1a\n" + b"rest"


def _config(tmp_path: Path) -> Path:
    path = tmp_path / "subreddits.json"
    path.write_text(
        json.dumps({"subreddits": ["test", {"name": "memes", "flair_id": "abc", "flair_text": "Meme"}]}),
        encoding="utf-8",
    )
    return path


def test_dry_run_prints_plan_without_credentials(tmp_path: Path, capsys):
    image = tmp_path / "photo.png"
    image.write_bytes(PNG)
    config = _config(tmp_path)
    code = main(
        [
            "--config",
            str(config),
            "post",
            str(image),
            "--title",
            "Hello",
            "--subs",
            "r/memes,pics",
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "r/memes (flair: Meme)" in captured.out
    assert "r/pics" in captured.out
    assert "Dry run only" in captured.out
    assert captured.err == ""


def test_dry_run_flag_overrides_show_in_the_plan(tmp_path: Path, capsys):
    image = tmp_path / "photo.png"
    image.write_bytes(PNG)
    code = main(
        ["--config", str(_config(tmp_path)), "post", str(image), "--title", "Hello", "--nsfw", "--dry-run"]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "r/test (nsfw)" in captured.out


def test_subs_command(tmp_path: Path, capsys):
    config = _config(tmp_path)
    code = main(["--config", str(config), "subs"])
    captured = capsys.readouterr()
    assert code == 0
    assert "r/test" in captured.out
    assert "r/memes (flair: Meme)" in captured.out


def test_post_requires_yes_when_not_a_tty(tmp_path: Path, capsys, monkeypatch):
    image = tmp_path / "photo.png"
    image.write_bytes(PNG)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    code = main(["--config", str(_config(tmp_path)), "post", str(image), "--title", "Hello"])
    captured = capsys.readouterr()
    assert code == 1
    assert "--yes" in captured.err
