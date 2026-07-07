"""Compute the full set of technical indicators + key levels."""
from __future__ import annotations
import numpy as np
import pandas as pd
import ta


def _last(s):
    try:
        v = s.dropna().iloc[-1]
        return float(v) if pd.notna(v) else None
    except Exception:
        return None


def _supertrend(df: pd.DataFrame, period: int = 10, mult: float = 3.0) -> tuple[float | None, str | None]:
    h, l, c = df["high"], df["low"], df["close"]
    atr = ta.volatility.AverageTrueRange(h, l, c, window=period).average_true_range()
    hl2 = (h + l) / 2
    upper = hl2 + mult * atr
    lower = hl2 - mult * atr
    final_upper = upper.copy()
    final_lower = lower.copy()
    st = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    for i in range(1, len(df)):
        if upper.iat[i] < final_upper.iat[i - 1] or c.iat[i - 1] > final_upper.iat[i - 1]:
            final_upper.iat[i] = upper.iat[i]
        else:
            final_upper.iat[i] = final_upper.iat[i - 1]
        if lower.iat[i] > final_lower.iat[i - 1] or c.iat[i - 1] < final_lower.iat[i - 1]:
            final_lower.iat[i] = lower.iat[i]
        else:
            final_lower.iat[i] = final_lower.iat[i - 1]
        if c.iat[i] > final_upper.iat[i - 1]:
            direction.iat[i] = 1
        elif c.iat[i] < final_lower.iat[i - 1]:
            direction.iat[i] = -1
        else:
            direction.iat[i] = direction.iat[i - 1] if pd.notna(direction.iat[i - 1]) else 1
        st.iat[i] = final_lower.iat[i] if direction.iat[i] == 1 else final_upper.iat[i]
    d = direction.dropna()
    return _last(st), ("up" if not d.empty and d.iloc[-1] == 1 else "down")


def _support_resistance(df: pd.DataFrame, lookback: int = 60) -> dict:
    seg = df.tail(lookback)
    highs = seg["high"].values
    lows = seg["low"].values
    pivots_high, pivots_low = [], []
    w = 3
    for i in range(w, len(seg) - w):
        if highs[i] == max(highs[i - w:i + w + 1]):
            pivots_high.append(float(highs[i]))
        if lows[i] == min(lows[i - w:i + w + 1]):
            pivots_low.append(float(lows[i]))
    px = float(seg["close"].iloc[-1])
    res = sorted([p for p in pivots_high if p > px])[:3]
    sup = sorted([p for p in pivots_low if p < px], reverse=True)[:3]
    return {"resistance": res, "support": sup}


def _fibonacci(df: pd.DataFrame, lookback: int = 120) -> dict:
    seg = df.tail(lookback)
    hi = float(seg["high"].max())
    lo = float(seg["low"].min())
    diff = hi - lo
    levels = {f"{int(p*1000)/10}%": round(hi - diff * p, 4)
              for p in [0.236, 0.382, 0.5, 0.618, 0.786]}
    return {"high": hi, "low": lo, **levels}


def _pivot_points(df: pd.DataFrame) -> dict:
    last = df.iloc[-1]
    h, l, c = float(last["high"]), float(last["low"]), float(last["close"])
    p = (h + l + c) / 3
    return {
        "P": round(p, 4),
        "R1": round(2 * p - l, 4), "S1": round(2 * p - h, 4),
        "R2": round(p + (h - l), 4), "S2": round(p - (h - l), 4),
        "R3": round(h + 2 * (p - l), 4), "S3": round(l - 2 * (h - p), 4),
    }


def analyze(df: pd.DataFrame) -> dict:
    if df is None or df.empty or len(df) < 60:
        return {"error": "insufficient data"}

    h, l, c, v = df["high"], df["low"], df["close"], df["volume"]
    price = float(c.iloc[-1])
    prev = float(c.iloc[-2])
    chg_pct = (price - prev) / prev * 100

    out: dict = {
        "price": round(price, 4),
        "change_pct": round(chg_pct, 3),
        "high_24": round(float(h.tail(24).max()), 4),
        "low_24": round(float(l.tail(24).min()), 4),
    }

    # Trend MAs
    out["ma"] = {
        "sma20": _last(ta.trend.sma_indicator(c, 20)),
        "sma50": _last(ta.trend.sma_indicator(c, 50)),
        "sma200": _last(ta.trend.sma_indicator(c, 200)) if len(df) >= 200 else None,
        "ema12": _last(ta.trend.ema_indicator(c, 12)),
        "ema26": _last(ta.trend.ema_indicator(c, 26)),
        "ema50": _last(ta.trend.ema_indicator(c, 50)),
    }

    # MACD
    macd = ta.trend.MACD(c)
    out["macd"] = {
        "macd": _last(macd.macd()),
        "signal": _last(macd.macd_signal()),
        "hist": _last(macd.macd_diff()),
    }

    # ADX / DI
    adx = ta.trend.ADXIndicator(h, l, c)
    out["adx"] = {
        "adx": _last(adx.adx()),
        "+di": _last(adx.adx_pos()),
        "-di": _last(adx.adx_neg()),
    }

    # Ichimoku
    ich = ta.trend.IchimokuIndicator(h, l)
    out["ichimoku"] = {
        "tenkan": _last(ich.ichimoku_conversion_line()),
        "kijun": _last(ich.ichimoku_base_line()),
        "senkou_a": _last(ich.ichimoku_a()),
        "senkou_b": _last(ich.ichimoku_b()),
    }

    # SuperTrend
    st_val, st_dir = _supertrend(df)
    out["supertrend"] = {"value": st_val, "direction": st_dir}

    # PSAR
    psar = ta.trend.PSARIndicator(h, l, c)
    out["psar"] = _last(psar.psar())

    # Momentum
    out["momentum"] = {
        "rsi14": _last(ta.momentum.RSIIndicator(c, 14).rsi()),
        "stoch_k": _last(ta.momentum.StochasticOscillator(h, l, c).stoch()),
        "stoch_d": _last(ta.momentum.StochasticOscillator(h, l, c).stoch_signal()),
        "williams_r": _last(ta.momentum.WilliamsRIndicator(h, l, c).williams_r()),
        "roc": _last(ta.momentum.ROCIndicator(c).roc()),
        "cci": _last(ta.trend.CCIIndicator(h, l, c).cci()),
    }

    # KDJ (derived from stoch)
    k = ta.momentum.StochasticOscillator(h, l, c).stoch()
    d = k.rolling(3).mean()
    j = 3 * k - 2 * d
    out["kdj"] = {"K": _last(k), "D": _last(d), "J": _last(j)}

    # Volatility
    bb = ta.volatility.BollingerBands(c)
    kc = ta.volatility.KeltnerChannel(h, l, c)
    out["volatility"] = {
        "bb_upper": _last(bb.bollinger_hband()),
        "bb_mid": _last(bb.bollinger_mavg()),
        "bb_lower": _last(bb.bollinger_lband()),
        "bb_width": _last(bb.bollinger_wband()),
        "atr14": _last(ta.volatility.AverageTrueRange(h, l, c).average_true_range()),
        "kc_upper": _last(kc.keltner_channel_hband()),
        "kc_lower": _last(kc.keltner_channel_lband()),
    }

    # Volume
    out["volume"] = {
        "obv": _last(ta.volume.OnBalanceVolumeIndicator(c, v).on_balance_volume()),
        "vwap": _last(ta.volume.VolumeWeightedAveragePrice(h, l, c, v).volume_weighted_average_price()),
        "mfi": _last(ta.volume.MFIIndicator(h, l, c, v).money_flow_index()),
        "cmf": _last(ta.volume.ChaikinMoneyFlowIndicator(h, l, c, v).chaikin_money_flow()),
        "vol_sma20": float(v.rolling(20).mean().iloc[-1]) if len(v) >= 20 else None,
        "last_vol": float(v.iloc[-1]),
    }

    # Levels
    out["levels"] = {
        "fibonacci": _fibonacci(df),
        "pivots": _pivot_points(df),
        "sr": _support_resistance(df),
    }

    out["signals"] = _signals(price, out)
    return out


# 权重表：按交易员实际使用频率分级
#   3 = 最常用（RSI / MACD / 均线 / 量能确认）
#   2 = 常用（布林带、ADX、KDJ/Stoch、SuperTrend）
#   1 = 辅助（Ichimoku、PSAR、CCI、W%R、ROC、OBV、VWAP、MFI、CMF）
WEIGHTS = {
    "rsi": 3, "macd": 3, "ma_cross": 3, "ma_trend": 3, "volume": 3,
    "boll": 2, "adx": 2, "kdj": 2, "stoch": 2, "supertrend": 2,
    "ichimoku": 1, "psar": 1, "cci": 1, "willr": 1, "roc": 1,
    "obv": 1, "vwap": 1, "mfi": 1, "cmf": 1,
}


def _vote(name: str, direction: int, reason: str, votes: list, weight: int):
    """direction: +1 多 / -1 空 / 0 中性"""
    votes.append({
        "name": name, "weight": weight, "vote": direction,
        "weighted": direction * weight, "reason": reason,
    })


def _signals(price: float, ind: dict) -> dict:
    votes: list[dict] = []

    # ===== 高权重 (3) =====
    rsi = ind["momentum"].get("rsi14")
    if rsi is not None:
        if rsi < 30: _vote("RSI", +1, f"RSI {rsi:.1f} 超卖→反弹概率高", votes, WEIGHTS["rsi"])
        elif rsi < 45: _vote("RSI", +1, f"RSI {rsi:.1f} 偏弱反转", votes, WEIGHTS["rsi"])
        elif rsi > 70: _vote("RSI", -1, f"RSI {rsi:.1f} 超买→回调风险", votes, WEIGHTS["rsi"])
        elif rsi > 55: _vote("RSI", -1, f"RSI {rsi:.1f} 偏强但接近超买", votes, WEIGHTS["rsi"])
        else: _vote("RSI", 0, f"RSI {rsi:.1f} 中性", votes, WEIGHTS["rsi"])

    macd_h = ind["macd"].get("hist")
    macd_v = ind["macd"].get("macd")
    macd_s = ind["macd"].get("signal")
    if macd_h is not None and macd_v is not None and macd_s is not None:
        if macd_v > macd_s and macd_h > 0:
            _vote("MACD", +1, "MACD 金叉且红柱扩大", votes, WEIGHTS["macd"])
        elif macd_v < macd_s and macd_h < 0:
            _vote("MACD", -1, "MACD 死叉且绿柱扩大", votes, WEIGHTS["macd"])
        else:
            _vote("MACD", 0, "MACD 临界", votes, WEIGHTS["macd"])

    sma50 = ind["ma"].get("sma50")
    sma200 = ind["ma"].get("sma200")
    sma20 = ind["ma"].get("sma20")
    if sma50 and sma200:
        if sma50 > sma200:
            _vote("MA金叉", +1, "MA50 > MA200 多头排列", votes, WEIGHTS["ma_cross"])
        else:
            _vote("MA金叉", -1, "MA50 < MA200 空头排列", votes, WEIGHTS["ma_cross"])
    if sma20:
        if price > sma20:
            _vote("价格vsMA20", +1, "价格站上 MA20", votes, WEIGHTS["ma_trend"])
        else:
            _vote("价格vsMA20", -1, "价格跌破 MA20", votes, WEIGHTS["ma_trend"])

    last_v = ind["volume"].get("last_vol")
    avg_v = ind["volume"].get("vol_sma20")
    if last_v and avg_v:
        ratio = last_v / avg_v if avg_v > 0 else 1
        if ratio > 1.5 and ind["change_pct"] > 0:
            _vote("放量", +1, f"放量上涨 ({ratio:.1f}x)", votes, WEIGHTS["volume"])
        elif ratio > 1.5 and ind["change_pct"] < 0:
            _vote("放量", -1, f"放量下跌 ({ratio:.1f}x)", votes, WEIGHTS["volume"])
        elif ratio < 0.6:
            _vote("放量", 0, f"缩量 ({ratio:.1f}x)", votes, WEIGHTS["volume"])
        else:
            _vote("放量", 0, f"成交量正常 ({ratio:.1f}x)", votes, WEIGHTS["volume"])

    # ===== 中权重 (2) =====
    bb_u = ind["volatility"].get("bb_upper")
    bb_l = ind["volatility"].get("bb_lower")
    bb_m = ind["volatility"].get("bb_mid")
    if bb_u and bb_l and bb_m:
        if price < bb_l:
            _vote("布林带", +1, "跌破下轨（超跌反弹）", votes, WEIGHTS["boll"])
        elif price > bb_u:
            _vote("布林带", -1, "突破上轨（超涨回调）", votes, WEIGHTS["boll"])
        elif price > bb_m:
            _vote("布林带", +1, "运行于中轨上方", votes, WEIGHTS["boll"])
        else:
            _vote("布林带", -1, "运行于中轨下方", votes, WEIGHTS["boll"])

    adx = ind["adx"].get("adx")
    pdi = ind["adx"].get("+di")
    ndi = ind["adx"].get("-di")
    if adx is not None and pdi is not None and ndi is not None:
        if adx > 25 and pdi > ndi:
            _vote("ADX", +1, f"ADX {adx:.0f} 强趋势+多头主导", votes, WEIGHTS["adx"])
        elif adx > 25 and ndi > pdi:
            _vote("ADX", -1, f"ADX {adx:.0f} 强趋势+空头主导", votes, WEIGHTS["adx"])
        else:
            _vote("ADX", 0, f"ADX {adx:.0f} 震荡市（信号弱化）", votes, WEIGHTS["adx"])

    k = ind["kdj"].get("K"); d = ind["kdj"].get("D"); j = ind["kdj"].get("J")
    if k is not None and d is not None and j is not None:
        if j < 20 and k > d:
            _vote("KDJ", +1, f"KDJ 低位金叉 J={j:.0f}", votes, WEIGHTS["kdj"])
        elif j > 80 and k < d:
            _vote("KDJ", -1, f"KDJ 高位死叉 J={j:.0f}", votes, WEIGHTS["kdj"])
        elif k > d:
            _vote("KDJ", +1, "KDJ 金叉", votes, WEIGHTS["kdj"])
        else:
            _vote("KDJ", -1, "KDJ 死叉", votes, WEIGHTS["kdj"])

    stoch_k = ind["momentum"].get("stoch_k")
    if stoch_k is not None:
        if stoch_k < 20: _vote("Stoch", +1, f"Stoch {stoch_k:.0f} 超卖", votes, WEIGHTS["stoch"])
        elif stoch_k > 80: _vote("Stoch", -1, f"Stoch {stoch_k:.0f} 超买", votes, WEIGHTS["stoch"])
        else: _vote("Stoch", 0, f"Stoch {stoch_k:.0f} 中性", votes, WEIGHTS["stoch"])

    st_dir = ind["supertrend"].get("direction")
    if st_dir == "up":
        _vote("SuperTrend", +1, "SuperTrend 多头", votes, WEIGHTS["supertrend"])
    elif st_dir == "down":
        _vote("SuperTrend", -1, "SuperTrend 空头", votes, WEIGHTS["supertrend"])

    # ===== 低权重 (1) =====
    ich = ind["ichimoku"]
    sa, sb = ich.get("senkou_a"), ich.get("senkou_b")
    if sa and sb:
        cloud_top, cloud_bot = max(sa, sb), min(sa, sb)
        if price > cloud_top: _vote("Ichimoku", +1, "价格在云层上方", votes, WEIGHTS["ichimoku"])
        elif price < cloud_bot: _vote("Ichimoku", -1, "价格在云层下方", votes, WEIGHTS["ichimoku"])
        else: _vote("Ichimoku", 0, "价格在云层内（震荡）", votes, WEIGHTS["ichimoku"])

    psar = ind.get("psar")
    if psar:
        if price > psar: _vote("PSAR", +1, "PSAR 在价格下方（多）", votes, WEIGHTS["psar"])
        else: _vote("PSAR", -1, "PSAR 在价格上方（空）", votes, WEIGHTS["psar"])

    cci = ind["momentum"].get("cci")
    if cci is not None:
        if cci < -100: _vote("CCI", +1, f"CCI {cci:.0f} 超卖", votes, WEIGHTS["cci"])
        elif cci > 100: _vote("CCI", -1, f"CCI {cci:.0f} 超买", votes, WEIGHTS["cci"])
        else: _vote("CCI", 0, f"CCI {cci:.0f}", votes, WEIGHTS["cci"])

    wr = ind["momentum"].get("williams_r")
    if wr is not None:
        if wr < -80: _vote("Williams%R", +1, f"W%R {wr:.0f} 超卖", votes, WEIGHTS["willr"])
        elif wr > -20: _vote("Williams%R", -1, f"W%R {wr:.0f} 超买", votes, WEIGHTS["willr"])
        else: _vote("Williams%R", 0, f"W%R {wr:.0f}", votes, WEIGHTS["willr"])

    roc = ind["momentum"].get("roc")
    if roc is not None:
        if roc > 0: _vote("ROC", +1, f"ROC {roc:.2f}% 上行", votes, WEIGHTS["roc"])
        else: _vote("ROC", -1, f"ROC {roc:.2f}% 下行", votes, WEIGHTS["roc"])

    vwap = ind["volume"].get("vwap")
    if vwap:
        if price > vwap: _vote("VWAP", +1, "价格 > VWAP", votes, WEIGHTS["vwap"])
        else: _vote("VWAP", -1, "价格 < VWAP", votes, WEIGHTS["vwap"])

    mfi = ind["volume"].get("mfi")
    if mfi is not None:
        if mfi < 20: _vote("MFI", +1, f"MFI {mfi:.0f} 资金超卖", votes, WEIGHTS["mfi"])
        elif mfi > 80: _vote("MFI", -1, f"MFI {mfi:.0f} 资金超买", votes, WEIGHTS["mfi"])
        else: _vote("MFI", 0, f"MFI {mfi:.0f}", votes, WEIGHTS["mfi"])

    cmf = ind["volume"].get("cmf")
    if cmf is not None:
        if cmf > 0.1: _vote("CMF", +1, f"CMF {cmf:.2f} 资金净流入", votes, WEIGHTS["cmf"])
        elif cmf < -0.1: _vote("CMF", -1, f"CMF {cmf:.2f} 资金净流出", votes, WEIGHTS["cmf"])
        else: _vote("CMF", 0, f"CMF {cmf:.2f}", votes, WEIGHTS["cmf"])

    # ===== 汇总 =====
    total_w = sum(abs(v["weight"]) for v in votes)
    weighted = sum(v["weighted"] for v in votes)
    bull_w = sum(v["weight"] for v in votes if v["vote"] > 0)
    bear_w = sum(v["weight"] for v in votes if v["vote"] < 0)
    neutral_w = sum(v["weight"] for v in votes if v["vote"] == 0)

    # 0-100 买入分：50 = 中性，>50 偏多，<50 偏空
    buy_score = round(50 + (weighted / total_w) * 50, 1) if total_w > 0 else 50

    if buy_score >= 75: action, label = "强烈买入", "强多"
    elif buy_score >= 60: action, label = "买入", "偏多"
    elif buy_score >= 45: action, label = "观望偏多", "中性偏多"
    elif buy_score >= 35: action, label = "观望偏空", "中性偏空"
    elif buy_score >= 25: action, label = "卖出", "偏空"
    else: action, label = "强烈卖出", "强空"

    return {
        "buy_score": buy_score,
        "action": action,
        "label": label,
        "weighted_sum": weighted,
        "total_weight": total_w,
        "bull_weight": bull_w,
        "bear_weight": bear_w,
        "neutral_weight": neutral_w,
        "votes": sorted(votes, key=lambda x: -abs(x["weighted"])),
        # 兼容旧字段
        "score": weighted,
        "notes": [v["reason"] for v in votes],
    }
