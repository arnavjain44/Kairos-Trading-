# PRD: ML-Based Intraday Trade Recommender

Oct 9, 2026 · @Arnav Jain

## Overview

The product takes a rupee amount and returns a ranked list of intraday trades (stock, side, quantity, entry, stop loss, target) that the model expects to close in profit before the market closes the same day. Version 1 is intraday only; the design leaves room for long (positional) trades later.

Assumptions to confirm:

- Market: Indian equities on NSE, cash segment, intraday (MIS) product, INR amounts, session 09:15 to 15:30 IST, all positions closed by about 15:15.
- Version 1 is semi-automatic: it only recommends trades and you place them yourself, so there is no broker integration. The reference amount is a few thousand rupees (₹5,000 is used for defaults), with both long and short trades. This is a personal learning project: the live engine runs on your own machine, and the public version is a Replay mode demo on historical days only, because sharing live buy or sell ideas with the public in India can require registration with SEBI as a research analyst or investment adviser. Kairos is a learning project and is not registered, so this demo replays historical days only. Nothing here is investment advice. Live recommendations stay local.
- Universe starts with highly liquid NSE stocks priced low enough that several shares fit the amount (for a few thousand rupees, roughly under ₹1,000), with both long and short setups.
- No profit is guaranteed. The system aims for positive expected value after costs and capped losses; most retail intraday traders lose money, so the bar for going live is deliberately high.

## Problem, goals and scope

Retail traders pick intraday trades by tips or gut feel, size positions arbitrarily and exit late. This product replaces that with a repeatable, cost-aware, risk-capped trade plan sized to the money the user actually has.

**Goals**

- G1: Given an amount, return a ranked and sized trade plan in under 10 seconds.
- G2: Every trade carries an entry, stop loss, target and a time exit before the close.
- G3: Positive expected net return after brokerage, taxes, charges and slippage, in backtest and in paper trading.
- G4: Strategy horizon is pluggable, so long trades can be added without rewriting the system.

**Non-goals for version 1:** options and futures, scalping below one minute, crypto or forex, multi-user SaaS, unattended auto-trading before paper results, overnight positions, publishing live or same-day recommendations to the public, guaranteed returns.

| Area | Version 1 | Later |
| --- | --- | --- |
| Horizon | Intraday, same-day exit | Swing and long-term |
| Instruments | Liquid NSE equities | ETFs, F&O, more markets |
| Output | Ranked trade plan and alerts | Auto-execution, portfolio view |
| Users | Single user (you) | Multi-user |

## Users and core flow

The primary user is a retail trader with limited capital who wants a short, justified list of trades rather than a screen of signals.

**User stories**

- I enter my amount and get trades that fit it.
- I see why each trade was picked: probability, expected move and the top contributing signals.
- I get an alert when a target, stop or the 15:15 time exit is reached.
- I review each day's results against what the model predicted.

**Core flow**

1. User enters the amount, plus optional risk per trade, maximum number of trades and direction (long, short or both).
2. System filters the liquid universe using pre-market data: gap, volume, event and surveillance flags.
3. After the opening range forms (about 09:30 to 09:45), the model scores each candidate setup on live bars.
4. The allocator picks and sizes trades to fit the amount and risk budget.
5. User receives trade cards; the system monitors them and flags exits.
6. Everything is squared off by 15:15 and logged for review.

## Approach

Do not ask the model to predict the price. Ask it a narrower question per candidate trade: will this trade hit its target before its stop, within today's session? Then rank by expected net value and size to the amount.

1. **Universe filter.** Keep stocks with high average turnover, tight spreads and no surveillance or ban flags, priced so at least one share fits the amount.
2. **Candidate generation.** Rule-based setups define when a trade is even considered: opening range breakout, VWAP reclaim or rejection, gap-and-go, gap fade, momentum continuation, mean reversion from VWAP bands.
3. **ML scoring.** For each candidate, predict the probability of hitting target before stop and the expected return, using price features plus news and sentiment features; a strong negative or positive news signal can veto or boost a trade.
4. **Ranking.** Expected net value = P(win) x reward - P(loss) x risk - costs.
5. **Sizing and allocation.** Fit the best trades to the amount and risk budget.
6. **Risk gates and exits.** Stop, target, time exit and daily loss cap.

Why hybrid: rules give the model a clean, labelled set of events instead of every minute of noise, and a plain rule-only strategy becomes the baseline the ML must beat. If it cannot, the ML is not adding value and should not go live.

## Data requirements

One to two years of 1-minute data is enough to start; three or more years across different market conditions is better.

| Data | Granularity | History | Source options |
| --- | --- | --- | --- |
| Intraday OHLCV | 1-minute, resampled to 5 and 15 | 2 to 3 years | Broker APIs (Kite Connect, Upstox, Angel One, Dhan) or a data vendor; some charge for historical data |
| Daily OHLCV | Daily | 5+ years | NSE bhavcopy (free); yfinance only for prototyping |
| Corporate actions | Event | Same as prices | NSE announcements, for split and bonus adjustment |
| Market context | 1-minute and daily | Same | NIFTY 50, Bank NIFTY, sector indices, India VIX |
| Live quotes | Websocket ticks or bars | Real time | Broker websocket |
| Event and restriction lists | Daily | Rolling | Results calendar, F&O ban list, ASM and GSM lists, circuit limits |
| News and sentiment | Event | Required, 1+ year timestamped to the minute | NSE and BSE announcements, news APIs or RSS, earnings-call text, social feeds |

Data quality rules: adjust prices for corporate actions, store timestamps in IST, include delisted stocks to avoid survivorship bias, and drop or repair bad ticks and gaps before any feature is computed.

**Free sources first, and the cheapest paid upgrade**

Start free with Angel One's SmartAPI for intraday candles and live quotes; add the paid Dhan Data API only if the free history proves too short or unreliable. Prices below came from web search on 9 Oct 2026, so confirm them on each provider's site.

| Need | Free option | Cheapest paid option |
| --- | --- | --- |
| Daily prices | NSE bhavcopy files; yfinance for prototyping only | Not needed |
| 1-minute candles and live quotes | [Angel One SmartAPI](https://www.angelone.in/news/angel-one-smartapi-the-secret-to-easy-automated-algo-trading), free with an Angel One account, includes historical data; [Upstox API](https://upstox.com/help-center/249898/), free, with limited intraday history | [Dhan Data API](https://dhan.co/support/platforms/dhanhq-api/how-to-use-algo-in-dhan/): ₹499 + GST a month, up to 5 years of intraday history; ₹399 a month if billed yearly per [OpenAlgo docs](https://docs.openalgo.in/connect-brokers/dhan) |
| News and announcements | NSE and BSE announcement pages, Google News RSS, RSS feeds of Indian financial news sites, GDELT | None recommended yet; compare paid news APIs only if free feeds prove too slow or thin |
| Sentiment scoring | FinBERT, open source, run locally | Optional hosted LLM calls, billed per use |

Zerodha's Kite Connect is not the cheapest route: its paid plan is [₹2,000 a month](https://www.marketcalls.in/fintech/zerodha-makes-trading-api-free-for-personal-use-bundles-historical-data-with-connect-api.html), and its free personal plan has no market data. Using Angel One or Upstox data needs an account with that broker, but version 1 never places orders through it.

## Indicators and features

Start with about 30 to 50 features across the groups below, computed on 1, 5 and 15-minute bars, and let the model and feature importance prune them.

| Group | Indicators | What it tells the model |
| --- | --- | --- |
| Trend | VWAP and price distance from it, EMA 9 and 21, Supertrend, ADX | Direction and strength of the day's move |
| Momentum | RSI(14), MACD histogram, rate of change, Stochastic | Continuation vs exhaustion |
| Volatility | ATR(14), Bollinger Band width, opening range size, India VIX | Expected move, stop and target distance, position size |
| Volume | Relative volume vs same time of day, OBV, volume spikes | Whether a move has participation |
| Price structure | Opening range high and low, previous day high, low and close, gap %, pivot points, distance from day high and low | Breakout and reversal levels |
| Market context | NIFTY return since open, sector strength, stock vs NIFTY relative strength, beta | Whether the stock is moving with or against the market |
| Time | Minutes since open, day of week, expiry day flag | Intraday seasonality |
| Liquidity | Bid-ask spread, average turnover | Slippage and fill risk |

Two points matter more than adding indicators: normalise volume and volatility by time of day (09:20 and 13:00 are not comparable), and remember most of these indicators are derived from the same price series, so they are highly correlated.

**News and sentiment features (part of version 1)**

- **Stock-level news:** sentiment score of headlines and exchange announcements in the last 15 and 60 minutes and since the previous close; count of news items; a flag for news arriving in the last few minutes.
- **Event type:** results, order wins, regulatory action, management change, block deals and rating changes, tagged and scored separately because each moves prices differently.
- **Market and sector news:** index and sector sentiment, macro events, global cues before the open.
- **Surprise and novelty:** how different the news is from what was already reported and from the stock's usual news flow.
- **Attention:** volume of mentions on news and social feeds relative to normal.

The main intraday risk is timing: by the time a headline is scored, the price may already have moved. Every news item is therefore stored with its publication time, features use only items published before the signal, and the model is also given how long ago the news arrived and how much price has moved since.

## ML model design

- **Label (target).** Triple-barrier: from each signal, enter at the next bar's open; the target is k1 x ATR away, the stop is k2 x ATR away, and the time barrier is 15:15. Label = target hit first, stop hit first, or timed out (with the return at timeout). Regression on the return to 15:15 is the alternative.
- **Models.** Logistic regression as the baseline, then gradient boosting (LightGBM or XGBoost) as the main model. Sequence models (LSTM, temporal CNN) only if boosting plateaus; tabular boosting is the pragmatic default here.
- **Validation.** Walk-forward by time (train on a rolling past window, test on the next), with purging and an embargo around each split. Never shuffle randomly. Keep the most recent 3 months fully untouched until the end.
- **Leakage controls.** Features use only bars closed before the signal; prices are corporate-action adjusted; nothing uses the day's final high, low or close.
- **Calibration.** Calibrate probabilities (isotonic or Platt) because position sizing and ranking depend on them being meaningful.
- **Metrics that matter.** Expected net value per trade, profit factor and precision in the top 3 picks per day. Accuracy is not useful here because wins and losses are not symmetric.
- **Explainability.** SHAP values per trade, shown on the trade card.
- **Retraining.** Weekly or monthly on a rolling window, with drift monitoring on feature distributions and live hit rate.

**News and sentiment in the model.** A finance-tuned language model (for example FinBERT, or an LLM prompt with a fixed scoring schema) turns each headline or announcement into sentiment, event type and a novelty score. These become ordinary features for the gradient boosting model, alongside the price features. Validation checks that news features improve out-of-sample net value over the price-only model; if they do not, they stay as a veto filter only.

## Capital allocation for a given amount

Risk a fixed fraction of the amount on each trade, so a stop-out costs a known, small amount. With amount A and risk per trade r (default 0.5% to 1% of A, configurable):

```latex
qty = \left\lfloor \frac{A \cdot r}{\lvert entry - stop \rvert} \right\rfloor
```

1. Take trades in ranked order and compute the quantity for each.
2. Check that the position value fits the available capital (and margin, if leverage is enabled) and a per-position cap (default 30% of A).
3. Stop adding trades when capital is used up, the maximum trade count is reached (default 3 to 5), or total risk hits the daily budget (default 2% of A).
4. Drop any trade whose expected net gain is not clearly above its round-trip costs (for example, below 2x costs).

Small amounts need care: a high-priced stock may not fit, and fixed per-order brokerage plus STT and other charges can consume most of a small expected gain. The tool should show a minimum workable amount and the cost-adjusted expected profit for each trade.

Version 1 defaults to no leverage. Intraday leverage multiplies losses as much as gains and should be an explicit opt-in.

**Planning for a few thousand rupees**

- Treat the amount as the maximum position value, with no leverage on longs or shorts. Defaults at ₹5,000: 2 to 3 trades a day, a per-position cap of 40%, and risk per trade of 1% (₹50).
- Shorts are only possible as same-day trades in an intraday margin account at a broker. Version 1 recommends them and you place them yourself, so every short idea must also be closed before the market closes.
- Costs decide feasibility. On a ₹2,000 trade, brokerage, STT and exchange charges can come to roughly ₹2 to ₹4 round trip (about 0.1% to 0.2%) with a broker that charges the lower of a flat fee or a small percentage per order, but a flat ₹20 per order is 2% round trip and eats most of the edge. Check your broker's intraday plan before trusting any backtest, and keep slippage in the model on top.
- Expect small absolute numbers: a 0.5% net gain on ₹5,000 is ₹25. At this size the product is for proving the hit rate and net expectancy, which then scale to larger amounts.

## Risk management

- **Stop loss on every trade**, ATR-based, placed as a real stop order the moment a position is opened if auto-execution is on.
- **Target and trailing stop:** move the stop to breakeven after the trade gains 1x its risk.
- **Time exit:** close everything by 15:15 IST, ahead of the broker's own auto square-off, which usually carries an extra charge.
- **Daily loss cap:** stop trading for the day at a loss of 2% of the amount (configurable), and after 3 consecutive losing trades.
- **Exposure limits:** maximum trades per day, maximum share of capital per stock and per sector.
- **Avoid list:** the first 5 to 10 minutes after the open, results-day stocks, stocks near circuit limits, illiquid names, F&O ban and surveillance-list stocks.
- **Market filter:** reduce size or skip the day on extreme gaps or a sharp India VIX spike.
- **Kill switch:** manual, plus automatic on stale data, repeated API errors or model drift.

## Backtesting, paper trading and go-live criteria

The backtester must be bar-by-bar and event-driven, using the same feature and model code as live, so results are not flattered by differences between the two.

- **Realistic fills:** enter at the next bar's open, add slippage (basis points or half the spread), and never fill at a price that was not tradable.
- **Full cost model:** brokerage, STT, exchange transaction charges, SEBI fees, stamp duty and GST for intraday equity.
- **Metrics:** net P&L, win rate, average win vs average loss, profit factor, daily Sharpe and Sortino, maximum drawdown, top-1 and top-3 hit rate.
- **Robustness:** sensitivity to ATR multiples and thresholds, results split by market regime (trending, choppy, high VIX), and Monte Carlo reshuffling of trade order.

Proposed gates before more money is risked:

| Stage | Pass criteria (proposed starting points) |
| --- | --- |
| 1. Backtest | Net positive after costs on at least 6 months of untouched out-of-sample data; profit factor above 1.3; drawdown within the daily and monthly limits |
| 2. Paper trading | 4 to 8 weeks of live paper trades with results close to the backtest |
| 3. Live, small | Smallest practical capital, manual confirmation of each trade, at least 4 weeks |
| 4. Scale up | Increase capital in steps only while live results stay consistent with paper |

## Model verification charts

Every model decision must be visible on a candlestick chart, so you can see at a glance whether it was right. The reference is the chart you shared: candles with the model's signals and the true labels drawn on the same candles, plus a range slider to scroll through history.

**Main chart (same view for backtest, paper and live)**

- **Candles and volume:** selectable stock, day and timeframe (1, 5, 15 minutes), with zoom and a range slider.
- **Indicator overlays, toggled on and off:** EMA 9 and 21, VWAP, opening range high and low, Bollinger Bands.
- **Model signals:** a distinct marker for each long and short recommendation, with the predicted probability on hover.
- **True labels:** markers from the triple-barrier labelling (target hit, stop hit, timed out), in a different colour and shape from the signals, so prediction and outcome can be compared on the same candle.
- **Trade box:** entry, stop and target lines with a shaded area from signal to exit.
- **News markers:** a flag at each news timestamp, coloured by sentiment, with the headline and score on hover.
- **Hover details:** open, high, low, close, indicator values, probability and the top contributing features.

**Supporting views**

| View | What it shows | Question it answers |
| --- | --- | --- |
| Signals vs labels | Model markers against true labels over a day or range | Is the model right where it matters? |
| Trade replay | One trade candle by candle with its plan lines | Why did it enter and exit there? |
| Equity and drawdown | Cumulative net P&L after costs | Does it make money, and how bumpy is it? |
| Calibration | Predicted probability against actual hit rate | Can the probabilities be trusted for ranking and sizing? |
| Long vs short breakdown | Precision, recall and net P&L per side | Does one side carry the results? |
| Feature importance | SHAP values for price, news and sentiment features | What is driving the signals? |
| Regime breakdown | Results by trending, choppy and high-VIX days | Where does it fail? |

To draw these, every prediction is stored with its timestamp, stock, side, probability, feature snapshot, the later true label and the realised outcome. Plotly candlestick charts inside Streamlit cover version 1.

## Functional requirements and architecture

| ID | Requirement | Priority |
| --- | --- | --- |
| FR1 | Accept amount in INR, risk per trade, max trades and direction | P0 |
| FR2 | Ingest and store historical and live market data | P0 |
| FR3 | Compute indicators and features, identical in backtest and live | P0 |
| FR4 | Generate candidate setups, score and rank them | P0 |
| FR5 | Size and allocate trades to the amount and risk budget | P0 |
| FR6 | Output a trade plan: symbol, side, quantity, entry, stop, target, probability, expected net P&L, reasons | P0 |
| FR7 | Backtester with full cost and slippage model | P0 |
| FR8 | Paper trading, trade log and daily performance dashboard | P1 |
| FR9 | Out of version 1: broker API execution with stop orders and 15:15 square-off; version 1 shows exit levels and alerts instead | P1 |
| FR10 | Alerts for entries, exits and kill-switch events (Telegram or email) | P1 |
| FR11 | Model registry, scheduled retraining, drift monitoring | P2 |
| FR12 | Long-horizon strategy plug-in using daily features | P2 |
| FR13 | Ingest news and announcements in real time, score sentiment and event type, and feed both the model and a news veto or boost rule | P0 |
| FR14 | Candlestick verification chart with indicator overlays, model signals, true labels, trade levels, news markers and a range slider | P0 |
| FR15 | Performance views: equity and drawdown, calibration, long vs short breakdown, feature importance, regime breakdown | P1 |
| FR16 | Replay mode: pick a past date and an amount and view the saved plan, charts and results, labelled as an educational demo on historical data | P1 |
| FR17 | Last session review: optional, off by default; static page published after market close showing the previous trading day's plan, charts and outcomes, labelled as a historical review | P2 |

The components below are shared between the backtester and the live path, which is what keeps backtest results honest.

&#91;embedded content: system architecture · 9 components\]

Data flows through the top row, is scored and sized in the middle row, and ends in a trade plan; execution (dashed) is added only after paper trading.

## Tech stack, non-functional needs and compliance

| Layer | Suggested choice |
| --- | --- |
| Language | Python |
| Data handling | pandas or polars; TA-Lib or pandas-ta for indicators |
| Storage | Parquet with DuckDB for version 1; PostgreSQL with TimescaleDB later |
| ML | scikit-learn, LightGBM or XGBoost, Optuna for tuning, SHAP, MLflow for experiment tracking |
| Backtesting | Custom event-driven engine, or vectorbt for fast research |
| Backend and UI | FastAPI backend; React (Next.js) front end with Plotly charts, as in the design doc |
| Scheduling | APScheduler or cron; Airflow only if pipelines grow |
| Broker API | Market data only in version 1: Angel One SmartAPI (free), optionally Dhan Data API (paid); no order placement |
| Infra | Docker on your own machine for development; public Replay mode demo on Vercel's free plan; structured logs; secrets in environment files |

**Non-functional requirements:** decisions on bar close within 1 to 2 seconds of data arrival; data feed and broker checks during 09:15 to 15:30; idempotent order placement so a retry never doubles a position; full audit log of every signal, order and fill; reproducible runs from a stored model and data version.

**Compliance (verify before relying on this; this is not legal or tax advice):**

- Trading your own money with your own tool is a personal matter. Sharing live buy or sell ideas with the public in India can require registration with SEBI as a research analyst or investment adviser. Kairos is a learning project and is not registered, so this demo replays historical days only. Nothing here is investment advice. Anything shared publicly is historical; live recommendations remain strictly local.
- Retail algorithmic trading through broker APIs is subject to SEBI and exchange rules, which have been changing recently (for example around static IP and broker-side registration of algos). Confirm the current requirements with your chosen broker.
- Intraday equity profit is generally taxed as speculative business income in India; confirm treatment with a chartered accountant.

## Success metrics and roadmap

Proposed starting targets, to be revised once real backtest numbers exist:

| Metric | Target |
| --- | --- |
| Profit factor after costs, out-of-sample | Above 1.3 |
| Expected net gain per trade | Above 0 and above 2x round-trip costs |
| Maximum drawdown | Within the daily loss cap (2%) and a monthly limit you set |
| Top-3 pick precision | Clearly above the rule-only baseline |
| Paper vs backtest gap | Small and not drifting in one direction |
| Time from request to trade plan | Under 10 seconds |

The roadmap runs in phases, each ending in a gate. Durations are indicative for one person building part-time and will move.

&#91;embedded content: roadmap · 6 phases, 5 gates\]

A failed gate sends you back a phase rather than forward; the long-trades phase starts only once live intraday results hold up.

## Risks, open questions and next steps

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Overfitting: backtest looks good, live does not | High | Walk-forward validation, simple models first, mandatory paper trading |
| Costs and slippage erase the edge, especially on small amounts | High | Cost-aware ranking, minimum workable amount, liquid stocks only |
| Data leakage in features or labels | High | Purged splits, features from closed bars only, code review of every feature |
| Market regime changes | Medium | Drift monitoring, scheduled retraining, daily loss cap |
| Data feed or API failure mid-session | Medium | Staleness checks, kill switch, idempotent orders |
| Regulatory changes | Medium | Personal use first, confirm current algo rules with the broker |
| News is late, noisy or already priced in; sentiment model misreads headlines | Medium | Timestamp every item, use time-since-news and price move since, compare with a price-only model, review a sample of scores by hand |
| Public content mistaken for investment advice | High | Replay-only demo, visible disclaimer and explanation section, Last session review off by default and only after market close |

**Decisions and open questions**

Decided so far:

- Recommendations only, with no broker integration in version 1: you place the trades yourself.
- Reference amount of a few thousand rupees, long and short, no leverage.
- Free data first, with the cheapest paid option as a fallback (see Data requirements). Personal learning project: the public version is a Replay mode demo on historical days, not live recommendations, because sharing live buy or sell ideas with the public in India can require registration with SEBI as a research analyst or investment adviser. Kairos is a learning project and is not registered, so this demo replays historical days only. Nothing here is investment advice. Live recommendations stay local.

Still open:

1. Confirm NSE equities as the market.
2. Are the recommendations for you only, or will others receive them? Sharing with others can require SEBI registration.
3. Should Last session review be enabled in the public demo? (Default: off; keep off until rules are verified with a qualified person).
4. Which broker account will you use to place trades by hand, especially shorts, which need an intraday margin account?
5. Who is on the build team, and what is the timeline?

**Next steps**

- Pick the broker and pull 1 to 2 years of 1-minute data for the top 100 liquid stocks.
- Build the cost model and a simple opening-range-breakout backtest as the baseline.
- Define the triple-barrier labels and train the first gradient boosting model.
