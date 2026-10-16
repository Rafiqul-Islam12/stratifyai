# PROGRESS

Current task: T01 (done)
Last updated: 2026-10-17

## In progress (checkpoints; one line per finished sub-step, cleared when the task is done)
(none)

## Done
- **T01 Scaffold, tooling, run.py launcher, CI, status script** (2026-10-17)
  - Folder skeleton: core/, services/, app/pages/, data/, tests/, scripts/, evidence/, static/fonts/, docs/img/, .streamlit/, .github/workflows/
  - `run.py` launcher (stdlib only): setup, start, demo, test, eval, check, status, report
  - `requirements.txt` + `requirements-dev.txt` pinned: streamlit 1.66.0, pandas 3.0.6, numpy 2.4.6, plotly 7.1.0, pydantic 2.14.1, pytest 9.1.1, openpyxl 3.1.5, ruff 0.17.1
  - `scripts/status.py`, `scripts/check_secrets.py`, `.env.example`, `.github/workflows/ci.yml` (Python 3.11 + 3.12)
  - `app/main.py` minimal scaffold page, `tests/test_smoke.py` (9 tests), `README.md` stub
  - Verified: `setup`, `test` (9 passed), `check` (exit 0), `status`, `start` serves on 127.0.0.1:8501 (Health: ok)
  - No git remote `origin` - local commits only (asked the user)

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
- The competition PDF in docs/inputs/ could not be read on this machine (no poppler, no PDF library; the file has no /ToUnicode CMap). docs/COMPETITION.md is therefore unverified against the PDF - verify by hand before submission.
- `python run.py start` leaves the server running in its terminal (normal Streamlit behaviour); stop with Ctrl-C.
- data/, evidence/ and static/fonts/ hold only .gitkeep until T02/T03.

## Decisions or assumptions changed (details in DECISIONS.md)
- Streamlit pinned to 1.66.0 rather than ">= 1.45" so the demo is reproducible (>= 1.45 was the stated floor for self-hosted fonts).
