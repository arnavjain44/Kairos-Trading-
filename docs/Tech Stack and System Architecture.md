# Tech Stack and System Architecture

## Overview

This doc defines how the intraday trade recommender is built: architecture, tech stack, data model, APIs, the AI gateway, deployment and build order. It implements the PRD and serves the front end described in the design doc.

Constraints that shape every choice:

- Version 1 recommends trades and never places orders.
- The working amount is a few thousand rupees, so running costs must be close to zero.
- Data and AI run on free tiers wherever possible, with a cheap paid upgrade path.
- A small team, one user now, more users later.
- Every model decision must be logged so it can be checked on a chart.

This is a personal learning project. The live engine runs on your own machine; what the public sees is a replay demo on historical days, hosted on free tiers.

## Key decisions

| Decision | Choice | Why |
| --- | --- | --- |
| Overall shape | Modular monolith plus background workers | One codebase is easier to build, debug and deploy than microservices, and nothing here needs independent scaling yet |
| Main language | Python for backend and ML, TypeScript for the web app | The ML libraries live in Python; one language for the backend avoids translation |
| Shared core | One package for features, labels, models, costs and sizing | The backtester and the live path run the same code, so backtest results are honest |
| Database | PostgreSQL with TimescaleDB | Time-series candles and ordinary relational data in one place |
| Prediction log | Append-only table of every prediction, with the later true label and outcome | Powers verification charts, performance views and the AI assistant |
| Market data | Behind an adapter, Angel One SmartAPI first | Switching to another source is a one-file change |
| AI | A gateway that routes across free-tier providers, Groq first | Free, with automatic failover when a provider hits its limit |
| Orders | Not in version 1 | Recommendation only; avoids order-placement rules and risk |
| Hosting | Live engine on your own machine with Docker Compose; public replay demo on Vercel | No server to rent for a personal project; a VPS can run the same Compose stack later if unattended runs are wanted |

## System architecture

The web app talks to the API service over HTTPS, with live updates pushed from the API. The workers do the heavy lifting: they pull market data and news, compute features, score candidates and write predictions to the database. External sources feed the backend; alerts and AI calls go out from it.

&#91;embedded content: system architecture · web app, backend, state, external sources\]

| Component | Responsibility | Technology |
| --- | --- | --- |
| Web app | Landing page, dashboard, verification charts, AI panel | Next.js, TypeScript, Tailwind, Plotly.js, on Vercel |
| API service | REST endpoints, auth, live push, serves plans, chart data, performance and assistant | FastAPI, Uvicorn, Pydantic |
| Workers | Data and news ingestion, features, candidate generation, scoring, sizing, labelling, backtests | Python with Arq on Redis |
| Scheduler | Pre-market, market-hours, post-close (including optional Last session review export), and weekly jobs; exchange holiday calendar | APScheduler in its own container |
| Core package | Features, labels, models, cost model, allocator | Python package shared by all services |
| Database | Candles, features, predictions, outcomes, news, users | PostgreSQL with TimescaleDB |
| Cache and queue | Live signals, job queues, rate-limit counters | Redis |
| Object storage | Parquet datasets and model files | S3-compatible storage (Cloudflare R2 or similar); local disk at first |
| Market data adapter | Candles, quotes, instrument list | Angel One SmartAPI, with a second adapter for Dhan or Upstox |
| News adapter | Headlines and exchange announcements | RSS feeds, NSE and BSE announcement pages |
| AI gateway | Summaries and assistant replies across several free providers | LiteLLM router or a thin custom module |
| Alerting | Entry, exit and failure alerts | Telegram bot |

## Daily data flow

The system runs on the market's clock. Every step writes to the database, so each day can be replayed.

&#91;embedded content: daily cycle · four phases\]

- **Pre-market:** filter the stock universe, compute daily features and gaps, ingest and score overnight news.
- **Live session:** stream candles; at each bar close compute features, generate candidates, score them, size trades to the amount, and push the plan and alerts.
- **After close:** compute true labels and realised outcomes, P&L after costs, the daily report, drift checks, and the optional Last session review export (runs only if enabled and guarded to finished sessions).
- **Weekly:** retrain with walk-forward validation and promote the new model only if it beats the current one.

## Tech stack

| Layer | Choice | Alternatives |
| --- | --- | --- |
| Web framework | Next.js with TypeScript | Vite and React |
| Styling | Tailwind CSS, shadcn/ui components | Any component library |
| Charts | Plotly.js for verification charts | TradingView Lightweight Charts for live candles |
| API | FastAPI | Django REST |
| Auth | Auth.js with email and Google sign-in; API verifies the token | Clerk, Supabase Auth |
| Jobs and queue | Arq on Redis; APScheduler for time-based jobs | Celery, Prefect |
| Database | PostgreSQL with TimescaleDB | Plain PostgreSQL with partitioning |
| Cache | Redis | None at first |
| Datasets | Parquet files read with DuckDB or Polars | Postgres tables only |
| ML | LightGBM or XGBoost, scikit-learn, Optuna, SHAP | CatBoost |
| Experiment tracking | MLflow with a local backend | Weights and Biases free tier |
| Indicators | pandas-ta or TA-Lib | Hand-written functions |
| Sentiment | FinBERT through Hugging Face transformers, on CPU | LLM scoring through the gateway |
| AI summaries and assistant | AI gateway over Groq, Cerebras, Mistral, Gemini, OpenRouter | Single provider |
| Monitoring | Sentry, Grafana with Prometheus, uptime check | Hosted logging free tier |
| Containers | Docker and Docker Compose | Kubernetes, not needed |
| CI | GitHub Actions | None |
| Reverse proxy and TLS | Caddy | Nginx |

## Data model

Market and model tables are global. Anything personal carries a user id from day one, so adding users later is not a rewrite.

| Table | Key columns | Notes |
| --- | --- | --- |
| instruments | symbol, exchange, token, lot data, status, eligibility flags | Refreshed daily from the broker instrument file |
| candles\_1m | symbol, time, open, high, low, close, volume | Timescale hypertable, compressed; 5 and 15-minute views built as continuous aggregates |
| daily\_prices | symbol, date, OHLCV, adjustment factor | Corporate-action adjusted |
| news\_items | id, source, published time, symbol links, headline, body hash | Stored with publication time for leakage control |
| news\_scores | news id, sentiment, event type, novelty, model version | Written by FinBERT |
| ai\_summaries | content hash, summary, provider, created time | Cache so each article is summarised once |
| model\_versions | id, created time, training window, metrics, artifact path, status | Status: candidate, active, retired |
| predictions | id, time, symbol, side, probability, expected net gain, model version, feature snapshot | Append-only |
| outcomes | prediction id, true label, exit time, exit reason, realised return after costs | Filled after close |
| trade\_plans | id, user id, date, amount, settings, ranked trades | What each user was shown |
| user\_settings | user id, risk per trade, max trades, direction, theme | One row per user |
| alerts | id, user id, trade plan id, type, sent time, channel | Delivery log |
| llm\_usage | provider, model, time, tokens, status, latency | Feeds rate-limit tracking and cost review |

## API design

Versioned under /api/v1, JSON throughout, Pydantic schemas shared with the web app, and server-sent events for live updates (one-way push is all the UI needs, so WebSockets are not required).

| Method and path | Purpose |
| --- | --- |
| POST /plans | Create today's plan from an amount and settings; returns ranked trades |
| GET /plans/{id} | Fetch a plan with its trades |
| GET /recommendations | Current ranked list for the user's latest plan |
| GET /trades/{id} | One trade with levels, probability and reasons |
| GET /charts/{symbol} | Candles, indicators, signals, labels and news flags for a day and timeframe |
| GET /predictions | Filtered prediction log with outcomes |
| GET /performance | Equity, drawdown, calibration, long vs short, regime breakdown |
| GET /news/{symbol} | Scored headlines with summaries |
| GET /model/insights | Feature importance and per-trade explanations |
| POST /assistant/messages | Assistant reply, streamed |
| GET and PUT /settings | User settings |
| GET and POST /alerts | Alert rules and history |
| GET /status | Market status, data freshness, active model, kill-switch state |
| GET /stream | Server-sent events for plan updates, trade status and alerts |

Conventions: cursor pagination for lists, one error shape with a code and message, idempotency keys on POST /plans, and per-user rate limits on the assistant.

## ML pipeline

1. **Feature building:** the shared core computes price, volume, volatility, context, time and news features from closed bars only.
2. **Labelling:** triple-barrier labels (target, stop, time exit at 15:15) written to the outcomes table after close.
3. **Training:** gradient boosting trained on a rolling window with purged, embargoed walk-forward splits; Optuna tunes parameters; probabilities are calibrated.
4. **Evaluation:** net value per trade after costs, profit factor and top-3 precision, compared against the rule-only baseline.
5. **Registry:** MLflow stores runs and artifacts; a model is promoted only if it beats the active model on untouched recent data.
6. **Serving:** the active model loads inside the workers and scores in-process, so there is no separate model server to run.
7. **Monitoring:** feature drift, calibration drift and live hit rate are checked daily; a breach raises an alert and can switch the system to baseline-only mode.

## AI gateway

AI is used only to summarise news and phrase explanations from data already in the database. It never produces numbers, and sentiment scoring stays on local FinBERT, so quota use is small.

&#91;embedded content: AI gateway · provider fallback chain\]

**Providers (free tiers, verified by web search in October 2026; limits change, so read each provider's console):**

| Order | Provider | Free-tier notes |
| --- | --- | --- |
| 1 | Groq | Sample limits for text models: about 30 requests a minute, 1,000 a day, 8,000 tokens a minute and 200,000 tokens a day, applied per organisation |
| 2 | Cerebras | Roughly 30 requests a minute and about 1M tokens a day; sources differ, so check |
| 3 | Mistral | Free tier with a large monthly token allowance but only a few requests a minute |
| 4 | Google Gemini (AI Studio) | Free limits vary by model and are shown only in the console |
| 5 | OpenRouter free models | Tight daily request cap without purchased credit |
| 6 | No-model fallback | Show the original headline or a simple extractive summary |

**Rules:**

- One account per provider. Extra keys on the same account share its quota, and creating several accounts to multiply quota is likely against terms.
- Providers, models and limits live in config, not code, because free tiers change and models get removed.
- Per-provider counters for requests and tokens per minute and per day, updated from rate-limit headers in responses.
- On a rate-limit error, honour the retry-after time, put that provider on cooldown, and move to the next one; a circuit breaker skips providers that keep failing.
- Two lanes: chat gets priority; bulk news summaries run as background jobs that can wait.
- Summaries are cached by content hash, so each article is summarised once for all users.
- Every model is asked for the same JSON shape, and replies are validated before use.
- Only public news text and aggregated model output are sent to providers; no personal data.

## Market data and news adapters

- **Interface:** get instruments, get historical candles, subscribe to live quotes, and report data freshness. Nothing else in the system imports a broker library.
- **Angel One adapter:** needs a daily automated login with a time-based code, with alerts if login fails; candles are stored as they arrive.
- **Backups and swaps:** a second adapter (Dhan Data API as the paid option, or Upstox) can be turned on in config; daily files from NSE are used for end-of-day checks.
- **Calendar:** an NSE holiday calendar drives the scheduler; times are stored in UTC and shown in IST.
- **Validation:** reject out-of-order or duplicate bars, fill small gaps, and flag stale feeds, which pause recommendations.
- **News adapter:** polls RSS feeds and exchange announcement pages, deduplicates, stores publication time, and queues scoring.

## Deployment and infrastructure

- **Web app:** the public demo is deployed on Vercel from the main branch; the free plan is meant for personal projects, so check its terms if this ever becomes commercial.
- **Backend:** runs on your own laptop with Docker Compose (api, worker, scheduler, postgres, redis); 8 GB of memory or more is comfortable for FinBERT on CPU. Keep the laptop awake from about 09:00 to 15:30 IST on trading days for live runs. A small VPS can run the same stack later for unattended runs.
- **Environments:** local with the same Compose file, and production; staging added once there are users.
- **Backups:** regular copies of the database and model files to cloud storage or an external drive, with a restore test now and then.
- **Secrets:** environment files kept out of the repository, with a secrets manager once there is a team.
- **Time:** server clock synced, all schedules defined in IST with a holiday calendar.

## Public demo deployment

The public version is a Replay mode demo on historical days, not the live system. Visitors pick a past date and an amount, and see the plan the model produced that day, the verification charts and the results after costs.

| Piece | Approach |
| --- | --- |
| Demo data | An export job writes the plan, candles, signals, true labels, outcomes, news flags, news summaries and performance numbers for chosen past dates to static JSON or Parquet files |
| Last session review | Optional export job that runs after the close, once outcomes are computed, exports the previous session as static JSON files, and commits them so Vercel redeploys. Feature flag LAST_SESSION_ENABLED (default false) and a configurable publish delay (default: after close, same evening). Includes a guard in the export that refuses to publish any data for a session that has not finished |
| Hosting | Next.js app on Vercel's free plan, with the data served as static files or from a free hosted database such as Neon or Supabase |
| Python parts | None needed in the public version; if one is wanted, a small free service on Render or Hugging Face Spaces, with a loading state because free services sleep when idle |
| AI assistant | Groq key kept on the server, a per-visitor request limit, cached answers, and pre-written summaries as the fallback when limits are hit |
| Labelling | A banner on every page: educational demo on historical data, not investment advice |
| Not public | The live engine, the broker data login, live recommendations and any API keys |

Why Replay mode instead of live: sharing live buy or sell ideas with the public in India can require registration with SEBI as a research analyst or investment adviser. Kairos is a learning project and is not registered, so this demo replays historical days only. Nothing here is investment advice. In addition, the live engine holds a broker login that should not sit on a public server, and a live demo breaks whenever the market is closed or a free quota runs out.

**Repository checklist:** a README with the architecture diagram, how the model works and how to run it; a results page showing backtest and paper results with costs, including what did not work; a short screen recording; keys in environment variables with .env ignored by git; and a seed script that loads the demo data.

Free-tier terms change, so check each provider's limits before deploying.

## Security

- HTTPS everywhere, with TLS handled by Caddy.
- Auth tokens verified on every API call; user data filtered by user id.
- Broker login credentials and the time-based login secret stored encrypted and never logged.
- Rate limits on public endpoints and a strict limit on the assistant.
- Dependency and container scanning in CI.
- Audit log of settings changes and plan generation.
- Compliance: sharing live buy or sell ideas with the public in India can require registration with SEBI as a research analyst or investment adviser. Kairos is a learning project and is not registered, so this demo replays historical days only. Nothing here is investment advice. No live or same-day-in-progress data is ever published; anything shared publicly must be finished, historical data. Last session review remains off by default behind LAST_SESSION_ENABLED.

## Observability and reliability

| Area | What we watch | Action |
| --- | --- | --- |
| Data freshness | Age of latest candle during market hours | Pause recommendations and alert past a threshold |
| Job health | Scheduler and worker heartbeats, queue length | Telegram alert on missed runs |
| Model health | Drift, calibration and live hit rate | Switch to baseline-only mode and alert |
| API health | Latency, error rate, plan generation time (target under 10 seconds) | Dashboards and alerts |
| AI gateway | Provider errors, cooldowns, daily quota use | Fail over; alert if all providers are down |
| Kill switch | Manual toggle and automatic triggers | Banner in the app, recommendations paused |

Structured logs with a request id, errors to Sentry, and a short runbook for each alert.

## Testing and delivery

- **Unit tests:** features, labels and the allocator, including tests that fail if a feature uses data from after the signal time.
- **Regression tests:** a fixed historical day must reproduce the same predictions.
- **Adapter tests:** recorded responses for the data and news adapters.
- **API tests:** schema and auth checks.
- **CI:** GitHub Actions runs lint, types and tests on every pull request, builds images, and deploys to the VPS on merge to main.
- **Repo layout:** one monorepo with apps/web, apps/api, workers, packages/core, ml and infra.

## Cost

| Item | Cost |
| --- | --- |
| Market data (Angel One) | Free with an account |
| News feeds | Free |
| AI providers | Free tiers |
| Web hosting | Vercel free plan to start; check terms if commercial |
| VPS | Not needed for a personal project; add one only for unattended runs |
| Domain | Small yearly cost |
| Optional data upgrade | Dhan Data API at ₹499 plus GST a month, only if free history proves too short |

## Build order

| Phase | Deliverables | Matches PRD phase |
| --- | --- | --- |
| 1. Foundations | Monorepo, Compose stack, database schema, market data and news adapters, holiday calendar, cost model | Data and costs |
| 2. Research loop | Core features and labels, rule-based baseline, backtester, first charts | Baseline backtest |
| 3. Model | Feature set with news, triple-barrier training, walk-forward validation, MLflow registry | ML model |
| 4. Product | API, web app shell, plan generation, verification charts, AI gateway, alerts, paper results, replay-data export and public demo | Recommender and paper trading |
| 5. Live use | Monitoring, backups, kill switch, daily reports, real-money use with manual orders | Live, manual orders |
| 6. Later | Long-trade strategies, multi-user hardening, optional broker execution | Long trades |

## Risks and open questions

| Risk | Mitigation |
| --- | --- |
| Free data login breaks or the feed goes stale | Alerts, a second adapter, and pausing recommendations when data is stale |
| Free AI limits change or models disappear | Config-driven provider list, several providers, and a no-model fallback |
| Single VPS failure during market hours | Backups, quick-restore script, and a clear runbook; a second node only if the product grows |
| Prediction log grows large | Compression, retention rules, and moving old data to Parquet |
| Model degrades quietly | Daily drift checks and an automatic baseline-only mode |
| Public AI key abused or free quota used up by visitors | Key kept on the server, per-visitor limits, cached answers, and pre-written summaries as the fallback |
| Last session export published too early or by mistake | Mitigation: feature flag off by default, time guard in the export job, secrets scan before every push |

**Open questions**

1. Should the public demo use Vercel alone with static data, or Vercel plus a small free Python service?
2. Does the public demo need sign-in, or can it be open to anyone with request limits on the AI assistant?
3. Is Telegram acceptable for alerts, or do you also want email and push notifications?
4. Who deploys and maintains the system day to day?
