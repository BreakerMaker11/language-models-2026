---
name: sync-course-material
description: Set up and sync a participant's private repo with the upstream course repo. TRIGGER when participant says "sync course material", "sync upstream", "sync upstream repo", "pull latest", "set up my repo", or "get course updates".
allowed-tools: [Bash, Read, Glob, Grep]
model: sonnet
---

You are helping a participant wire up their local clone of the course repo so they can pull course updates from the upstream source and push their own work to a private GitHub repo.

This skill is designed to run quickly on repeat visits — early phases are silent pass-through checks. Only stop if something needs fixing.

**Your local work is safe.** Pulling from upstream only merges new course content. If conflicts arise, you will be asked how to handle each file individually before anything is overwritten.

Read `references/details.md` for the notebook diff script and full error reference.

---

## Phase 0 — Prerequisites

Run this single check to scan all four prerequisites at once:

```bash
echo "=== Prereq check ===" && \
echo "git:       $(git --version 2>/dev/null || echo MISSING)" && \
echo "gh:        $(gh --version 2>/dev/null | head -1 || echo MISSING)" && \
echo "gh auth:   $(gh auth status 2>&1 | grep -E "Logged in|not logged in" | xargs || echo MISSING)" && \
echo ".env token: $(grep -E 'GITHUB.*(TOKEN|PAT)' .env 2>/dev/null | cut -d'=' -f1 | tr '\n' ' ' || echo MISSING)"
```

Expected output — all four lines show a version or "Logged in" or token variable names. Fix anything that shows `MISSING` or `not logged in` before continuing.

### 0a — git missing
> "git is not installed. Download it from https://git-scm.com/downloads, install it, then let me know when done."

### 0b — gh missing
> "The GitHub CLI (gh) is not installed. Download it from https://cli.github.com, install it, then let me know when done."

### 0c — gh not authenticated
> "gh is not authenticated. Run `gh auth login` in your terminal, choose HTTPS, and follow the browser prompts. Let me know when done."

### 0d — .env or token missing

**If `.env` doesn't exist:**
> "I don't see a `.env` file in your project. We need one with a GitHub Personal Access Token. Let me walk you through it."

**If `.env` exists but has no GitHub token:**
> "Your `.env` file exists but I don't see a GitHub token in it. Add `GITHUB_PAT=<your-token>` to the file, then let me know."

**To generate a token** — guide them through Option A first, fall back to Option B if they hit a 403 during fetch:

*Option A — Fine-grained (recommended)*
1. Go to `https://github.com/settings/tokens?type=beta` → **Generate new token**
2. Name: `language-models-sync` · Expiration: 90 days
3. Repository access: **All repositories**
4. Permissions → Repository permissions: **Contents: Read and Write** (Metadata auto-selected)
5. Generate and copy immediately — GitHub shows it only once

*Option B — Classic (fallback)*
1. Go to `https://github.com/settings/tokens/new`
2. Name: `language-models-sync` · Expiration: 90 days
3. Scopes: tick **`repo`** only
4. Generate and copy immediately

Add to `.env` in the project root:
```
GITHUB_PAT=<paste-your-token-here>
```

Do not proceed until confirmed.

Once all four checks pass, run silently:
```bash
gh auth setup-git
```
This wires git to use gh for credentials — no manual token handling needed in Phase 3.

---

## Phase 1 — Identify tokens

Scan `.env` for all variables whose name contains `GITHUB` and either `TOKEN` or `PAT`. Show the participant the **variable names only** — never the values.

- **One token found** → use it for both upstream fetch and origin push. Confirm before proceeding.
- **Two or more found** → ask:
  > "I found these GitHub token variables: [NAME_A, NAME_B]. Which one is for the upstream course repo, and which is for your private repo?"

Wait for their answer before proceeding.

---

## Phase 2 — Detect and configure remotes

Run `git remote -v` and match against the known course repo: `github.com/watspeed/language-models`.

**Scenario A — Fresh clone** (`origin` points to watspeed):
1. `git remote rename origin upstream`
2. `git remote set-url --push upstream DISABLED`
3. `grep '^<ORIGIN_TOKEN_VAR>=' .env | cut -d'=' -f2 | gh auth login --with-token`
4. `gh repo create language-models --private --source=. --remote=origin --push`

**Scenario B — Already set up** (`upstream` → watspeed, `origin` → participant's repo):
- Run `gh repo view --json name 2>&1`
- OK → proceed to Phase 3
- Not found → ask: "Your origin is configured but the GitHub repo doesn't seem to exist. Recreate it?"
  - Yes → `gh repo create language-models --private --source=. --remote=origin --push`
  - No → proceed to Phase 3, skip the push at the end

**Scenario C — Upstream only, no origin** (`upstream` → watspeed, no `origin`):
- Ask: "You don't have a private remote yet. Create one on GitHub, or just sync locally?"
  - Create → `gh repo create language-models --private --source=. --remote=origin --push`
  - Just sync → proceed to Phase 3, skip the push at the end

**Scenario D — Unclear state**: Show what remotes exist and ask the participant to clarify.

---

## Phase 2.5 — Preview changes before pulling

```bash
git diff --name-only upstream/main..HEAD
git diff --name-only HEAD..upstream/main
```

For plain text files: `git diff HEAD upstream/main -- <filename>`

For `.ipynb` notebooks — use the Python cell comparison script in `references/details.md`. Raw git diff is too noisy.

If no differences found → proceed directly to Phase 3.

---

## Phase 3 — Fetch, pull, and push

Ask the participant which auth method they'd like to use:

> "How would you like to authenticate git operations?
> **A)** Use gh (already logged in — simplest)
> **B)** Use a Personal Access Token from `.env` (more control, useful if you have separate tokens per repo)"

**Option A — gh auth (default):**
```bash
gh auth setup-git
git fetch upstream
git branch --set-upstream-to=upstream/main main
git pull --no-rebase
git push origin main
```

**Option B — PAT via .env** (never embed the token in the URL):
```bash
cat > /tmp/git-cred-helper.sh << 'EOF'
#!/bin/bash
source <absolute-path-to-.env>
echo "username=x"
echo "password=$<TOKEN_VAR>"
EOF
chmod +x /tmp/git-cred-helper.sh
git -c "credential.helper=" -c "credential.helper=/tmp/git-cred-helper.sh" fetch upstream
git branch --set-upstream-to=upstream/main main
git -c "credential.helper=" -c "credential.helper=/tmp/git-cred-helper.sh" pull --no-rebase
git -c "credential.helper=" -c "credential.helper=/tmp/git-cred-helper.sh" push origin main
rm /tmp/git-cred-helper.sh
```

**If merge conflicts arise (either option):**
1. `git diff --name-only --diff-filter=U` — show conflicted files
2. For each file ask: Keep yours / Keep upstream's / Merge manually
   - Keep yours: `git checkout --ours -- <file> && git add <file>`
   - Keep upstream's: `git checkout --theirs -- <file> && git add <file>`
   - Merge manually: show conflict blocks, wait for confirmation, then stage
3. `git commit --no-edit`
4. For `notebooks/` and `data/`, keeping upstream's version is usually right

Confirm: how many commits were pulled and that origin is now up to date.

---

## Auth Fallback — if fetch or push fails with 401/403

If git operations fail with an auth error, offer the participant the other option:

> "Git couldn't authenticate. Would you like to:
> **A)** Fix gh authentication — re-run `gh auth login` then `gh auth setup-git`
> **B)** Switch to a Personal Access Token stored in `.env`"

**Option A — Fix gh auth:**
```bash
gh auth login
gh auth setup-git
```
Then retry the failed git command.

**Option B — PAT via .env** (never embed the token in the URL):
```bash
cat > /tmp/git-cred-helper.sh << 'EOF'
#!/bin/bash
source <absolute-path-to-.env>
echo "username=x"
echo "password=$<TOKEN_VAR>"
EOF
chmod +x /tmp/git-cred-helper.sh
git -c "credential.helper=" -c "credential.helper=/tmp/git-cred-helper.sh" fetch upstream
git -c "credential.helper=" -c "credential.helper=/tmp/git-cred-helper.sh" pull --no-rebase
git push origin main
rm /tmp/git-cred-helper.sh
```

If `.env` has no token yet, guide them through the PAT setup in Phase 0d first.

Resume from the failed step once fixed — do not restart the whole flow.

---

## Error Quick-Reference

| Symptom | Fix |
|---|---|
| `401` / `403` on fetch or push | gh token expired — re-run `gh auth login`, or switch to PAT fallback |
| `Repository not found` on push | Repo deleted — recreate with `gh repo create` |
| SSO error | Authorise the token for the org under GitHub SSO settings |
| `gh: command not found` | `brew install gh` (Mac) or https://cli.github.com |
| `Unable to add remote "origin"` | Origin already exists — skip `--remote` flag and push directly |
| Fine-grained PAT 403 on fetch | Switch to classic token with `repo` scope (Option B in Phase 0d) |

For auth errors: tell the participant which step failed, offer Option A/B above, and resume from the failed step.
