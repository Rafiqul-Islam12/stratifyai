# PROGRESS

Current task: T04 (next)
Last updated: 2026-10-18

## In progress (checkpoints; one line per finished sub-step, cleared when the task is done)


## Done
- **T01 Scaffold, tooling, run.py launcher, CI, status script** (2026-10-17)
  - Folder skeleton: core/, services/, app/pages/, data/, tests/, scripts/, evidence/, static/fonts/, docs/img/, .streamlit/, .github/workflows/
  - `run.py` launcher (stdlib only): setup, start, demo, test, eval, check, status, report
  - `requirements.txt` + `requirements-dev.txt` pinned: streamlit 1.66.0, pandas 3.0.6, numpy 2.4.6, plotly 7.1.0, pydantic 2.14.1, pytest 9.1.1, openpyxl 3.1.5, ruff 0.17.1
  - `scripts/status.py`, `scripts/check_secrets.py`, `.env.example`, `.github/workflows/ci.yml` (Python 3.11 + 3.12)
  - `app/main.py` minimal scaffold page, `tests/test_smoke.py` (9 tests), `README.md` stub
  - Verified: `setup`, `test` (9 passed), `check` (exit 0), `status`, `start` serves on 127.0.0.1:8501 (Health: ok)
- **T02 Design system and app shell** (2026-10-17)
  - App shell, theme, shared components and charts are implemented in commit `9f1387a`.
  - Per the user's direction, font sizing, alignment, vertical text placement, and card text/layout are deferred to T14 cross-page polish.
- **T03 Synthetic data and schema** (2026-10-18)
  - Added typed Pydantic schemas and a loader for transactions, receivables, payables, profiles and assumptions.
  - Added a fixed-seed generator for five synthetic cases, with 39 weeks of transaction history, 10 synthetic customers, 6 synthetic suppliers and labelled case folders.
  - Generated all five cases; validated each case through the typed loader and confirmed repeat generation produces identical hashes.
  - Verified: `pytest -q` (33 passed), `python scripts/check_secrets.py` (no matches in 109 files); focused data tests (7 passed).
  - Local checkpoint commit: `10c8c6c`.

## How to run
```
python run.py setup     # create .venv, install pinned deps, seed .env
python run.py demo      # setup if needed, then start and open the browser
python run.py test      # pytest -q
python run.py status    # tasks done, current task, last commits, tests
python run.py check     # health: imports, data, fonts, copilot mode, audit chain, .env
python run.py eval      # not built yet (T15)
python run.py report    # not built yet (T15)
```
Streamlit page is `app/main.py`, served on `http://127.0.0.1:8501`.
Python 3.11.9 in `.venv`; no CDN and no external fonts.
Secret scan: `python scripts/check_secrets.py` (exit 0 = clean).

## Known issues
- T02 visual follow-up deferred at the user's direction: font sizing, alignment, vertical text placement, and card text/layout need review and correction during T14 cross-page UI polish. T02 shell is implemented; the user confirmed all 10 pages are clickable and show content, with these visual issues remaining.
- The competition PDF in docs/inputs/ could not be read on this machine (no poppler, no PDF library; the file has no /ToUnicode CMap). docs/COMPETITION.md is therefore unverified against the PDF - verify by hand before submission.
- `python run.py start` leaves the server running in its terminal (normal Streamlit behaviour); stop with Ctrl-C.
- evidence/ holds only .gitkeep until related later tasks; static/fonts/ has no Inter files, so the system fallback stack is active.

## Decisions or assumptions changed (details in DECISIONS.md)
- Streamlit pinned to 1.66.0 rather than ">= 1.45" so the demo is reproducible (>= 1.45 was the stated floor for self-hosted fonts).
