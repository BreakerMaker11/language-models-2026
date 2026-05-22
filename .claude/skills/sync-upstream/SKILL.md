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

## Phase 1 — Collect tokens

Ask the participant to paste their tokens using silent input (nothing is written to disk — tokens live only in the shell session):

```bash
read -s -p "Paste your upstream course token (input hidden): " UPSTREAM_TOKEN && echo ""
```

Then ask if they have a separate token for their private repo:

> "Do you have a separate token for your private GitHub repo, or should I use the same one?"

- Same token → set `ORIGIN_TOKEN=$UPSTREAM_TOKEN`
- Separate → collect it:
  ```bash
  read -s -p "Paste your private repo token (input hidden): " ORIGIN_TOKEN && echo ""
  ```

**Verify upstream token** works before proceeding:
```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $UPSTREAM_TOKEN" \
  https://api.github.com/repos/watspeed/language-models
```
- `200` → valid, proceed.
- `401` / `404` → tell the participant the upstream token is invalid or lacks `repo` scope, ask them to re-paste.

**Verify origin token** (if different) by checking their username resolves:
```bash
curl -s -H "Authorization: Bearer $ORIGIN_TOKEN" https://api.github.com/user | python3 -c "import sys,json; print(json.load(sys.stdin).get('login','error'))"
```
- Returns a username → valid, proceed.
- Returns `error` or empty → token is invalid, ask them to re-paste.

---

## Phase 2 — Detect and configure remotes

Run `git remote -v` and match against the known course repo: `github.com/watspeed/language-models`.

**Scenario A — Fresh clone** (`origin` points to watspeed):
1. `git remote rename origin upstream`
2. `git remote set-url --push upstream DISABLED`
3. Authenticate gh CLI: `echo "$ORIGIN_TOKEN" | gh auth login --with-token`
4. `gh repo create language-models --private --source=. --remote=origin --push`

**Scenario B — Already set up** (`upstream` → watspeed, `origin` → participant's repo):
- Verify the remote repo exists: `echo "$ORIGIN_TOKEN" | gh auth login --with-token && gh repo view --json name 2>&1`
- If OK → proceed to Phase 3.
- If not found or error → ask:
  > "Your origin remote is configured but the GitHub repo doesn't seem to exist. Would you like me to recreate it?"
  - Yes → `gh repo create language-models --private --source=. --remote=origin --push`
  - No → proceed to Phase 3, skip the push at the end.

**Scenario C — Upstream only, no origin** (`upstream` → watspeed, no `origin`):
- Ask:
  > "You don't have a private remote repo set up yet. Would you like me to create one on GitHub, or just sync the latest course updates locally?"
  - Create one → `echo "$ORIGIN_TOKEN" | gh auth login --with-token && gh repo create language-models --private --source=. --remote=origin --push`
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
echo "username=x"
echo "password=$UPSTREAM_TOKEN"
EOF
chmod +x /tmp/git-cred-helper.sh
git -c "credential.helper=" -c "credential.helper=/tmp/git-cred-helper.sh" fetch upstream
rm /tmp/git-cred-helper.sh
```

**Set tracking and pull:**
```bash
git branch --set-upstream-to=upstream/main main
cat > /tmp/git-cred-helper.sh << 'EOF'
#!/bin/bash
echo "username=x"
echo "password=$UPSTREAM_TOKEN"
EOF
chmod +x /tmp/git-cred-helper.sh
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
