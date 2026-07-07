"""FastAPI server that powers the desktop app."""
from __future__ import annotations
import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from . import data, analyzer, news

ROOT = Path(__file__).resolve().parent.parent
WATCHLIST_FILE = ROOT / "watchlist.json"
FRONTEND_DIR = ROOT / "frontend"

app = FastAPI(title="Indicator App")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


def _load_watchlist() -> dict:
    return json.loads(WATCHLIST_FILE.read_text())


def _save_watchlist(d: dict) -> None:
    WATCHLIST_FILE.write_text(json.dumps(d, indent=2, ensure_ascii=False))


@app.get("/api/watchlist")
def get_watchlist():
    return _load_watchlist()


@app.post("/api/watchlist")
def update_watchlist(payload: dict):
    _save_watchlist(payload)
    return {"ok": True}


@app.get("/api/analyze")
def analyze_symbol(symbol: str, tf: str = "1h"):
    try:
        df = data.fetch(symbol, tf)
    except Exception as e:
        raise HTTPException(500, f"data fetch failed: {e}")
    if df is None or df.empty:
        raise HTTPException(404, "no data")
    result = analyzer.analyze(df)
    candles = [
        {
            "t": int(idx.timestamp()),
            "o": float(row["open"]),
            "h": float(row["high"]),
            "l": float(row["low"]),
            "c": float(row["close"]),
            "v": float(row["volume"]),
        }
        for idx, row in df.tail(200).iterrows()
    ]
    return {"symbol": symbol, "tf": tf, "indicators": result, "candles": candles}


@app.get("/api/news")
def get_news(symbol: str):
    return {"symbol": symbol, "items": news.fetch_news(symbol)}


@app.get("/api/ai")
def ai_summary(symbol: str, tf: str = "1h"):
    """Optional AI synthesis. Requires ANTHROPIC_API_KEY in env."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return {"enabled": False, "summary": None}
    try:
        from anthropic import Anthropic
        df = data.fetch(symbol, tf)
        ind = analyzer.analyze(df)
        news_items = news.fetch_news(symbol, limit=5)
        client = Anthropic(api_key=key)
        prompt = (
            f"作为专业交易员，基于以下数据给出 100 字以内的中文判断，包含：方向(多/空/震荡)、关键点位、风险。\n\n"
            f"标的: {symbol} 周期: {tf}\n指标: {json.dumps(ind, ensure_ascii=False)[:3500]}\n"
            f"新闻标题: {[n['title'] for n in news_items]}"
        )
        msg = client.messages.create(
            model="claude-sonnet-4-5", max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return {"enabled": True, "summary": msg.content[0].text}
    except Exception as e:
        return {"enabled": True, "error": str(e), "summary": None}


@app.get("/")
def root():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
