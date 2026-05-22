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

```bash
echo "=== Prereq check ===" && \
echo "git:     $(git --version 2>/dev/null || echo MISSING)" && \
echo "gh:      $(gh --version 2>/dev/null | head -1 || echo MISSING)" && \
echo "gh auth: $(gh auth status 2>&1 | grep -E "Logged in|not logged in" | xargs || echo MISSING)"
```

Expected: all three lines show a version or "Logged in". Fix anything that shows `MISSING` or `not logged in` before continuing.

### 0a — git missing
> "git is not installed. Download it from https://git-scm.com/downloads, install it, then let me know when done."

### 0b — gh missing
> "The GitHub CLI (gh) is not installed. Download it from https://cli.github.com, install it, then let me know when done."

### 0c — gh not authenticated
> "gh is not authenticated. Run `gh auth login` in your terminal, choose HTTPS, and follow the browser prompts. Let me know when done."

Once all three pass, run silently:
```bash
gh auth setup-git
```

---

## Phase 1 — Detect and configure remotes

Run `git remote -v` and match against the known course repo: `github.com/watspeed/language-models`.

**Scenario A — Fresh clone** (`origin` points to watspeed):
1. `git remote rename origin upstream`
2. `git remote set-url --push upstream DISABLED`
3. `gh repo create language-models --private --source=. --remote=origin --push`

**Scenario B — Already set up** (`upstream` → watspeed, `origin` → participant's repo):
- Run `gh repo view --json name 2>&1`
- OK → proceed to Phase 2
- Not found → ask: "Your origin is configured but the GitHub repo doesn't seem to exist. Recreate it?"
  - Yes → `gh repo create language-models --private --source=. --remote=origin --push`
  - No → proceed to Phase 2, skip the push at the end

**Scenario C — Upstream only, no origin** (`upstream` → watspeed, no `origin`):
- Ask: "You don't have a private remote yet. Create one on GitHub, or just sync locally?"
  - Create → `gh repo create language-models --private --source=. --remote=origin --push`
  - Just sync → proceed to Phase 2, skip the push at the end

**Scenario D — Unclear state**: Show what remotes exist and ask the participant to clarify.

---

## Phase 2 — Preview changes before pulling

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

**Option A — gh auth:**
```bash
git fetch upstream
git branch --set-upstream-to=upstream/main main
git pull --no-rebase
git push origin main
```

**Option B — PAT via .env:**

First, scan `.env` for token variables (name contains `GITHUB` + `TOKEN` or `PAT`). Show **variable names only — never values**.
- One found → use it for both fetch and push
- Two or more found → ask: "I found [NAME_A, NAME_B]. Which is for the upstream course repo, and which is for your private repo?"

Then run (never embed the token in the URL):
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

If no token found in `.env`, guide them through generating one:

*Option A — Fine-grained (recommended)*
1. Go to `https://github.com/settings/tokens?type=beta` → **Generate new token**
2. Name: `language-models-sync` · Expiration: 90 days
3. Repository access: **All repositories**
4. Permissions → Repository permissions: **Contents: Read and Write** (Metadata auto-selected)
5. Generate and copy immediately — GitHub shows it only once

*Option B — Classic (fallback if fine-grained gives 403)*
1. Go to `https://github.com/settings/tokens/new`
2. Name: `language-models-sync` · Expiration: 90 days
3. Scopes: tick **`repo`** only
4. Generate and copy immediately

Add to `.env`: `GITHUB_PAT=<your-token>`

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

> "Git couldn't authenticate. Would you like to:
> **A)** Fix gh — re-run `gh auth login` then `gh auth setup-git`
> **B)** Switch to a PAT from `.env`"

Resume from the failed step once fixed — do not restart the whole flow.

---

## Error Quick-Reference

| Symptom | Fix |
|---|---|
| `401` / `403` on fetch or push | gh token expired — re-run `gh auth login`, or switch to PAT |
| `Repository not found` on push | Repo deleted — recreate with `gh repo create` |
| SSO error | Authorise the token for the org under GitHub SSO settings |
| `gh: command not found` | `brew install gh` (Mac) or https://cli.github.com |
| `Unable to add remote "origin"` | Origin already exists — skip `--remote` flag and push directly |
| Fine-grained PAT 403 on fetch | Switch to classic token with `repo` scope |

For auth errors: tell the participant which step failed, offer A/B above, and resume from the failed step.
