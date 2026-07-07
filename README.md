# Indicator Dashboard

Mac 桌面应用：实时技术分析 + 关键点位 + 相关新闻。

## 覆盖

- **市场**: 加密货币（Binance via ccxt）+ 美股（yfinance）
- **指标全套**:
  - 趋势：SMA(20/50/200), EMA(12/26/50), MACD, ADX/+DI/-DI, Ichimoku, SuperTrend, PSAR
  - 动量：RSI, Stochastic, Williams%R, ROC, CCI, KDJ
  - 波动：Bollinger Bands, ATR, Keltner Channel
  - 量能：OBV, VWAP, MFI, CMF
- **关键点位**: 支撑/阻力（pivot 算法）、Fibonacci 回撤、经典 Pivot Points (P/R1-3/S1-3)
- **信号**: 综合打分 + 解释（强多/偏多/中性/偏空/强空）
- **新闻**: 免费 RSS（CoinDesk / Cointelegraph / Yahoo Finance / Google News）
- **AI 综合判断**（可选）：设置 `ANTHROPIC_API_KEY` 即启用 Claude 一句话总结

## 运行

```bash
cd ~/Documents/indicator-app
/Users/ray/quant_env/bin/pip install -r requirements.txt
/Users/ray/quant_env/bin/python3 run.py
```

启用 AI 分析（可选）：

```bash
export ANTHROPIC_API_KEY=sk-ant-...
/Users/ray/quant_env/bin/python3 run.py
```

## 操作

- 左栏点击标的切换；输入框 + 按钮添加新标的
- 顶部切换周期（15m / 1h / 4h / 1d / 1w）
- 「🔄 刷新分析」按需拉最新数据
- 加密货币用 `BTC/USDT` 格式，美股用 `AAPL` 格式

## 定制

编辑 `watchlist.json` 持久化关注列表。
