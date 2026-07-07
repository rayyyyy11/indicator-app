"""Free RSS news for crypto + US stocks."""
from __future__ import annotations
import time
from urllib.parse import quote
import feedparser

CRYPTO_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
]


def _yahoo_feed(symbol: str) -> str:
    return f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={quote(symbol)}&region=US&lang=en-US"


def _google_news(query: str) -> str:
    return f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"


def _parse(url: str, limit: int = 5) -> list[dict]:
    out = []
    try:
        d = feedparser.parse(url)
        for e in d.entries[:limit]:
            out.append({
                "title": getattr(e, "title", ""),
                "link": getattr(e, "link", ""),
                "published": getattr(e, "published", ""),
                "source": d.feed.get("title", ""),
            })
    except Exception:
        pass
    return out


def fetch_news(symbol: str, limit: int = 8) -> list[dict]:
    items: list[dict] = []
    if "/" in symbol:
        base = symbol.split("/")[0]
        for url in CRYPTO_FEEDS:
            items += _parse(url, limit=4)
        items += _parse(_google_news(f"{base} crypto"), limit=5)
        items = [i for i in items if base.lower() in i["title"].lower()] or items
    else:
        items += _parse(_yahoo_feed(symbol), limit=limit)
        items += _parse(_google_news(f"{symbol} stock"), limit=4)

    seen = set()
    uniq = []
    for it in items:
        key = it["title"][:80]
        if key in seen:
            continue
        seen.add(key)
        uniq.append(it)
    return uniq[:limit]
