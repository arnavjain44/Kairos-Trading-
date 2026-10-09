# Kairos: Build Plan

## How to use this plan

This is the step-by-step order for building Kairos, the intraday trade recommender described in the PRD, design doc and architecture doc. It assumes one person working about 10 to 15 hours a week, which gives roughly 20 weeks. Week numbers are estimates; the order and the "done when" checks matter more.

Working rules:

- Finish a phase's "done when" check before starting the next phase, except where the timeline shows deliberate overlap.
- Commit at least once a day and keep a short decision log in the repo.
- Use only the free tiers until a free option clearly blocks you.
- Never commit keys. Everything secret lives in an .env file that git ignores.
- Keep a written note of every result, including the bad ones; they go into the final write-up.

## Timeline

The phases run mostly in sequence. The product build starts while the model work is finishing, and paper trading overlaps the end of the build so the system collects real days while you polish it.

&#91;embedded content: build timeline · 7 phases over 20 weeks\]

## Phase 0: Setup (week 1)

**Goal:** a working project skeleton and every account you need.

- **Step 1.** Create a GitHub repo named kairos as a monorepo with apps/web, apps/api, workers, packages/core, ml, infra and docs. Add a README, a .gitignore that includes .env, and a LICENSE.
- **Step 2.** Set up Python 3.12 with uv or Poetry, Ruff for linting, and pytest. Set up Node 20 or newer for the web app.
- **Step 3.** Write a Docker Compose file that starts PostgreSQL with TimescaleDB and Redis, and check you can connect to both.
- **Step 4.** Open the free accounts: Angel One (trading account plus a SmartAPI app, with the time-based login code set up), Groq, and the fallback AI providers (Cerebras, Mistral, Google AI Studio, OpenRouter). Create a Telegram bot with BotFather and a Vercel account.
- **Step 5.** Put all keys in an .env file and create an .env.example with empty values for the repo.
- **Step 6.** Add a GitHub Actions workflow that runs lint and tests on every push.
- **Step 7.** Copy the PRD, design doc and architecture doc into the docs folder as reference.

**Done when:** docker compose up starts the database and cache, and CI passes on an empty test.

## Phase 1: Data and costs (weeks 2 to 3)

**Goal:** clean market data, news and a trustworthy cost model.

- **Step 8.** Write database migrations (Alembic) for instruments, candles\_1m as a Timescale hypertable, daily\_prices, news\_items, news\_scores, predictions, outcomes and model\_versions.
- **Step 9.** Define the market data adapter interface (instruments, historical candles, live quotes, freshness) and implement it for Angel One, including the daily automated login.
- **Step 10.** Backfill 6 to 12 months of 1-minute candles for about 100 liquid stocks, respecting request limits by fetching in chunks, and store them.
- **Step 11.** Add data checks: duplicate and out-of-order bars, gaps, an NSE holiday calendar, and corporate-action adjustment using daily files. Produce a validation report.
- **Step 12.** Build the news ingestion: poll RSS feeds and exchange announcement pages, deduplicate, link items to stocks by name matching, and store the publication time.
- **Step 13.** Build the intraday equity cost model: brokerage (configurable per broker plan), STT, exchange charges, SEBI fees, stamp duty, GST and slippage. Test it against hand-calculated examples.
- **Step 14.** Build the universe filter: liquid stocks only, price low enough for the amount, and exclusion of banned and surveillance-list stocks.

**Done when:** you have clean 1-minute candles for the universe in the database, the cost model passes its tests, and a notebook can plot any stock on any day.

## Phase 2: Baseline and backtester (weeks 4 to 6)

**Goal:** a rule-based strategy and an honest backtester, so the ML has something to beat.

- **Step 15.** Write the first indicator set in packages/core: VWAP, EMA 9 and 21, RSI, MACD, ATR, Bollinger Bands, time-of-day relative volume, opening range and gap. Add tests that fail if any feature uses data from after the signal time.
- **Step 16.** Write setup detectors for long and short versions of opening range breakout, VWAP reclaim and rejection, and gap-and-go.
- **Step 17.** Write the triple-barrier labeller (target, stop, 15:15 time exit) and test it on small made-up days where you know the answer.
- **Step 18.** Write the allocator: the risk-based quantity formula, per-position cap, maximum trades and daily risk budget, with defaults for ₹5,000.
- **Step 19.** Write the event-driven backtester: fills at the next bar's open, slippage, full costs, the daily loss cap and the 15:15 exit.
- **Step 20.** Run the baseline over all history and record net P&L, win rate, profit factor, drawdown, and splits by long and short and by time of day. Save these as the benchmark.
- **Step 21.** Build the first verification chart in a notebook with Plotly: candles, indicator overlays, signals, true labels and the trade box.

**Done when:** one command reproduces the baseline results, the chart shows signals against outcomes for any day, and you can explain why the baseline wins or loses.

## Phase 3: Features, news and the model (weeks 7 to 10)

**Goal:** a calibrated model that beats the baseline after costs, or a documented honest answer that it doesn't.

- **Step 22.** Extend the features to the full 30 to 50: market context (NIFTY, sector, India VIX), relative strength, time features and liquidity.
- **Step 23.** Add news features: run FinBERT locally to score headlines, tag event types with simple keyword rules first, and build sentiment over the last 15 and 60 minutes, novelty, time since news and price move since.
- **Step 24.** Build the training dataset, one row per candidate setup with features at the signal time and its label, and save it as Parquet. Add a leakage test that rebuilds features using only past data.
- **Step 25.** Train a logistic regression baseline, then LightGBM. Tune with Optuna using purged walk-forward splits with an embargo, and calibrate the probabilities.
- **Step 26.** Evaluate on net value per trade after costs, profit factor and top-3 precision against the rule-only baseline. Run it with and without news features to see whether news helps. Add SHAP explanations.
- **Step 27.** Set up MLflow: log every run, store the model with its feature list and version, and write the promotion rule.
- **Step 28.** Review the worst misses on charts, fix real bugs, and keep the last 3 months untouched until the final check.

**Done when:** the model beats the baseline net of costs on the untouched last 3 months, or you have written down honestly that it does not and decided what to change.

## Phase 4: Product build (weeks 9 to 14)

**Goal:** the full app running end to end on your laptop.

- **Step 29.** Log every scored candidate to the predictions table, and write the after-close job that fills in true labels and outcomes.
- **Step 30.** Build the live scoring worker: at each bar close compute features, score, allocate, and keep the latest signals in Redis.
- **Step 31.** Build the scheduler for pre-market, session, after-close and weekly jobs, using the holiday calendar.
- **Step 32.** Build the FastAPI service with the endpoints from the architecture doc, shared schemas and a server-sent events stream.
- **Step 33.** Build the AI gateway: provider list and limits in config, per-provider counters, cooldowns on rate-limit errors, caching, a fixed JSON answer shape and the headline-only fallback. Add the news summary job.
- **Step 34.** Scaffold the Next.js app with the theme tokens (dark by default, light option), the sidebar and the top bar.
- **Step 35.** Build the dashboard: amount input, stat tiles and ranked trade cards.
- **Step 36.** Build the Charts screen: candles, overlays, signals, true labels, trade box, news flags and the range slider.
- **Step 37.** Build Recommendations, Performance, Backtests, News and sentiment, and Model insights screens, in that order, cutting from the end if time runs short.
- **Step 38.** Build the AI assistant panel. It reads stored predictions, news and performance, and cannot place orders.
- **Step 39.** Add Telegram alerts for entries, exits, the 15:15 exit and system failures.
- **Step 40.** Build the landing page from the design doc: hero with the candle strip, ticker, how it works, features, numbers, chart showcase, risk note and FAQ.

**Done when:** a full trading day runs end to end: the plan is generated, shown and alerted, and the next morning outcomes and the daily report are computed.

## Phase 5: Paper trading (weeks 13 to 18)

**Goal:** real market days run in recommendation mode, to see whether results match the backtest.

- **Step 41.** Run Kairos every trading day in recommendation mode with no real money, and review each day on the charts.
- **Step 42.** Do a weekly review: paper results against backtest, calibration, hit rate, costs, and any data problems. Keep a short journal.
- **Step 43.** Add guardrails: data freshness checks, a kill switch, drift checks, failure alerts, and regular backups of the database and model files.
- **Step 44.** Hold the gate: at least 4 weeks of paper results reasonably close to the backtest. If they are not, go back to Phase 3 with what you learned; the write-up is still valuable.

**Done when:** the gate is passed, or the reasons it was not are written down.

## Phase 6: Demo and launch (weeks 17 to 20)

**Goal:** a public Replay mode demo and a project others can understand in two minutes.

- **Step 45.** Write the replay export job and pick 20 to 30 past days, including losing days and quiet days, not only winners. Export plans, candles, signals, labels, outcomes, news flags, summaries and performance numbers as static files.
- **Step 46.** Add the "Why replay, not live" section and the two new FAQ entries to the landing page.
- **Step 47.** Build the optional Last session review export and page, off by default behind LAST_SESSION_ENABLED.
- **Step 48.** Add Replay mode demo to the web app: banner with "Why?" link, date picker limited to saved dates, read-only views, no sign-in, and AI limits with a pre-written fallback.
- **Step 49.** Deploy the web app to Vercel, set the server-side AI key, and test on a phone, with accessibility and speed checks.
- **Step 50.** Polish the repo: README with the architecture diagram, how the model works and how to run it, a results page with costs and what did not work, a GIF or short screen recording, and a secrets scan.
- **Step 51.** Write the case study and the LinkedIn post: the problem, the design choices, honest results and what you learned, with links to the demo and repo.
- **Step 52.** Run the launch checklist: disclaimer on every page, SEBI explanation visible on the landing page and linked from the demo banner, Last session review confirmed off unless the rules have been checked, no keys in the repo or browser code, the demo works with the backend switched off, and the AI fallback is tested.

**Done when:** the public link works from a phone, the SEBI explanation is clearly visible on the landing page and linked from the demo banner, Last session review is confirmed off unless rules have been checked, and a stranger can understand the project in two minutes.

## Phase gates

| After | Check before moving on |
| --- | --- |
| Phase 1 | Clean data and a tested cost model |
| Phase 2 | Reproducible baseline results and a working chart |
| Phase 3 | Model beats baseline net of costs on untouched data, or an honest write-up of why not |
| Phase 4 | A full day runs end to end |
| Phase 5 | Paper results close to backtest for at least 4 weeks |
| Phase 6 | Public Replay mode demo and write-up live, SEBI explanation visible, Last session review confirmed off by default |

## Weekly rhythm

- **Monday:** pick the week's steps and write them down.
- **Midweek:** build, with a commit every day.
- **Market days (from Phase 4):** check the day's plan and outcomes on the charts.
- **Friday:** review what got done, update the decision log and the results notes, and adjust next week.

## If you fall behind

Cut in this order, keeping the core path of data, baseline, model, charts and demo:

1. Last session review.
2. Model insights and Backtests screens.
3. Light mode.
4. Telegram alerts beyond failure alerts.
5. Landing page animation.
6. News features, if the ablation shows they add nothing.

Never cut the cost model, the leakage tests, the baseline comparison or the disclaimers.

## After launch

- Long-trade strategies using daily features.
- A paid data upgrade if the free history proves too short.
- A VPS for unattended runs.
- More users, which needs sign-in and a legal check on sharing recommendations.
- Broker execution, only after rechecking exchange and SEBI rules.

## Open questions

1. How many hours a week can you really spend? The timeline scales directly with it.
2. Do you want to start with the model first and build the app later, or follow this order?
3. Which Angel One account will you use for data?
