# Kairos

**Kairos** is an ML-assisted intraday trading research and recommendation system designed for Indian equities (NSE Cash / MIS segment, 09:15 to 15:30 IST).

> **Disclaimer & Operational Scope:**
> Kairos is strictly a personal research and paper trading project. Version 1 does **not** connect to broker execution APIs, does **not** trade real money, and does **not** guarantee profitability or risk-free returns. All recommendations must be validated through rigorous backtesting and paper trading before any capital is considered.

---

## Why this demo only shows past days

Sharing live buy or sell ideas with the public in India can require registration with SEBI as a research analyst or investment adviser. Kairos is a learning project and is not registered, so this demo replays historical days only. Nothing here is investment advice.

---

## Monorepo Architecture

```text
kairos/
├── apps/
│   ├── api/             # FastAPI backend REST service and SSE stream
│   └── web/             # Next.js web application (TypeScript, Tailwind, Plotly)
├── packages/
│   └── core/            # kairos_core: Shared quantitative logic, indicators, cost models, and risk rules
│       ├── kairos_core/ # Core Python package source
│       └── tests/       # Unit tests for core trading logic
├── workers/             # Background ingestion, candidate generation, and scoring tasks
├── ml/                  # Machine learning research and offline pipelines
│   ├── datasets/        # Parquet training datasets (git-ignored)
│   ├── training/        # Model training and Optuna tuning scripts
│   ├── evaluation/      # Purged walk-forward validation and SHAP analysis
│   └── notebooks/       # Jupyter research and verification notebooks
├── infra/               # Docker Compose infrastructure (TimescaleDB, Redis)
├── scripts/             # Operational and maintenance automation scripts
├── docs/                # Architecture, PRD, and system design specifications
├── .env.example         # Environment configuration template
├── .gitignore           # Git ignore rules for secrets, datasets, and caches
├── pyproject.toml       # Centralized Python package and tooling configuration
└── README.md            # Project overview and setup instructions
```

---

## Prerequisites

Ensure the following tools are installed on your Windows machine:

| Tool | Minimum Version | Check Command |
| :--- | :--- | :--- |
| **Python** | 3.11+ | `python --version` |
| **Node.js** | 20+ | `node -v` |
| **Docker Desktop** | Latest | `docker --version` |
| **Git** | 2.40+ | `git --version` |

---

## Quickstart Setup Guide (Windows / PowerShell)

### 1. Configure Local Environment Variables
Create your local `.env` configuration file from the template:
```powershell
Copy-Item .env.example .env
```
> **Security Note:** `.env` is ignored by Git and should never be committed. No broker or AI keys are required for Phase 0 setup or testing.

### 2. Set Up Python Virtual Environment
Create and activate an isolated Python virtual environment:
```powershell
# Create virtual environment in .venv
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```

*Note:* If PowerShell blocks script execution, run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3. Install Development Tooling
Install the project in editable mode with development dependencies (`pytest` and `ruff`):
```powershell
pip install --upgrade pip
pip install -e ".[dev]"
```

### 4. Start Local Infrastructure (Docker)
Start the PostgreSQL / TimescaleDB and Redis containers in the background:
```powershell
docker compose -f infra/docker-compose.yml up -d
```

Verify service status and health:
```powershell
docker compose -f infra/docker-compose.yml ps
```

To view live container logs:
```powershell
docker compose -f infra/docker-compose.yml logs -f
```

To stop containers:
```powershell
docker compose -f infra/docker-compose.yml down
```

To reset containers and wipe local volumes (warning: deletes all stored database data):
```powershell
docker compose -f infra/docker-compose.yml down -v
```

---

## Running Verification & Tests

### Run Unit Tests
Execute the test suite using `pytest`:
```powershell
pytest
```

### Run Code Quality & Linter
Run `ruff` for code inspection and format checks:
```powershell
# Lint check
ruff check .

# Format check
ruff format --check .

# Auto-fix lint issues and format
ruff check --fix .
ruff format .
```

---

## Troubleshooting & Common Issues

* **PowerShell script activation blocked:**
  Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` and re-run `.\.venv\Scripts\Activate.ps1`.
* **Docker daemon connection error (`cannot find the file specified`):**
  Ensure Docker Desktop is launched and running on Windows.
* **Database port conflict (5432) or Redis port conflict (6379):**
  Check if a local PostgreSQL or Redis instance is already running on your machine via `netstat -ano | findstr :5432` and update the port mapping in `.env` if needed.

---

## Documentation

Comprehensive product and engineering documentation is maintained in the [`docs/`](docs/) directory:

* [PRD: ML-Based Intraday Trade Recommender](docs/PRD%20ML-Based%20Intraday%20Trade%20Recommender.md)
* [Tech Stack and System Architecture](docs/Tech%20Stack%20and%20System%20Architecture.md)
* [Design Doc: Landing Page and App Shell](docs/Design%20Doc%20Landing%20Page%20and%20App%20Shell.md)
* [Kairos: Build Plan](docs/Kairos%20Build%20Plan.md)