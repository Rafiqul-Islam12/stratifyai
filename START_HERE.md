# START HERE (any AI tool: Claude, Codex or any other)

You are joining or resuming the StratifyAI project. Do this, in order:
1. Read AGENTS.md (or CLAUDE.md; they are the same rules).
2. Read docs/PROGRESS.md, then docs/PLAN.md.
3. Run `python run.py status` and `git log -5`.
4. Report the state in at most 10 lines: last finished task, anything under "In progress", failing tests, next task.
5. Wait for the user to say `next` (or `continue`). Then do ONLY the next unchecked task, using docs/tasks/<task>.md.

If the previous tool stopped mid-task, PROGRESS.md "In progress" lists the checkpoints and git has "wip:" commits. Continue from the last checkpoint; do not restart the task.
Before you stop for ANY reason (limit warning, end of session): update docs/PROGRESS.md, commit, and push if possible. The next tool depends on it.
Never read docs/archive/*. Never read other task files than the current one.
