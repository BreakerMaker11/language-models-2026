---
name: sync-upstream
description: Set up and sync a participant's private repo with the upstream course repo. Participants clone the course repo directly and create their own separate private GitHub repo — no forking. TRIGGER when: participant says "sync upstream", "sync upstream repo", "pull latest", "set up my repo", "get course updates", or invokes /sync-upstream.
allowed-tools: [Bash, Read, Glob, Grep]
model: sonnet
---

Help the participant set up their own private GitHub repo and keep it in sync with the upstream course repo. The participant cloned the course repo directly (not a fork) and needs to wire it up: the course repo becomes `upstream` (read-only), and their own newly created private repo becomes `origin`. Never expose token values.

## Step 1 — Scan .env for GitHub tokens

Read `.env` and find all variables matching `GITHUB` + (`TOKEN` or `PAT`) in the name. Show the participant the **variable names only** — never the values.

- If **one token found** → use it for both upstream fetch and origin push.
- If **two or more found** → ask the participant:
  > "I found these GitHub token variables: [NAME_A, NAME_B]. Which one is for accessing the upstream course repo, and which is for your private repo?"
  Wait for their answer before proceeding.

## Step 2 — Detect remote state

Run `git remote -v` and match against the known course repo: `github.com/watspeed/language-models`.

**Scenario A — Fresh clone** (`origin` points to watspeed):
1. Rename origin to upstream: `git remote rename origin upstream`
2. Disable push to upstream: `git remote set-url --push upstream DISABLED`
3. Authenticate gh CLI using the origin token: `grep '^<ORIGIN_TOKEN_VAR>=' .env | cut -d'=' -f2 | gh auth login --with-token`
4. Create private repo and set as origin: `gh repo create language-models --private --source=. --remote=origin --push`
5. Proceed to Step 3.

**Scenario B — Already set up** (`upstream` points to watspeed, `origin` is participant's own repo):
- Verify the origin repo actually exists: `gh repo view --json name 2>&1`
- If it responds successfully → proceed to Step 3.
- If it returns a "not found" or auth error → the local config exists but the remote repo was deleted or is inaccessible. Ask the participant:
  > "Your origin remote is configured but the GitHub repo doesn't seem to exist. Would you like me to recreate it?"
  - If **yes** → authenticate gh CLI with the origin token, run `gh repo create language-models --private --source=. --remote=origin --push`, then proceed to Step 3.
  - If **no** → proceed to Step 3 but skip Step 5.

**Scenario C — Upstream only, no origin** (`upstream` points to watspeed, no `origin` exists):
- Ask the participant:
  > "You don't have a private remote repo set up yet. Would you like me to create one on GitHub, or just sync the latest course updates locally?"
- If **yes, create one** → authenticate gh CLI and run `gh repo create language-models --private --source=. --remote=origin --push`, then proceed to Step 3.
- If **no, just sync locally** → skip to Step 3, omit Step 5 (no push needed).

**Scenario D — Unclear state**:
- Show the participant what remotes exist and ask them to clarify before proceeding.

## Step 3 — Fetch from upstream using credential helper

Never embed the token in the remote URL. Always use a temporary credential helper:

```bash
# Write temp helper (reads token from .env at runtime, never echoes it)
cat > /tmp/git-cred-helper.sh << 'EOF'
#!/bin/bash
source /path/to/.env
echo "username=x"
echo "password=$<UPSTREAM_TOKEN_VAR>"
EOF
chmod +x /tmp/git-cred-helper.sh

# Clear global credential helper to avoid PAT/CTOKEN conflict, then fetch
git -c "credential.helper=" -c "credential.helper=/tmp/git-cred-helper.sh" fetch upstream

# Clean up immediately
rm /tmp/git-cred-helper.sh
```

Replace `/path/to/.env` with the actual absolute path and `<UPSTREAM_TOKEN_VAR>` with the confirmed variable name.

## Step 4 — Set tracking and pull

```bash
git branch --set-upstream-to=upstream/main main
git -c "credential.helper=" -c "credential.helper=/tmp/git-cred-helper.sh" pull
rm /tmp/git-cred-helper.sh
```

If the pull succeeds cleanly → proceed to Step 5.

If the pull reports **merge conflicts**:
1. Run `git diff --name-only --diff-filter=U` to list conflicted files — show this list to the participant.
2. For each conflicted file, ask:
   > "In `<filename>`, would you like to:
   > - **Keep yours** — discard the upstream change for this file
   > - **Keep upstream's** — overwrite your version with the course version
   > - **Merge manually** — I'll show you the conflicting sections so you can decide line by line"
3. Apply their choice:
   - Keep yours: `git checkout --ours -- <filename> && git add <filename>`
   - Keep upstream's: `git checkout --theirs -- <filename> && git add <filename>`
   - Merge manually: run `git diff <filename>`, show the conflict blocks (lines between `<<<<<<<` and `>>>>>>>`), and wait for the participant to confirm what to keep before staging.
4. Once all conflicts are resolved: `git commit --no-edit` to complete the merge.
5. Remind the participant: upstream changes in `notebooks/` and `data/` are course content — keeping upstream's version is usually the right choice for those.

## Step 5 — Push to private origin

```bash
git push origin main
```

This uses the gh credential helper (authenticated with GITHUB_PAT in Step 2A) — no manual token handling needed.

## Error handling — permission and auth failures

If any git or gh command returns a 401, 403, or "Bad credentials" error:
1. Do NOT retry silently.
2. Tell the participant clearly which operation failed and which token was being used (by variable name only, not value).
3. Guide them with:
   > "It looks like `<TOKEN_VAR>` doesn't have the required access. Please check:
   > - The token is still valid (not expired or revoked)
   > - It has the `repo` scope enabled
   > - If the repo is under an organisation, the token is authorised for SSO"
4. Once they confirm they've fixed it, re-run from the failed step only — don't restart the whole flow.

If gh CLI is not installed or not authenticated:
- Detect with `gh auth status 2>&1`
- If not installed: tell the participant to install it (`brew install gh` on Mac) and re-run the skill.
- If not authenticated: authenticate using the origin token from `.env` before proceeding.

## Key rules

- **Never display token values** — only variable names from .env.
- **Never embed tokens in remote URLs** — always use the credential helper pattern.
- **Always delete /tmp/git-cred-helper.sh** after each use.
- **Always clear the global credential helper** (`credential.helper=`) before injecting the upstream token to avoid conflicts with the origin token.
- Do not push to upstream — it is read-only. If push URL is not already DISABLED, set it.
- After a successful sync, confirm to the participant: how many commits pulled and that origin is up to date.
