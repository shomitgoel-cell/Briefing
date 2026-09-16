# Daily Briefing: Geopolitics & Markets

A fully automated 5-minute daily audio briefing, delivered to your iPhone
as a private podcast, covering:

- **~2 min** US geopolitics & financial markets
- **~2 min** global geopolitics & markets
- **~1 min** Philippines news

Every morning at **7:00 AM Asia/Manila time**, a GitHub Actions workflow:

1. Pulls fresh headlines from free public RSS feeds (`config/feeds.yaml`).
2. Uses the Claude API to write a tight, conversational script for the episode.
3. Converts the script to speech with `edge-tts` (free, no API key).
4. Publishes the MP3 and an updated podcast RSS feed to `docs/`, served by
   GitHub Pages.

Your iPhone's Podcasts app subscribes to that RSS feed like any other show.

## One-time setup

### 1. Add your Anthropic API key as a repo secret

Repo → **Settings → Secrets and variables → Actions → New repository secret**

- Name: `ANTHROPIC_API_KEY`
- Value: your Claude API key

Without this secret the pipeline still runs (so you never miss a day) but
falls back to a plain headline read-out instead of a written script.

### 2. Merge this branch to your default branch

GitHub only runs **scheduled** workflows (`on: schedule`) from the
repository's default branch. Merge this branch into `main` (or whichever
branch is set as default) before the 7 AM cron job will actually fire.
Until then, you can still trigger it manually (see below).

### 3. Enable GitHub Pages

Repo → **Settings → Pages**:

- Source: **Deploy from a branch**
- Branch: your default branch, folder **`/docs`**

Save. GitHub will give you a URL like:

```
https://<your-username>.github.io/<repo-name>/
```

The podcast feed will be at `https://<your-username>.github.io/<repo-name>/feed.xml`.

> If your GitHub Pages URL doesn't match `https://<owner>.github.io/<repo>/`
> (e.g. you use a custom domain), set a `PODCAST_BASE_URL` repository
> variable or secret and the pipeline will use that instead.

### 4. Subscribe on your iPhone

Open the **Podcasts** app:

1. Library tab → tap **•••** (top right) → **Follow a Show by URL**
2. Paste your feed URL from step 3
3. Tap **Follow**

New episodes will appear each morning once the workflow runs. Podcast apps
poll feeds periodically rather than instantly, so the very first time you
subscribe you may need to pull-to-refresh in the app.

## Running it manually

To generate an episode right now instead of waiting for the schedule:

Repo → **Actions** tab → **Daily Geopolitics & Markets Briefing** → **Run workflow**

Or locally:

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...
python scripts/run_pipeline.py
```

This writes `docs/episodes/<date>.mp3`, `docs/episodes/<date>.json` (the
script that was read), and updates `docs/feed.xml` and `docs/index.html`.

## Customizing

- **News sources**: edit `config/feeds.yaml`. Any feed that fails to load is
  skipped automatically, so it's safe to add more.
- **Segment lengths / tone**: edit the prompt in `scripts/generate_script.py`.
- **Voice**: change `VOICE` in `scripts/synthesize_audio.py`. Run
  `edge-tts --list-voices` to see all available voices/accents.
- **Schedule / timezone**: edit the cron expression in
  `.github/workflows/daily-briefing.yml` (cron runs in UTC).
- **How many past episodes to keep**: `MAX_EPISODES_KEPT` in
  `scripts/build_feed.py` (default 14 days; older audio files are deleted
  automatically to keep the repo small).

## Notes & limitations

- Every git push permanently stores that day's MP3 in git history, so the
  repository will slowly grow over time even though old files are removed
  from the working tree. Periodic history cleanup (e.g. `git filter-repo`)
  is a manual, occasional maintenance task if repo size becomes a concern.
- `edge-tts` is an unofficial wrapper around a Microsoft service; if it ever
  breaks, swap in OpenAI TTS or ElevenLabs by replacing
  `scripts/synthesize_audio.py`.
- The Claude-written script only uses facts present in the fetched
  headlines/summaries -- it will not fabricate news.
