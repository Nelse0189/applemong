import json
from pathlib import Path

import pytest

from reddit_upload.config import load_config, parse_subreddit_name, parse_subs_argument, resolve_targets, validate_title
from reddit_upload.errors import UserError


def test_parse_subreddit_name_strips_prefix():
    assert parse_subreddit_name("pics") == "pics"
    assert parse_subreddit_name("r/pics") == "pics"
    assert parse_subreddit_name("/r/Aww") == "Aww"
    assert parse_subreddit_name("  r/test  ") == "test"


@pytest.mark.parametrize("name", ["", "r/", "ab", "has space", "pics!", "a" * 22])
def test_parse_subreddit_name_rejects_invalid(name):
    with pytest.raises(UserError):
        parse_subreddit_name(name)


def test_parse_subs_argument():
    assert parse_subs_argument("pics, r/aww") == ["pics", "r/aww"]
    with pytest.raises(UserError):
        parse_subs_argument("pics,,aww")


def test_load_config_and_resolve_override(tmp_path: Path):
    path = tmp_path / "subreddits.json"
    path.write_text(
        json.dumps(
            {
                "delay_seconds": 5,
                "subreddits": [
                    "test",
                    {"name": "r/memes", "flair_id": "abc", "flair_text": "Meme", "nsfw": True},
                ],
            }
        ),
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.delay_seconds == 5
    assert config.timeout_seconds == 30
    assert [item.name for item in config.subreddits] == ["test", "memes"]

    selected = resolve_targets(config, ["r/memes", "pics", "memes"])
    assert [item.name for item in selected] == ["memes", "pics"]
    assert selected[0].flair_id == "abc"
    assert selected[1].flair_id is None


def test_load_config_rejects_bad_documents(tmp_path: Path):
    missing = tmp_path / "missing.json"
    with pytest.raises(UserError, match="not found"):
        load_config(missing)

    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    with pytest.raises(UserError, match="not valid JSON"):
        load_config(broken)

    duplicate = tmp_path / "dup.json"
    duplicate.write_text(json.dumps({"subreddits": ["pics", "r/pics"]}), encoding="utf-8")
    with pytest.raises(UserError, match="more than once"):
        load_config(duplicate)

    flair = tmp_path / "flair.json"
    flair.write_text(
        json.dumps({"subreddits": [{"name": "memes", "flair_text": "Meme"}]}),
        encoding="utf-8",
    )
    with pytest.raises(UserError, match="flair_id"):
        load_config(flair)


def test_validate_title():
    assert validate_title("  hello  ") == "hello"
    assert len(validate_title("a" * 300)) == 300
    with pytest.raises(UserError):
        validate_title("   ")
    with pytest.raises(UserError):
        validate_title("a" * 301)
