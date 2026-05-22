---
name: sync-upstream
description: Set up and sync a participant's private repo with the upstream course repo. Participants clone the course repo directly and create their own separate private GitHub repo — no forking. TRIGGER when: participant says "sync upstream", "sync upstream repo", "pull latest", "set up my repo", "get course updates", or invokes /sync-upstream.
---

You are helping a participant wire up their local clone of the course repo so they can pull course updates from the upstream source and push their own work to a private GitHub repo. Work through three phases in order — wait for confirmation before each transition.

**Your local work is safe.** Pulling from upstream only merges new course content into your local branch. If conflicts arise, you will be asked how to handle each file individually before anything is overwritten.

---

## Phase 1 — Identify tokens

Scan `.env` for all variables whose name contains `GITHUB` and either `TOKEN` or `PAT`. Show the participant the **variable names only** — never the values.

- If **one token found** → use it for both upstream fetch and origin push. Confirm with the participant before proceeding.
- If **two or more found** → ask:
  > "I found these GitHub token variables: [NAME_A, NAME_B]. Which one is for the upstream course repo, and which is for your private repo?"

Wait for their answer before proceeding.

---

## Phase 2 — Detect and configure remotes

Run `git remote -v` and match against the known course repo: `github.com/watspeed/language-models`.

**Scenario A — Fresh clone** (`origin` points to watspeed):
1. `git remote rename origin upstream`
2. `git remote set-url --push upstream DISABLED`
3. Authenticate gh CLI with the origin token: `grep '^<ORIGIN_TOKEN_VAR>=' .env | cut -d'=' -f2 | gh auth login --with-token`
4. `gh repo create language-models --private --source=. --remote=origin --push`

**Scenario B — Already set up** (`upstream` → watspeed, `origin` → participant's repo):
- Verify the remote repo exists: `gh repo view --json name 2>&1`
- If OK → proceed to Phase 3.
- If not found or error → ask:
  > "Your origin remote is configured but the GitHub repo doesn't seem to exist. Would you like me to recreate it?"
  - Yes → authenticate gh CLI, then `gh repo create language-models --private --source=. --remote=origin --push`
  - No → proceed to Phase 3, skip the push at the end.

**Scenario C — Upstream only, no origin** (`upstream` → watspeed, no `origin`):
- Ask:
  > "You don't have a private remote repo set up yet. Would you like me to create one on GitHub, or just sync the latest course updates locally?"
  - Create one → authenticate gh CLI, then `gh repo create language-models --private --source=. --remote=origin --push`
  - Just sync locally → proceed to Phase 3, skip the push at the end.

**Scenario D — Unclear state**:
- Show the participant what remotes exist and ask them to clarify before proceeding.

---

## Phase 3 — Fetch, pull, and push

**Fetch from upstream** (never embed the token in the URL — use a temporary credential helper):
```bash
cat > /tmp/git-cred-helper.sh << 'EOF'
#!/bin/bash
source <absolute-path-to-.env>
echo "username=x"
echo "password=$<UPSTREAM_TOKEN_VAR>"
EOF
chmod +x /tmp/git-cred-helper.sh
git -c "credential.helper=" -c "credential.helper=/tmp/git-cred-helper.sh" fetch upstream
rm /tmp/git-cred-helper.sh
```

**Set tracking and pull:**
```bash
git branch --set-upstream-to=upstream/main main
git -c "credential.helper=" -c "credential.helper=/tmp/git-cred-helper.sh" pull
rm /tmp/git-cred-helper.sh
```

If the pull succeeds cleanly → push to origin and confirm to the participant how many commits were pulled.

**If merge conflicts arise:**
1. Run `git diff --name-only --diff-filter=U` and show the list of conflicted files.
2. For each file, ask:
   > "In `<filename>`, would you like to:
   > - **Keep yours** — discard the upstream change
   > - **Keep upstream's** — overwrite with the course version
   > - **Merge manually** — I'll show you the conflicting sections line by line"
3. Apply the choice:
   - Keep yours: `git checkout --ours -- <filename> && git add <filename>`
   - Keep upstream's: `git checkout --theirs -- <filename> && git add <filename>`
   - Merge manually: show the conflict blocks between `<<<<<<<` and `>>>>>>>`, wait for confirmation, then stage.
4. `git commit --no-edit` once all conflicts are resolved.
5. Note: for files in `notebooks/` and `data/`, keeping upstream's version is usually right — these are course content.

**Push to private origin:**
```bash
git push origin main
```

Confirm to the participant: how many commits were pulled and that origin is now up to date.

---

## Error Quick-Reference

| Symptom | Fix |
|---|---|
| `401` / `403` / `Bad credentials` on fetch | `<UPSTREAM_TOKEN_VAR>` is expired, revoked, or missing `repo` scope — check token settings on GitHub |
| `401` / `403` on push | `<ORIGIN_TOKEN_VAR>` is expired or missing `repo` scope |
| `Repository not found` on push | Origin repo was deleted — offer to recreate with `gh repo create` |
| SSO error on fetch or push | Token needs to be authorised for the organisation under GitHub SSO settings |
| `gh: command not found` | Install gh CLI: `brew install gh` (Mac) or follow https://cli.github.com |
| `gh auth login` fails | Token may lack sufficient scopes — generate a new one with `repo` scope |
| `Unable to add remote "origin"` | Origin already exists locally — skip `gh repo create --remote` flag and push directly |

For auth errors: tell the participant which token variable failed (not its value), what to fix, and resume from the failed step — do not restart the whole flow.
