from pathlib import Path

from reddit_upload.reddit_api import PrawUploader, current_username, link_flairs

PNG = b"\x89PNG\r\n\x1a\n" + b"rest"


class FakeSubmission:
    id = "abc123"


class FakeSubreddit:
    def __init__(self):
        self.title = None
        self.kwargs = None

    def submit(self, title, **kwargs):
        self.title = title
        self.kwargs = kwargs
        return FakeSubmission()


class FakeTemplates:
    def user_selectable(self):
        return [{"flair_template_id": "abc", "flair_text": "News"}, {"flair_template_id": "def"}]


class FakeFlair:
    link_templates = FakeTemplates()


class FakeReddit:
    def __init__(self):
        self.subreddit_name = None
        self.subreddit_obj = FakeSubreddit()
        self.subreddit_obj.flair = FakeFlair()
        self.account = "tester"

    def subreddit(self, name):
        self.subreddit_name = name
        return self.subreddit_obj

    @property
    def user(self):
        return self

    def me(self):
        return self.account


def test_praw_uploader_sends_image_post_and_returns_comment_url(tmp_path: Path):
    image = tmp_path / "photo.png"
    image.write_bytes(PNG)
    reddit = FakeReddit()
    url = PrawUploader(reddit).submit(
        subreddit="pics",
        title="Hello",
        media_path=image,
        flair_id="abc",
        flair_text=None,
        nsfw=True,
        spoiler=False,
        send_replies=False,
        timeout=15,
    )
    assert reddit.subreddit_name == "pics"
    assert reddit.subreddit_obj.title == "Hello"
    assert reddit.subreddit_obj.kwargs["flair_id"] == "abc"
    assert "flair_text" not in reddit.subreddit_obj.kwargs
    assert reddit.subreddit_obj.kwargs["nsfw"] is True
    assert url == "https://www.reddit.com/comments/abc123"


def test_account_and_flair_helpers():
    reddit = FakeReddit()
    assert current_username(reddit) == "tester"
    assert link_flairs(reddit, "memes") == [("abc", "News"), ("def", "")]
    assert reddit.subreddit_name == "memes"
