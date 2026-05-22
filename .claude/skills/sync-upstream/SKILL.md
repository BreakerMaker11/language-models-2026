---
name: sync-upstream
description: Set up and sync a participant's private repo with the upstream course repo. TRIGGER when participant says "sync upstream", "sync upstream repo", "pull latest", "set up my repo", or "get course updates".
allowed-tools: [Bash, Read, Glob, Grep]
model: sonnet
---

You are helping a participant wire up their local clone of the course repo so they can pull course updates from the upstream source and push their own work to a private GitHub repo. Work through three phases in order — wait for confirmation before each transition.

Read `references/details.md` for the notebook diff script and error reference.

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

## Phase 2.5 — Preview changes before pulling

After fetching, before pulling, always run a pre-pull diff so the participant can see exactly what upstream changed.

**Identify changed files:**
```bash
git diff --name-only upstream/main..HEAD
git diff --name-only HEAD..upstream/main
```

For plain text files, run `git diff HEAD upstream/main -- <filename>`.

For `.ipynb` notebooks — use the Python cell comparison script in `references/details.md`. Raw git diff is too noisy and misses partial changes like spelling fixes inside large cells.

If no differences found → proceed directly to Phase 3.

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
git -c "credential.helper=" -c "credential.helper=/tmp/git-cred-helper.sh" pull --no-rebase
rm /tmp/git-cred-helper.sh
```

**If merge conflicts arise:**
1. Run `git diff --name-only --diff-filter=U` and show conflicted files.
2. For each file ask: Keep yours / Keep upstream's / Merge manually.
   - Keep yours: `git checkout --ours -- <filename> && git add <filename>`
   - Keep upstream's: `git checkout --theirs -- <filename> && git add <filename>`
   - Merge manually: show conflict blocks between `<<<<<<<` and `>>>>>>>`, wait for confirmation, then stage.
3. `git commit --no-edit` once all conflicts are resolved.
4. Note: for `notebooks/` and `data/`, keeping upstream's version is usually right.

**Push to private origin:**
```bash
git push origin main
```

Confirm to the participant: how many commits were pulled and that origin is now up to date.

See `references/details.md` for the full error reference.
