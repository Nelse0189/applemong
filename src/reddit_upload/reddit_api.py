from __future__ import annotations

import os
from pathlib import Path

import praw
from dotenv import load_dotenv
from praw.models import PostMedia

from reddit_upload.errors import UserError


def load_environment(config_path: Path | None = None) -> None:
    if config_path is not None:
        load_dotenv(config_path.resolve().parent / ".env")
    load_dotenv()


def build_reddit(config_path: Path | None = None) -> praw.Reddit:
    load_environment(config_path)
    missing = [
        name
        for name in (
            "REDDIT_CLIENT_ID",
            "REDDIT_CLIENT_SECRET",
            "REDDIT_USERNAME",
            "REDDIT_PASSWORD",
        )
        if not os.environ.get(name, "").strip()
    ]
    if missing:
        raise UserError(
            "Missing Reddit credentials: "
            + ", ".join(missing)
            + ". Copy .env.example to .env and fill them in."
        )

    username = os.environ["REDDIT_USERNAME"].strip()
    user_agent = os.environ.get("REDDIT_USER_AGENT", "").strip()
    if not user_agent:
        user_agent = f"script:reddit-upload:0.1 (by /u/{username})"

    return praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"].strip(),
        client_secret=os.environ["REDDIT_CLIENT_SECRET"].strip(),
        username=username,
        password=os.environ["REDDIT_PASSWORD"],
        user_agent=user_agent,
        check_for_async=False,
        ratelimit_seconds=120,
    )


class PrawUploader:
    def __init__(self, reddit: praw.Reddit) -> None:
        self.reddit = reddit

    def submit(
        self,
        *,
        subreddit: str,
        title: str,
        media_path: Path,
        flair_id: str | None,
        flair_text: str | None,
        nsfw: bool,
        spoiler: bool,
        send_replies: bool,
        timeout: int,
    ) -> str | None:
        kwargs: dict[str, object] = {
            "flair_id": flair_id,
            "flair_text": flair_text,
            "image": PostMedia(str(media_path)),
            "nsfw": nsfw,
            "send_replies": send_replies,
            "spoiler": spoiler,
            "timeout": timeout,
        }
        submission = self.reddit.subreddit(subreddit).submit(title, **_without_empty(kwargs))
        if submission is None or not getattr(submission, "id", None):
            return None
        return f"https://www.reddit.com/comments/{submission.id}"


def current_username(reddit: praw.Reddit) -> str:
    account = reddit.user.me()
    if account is None:
        raise UserError("Reddit did not return an account. Check the username and password.")
    return str(account)


def link_flairs(reddit: praw.Reddit, subreddit: str) -> list[tuple[str, str]]:
    templates = reddit.subreddit(subreddit).flair.link_templates.user_selectable()
    return [
        (str(template.get("flair_template_id", "")), str(template.get("flair_text") or ""))
        for template in templates
    ]


def _without_empty(values: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in values.items() if value is not None}
