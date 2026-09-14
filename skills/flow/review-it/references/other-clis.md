# review-it under other CLIs

The per-CLI review-command matrix and the runner's host probes. Skill loading and delegation are
host mechanics and live in [`dsh-runtime.md`](dsh-runtime.md) and
[`codex-runtime.md`](codex-runtime.md); this file is only the commands.

## Review commands

| Agent | Review Command | Notes |
|-------|---------------|-------|
| DSH | none — review it yourself | The running agent applies the Review Focus directly; this is the default |
| Claude Code | `/review` | Built-in, works on uncommitted changes or diff |
| Codex | `codex review` | Pass diff file or let it auto-detect |
| OpenCode | `/review` | Same as Claude Code |
| DeepSeek TUI | `/review` or manual diff review | Pass diff content for analysis |
| Antigravity CLI | `/code-review` | Built-in slash command, auto-detects diff |

The helper takes `--agent auto|dsh|claude|antigravity|codex`; `auto` probes the harness
environment — DSH from `DSH_SESSION_ID` / `DSH_HOME`, Codex from `CODEX_HOME`, Antigravity from
`ANTIGRAVITY_CLI` / `GEMINI_CLI`, Claude Code from `CLAUDE_CODE` / `CLAUDE_CLI` — and falls back
to `dsh`.

## Preparing the target

Every CLI below reviews the same two things, so the target is prepared the same way and only the
invocation differs. Dirty local work needs no preparation — these CLIs review the working tree in
place. Branch/PR work needs a diff file, and the base is never the literal `main`: it is the open
PR's base when there is one, otherwise the repo's resolved default branch, and `main` only as the
last resort.

```bash
# One invocation, always: each bash call in these harnesses is a fresh shell, so a
# `base=…` assignment does not survive into the next one.
base=$(gh pr view --json baseRefName --jq .baseRefName 2>/dev/null \
  || git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||' \
  || echo main)
diff_file="$(mktemp)"   # 0600 and unpredictable; a fixed /tmp name is world-readable and pre-creatable
git diff "origin/$base"...HEAD > "$diff_file"
echo "$diff_file"       # print it — the shell call that runs the review cannot see the variable
```

This recipe lives here once on purpose. It used to be copy-pasted into each section below, which
is how the fixed-`/tmp` form outlived the change that replaced it in `SKILL.md`.

## Claude Code / OpenCode / DeepSeek TUI

Uncommitted work:

```
/review
```

Branch/PR work — prepare the target above, then hand over the path it printed:

```
/review the changes in <the printed diff_file> against origin/<base>
```

## Antigravity CLI (`agy`)

Uncommitted work:

```
/code-review
```

Branch/PR work:

```
/code-review the changes in <the printed diff_file> against origin/<base>
```

## Codex

```bash
# Review uncommitted changes
codex review

# Review branch diff — prepare the target above first
codex review <the printed diff_file>
```

`<SKILL_DIR>/scripts/review-it --agent codex` prints exactly these two forms, and `auto` selects
it when `$CODEX_HOME` is set; the loading and delegation mechanics are in
[`codex-runtime.md`](codex-runtime.md).
