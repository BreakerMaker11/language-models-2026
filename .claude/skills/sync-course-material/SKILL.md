---
name: sync-course-material
description: Set up and sync a participant's private repo with the upstream course repo. TRIGGER when participant says "sync course material", "sync upstream", "sync upstream repo", "pull latest", "set up my repo", or "get course updates".
allowed-tools: [Bash, Read, Glob, Grep]
model: sonnet
---

You are helping a participant wire up their local clone of the course repo so they can pull course updates from the upstream source and push their own work to a private GitHub repo.

This skill is designed to run quickly on repeat visits. Early phases are silent pass-through checks — only stop and ask if something needs fixing.

Read `references/details.md` for the notebook diff script and error reference.

**Your local work is safe.** Pulling from upstream only merges new course content into your local branch. If conflicts arise, you will be asked how to handle each file individually before anything is overwritten.

---

## Phase 0 — Prerequisites check

Run all four checks in order. For each one: if it passes, move on silently. If it fails, help fix it and wait for confirmation before continuing.

**Check 1 — git installed**
```bash
git --version
```
- Pass → continue
- Fail → "git is not installed. Download it from https://git-scm.com/downloads, install it, then let me know when done."

**Check 2 — gh installed**
```bash
gh --version
```
- Pass → continue
- Fail → "The GitHub CLI (gh) is not installed. Download it from https://cli.github.com, install it, then let me know when done."

**Check 3 — gh authenticated**
```bash
gh auth status
```
- Pass → continue
- Fail → "gh is not authenticated with GitHub. Run `gh auth login` in your terminal and follow the prompts (choose HTTPS and paste a browser token when asked), then let me know when done."

**Check 4 — .env and GitHub token present**

Run `ls .env 2>/dev/null` to check if `.env` exists, then scan it for variables whose name contains `GITHUB` and either `TOKEN` or `PAT`.

- Pass (file exists + at least one matching variable) → continue
- Fail (.env missing) → tell the participant:

  > "I don't see a `.env` file in your project. We need one with a GitHub Personal Access Token before we can sync. Let me walk you through it."

  **Generate a GitHub PAT**

  GitHub offers two types. Start with fine-grained — it's more secure. Fall back to classic if you hit a 403 error during fetch.

  *Option A — Fine-grained token (recommended)*
  - Go to: `https://github.com/settings/tokens?type=beta` then click **Generate new token**
  - Name it `language-models-sync`, set expiration to 90 days
  - Under **Repository access**, choose **All repositories**
  - Under **Permissions → Repository permissions**, set:
    - **Contents** → Read and Write
    - **Metadata** → Read-only (auto-selected)
  - Click **Generate token** and copy it immediately — GitHub only shows it once

  *Option B — Classic token (fallback)*
  - Go to: `https://github.com/settings/tokens/new`
  - Name it `language-models-sync`, set expiration to 90 days
  - Under **Select scopes**, tick **`repo`** only
  - Click **Generate token** and copy it immediately

  **Create the `.env` file** in the project root:
  ```
  GITHUB_PAT=<paste-your-token-here>
  ```
  Wait for confirmation that the file is saved, then continue.

- Fail (.env exists but no matching token variable) →

  > "Your `.env` file exists but I don't see a GitHub token in it. Add the following line, then let me know: `GITHUB_PAT=<your-token>`"

  If they don't have a token yet, guide them through the PAT steps above. Wait for confirmation, then continue.

---

Once all four checks pass, say: **"Everything looks good — moving on."** and proceed to Phase 1 without asking for confirmation.

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
