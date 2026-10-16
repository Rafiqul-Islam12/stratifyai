# PROMPTS (reusable; the user pastes these)

## Next task
next            (or: next T07)

## FIX (bug)
Bug: <describe or paste only the failing part of the error>.
Read CLAUDE.md and docs/PROGRESS.md. Find the root cause with minimal file reads (use grep). Fix it, add a regression test, run pytest -q, record it in docs/PROGRESS.md (Known issues if unresolved), commit "fix: <short>", push if possible. Stop and report real results.

## RESUME (another AI tool or another account)
Read START_HERE.md and follow it. Then wait for my "next".

## AUDIT (read-only review before submission)
Read-only audit. Read docs/CHECKLIST.md and docs/BRIEF.md. For every item verify the claim in code, tests or evidence files. Output a table: item id, status (verified, partial, missing), evidence path, fix needed. Do not change any file. Do not read docs/archive.

## UI POLISH (looks only)
Read CLAUDE.md and docs/DESIGN.md. Page: <name>. Problems (my list): <alignment, spacing, font, colour issues>. Fix ONLY styles.css and components usage; do not change logic or numbers. Use tokens only. Run the page smoke test, commit "ui: <page> polish". Stop.

## STOP and save state (limit about to end)
Stop now. Write the current state into docs/PROGRESS.md in at most 15 lines (done, half done, files touched, failing tests, next step). Commit "wip: state saved" and push if possible. Do nothing else.

## COMPACT (session got long)
/compact keep: current task id, files changed, failing tests, decisions made
