# Sync Upstream — Reference Details

## Notebook Cell Diff Script

For `.ipynb` files, never use raw `git diff` (too noisy). Run this Python script to compare source cells directly — catches all differences including partial changes like spelling fixes buried inside large cells:

```bash
python3 -c "
import json, subprocess, difflib

upstream_raw = subprocess.run(
    ['git', 'show', 'upstream/main:<notebook-path>'],
    capture_output=True, text=True
).stdout
local_raw = open('<notebook-path>').read()

up_cells = json.loads(upstream_raw)['cells']
lo_cells = json.loads(local_raw)['cells']

changes = []
for i, (u, l) in enumerate(zip(up_cells, lo_cells)):
    u_src = ''.join(u.get('source', []))
    l_src = ''.join(l.get('source', []))
    if u_src != l_src:
        diff = list(difflib.unified_diff(
            l_src.splitlines(), u_src.splitlines(),
            lineterm='', n=1
        ))
        changes.append((i, l_src, u_src, diff))

print(f'Found {len(changes)} changed cell(s):')
for idx, local_src, up_src, diff in changes:
    print(f'\n=== Cell {idx} ===')
    for line in diff[2:]:  # skip unified diff header
        print(line)
"
```

Present changes clearly to the participant:

> "I found differences in `<filename>`. Here's what upstream changed:
>
> **Change 1** — `<brief description, e.g. spelling fix>`
> - Yours: `vegeteraion`
> - Upstream: `vegetarian`
>
> For each change, would you like to:
> - **Keep yours** — leave your local version as-is
> - **Take upstream's** — apply the upstream change
>
> You can decide separately for each change."

**Applying per-change decisions:**
- All take upstream's → pull normally, auto-resolve with `git checkout --theirs`
- All keep yours → pull then `git checkout --ours -- <file> && git add <file>`
- Mixed → pull, then manually apply or revert specific changes per file

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
