---
description: Abandon git worktree by removing directory and branches.
agent: build
---

$1

1. Identify git worktree via `git worktree list`

2. Remove the worktree using `git worktree remove <directory>`

3. Remove the branch using `git branch -d <branch-name>`