from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from reddit_upload.config import SubredditTarget
from reddit_upload.errors import UserError


@dataclass(frozen=True)
class UploadJob:
    subreddit: str
    flair_id: str | None
    flair_text: str | None
    nsfw: bool
    spoiler: bool


@dataclass(frozen=True)
class PostResult:
    subreddit: str
    ok: bool
    url: str | None = None
    error: str | None = None


class Uploader(Protocol):
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
    ) -> str | None: ...


def build_jobs(
    targets: list[SubredditTarget],
    *,
    cli_nsfw: bool | None,
    cli_spoiler: bool | None,
    config_nsfw: bool,
    config_spoiler: bool,
) -> list[UploadJob]:
    return [
        UploadJob(
            subreddit=target.name,
            flair_id=target.flair_id,
            flair_text=target.flair_text,
            nsfw=_flag(cli_nsfw, target.nsfw, config_nsfw),
            spoiler=_flag(cli_spoiler, target.spoiler, config_spoiler),
        )
        for target in targets
    ]


def post_all(
    uploader: Uploader,
    jobs: list[UploadJob],
    *,
    title: str,
    media_path: Path,
    send_replies: bool,
    timeout: int,
    delay_seconds: float,
    sleep: Callable[[float], None] = time.sleep,
    on_status: Callable[[str], None] | None = None,
) -> list[PostResult]:
    if not jobs:
        raise UserError("No subreddits selected.")

    results: list[PostResult] = []
    for index, job in enumerate(jobs):
        if on_status:
            on_status(f"Posting to r/{job.subreddit}...")
        try:
            url = uploader.submit(
                subreddit=job.subreddit,
                title=title,
                media_path=media_path,
                flair_id=job.flair_id,
                flair_text=job.flair_text,
                nsfw=job.nsfw,
                spoiler=job.spoiler,
                send_replies=send_replies,
                timeout=timeout,
            )
        except Exception as exc:
            results.append(PostResult(subreddit=job.subreddit, ok=False, error=_error_text(exc)))
        else:
            results.append(PostResult(subreddit=job.subreddit, ok=True, url=url))

        if delay_seconds > 0 and index < len(jobs) - 1:
            if on_status:
                on_status(f"Waiting {delay_seconds:g}s before the next subreddit...")
            sleep(delay_seconds)
    return results


def confirm_post(yes: bool, *, stdin_is_tty: bool, prompt: Callable[[str], str]) -> bool:
    if yes:
        return True
    if not stdin_is_tty:
        raise UserError(
            "Refusing to post without a confirmation prompt. Re-run with --yes to post."
        )
    answer = prompt("Post to these subreddits? [y/N] ")
    return answer.strip().lower() in {"y", "yes"}


def describe_job(job: UploadJob) -> str:
    extras: list[str] = []
    if job.flair_text or job.flair_id:
        extras.append(f"flair: {job.flair_text or job.flair_id}")
    if job.nsfw:
        extras.append("nsfw")
    if job.spoiler:
        extras.append("spoiler")
    suffix = f" ({', '.join(extras)})" if extras else ""
    return f"r/{job.subreddit}{suffix}"


def _flag(cli_value: bool | None, target_value: bool | None, config_value: bool) -> bool:
    if cli_value is not None:
        return cli_value
    if target_value is not None:
        return target_value
    return config_value


def _error_text(exc: Exception) -> str:
    items = getattr(exc, "items", None)
    if items:
        text = "; ".join(getattr(item, "error_message", str(item)) for item in items)
    else:
        text = str(exc)
    if "websocket" in text.lower():
        return text + " Try a higher timeout_seconds in subreddits.json."
    return text
