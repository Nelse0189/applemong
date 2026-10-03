# Reddit upload

Upload one picture or GIF, as your Reddit account, to the subreddits you list in `subreddits.json`. Each community gets its own image post.

## Set up

1. Create a Reddit **script** app at <https://www.reddit.com/prefs/apps>.
   - Name and description can be anything.
   - Set the about URL and redirect URI to `http://localhost`.
   - After you create it, the client id is the string under the app name. The secret is labeled **secret**.
2. Install the program and save your credentials:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Fill in `.env`:

```bash
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_secret
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password
```

If the account has two-factor authentication, set the password to `your_password:123456`, using the current 6-digit code.

3. Edit `subreddits.json` and replace `test` with the communities you want. `r/test` is Reddit's sandbox. A name can be a string, or an object when a community requires flair:

```json
{
  "delay_seconds": 10,
  "timeout_seconds": 30,
  "nsfw": false,
  "spoiler": false,
  "send_replies": true,
  "subreddits": [
    "pics",
    "aww",
    {"name": "memes", "flair_id": "paste-id-here", "flair_text": "Meme"}
  ]
}
```

Look up flair ids with:

```bash
reddit-upload flairs memes
```

Check the saved account and the list:

```bash
reddit-upload whoami
reddit-upload subs
```

## Post

Supported files are `.jpg`, `.jpeg`, `.png`, `.gif`, and `.webp`, up to 20 MB. GIF files are uploaded as image posts.

```bash
reddit-upload post ./photo.png --title "A calm lake" --dry-run
reddit-upload post ./photo.png --title "A calm lake"
reddit-upload post ./clip.gif --title "Loop" --subs pics,aww --yes
```

The program asks you to confirm before it posts. `--yes` skips that prompt. `--dry-run` prints the file, title, and subreddits and does not contact Reddit. `--subs` limits one run to those communities. Names that are already in `subreddits.json` keep their flair settings.

`--nsfw` and `--spoiler` (or `--no-nsfw` and `--no-spoiler`) override the config for that run. There is a pause between communities so the posts are not fired in one burst. Change it with `delay_seconds` or `--delay`.

A failed community is reported, and the rest of the list still runs. The command exits with status 1 when any post fails.

Post only in communities whose rules allow the image. Some subreddits remove duplicates, require flair, or block new accounts.
