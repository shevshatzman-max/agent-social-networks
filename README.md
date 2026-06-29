# Agent Social Networks — auto-updating dashboard

A static dashboard of consumer & social AI-agent platforms (agent counts, trends,
founders, deep dives). The page reads its data from `data.json`, and a daily
GitHub Action regenerates that file from live sources and redeploys.

```
agent-social-site/
├── index.html      ← the page (renders from data.json)
├── data.json       ← all the content + live metrics (the only file the daily job edits)
├── scripts/
│   └── refresh.py  ← morning refresh: scrapes The Colony + CHIRP token
├── .github/workflows/
│   └── daily-refresh.yml  ← cron (06:30 UTC) → refresh → commit → deploy
├── netlify.toml    ← Netlify config (only if hosting on Netlify)
└── README.md
```

## Which host? (you asked)

For a self-updating site the **cron lives on GitHub Actions** regardless of host.
The only choice is where the files are served from:

| Host | Best if… | Cost | Setup |
|---|---|---|---|
| **GitHub Pages** | you want it all in one place | free | enable Pages (deploy from branch); daily commits auto-redeploy |
| **Netlify** | you like a polished UI / previews | free tier | "Import from Git" → auto-deploys on every push |
| **Cloudflare Pages** | you want the fastest CDN | free tier | "Connect to Git" → auto-deploys on every push |

**Recommendation:** start with **GitHub Pages** (zero extra accounts — the
included workflow already publishes it). Move to Netlify/Cloudflare later if you
want their UI; if you do, delete the `deploy-pages` job from the workflow since
those hosts redeploy on the push themselves.

## One-time setup

1. Create a GitHub repo and push this folder to it.
2. **GitHub Pages:** Settings → Pages → Source = "Deploy from a branch" → branch `main`, folder `/ (root)` → Save. Every push (including the daily refresh) redeploys automatically.
   **Netlify/Cloudflare:** create a site from this repo; set publish directory = repo root. It also redeploys on every push.
3. (Optional, for fully-automatic *new-platform discovery*) add an Anthropic
   API key: Settings → Secrets and variables → Actions → `ANTHROPIC_API_KEY`.
   Without it, the daily job still refreshes the live metrics — it just won't
   auto-add new platforms.
4. Run it once now: Actions tab → "Daily data refresh" → "Run workflow".

## What auto-updates, and the honest caveat

- **Live metrics (safe):** `refresh.py` pulls The Colony's counts and the CHIRP
  token every morning from structured sources and updates `data.json`.
- **New platforms / profile edits (needs judgement):** this is the
  `discover_new_platforms()` stub in `refresh.py`. A scraper cannot do it; it
  needs an LLM step. You chose **fully automatic**, so if you wire it in, keep
  the built-in guardrails: never publish a number without a source URL, mark
  auto-added cards as "▲ New (unverified)," and de-dupe. Even so, an unattended
  LLM will occasionally publish something wrong — glance at the site weekly.

## Local preview

`data.json` is loaded via `fetch()`, which browsers block on `file://`. To
preview locally, run a tiny server from this folder:

```bash
python -m http.server 8000   # then open http://localhost:8000
```

## Editing content by hand

Everything on the page lives in `data.json` (`core`, `tier1`, `tier2`, `chart`).
Edit it, push, and the site redeploys. No need to touch `index.html`.
