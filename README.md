# AI Shelby — Automated Community Manager

> **Built for:** The Class Economy System — [skool.com/class-economy](https://skool.com/class-economy)
> **Community Owner:** Shelby Lattimore
> **Last Updated:** May 2026

---

## What This System Does

AI Shelby is a fully automated community management system that keeps the Class Economy Skool community active and engaged — without Shelby needing to do anything day-to-day.

| Workflow | Schedule | What it does |
|----------|----------|-------------|
| **Daily Post** | Every day at 7:00 AM ET | Posts engaging day-specific content in Shelby's voice |
| **Comment Reply** | Every hour | Scans for unanswered comments and replies as Shelby |
| **Weekly Events** | Monday at 8:00 AM ET | Generates 4 community events/challenges for the week |

All three workflows can be paused/resumed with a **single toggle** — no code changes required.

---

## Project File Structure

```
ai-shelby/
│
├── config.json              ← On/off toggle (edit SYSTEM_ACTIVE here)
├── .env                     ← API keys (never commit this to GitHub)
├── requirements.txt         ← Python dependencies
│
├── shelby_prompt.py         ← Shelby's AI personality (shared by all scripts)
├── daily_post.py            ← Workflow 1: Daily morning post
├── comment_reply.py         ← Workflow 2: Hourly comment reply
├── weekly_events.py         ← Workflow 3: Weekly event generator
│
├── utils/
│   ├── apify_client.py      ← All Skool read/write via Apify
│   ├── claude_client.py     ← All AI content generation via Claude
│   └── toggle.py            ← On/off toggle reader/writer
│
├── dashboard/
│   ├── app.py               ← Flask toggle dashboard server
│   └── templates/
│       └── index.html       ← Beautiful one-page toggle UI
│
└── README.md                ← This file
```

---

## Setup Instructions

### Step 1: Prerequisites

Make sure you have **Python 3.10+** installed:
```bash
python --version
```

### Step 2: Install Dependencies

```bash
cd ai-shelby
pip install -r requirements.txt
```

### Step 3: Set Up API Keys

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill in your real API keys (see **Credentials** section below).

### Step 4: Verify the Toggle

Open `config.json` and make sure it reads:
```json
{
  "SYSTEM_ACTIVE": true
}
```

---

## Credentials & API Keys

### 1. Anthropic Claude API Key

| Field | Value |
|-------|-------|
| **Used for** | Generating all AI content in Shelby's voice |
| **Where to get** | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| **Where to put** | `.env` → `ANTHROPIC_API_KEY=...` |
| **Model used** | `claude-sonnet-4-6` |
| **Est. monthly cost** | $5–15/month depending on usage |

> **Model note:** The original spec referenced `claude-sonnet-4-20250514`, which Anthropic's API returns 404 for (it isn't a published model ID). We use the current Sonnet 4.6 alias `claude-sonnet-4-6` instead — same family, newer generation, verified working against the API.

### 2. Apify API Token

| Field | Value |
|-------|-------|
| **Used for** | Reading posts from and writing posts to Skool |
| **Where to get** | [console.apify.com](https://console.apify.com) → Settings → Integrations → Personal API Token |
| **Where to put** | `.env` → `APIFY_API_TOKEN=...` |
| **Actor used** | `cristiantala/skool-all-in-one-api` |
| **Est. monthly cost** | $10–30/month |

> **Apify Setup:** Log into Apify, search the store for "Skool All-in-One API" by cristiantala, and click "Try for free". The first call pays a ~10s Playwright login cost; the actor caches the session internally per run.

### 3. Shelby's Skool credentials

The Apify actor logs into Skool as Shelby using email + password (not just a cookie). Both go in `.env`:

| Field | Value |
|-------|-------|
| **Used for** | Authenticating Apify calls as Shelby |
| **Where to put** | `.env` → `SKOOL_EMAIL=...` and `SKOOL_PASSWORD=...` |

### 4. Shelby's Skool User ID

| Field | Value |
|-------|-------|
| **Used for** | Filtering out comments Shelby already replied to |
| **Where to get** | Call `posts:list` for `class-economy` and look at `author.id` on any post by Shelby |
| **Where to put** | `.env` → `SHELBY_USER_ID=...` |

### 5. (Optional) Post category

The class-economy group has several Skool categories ("labels"). Daily and weekly posts default to the most-used category. Override if needed:

| Field | Value |
|-------|-------|
| **Where to put** | `.env` → `SKOOL_POST_LABEL_ID=...` |
| **Default** | The 24-post category id baked into [utils/apify_client.py](utils/apify_client.py) |

---

## Running the Scripts Manually

Always `cd` into the `ai-shelby` directory first.

### Test: Daily Post
```bash
python daily_post.py
```
Expected output: Logs showing Claude generating a post, then Apify posting it.

### Test: Comment Reply
```bash
python comment_reply.py
```
Expected output: Fetches posts, finds unanswered comments, generates and posts replies.

### Test: Weekly Events
```bash
python weekly_events.py
```
Expected output: Claude generates 4 events as JSON, each posted to Skool.

---

## Toggle: Pause & Resume

### Option 1 — Web Dashboard (easiest for Shelby)
Run the dashboard:
```bash
python dashboard/app.py
```
Open a browser to `http://localhost:5000` (or your deployed URL).

Flip the toggle — done. No code needed.

### Option 2 — Edit config.json directly
Open `config.json` and change:
```json
{ "SYSTEM_ACTIVE": false }   ← PAUSED (no posts will be made)
{ "SYSTEM_ACTIVE": true }    ← ACTIVE (all workflows run normally)
```

---

## Deploying to Railway or Render

This runs as **one always-on service**. That single process serves the toggle
dashboard *and* runs the built-in scheduler ([scheduler.py](scheduler.py)) that
fires the three workflows on time. Because everything lives in one process on
one filesystem, the toggle dashboard and the workflows share the **same**
`config.json` — flipping the switch reliably pauses/resumes everything.

The scheduler uses Eastern Time directly, so **daylight saving is handled
automatically** — there is nothing to adjust twice a year.

### Why one service (not separate cron jobs)

Platform cron jobs run as separate containers with separate filesystems. A
toggle written to `config.json` in one container would never be seen by the
others, so the on/off switch would silently fail. Running the dashboard and
scheduler together keeps one shared source of truth.

### Step 1 — Push to GitHub
Push this project to a GitHub repository.

### Step 2 — Create ONE service

| Platform | Service type | Start command |
|----------|-------------|---------------|
| **Railway** | Service from repo | `python dashboard/app.py` |
| **Render**  | **Web Service** (not free tier — see note) | `python dashboard/app.py` |

> **Render note:** Render's *free* web services sleep after ~15 min of inactivity, which would freeze the scheduler. Use Railway, or a Render **paid** instance, so the service stays awake 24/7.

### Step 3 — Add a persistent volume (so the toggle survives redeploys)

The container filesystem resets on every redeploy. Mount a small volume and
point the config at it so Shelby's on/off choice (and posting state) persists:

1. Add a volume/disk mounted at `/data` (1 GB is plenty).
2. Set env var `CONFIG_PATH=/data/config.json`.

On first boot the service auto-creates `/data/config.json` with `SYSTEM_ACTIVE: true`,
so it goes live immediately.

### Step 4 — Add environment variables

| Variable | Value |
|----------|-------|
| `ANTHROPIC_API_KEY` | your Anthropic key |
| `APIFY_API_TOKEN` | your Apify token |
| `SKOOL_EMAIL` | Shelby's Skool login email |
| `SKOOL_PASSWORD` | Shelby's Skool password (used by the Apify actor to log in) |
| `SHELBY_USER_ID` | Shelby's Skool user ID (her `author.id`) |
| `CONFIG_PATH` | `/data/config.json` (the mounted volume) |
| `REPLIED_STORE_PATH` | *(optional)* defaults to `replied_comments.json` next to `config.json`. Set to a volume path (e.g. `/data/replied_comments.json`) so the duplicate-reply guard persists across redeploys. |
| `SKOOL_POST_LABEL_ID` | *(optional)* override the default Skool category daily/weekly posts go into |
| `PORT` | provided automatically by Railway/Render |

That's it — the dashboard URL is what you hand to Shelby.

### Local / single-server (cron) alternative

If you ever deploy on a plain VPS where the dashboard and jobs share one disk,
you can use OS cron instead of the built-in scheduler. Run the dashboard with
`RUN_SCHEDULER=false` and add these cron lines (Eastern Time — adjust for DST):

```bash
# Daily post — 7:00 AM Eastern (UTC-4 during DST, UTC-5 during standard)
0 11 * * *   python /path/to/ai-shelby/daily_post.py     # DST
0 12 * * *   python /path/to/ai-shelby/daily_post.py     # Standard time

# Comment reply — every hour
0 * * * *    python /path/to/ai-shelby/comment_reply.py

# Weekly events — Monday 8:00 AM Eastern
0 12 * * 1   python /path/to/ai-shelby/weekly_events.py  # DST
0 13 * * 1   python /path/to/ai-shelby/weekly_events.py  # Standard time
```

You can also run the scheduler by itself (no dashboard) with `python scheduler.py`.

---

## Go-Live Checklist

- [ ] `.env` (or platform env vars) has `ANTHROPIC_API_KEY`, `APIFY_API_TOKEN`, `SKOOL_EMAIL`, `SKOOL_PASSWORD`, `SHELBY_USER_ID`
- [ ] `CONFIG_PATH` points at the mounted volume (`/data/config.json`)
- [ ] `SYSTEM_ACTIVE: true` in the live config (the volume seed does this on first boot)
- [ ] Service start command is `python dashboard/app.py` with `RUN_SCHEDULER` unset or `true`
- [ ] Dashboard URL loads and the toggle flips the live state
- [ ] Service logs show: `Background scheduler started` with three jobs and their next run times
- [ ] Manual smoke test: run `python comment_reply.py` once and confirm logs show real posts/comments being processed

---

## Testing Checklist

Before going live, complete every item below:

- [ ] Apify read test — fetch posts from `class-economy` group successfully
- [ ] Apify write test — test post appears in community (delete immediately after)
- [ ] Apify reply test — test reply appears under a post (delete immediately after)
- [ ] Claude generates a post that sounds like Shelby (not robotic)
- [ ] Claude generates a comment reply that sounds like Shelby
- [ ] `daily_post.py` runs manually and posts successfully
- [ ] `comment_reply.py` runs manually and replies successfully
- [ ] `weekly_events.py` runs manually and posts 4 event announcements
- [ ] `SYSTEM_ACTIVE: false` — all scripts exit immediately without posting
- [ ] `SYSTEM_ACTIVE: true` — all scripts resume normally
- [ ] Toggle dashboard loads and toggle button works
- [ ] Cron schedules confirmed active on server
- [ ] All API keys documented and stored securely

---

## Troubleshooting

### "ANTHROPIC_API_KEY is not set"
→ Make sure your `.env` file exists and contains the real key (not the placeholder).

### "APIFY_API_TOKEN is not set"
→ Same — check your `.env` file.

### "SHELBY_USER_ID is not set"
→ Run an Apify test call, find Shelby's `createdBy.id` and add it to `.env`.

### Apify returns empty results
→ The actor may need authentication. Verify Shelby's Skool login credentials are saved in the Apify actor's input settings.

### Claude generates content that sounds robotic
→ Check `shelby_prompt.py` — the system prompt must be passed exactly as-is to every Claude call.

### Comment reply posts duplicate replies
→ Verify `SHELBY_USER_ID` is correct — it's the first line of defense for detecting Shelby's existing replies. As a backstop, every reply made in live mode is also recorded in `replied_comments.json` (see `REPLIED_STORE_PATH`), so even if Apify is slow to show the new reply, the next hourly run won't reply again. If you ever *want* the bot to re-reply to everything, delete that file. Make sure it lives on the persistent volume so it isn't wiped on redeploy.

---

## Security Notes

- **Never commit `.env` to GitHub.** It is listed in `.gitignore`.
- API keys should be added to the deployment platform (Railway/Render) as environment variables, not hardcoded.
- The toggle dashboard has no login — the URL itself is the password. Deploy it on a non-guessable URL or add basic auth for extra security.

---

## Monthly Cost Estimate

| Service | Est. Cost |
|---------|-----------|
| Anthropic Claude API | $5–15/month |
| Apify | $10–30/month |
| Railway / Render hosting | $5–20/month |
| **Total** | **$20–65/month** |

---

*AI Shelby — Built for The Class Economy System by Shelby Lattimore.*
*Questions? Contact the project owner listed in your handover document.*
