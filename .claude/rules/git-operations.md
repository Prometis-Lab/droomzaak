# Git operations — sub-agent restrictions

**CRITICAL: If you are a sub-agent (spawned via the Agent/Task tool), you MUST NOT run any git write commands.**

Prohibited for sub-agents (any form): `git add`, `git commit`, `git push`, `git stash`, `git checkout`, `git reset`, `git merge`, `git rebase`, `git rm`, `git restore`.

**Why:** when multiple sub-agents run in parallel, concurrent git operations corrupt the working tree — they unstage each other's changes, create conflicts, and produce broken commits.

**What to do instead:** complete your file edits (Read/Edit/Write) and return your results. The orchestrator (main Claude session) handles all git operations after reviewing your changes — and only ever through `/ship`.

**Read-only git is allowed:** `git status`, `git log`, `git diff`, `git show`, `git blame`, `git ls-files`, `git rev-parse`, etc.

**Nobody pushes via Claude.** `git push` is denied in `settings.json` for everyone (main session included) — pushing is a deliberate human action.
