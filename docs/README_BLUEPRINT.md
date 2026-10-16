# GitHub README BLUEPRINT (T16 builds README.md from this; it is the first thing judges open)

Goal: look like a polished product page. Clean, scannable, honest. English. Use shields.io badges, GitHub-rendered Mermaid diagrams, tables, and screenshots from docs/img/ (the user captures them; list the exact file names needed in your T16 report). No emoji clutter, no marketing exaggeration, no unverified claims.

Sections in this order:
1. Title, tagline "The Liquidity Decision Lab for SME Financial Intelligence", badges (Python version, Streamlit, CI status, tests, offline-ready, synthetic-data), hero screenshot (Overview), a 3-line pitch.
2. Try it in 60 seconds: `python run.py demo`, demo accounts (labelled DEMO), what to click first ("Load demo business", then open Decision Lab).
3. The problem: one short paragraph about SME owners finding out about cash gaps too late.
4. The five questions StratifyAI answers (table: question, where in the app).
5. Flagship: Liquidity Decision Lab: table of Option 0/A/B/C with the three levers, a screenshot, and a Mermaid flow (Data to Forecast to Shortage to Lab to Recommendation to Owner approval to Audit).
6. How it works: Mermaid pipeline (Upload and validate, Forecast, Uncertainty, Lab, Financing, Copilot, Approval, Audit). One sentence: "Code computes, the AI explains."
7. Features table (Feature, What it does, Why it matters), grouped: Forecast and alerts, Decision Lab, Financing, Analysis, Agent actions and approvals, Copilot, Security and audit.
8. Architecture: Mermaid component diagram and the repository tree.
9. Security and compliance: permission tiers table, roles matrix, hash-chained audit explained in 3 lines, prompt-injection defence, link to docs/SECURITY_SELF_ASSESSMENT.md.
10. Evaluation (real numbers only, copied from evidence/): backtest vs naive baseline, decision-quality check, security evaluation, task-completion suite, test summary; honest caveats (synthetic data).
11. How the entry maps to the scoring criteria (table: criterion, weight, evidence path) and Submission map (table: deliverable, path).
12. Quick start: prerequisites, setup, run, test, eval, Docker, configuration reference (env variables table).
13. Demo: script and fixtures pointers (docs/DEMO_SCRIPT.md, demo/).
14. Documentation map (table of docs with one line each).
15. Scope and known limitations (honest bullet list), then Roadmap (clearly marked future work).
16. Team, credits, licence note (placeholders for the user to fill).
Rules: every number comes from evidence files; every command is tested; every link works; keep the page skimmable (under about 400 lines).
