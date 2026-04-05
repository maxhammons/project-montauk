Run the following in the project root:
1. `git fetch origin` — fetches all remote branches
2. `git pull origin main` — pulls latest changes into main
3. Check for any remote branches that aren't `main`. For each one:
   a. Note which files are new/changed vs main: `git diff main...origin/<branch-name> --name-only`
   b. Merge it into main: `git merge origin/<branch-name>`
   c. Move any new files that landed outside the `remote/` folder (and aren't part of the core project structure like `src/`, `reference/`, `CLAUDE.md`, `.claude/`) into the `remote/` folder. Rename using the convention `[type]-YYYY-MM-DD.md` based on today's date if not already named that way.
   d. Stage and commit the moves: `git add -A && git commit -m "sync: move remote outputs to remote/ folder"`
   e. Delete the remote branch: `git push origin --delete <branch-name>`
   f. Delete the local tracking branch if it exists: `git branch -d <branch-name>`

Report what was merged, moved, and deleted. If there are merge conflicts, stop and tell the user.
