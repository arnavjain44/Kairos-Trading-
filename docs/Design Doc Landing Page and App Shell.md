# Design Doc: Landing Page and App Shell

## Overview

This doc covers two surfaces for the intraday trade recommender described in the PRD: a public landing page, and the app behind it. The landing page explains the product and sends people into the app. The app is a plain black-and-white interface with every feature listed in a side navigation, and a main dashboard area where each feature and the AI assistant open.

User path: landing page, then sign in, then the app dashboard, where the user enters an amount and receives the day's ranked trade plan.

**Reference:** the screenshots you shared show a dark landing page with a green glow, a large two-line hero headline, a strip of candlesticks along the bottom of the hero, pill buttons, a ruled grid of big numbers, a split story section and a scrolling price ticker. The landing page below takes that layout and mood; the wording, brand, figures and artwork are original to this product.

## Design principles

- **Black and white app, dark landing page.** The app is monochrome and opens in dark mode, with a light option, and colour is reserved for data: gains, losses and chart markers. The landing page is dark with one green accent, so it feels like the product's own charts.
- **Data over decoration.** Numbers, charts and trade cards are the visual centre; there are no stock illustrations.
- **One clear action per screen.** Landing: open the app. Dashboard: get today's plan.
- **Honest by default.** "No trade today" is a valid result, nothing is called guaranteed, and sample data is always labelled as sample.
- **Verifiable.** Every recommendation links to its chart, so the user can check the model against reality.

## Visual system

| Token | Value | Use |
| --- | --- | --- |
| Background | #FFFFFF | Page and app background |
| Surface | #F6F6F6 | Sidebar, cards, input fields |
| Border | #E2E2E2 | Dividers and card outlines |
| Text | #0A0A0A | Primary text |
| Text muted | #6B6B6B | Secondary text and labels |
| Inverse | #0A0A0A with #FFFFFF text | Primary buttons, selected navigation item, footer band |
| Gain | #1B7F4B | Profit and long trades, always paired with + or an up arrow |
| Loss | #C4302B | Loss and short trades, always paired with a minus or a down arrow |

The app opens in dark mode, using the dark tokens from the landing page theme below with grey instead of green for everything except data. Light mode uses the tokens in this table, with the gain and loss colours adjusted slightly for contrast in each mode. Users switch themes from the top bar or Settings, and the choice applies to the charts too. Chart colours follow the verification chart spec in the PRD.

**Typography:** Inter for interface text; a monospaced or tabular-figure face for prices and quantities so columns align. App body text 14 px; landing body 16 px; hero headline 56 px on desktop and 36 px on mobile.

**Shape and spacing:** 8 px spacing grid, 8 px corner radius on cards and inputs, 1 px borders instead of shadows, 12-column layout with 24 px gutters.

**Core components:** primary button (black, white text), secondary button (white, black border), trade card, stat tile, side-navigation item, side badge (LONG or SHORT), status pill (market open or closed), chart panel, AI message bubble, toast and banner.

**Landing page theme (dark, following your reference)**

| Token | Value | Use |
| --- | --- | --- |
| Page background | #07090A | Whole landing page |
| Surface | #101413 | Cards, stat cells, pills |
| Border | #1E2522 | Grid lines and outlines, 1 px |
| Text | #F2F5F3 | Headlines and body |
| Text muted | #8A948F | Supporting copy and labels |
| Accent green | #4ADE80 | Tinted headline words, arrows, plus signs, gains, candle highlights |
| Loss red | #F0605D | Negative moves in the ticker |
| Glow | Soft radial green at 15 to 25% opacity | Behind the hero and one or two other sections |

Typography on the landing page: a light-weight geometric sans at large sizes (hero 72 px with 76 px line height on desktop, 40 px on mobile), with the second half of the headline tinted green. Buttons are pills: the primary is white with a small green circular arrow chip, the secondary is dark with a thin outline.

## Landing page

Sections, top to bottom:

| # | Section | Content |
| --- | --- | --- |
| 1 | Top bar | Logo, links to How it works, Features, FAQ, a GitHub link, and an Open demo pill button |
| 2 | Hero | A small tag pill above a two-line headline such as "Intraday trade ideas / sized to your amount", with the second line tinted green; one supporting sentence; two pill buttons (Open app, See how it works); a slow-drifting strip of green and outlined candlesticks along the bottom with grid lines and faint particles behind it; a vertical "Scroll to explore" label at the right edge |
| 3 | Market ticker | A scrolling band of pills for NIFTY, BANKNIFTY and top movers, with up moves in green and down moves in red; labelled as delayed if the feed is delayed |
| 4 | What it is | Split section: a large statement on the left (for example "Your amount. Your plan.") over a faint glowing graphic, and on the right a small "What is the product?" pill with two short paragraphs |
| 5 | How it works | Four steps: enter your amount, get a ranked plan, verify on the chart, review at close |
| 6 | Features | Six cards: amount-based sizing, long and short ideas, news and sentiment, verification charts, AI assistant, risk limits and daily review |
| 7 | Numbers | A ruled grid of big numbers with a green plus sign, showing product facts such as stocks scanned each day, signals scored per day and features per decision. Verified results are added only after the go-live gates in the PRD pass; no earnings or payout claims |
| 8 | Chart showcase | A large candlestick chart showing model signals against true outcomes, with a caption explaining the markers, labelled as sample data |
| 9 | Why replay, not live | Heading: "Why this demo only shows past days". Body: "Sharing live buy or sell ideas with the public in India can require registration with SEBI as a research analyst or investment adviser. Kairos is a learning project and is not registered, so this demo replays historical days only. Nothing here is investment advice." Small outlined card with a muted info icon (green only on the icon) |
| 10 | AI assistant | A short sample conversation, such as asking why a trade was picked |
| 11 | Risk and FAQ | Plain-language risk and disclosure statement, and seven questions: what amount works, how trades are chosen, long and short, how news is used, what it costs, "Is this live?" (no, it replays past trading days from saved data; the live engine runs only on the builder's own machine), and "Why can't I see today's trades?" (Sharing live buy or sell ideas with the public in India can require registration with SEBI as a research analyst or investment adviser. Kairos is a learning project and is not registered, so this demo replays historical days only. Nothing here is investment advice.) |
| 12 | Final call to action and footer | Open demo pill button, legal links, GitHub and LinkedIn links |

The Open app button goes to sign in, then to the dashboard. Copy avoids profit promises and return figures.

**Motion:** the candle strip drifts slowly, the ticker scrolls, and the glow shifts subtly with scroll. All motion stops for users who have reduced motion turned on, and the page stays readable without it.

&#91;embedded content: landing page wireframe · 11 sections (needs redrawing for 12 sections to include the "Why replay, not live" card between Chart showcase and AI assistant)\]

## App shell

**Layout:** a fixed left sidebar (240 px, collapsible to a 64 px icon rail), a top bar (56 px), and a main area that holds the selected feature. The AI assistant is both a sidebar item and a panel docked to the right of the main area on the dashboard.

**Top bar:** market status pill with IST time, the amount field with an Update plan button, alerts bell, a light and dark theme toggle, and the user menu.

**Sidebar, grouped:**

| Group | Items |
| --- | --- |
| Today | Dashboard, Recommendations, Charts, Last session review (public demo only, hidden when the feature flag is off) |
| Research | Backtests, Performance, News and sentiment, Model insights |
| Assistant | AI assistant |
| Setup | Watchlist and universe, Alerts, Settings |
| Coming later | Long trades, Paper trading journal (shown disabled with a Soon badge) |

The selected item is filled black with white text; the rest are plain text with an icon.

&#91;embedded content: dashboard wireframe · sidebar, cards, chart, AI panel\]

## Feature screens

| Feature | What the main area shows | PRD link |
| --- | --- | --- |
| Dashboard | Stat tiles (amount, planned risk, trades, day result after costs), ranked trade cards, a chart of the selected trade, and the docked AI panel | FR1, FR5, FR6 |
| Recommendations | Full ranked list with side, quantity, entry, stop, target, probability, expected net gain, reasons, and a View on chart link per trade | FR4, FR6 |
| Charts | The verification chart: candles, overlays, signals, true labels, trade box, news flags, range slider | FR14 |
| Last session review | Previous trading day's plan, verification chart and outcomes, with a header "Last session review, [date]" and a note "Published after market close. A review of a finished day, not a recommendation." (public demo only, hidden when the feature flag is off) | FR17 |
| Backtests | Run history, settings, results, equity curve | FR7 |
| Performance | Equity and drawdown, calibration, long vs short, regime breakdown | FR15 |
| News and sentiment | Timeline of scored headlines and announcements per stock, with sentiment and event type | FR13 |
| Model insights | Feature importance and per-trade explanations | FR15 |
| AI assistant | Full-page conversation with history | See below |
| Watchlist and universe | Eligible stocks, price filter for the amount, exclusions | FR2 |
| Alerts | Entry, exit and time-exit alerts, and channel settings | FR10 |
| Settings | Default risk per trade, maximum trades, direction, theme | FR1 |

**Trade card contents:** symbol, LONG or SHORT badge, quantity, entry, stop, target, win probability, expected gain after costs, the top two reasons (one price signal, one news signal if present), and View on chart.

## AI assistant

- **What it does:** explains why a trade was picked using the model's outputs, summarises news for a stock, answers questions about performance, and explains chart markers.
- **What it never does:** place orders, promise outcomes, or invent numbers. If the model returns no trade, the assistant says so.
- **How it answers:** every figure comes from stored model output or data, shown with its time, and answers link to the relevant chart or card.
- **Placement:** a docked panel on the dashboard and a full page under the Assistant group. Suggested prompts appear in the empty state, such as "Why was this stock picked?" and "What changed since this morning?".
- **Disclosure:** a standing line under the input reminds users that responses are not investment advice.

## Key flows

1. **Get today's plan:** open the app, enter or confirm the amount, press Update plan, review ranked cards, open a card's chart.
2. **Verify a signal:** from a card, open the chart, compare the signal markers with the true labels, hover for probability and top features.
3. **During the session:** receive alerts for entry zones, stop, target and the 15:15 time exit; the dashboard shows each trade's live status.
4. **End of day review:** the dashboard shows what was recommended, what happened and the result after costs; the user can ask the AI to summarise the day.

## Demo (Replay mode)

The public version is a Replay mode demo on past trading days, so it works at any hour and never gives live recommendations. The live build stays on your own machine.

- **Top bar:** a "Demo: historical data" banner replaces the market status pill, with a "Why?" link that jumps to the "Why this demo only shows past days" explanation section, and a date picker sits beside the amount field, offering only dates that have saved results.
- **Update plan:** loads the saved plan for that date and amount; charts, performance, news and model insights are read-only views of saved data.
- **AI assistant:** works on the saved data, with a visible request limit and a pre-written summary shown when the limit is reached.
- **Live-only items:** Alerts and live settings show a short "Live mode only" note.
- **No sign-in:** visitors open the demo directly.
- **Footer on every page:** "Educational demo on historical data. Not investment advice."
- **Landing page:** the main button reads Open demo, and links to the GitHub repo and your LinkedIn sit in the top bar and footer.

## States and edge cases

| Situation | Behaviour |
| --- | --- |
| Market closed or pre-market | Status pill shows it; dashboard shows the previous day's review and the pre-market watch list |
| No trade passes the filters | A clear empty state: "No trade today", with the reason (for example costs exceed expected gain, or a high-volatility day) |
| Amount too small for any eligible stock | Message with the minimum workable amount |
| Data feed stale or kill switch on | Banner across the top, recommendations paused |
| Loading | Skeletons in the shape of cards and charts |
| Error | Inline message with a retry; the rest of the app keeps working |
| Demo mode, date without saved results | The date picker only offers dates with saved results, and a short note explains that this is a replay of past days |
| Last session review not yet published | Show the most recent published day |
| Last session review turned off | Item hidden |

## Responsive behaviour and accessibility

- **1280 px and wider:** full sidebar, docked AI panel.
- **768 to 1279 px:** sidebar collapses to the icon rail; the AI panel becomes a drawer.
- **Below 768 px:** a bottom tab bar with Dashboard, Recommendations, Charts, AI and More; charts scroll horizontally and offer a landscape view.
- **Accessibility:** WCAG AA contrast, gain and loss never shown by colour alone, full keyboard navigation with a visible 2 px black focus ring, and a data-table alternative for each chart.

## Compliance copy

The landing page footer and the app footer carry a risk statement: trading in securities involves risk of loss, the product provides model-generated ideas, results are not guaranteed, and it is not personal investment advice. Sharing live buy or sell ideas with the public in India can require registration with SEBI as a research analyst or investment adviser. Kairos is a learning project and is not registered, so this demo replays historical days only. Nothing here is investment advice. Last session review must stay off until the builder has checked the rules with a qualified person. If recommendations go to people other than you, SEBI registration may be required; confirm this before any public launch. Never display return claims on the landing page without verified live results.

## Build notes

- The landing page is a static page; the app is a single-page app at its own route, reached from the Open demo button and reading saved replay data in the public version.
- A React front end (for example Next.js with Tailwind) with Plotly.js charts fits this design; Streamlit would not reproduce the sidebar-and-dashboard layout well. The PRD tech stack row is updated to match.
- Charts and cards read from the same prediction store the PRD defines, so the landing page preview, dashboard and verification chart share one component.

The landing page effects (glow, drifting candles, scrolling ticker) use lightweight CSS and canvas, with a static fallback, so the page stays fast on mobile.

## Open questions

Decided:

- The app opens in dark mode by default, with a light mode option in the top bar and in Settings; the choice is remembered. Both ship in version 1.
- Green stays the accent.
- The public demo has no sign-in; the AI assistant has request limits.
- The landing page has no pricing and links to the GitHub repo and your LinkedIn.
- Should Last session review be turned on at launch? Default: off.

Product name: Kairos, chosen. The shortlist stays below for reference; domain, GitHub and trademark availability still need checking.

| Name | What it hints at | Tagline idea |
| --- | --- | --- |
| Kairos | Greek for the right moment | Trade ideas, timed to the day |
| Kestrel | A bird that hovers, watches, then acts once | Watch the day. Act once. |
| Gnomon | The pointer on a sundial that reads the time of day | Read the day |
| Meridian | The midpoint line the trading day crosses | Mapped to the day |
| Wick | The thin line on a candlestick | See the whole candle |

Logo idea: one green candlestick, simple enough to work as a browser icon; for Kairos, the candle's wick can form the stem of the K. Before choosing, check domain, GitHub and trademark availability, which has not been done.
