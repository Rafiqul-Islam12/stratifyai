# StratifyAI
# The Liquidity Decision Lab for SME Financial Intelligence

*2026 Shenzhen International FinTech Competition - International Track, Topic E: SME Finance Copilot*

> **Synthetic data only. Not financial advice.** Financing terms are illustrative templates, not real lender offers.

## Try it in 60 seconds

```bash
python run.py setup
python run.py demo
```

Then open the URL printed in the terminal, click **Load demo business**, and open the **Liquidity Decision Lab**.

| Command | What it does |
| --- | --- |
| `python run.py setup` | create the venv, install requirements, seed `.env` |
| `python run.py demo` | setup if needed, start the app and open the browser |
| `python run.py start` | start the app on `http://127.0.0.1:8501` |
| `python run.py test` | run `pytest -q` |
| `python run.py status` | task progress, recent commits, test result |
| `python run.py check` | health check (imports, data, fonts, secrets, audit chain) |
| `python run.py eval` | evaluation run (built by T15) |

Python 3.11+. No CDN and no external fonts: the demo runs fully offline.

## What StratifyAI does

For an SME owner: forecasts weekly cash, detects the shortage week, then compares four plans in the Liquidity Decision Lab - do nothing, collect and optimise, finance only the remaining gap, finance the full gap. Code computes every number; the AI only explains.

## Status

Scaffolded - task **T01**. Feature work starts at T02 (design system) and T03 (synthetic data). See `docs/PLAN.md`.

## Documentation

| File | Contents |
| --- | --- |
| `docs/BRIEF.md` | condensed product brief |
| `docs/DESIGN.md` | design system (single source of truth for UI) |
| `docs/DECISIONS.md` | formulas, defaults and assumptions |
| `docs/SECURITY.md` | permission tiers, roles, known risks |
| `docs/COMPETITION.md` | competition facts |
| `docs/PLAN.md` | task plan |
| `docs/CHECKLIST.md` | coverage matrix |

Demo accounts are labelled **DEMO**. No real payments, loans or bank connections exist in this system.
