#!/usr/bin/env python3
"""
Morning refresh for the Agent Social Networks dashboard.

Two halves, deliberately separated by reliability:

  1. LIVE METRICS (safe to auto-publish) — scraped from structured sources:
       - The Colony agent/human/post/comment counts (rendered in its HTML)
       - CHIRP token price + market cap (CoinGecko public API)
     These update data.json["live"], the Colony card, and the chart.

  2. NEW-PLATFORM DISCOVERY (needs judgement, NOT done here) — finding new
     platforms and writing accurate profiles cannot be done by a scraper. That
     belongs in an LLM step. See discover_new_platforms() — it is a guarded stub:
     it must NEVER write a numeric claim without a source URL. Wire in an
     Anthropic API call (key from env ANTHROPIC_API_KEY) only if you accept the
     fully-automatic accuracy risk.

Run:  python scripts/refresh.py
Deps: standard library only (urllib, json, re).
"""
import json, re, sys, urllib.request, urllib.error
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data.json"
UA = {"User-Agent": "agent-social-dashboard-refresh/1.0 (+https://github.com)"}


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def refresh_colony(data):
    """Scrape live counts from The Colony homepage footer."""
    try:
        html = fetch("https://thecolony.cc/")
    except Exception as e:
        print(f"[colony] fetch failed, keeping prior values: {e}", file=sys.stderr)
        return False
    # Activity block renders like: "733 Agents  888 Humans  6491 Posts  42272 Comments".
    # Strip HTML tags first so a number and its label can sit in separate elements.
    text = re.sub(r"<[^>]+>", " ", html)
    def grab(label):
        m = re.search(r"([\d,]+)\s*" + label + r"\b", text, re.I)
        return int(m.group(1).replace(",", "")) if m else None
    agents = grab("Agents"); humans = grab("Humans")
    posts = grab("Posts");   comments = grab("Comments")
    if not agents:
        print("[colony] could not parse counts; layout may have changed", file=sys.stderr)
        return False
    today = date.today().isoformat()
    live = data["live"]["the_colony"]
    live.update({"agents": agents, "humans": humans or live["humans"],
                 "posts": posts or live["posts"], "comments": comments or live["comments"],
                 "as_of": today})
    # reflect into the card + chart
    for c in data["core"]:
        if c["id"] == "colony":
            c["big"] = f"{agents:,} agents"
            c["lbl"] = (f"+ {humans:,} humans · {posts:,} posts · {comments:,} comments "
                        f"(live, {today})")
    for row in data["chart"]:
        if row["n"] == "The Colony":
            row["v"] = agents
    print(f"[colony] {agents} agents / {humans} humans / {posts} posts / {comments} comments")
    return True


def refresh_chirp(data):
    """CHIRP token price + market cap from CoinGecko public API."""
    try:
        raw = fetch("https://api.coingecko.com/api/v3/coins/chirper-ai"
                    "?localization=false&tickers=false&market_data=true"
                    "&community_data=false&developer_data=false")
        md = json.loads(raw)["market_data"]
    except Exception as e:
        print(f"[chirp] fetch failed, keeping prior values: {e}", file=sys.stderr)
        return False
    price = md["current_price"]["usd"]
    mcap = md["market_cap"]["usd"]
    chg_1y = md.get("price_change_percentage_1y_in_currency", {}).get("usd")
    ath = md.get("ath", {}).get("usd")
    from_ath = round((price - ath) / ath * 100, 1) if ath else None
    today = date.today().isoformat()
    tok = data["live"]["chirp_token"]
    tok.update({"price_usd": price, "market_cap_usd": round(mcap),
                "change_1y_pct": round(chg_1y, 1) if chg_1y is not None else tok["change_1y_pct"],
                "from_ath_pct": from_ath if from_ath is not None else tok["from_ath_pct"],
                "as_of": today})
    # reflect into Chirper card key-value (token line is the 4th kv row)
    for c in data["core"]:
        if c["id"] == "chirper":
            line = (f"CHIRP — ${price:.6f}, ~${round(mcap):,} mcap, "
                    f"{from_ath}% from peak, {tok['change_1y_pct']}% in 1yr ({today})")
            for kv in c["kv"]:
                if kv[0] == "Token":
                    kv[1] = line
    print(f"[chirp] ${price} mcap ${round(mcap):,} ({from_ath}% from peak)")
    return True


def discover_new_platforms(data):
    """
    GUARDED STUB. Finding new consumer/social agent platforms and writing
    accurate cards requires an LLM + web search, not a scraper.

    If you wire this in (fully-automatic mode), enforce these guardrails:
      * Never append a platform without at least one working source URL.
      * Never state a numeric agent/user count without a source; if unknown,
        use big="Unverified" and put the claim in conf with LOW confidence.
      * Mark brand-new entries with badge "▲ New (unverified)" so a reader can
        tell auto-added cards from human-reviewed ones.
      * De-dupe by id before appending.
    Left as a no-op by default.
    """
    return False


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    changed = False
    changed |= refresh_colony(data)
    changed |= refresh_chirp(data)
    changed |= discover_new_platforms(data)
    if changed:
        data["meta"]["refreshed"] = date.today().isoformat()
        data["meta"]["generator"] = "refresh.py @ " + datetime.now(timezone.utc).isoformat(timespec="minutes")
        DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("data.json updated.")
    else:
        print("No changes (sources unreachable or unchanged).")


if __name__ == "__main__":
    main()
