from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from reddit_upload.errors import UserError

SUBREDDIT_NAME = re.compile(r"^[A-Za-z0-9_]{3,21}$")
TITLE_LIMIT = 300
CONFIG_KEYS = {
    "delay_seconds",
    "timeout_seconds",
    "nsfw",
    "spoiler",
    "send_replies",
    "subreddits",
}
SUBREDDIT_KEYS = {"name", "flair_id", "flair_text", "nsfw", "spoiler"}


@dataclass(frozen=True)
class SubredditTarget:
    name: str
    flair_id: str | None = None
    flair_text: str | None = None
    nsfw: bool | None = None
    spoiler: bool | None = None


@dataclass(frozen=True)
class AppConfig:
    delay_seconds: float
    timeout_seconds: int
    nsfw: bool
    spoiler: bool
    send_replies: bool
    subreddits: tuple[SubredditTarget, ...]


def parse_subreddit_name(raw: str) -> str:
    name = raw.strip()
    if not name:
        raise UserError("Subreddit name is empty.")
    lowered = name.lower()
    if lowered.startswith("/r/"):
        name = name[3:]
    elif lowered.startswith("r/"):
        name = name[2:]
    name = name.strip().strip("/")
    if not SUBREDDIT_NAME.fullmatch(name):
        raise UserError(
            f"Invalid subreddit name {raw!r}. Use 3-21 letters, numbers, or underscores."
        )
    return name


def parse_subs_argument(raw: str) -> list[str]:
    parts = [part.strip() for part in raw.split(",")]
    if not parts or any(not part for part in parts):
        raise UserError("--subs contains an empty subreddit name.")
    return parts


def load_config(path: Path) -> AppConfig:
    if not path.is_file():
        raise UserError(
            f"Config file not found: {path}. Create it from subreddits.json and list the communities you want."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UserError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise UserError(f"{path} must contain a JSON object.")

    unknown = set(data) - CONFIG_KEYS
    if unknown:
        names = ", ".join(sorted(unknown))
        raise UserError(f"Unknown config setting(s): {names}.")

    delay = _number(data.get("delay_seconds", 10), "delay_seconds", minimum=0, maximum=3600)
    timeout = _number(
        data.get("timeout_seconds", 30),
        "timeout_seconds",
        integer=True,
        minimum=5,
        maximum=120,
    )
    entries = data.get("subreddits")
    if not isinstance(entries, list) or not entries:
        raise UserError("Add at least one subreddit to the \"subreddits\" list.")

    targets: list[SubredditTarget] = []
    seen: set[str] = set()
    for entry in entries:
        target = _parse_target(entry)
        key = target.name.lower()
        if key in seen:
            raise UserError(f"r/{target.name} is listed more than once.")
        seen.add(key)
        targets.append(target)

    return AppConfig(
        delay_seconds=delay,
        timeout_seconds=int(timeout),
        nsfw=_boolean(data.get("nsfw", False), "nsfw"),
        spoiler=_boolean(data.get("spoiler", False), "spoiler"),
        send_replies=_boolean(data.get("send_replies", True), "send_replies"),
        subreddits=tuple(targets),
    )


def resolve_targets(config: AppConfig, selected: list[str] | None) -> list[SubredditTarget]:
    if not selected:
        return list(config.subreddits)

    by_name = {target.name.lower(): target for target in config.subreddits}
    chosen: list[SubredditTarget] = []
    seen: set[str] = set()
    for raw in selected:
        name = parse_subreddit_name(raw)
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        chosen.append(by_name.get(key, SubredditTarget(name=name)))
    return chosen


def validate_title(title: str) -> str:
    cleaned = title.strip()
    if not cleaned:
        raise UserError("Title is empty.")
    if len(cleaned) > TITLE_LIMIT:
        raise UserError(f"Title is {len(cleaned)} characters. Reddit allows {TITLE_LIMIT}.")
    return cleaned


def _parse_target(entry: object) -> SubredditTarget:
    if isinstance(entry, str):
        return SubredditTarget(name=parse_subreddit_name(entry))
    if not isinstance(entry, dict):
        raise UserError("Each subreddit must be a name or an object with a name.")

    unknown = set(entry) - SUBREDDIT_KEYS
    if unknown:
        names = ", ".join(sorted(unknown))
        raise UserError(f"Unknown subreddit setting(s): {names}.")
    if "name" not in entry:
        raise UserError("Each subreddit object needs a name.")

    flair_id = _optional_text(entry.get("flair_id"), "flair_id")
    flair_text = _optional_text(entry.get("flair_text"), "flair_text")
    if flair_text and not flair_id:
        raise UserError(
            f"r/{entry.get('name')} sets flair_text without flair_id. "
            "Run `reddit-upload flairs <subreddit>` to look up the id."
        )
    return SubredditTarget(
        name=parse_subreddit_name(str(entry["name"])),
        flair_id=flair_id,
        flair_text=flair_text,
        nsfw=_optional_bool(entry.get("nsfw"), "nsfw"),
        spoiler=_optional_bool(entry.get("spoiler"), "spoiler"),
    )


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise UserError(f"{label} must be a string.")
    text = value.strip()
    return text or None


def _optional_bool(value: object, label: str) -> bool | None:
    if value is None:
        return None
    return _boolean(value, label)


def _boolean(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise UserError(f"{label} must be true or false.")
    return value


def _number(
    value: object,
    label: str,
    *,
    integer: bool = False,
    minimum: float,
    maximum: float,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        expected = "a whole number" if integer else "a number"
        raise UserError(f"{label} must be {expected}.")
    if integer and not isinstance(value, int):
        raise UserError(f"{label} must be a whole number.")
    if value < minimum or value > maximum:
        raise UserError(f"{label} must be between {minimum:g} and {maximum:g}.")
    return float(value)
