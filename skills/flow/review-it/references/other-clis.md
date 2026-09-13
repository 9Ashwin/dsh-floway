# review-it under other CLIs

`review-it` is DSH-first: under DSH the calling agent is the reviewer and `SKILL.md` is the
whole procedure. This file only matters when the same skill is loaded by one of the CLIs below,
each of which has its own review command.

| Agent | Review Command | Notes |
|-------|---------------|-------|
| DSH | none — review it yourself | The running agent applies the Review Focus directly; this is the default |
| Claude Code | `/review` | Built-in, works on uncommitted changes or diff |
| Codex | `codex review` | Pass diff file or let it auto-detect |
| OpenCode | `/review` | Same as Claude Code |
| DeepSeek TUI | `/review` or manual diff review | Pass diff content for analysis |
| Antigravity CLI | `/code-review` | Built-in slash command, auto-detects diff |

The helper takes `--agent auto|dsh|claude|antigravity|codex`; `auto` detects DSH from
`DSH_SESSION_ID` / `DSH_HOME` first and only then the others, and falls back to `dsh`.

## Claude Code / OpenCode / DeepSeek TUI

Dirty local work (default — `/review` works on uncommitted changes):

```
/review
```

Branch/PR work — generate a diff, then review it:

```bash
git diff origin/main...HEAD > /tmp/review-it.diff
```

Then review the diff file with a focused prompt:

```
/review the changes in /tmp/review-it.diff against origin/main
```

If an open PR exists, use its actual base:

```bash
base=$(gh pr view --json baseRefName --jq .baseRefName)
git diff "origin/$base"...HEAD > /tmp/review-it.diff
```

## Antigravity CLI (`agy`)

Dirty local work:

```
/code-review
```

Branch/PR work:

```bash
git diff origin/main...HEAD > /tmp/review-it.diff
```

Then:

```
/code-review the changes in /tmp/review-it.diff against origin/main
```

## Codex

```bash
# Review uncommitted changes
codex review

# Review branch diff
git diff origin/main...HEAD > /tmp/review-it.diff
codex review /tmp/review-it.diff
```

## Per-agent branch diff base

All of the above share one rule: the diff base comes from the open PR when there is one
(`gh pr view --json baseRefName`), otherwise `origin/main`. Keep the assignment and the use in a
single shell invocation — in DSH and in every one of these CLIs, a separate bash call is a fresh
shell.
