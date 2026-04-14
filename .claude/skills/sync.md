Run the following in the project root:
1. `git fetch origin` — fetches all remote branches
2. `git pull origin main` — pulls latest changes into main
3. Check for any remote branches that aren't `main`. For each one:
   a. Note which files are new/changed vs main: `git diff main...origin/<branch-name> --name-only`
   b. Merge it into main: `git merge origin/<branch-name>`
   c. Move any new files that landed outside the `spike/` folder (and aren't part of the core project structure like `src/`, `scripts/`, `data/`, `docs/`, `CLAUDE.md`, `.claude/`) into the `spike/` folder.
   d. Stage and commit the moves: `git add -A && git commit -m "sync: move remote outputs to spike/ folder"`
   e. Delete the remote branch: `git push origin --delete <branch-name>`
   f. Delete the local tracking branch if it exists: `git branch -d <branch-name>`

Report what was merged, moved, and deleted. If there are merge conflicts, stop and tell the user.
