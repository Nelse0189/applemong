from pathlib import Path

import pytest

from reddit_upload.config import SubredditTarget
from reddit_upload.errors import UserError
from reddit_upload.poster import UploadJob, build_jobs, confirm_post, describe_job, post_all


class FakeUploader:
    def __init__(self, fail: set[str] | None = None):
        self.fail = fail or set()
        self.calls: list[str] = []

    def submit(self, *, subreddit: str, **kwargs) -> str:
        self.calls.append(subreddit)
        if subreddit in self.fail:
            raise RuntimeError("rejected")
        return f"https://www.reddit.com/comments/{subreddit}"


def test_build_jobs_prefers_cli_then_subreddit_then_config():
    targets = [
        SubredditTarget("pics", nsfw=False),
        SubredditTarget("memes", flair_id="abc", flair_text="Meme", spoiler=True),
    ]
    jobs = build_jobs(targets, cli_nsfw=True, cli_spoiler=None, config_nsfw=False, config_spoiler=False)
    assert jobs[0] == UploadJob("pics", None, None, True, False)
    assert jobs[1] == UploadJob("memes", "abc", "Meme", True, True)
    assert describe_job(jobs[1]) == "r/memes (flair: Meme, nsfw, spoiler)"


def test_post_all_continues_after_failure_and_waits_between_posts(tmp_path: Path):
    media = tmp_path / "photo.png"
    waits: list[float] = []
    status: list[str] = []
    uploader = FakeUploader(fail={"bad"})
    jobs = [
        UploadJob("ok", None, None, False, False),
        UploadJob("bad", None, None, False, False),
        UploadJob("later", "flair", None, True, False),
    ]
    results = post_all(
        uploader,
        jobs,
        title="Hello",
        media_path=media,
        send_replies=True,
        timeout=30,
        delay_seconds=2,
        sleep=waits.append,
        on_status=status.append,
    )
    assert uploader.calls == ["ok", "bad", "later"]
    assert waits == [2, 2]
    assert [result.ok for result in results] == [True, False, True]
    assert results[1].error == "rejected"
    assert results[0].url == "https://www.reddit.com/comments/ok"
    assert any("Waiting 2s" in line for line in status)


def test_confirm_post():
    assert confirm_post(True, stdin_is_tty=False, prompt=lambda _: "n") is True
    assert confirm_post(False, stdin_is_tty=True, prompt=lambda _: "y") is True
    assert confirm_post(False, stdin_is_tty=True, prompt=lambda _: "no") is False
    with pytest.raises(UserError, match="--yes"):
        confirm_post(False, stdin_is_tty=False, prompt=lambda _: "y")
