from __future__ import annotations

import argparse
import sys
from pathlib import Path

from reddit_upload import __version__
from reddit_upload.config import (
    load_config,
    parse_subreddit_name,
    parse_subs_argument,
    resolve_targets,
    validate_title,
)
from reddit_upload.errors import UserError
from reddit_upload.media import validate_media
from reddit_upload.poster import build_jobs, confirm_post, describe_job, post_all
from reddit_upload.reddit_api import PrawUploader, build_reddit, current_username, link_flairs


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "post":
            return _post(args)
        if args.command == "subs":
            return _subs(args)
        if args.command == "flairs":
            return _flairs(args)
        if args.command == "whoami":
            return _whoami(args)
    except UserError as exc:
        print(exc, file=sys.stderr)
        return 1
    raise AssertionError(f"Unhandled command {args.command!r}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reddit-upload",
        description="Upload a picture or GIF to the subreddits listed in subreddits.json.",
    )
    parser.add_argument("--version", action="version", version=f"reddit-upload {__version__}")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("subreddits.json"),
        help="Subreddit list. Defaults to ./subreddits.json.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    post = commands.add_parser("post", help="Upload a picture or GIF")
    post.add_argument("media", type=Path, help="Path to a .jpg, .png, .gif, or .webp file")
    post.add_argument("--title", required=True, help="Post title")
    post.add_argument(
        "--subs",
        help="Comma-separated subreddits for this run. Defaults to every subreddit in the config.",
    )
    post.add_argument(
        "--delay",
        type=float,
        default=None,
        help="Seconds to wait between subreddits. Defaults to delay_seconds in the config.",
    )
    post.add_argument("--yes", action="store_true", help="Post without asking for confirmation")
    post.add_argument("--dry-run", action="store_true", help="Show the plan and do not contact Reddit")
    post.add_argument("--nsfw", action=argparse.BooleanOptionalAction, default=None)
    post.add_argument("--spoiler", action=argparse.BooleanOptionalAction, default=None)

    commands.add_parser("subs", help="Show the configured subreddit list")

    flairs = commands.add_parser("flairs", help="List link flairs you can assign in a subreddit")
    flairs.add_argument("subreddit", help="Subreddit name, with or without the r/ prefix")

    commands.add_parser("whoami", help="Show which Reddit account the saved credentials log in as")
    return parser


def _post(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    media_path = validate_media(args.media)
    title = validate_title(args.title)
    if args.delay is not None and (args.delay < 0 or args.delay > 3600):
        raise UserError("--delay must be between 0 and 3600 seconds.")
    selected = parse_subs_argument(args.subs) if args.subs is not None else None
    jobs = build_jobs(
        resolve_targets(config, selected),
        cli_nsfw=args.nsfw,
        cli_spoiler=args.spoiler,
        config_nsfw=config.nsfw,
        config_spoiler=config.spoiler,
    )
    delay = config.delay_seconds if args.delay is None else args.delay

    print(f"File: {media_path}")
    print(f"Title: {title}")
    print("Subreddits:")
    for job in jobs:
        print(f"  - {describe_job(job)}")

    if args.dry_run:
        print("Dry run only. Nothing was posted.")
        return 0

    if not confirm_post(args.yes, stdin_is_tty=sys.stdin.isatty(), prompt=input):
        print("Cancelled. Nothing was posted.")
        return 0

    reddit = build_reddit(args.config)
    results = post_all(
        PrawUploader(reddit),
        jobs,
        title=title,
        media_path=media_path,
        send_replies=config.send_replies,
        timeout=config.timeout_seconds,
        delay_seconds=delay,
        on_status=print,
    )
    failures = 0
    for result in results:
        if result.ok:
            location = result.url or "posted, but Reddit did not return a link"
            print(f"Posted to r/{result.subreddit}: {location}")
        else:
            failures += 1
            print(f"Failed r/{result.subreddit}: {result.error}", file=sys.stderr)
    print(f"{len(results) - failures} posted, {failures} failed.")
    return 1 if failures else 0


def _subs(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    jobs = build_jobs(
        list(config.subreddits),
        cli_nsfw=None,
        cli_spoiler=None,
        config_nsfw=config.nsfw,
        config_spoiler=config.spoiler,
    )
    if not jobs:
        raise UserError("No subreddits configured.")
    for job in jobs:
        print(describe_job(job))
    print(f"Wait between posts: {config.delay_seconds:g}s")
    return 0


def _flairs(args: argparse.Namespace) -> int:
    name = parse_subreddit_name(args.subreddit)
    rows = link_flairs(build_reddit(args.config), name)
    if not rows:
        print(f"r/{name} has no user-selectable link flairs.")
        return 0
    for flair_id, text in rows:
        label = text or "(no text)"
        print(f"{flair_id}\t{label}")
    return 0


def _whoami(args: argparse.Namespace) -> int:
    print(f"u/{current_username(build_reddit(args.config))}")
    return 0
