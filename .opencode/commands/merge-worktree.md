---
description: Complete work on git worktree by commiting and merging into main.
agent: build
---

1. Identify worktree from prompt context or recent output.

2. Commit worktree changes:
   ```bash
   cd ~/peaches-<worktree-name>
   git add -A
   git commit -m "<message matching recent style>"
   ```

3. Navigate to project directory: `cd ~/peaches`

4. Run merge script: `./merge-worktree.sh <worktree-name>`

5. If stash conflict occurs, resolve and stage the file.

