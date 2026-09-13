# Claude Code runtime notes for review-it

Read this when the review is running under Claude Code: how the skill was loaded, which reviewer
to invoke, and which tool replaces which neutral action. The body of the skill assumes these
facts; this file is where they live so the body stays short.

## Loading and invoking this skill

Claude Code discovers a skill at `~/.claude/skills/<name>/SKILL.md` (personal) and
`<project>/.claude/skills/<name>/SKILL.md` (project); a plugin contributes its skills through the
plugin manifest's `skills` list, so a plugin install serves the nested
`skills/flow/review-it/` layout as-is. The model loads a skill through the **`Skill` tool** by
name and a human types `/review-it`; there is no separate host-level "skill" command beyond that.

`<SKILL_DIR>` is the directory holding the `SKILL.md` the loader read; `scripts/review-it` and
everything under `references/` resolve against it. The frontmatter carries only `name` and
`description`: the collection keeps host-specific keys out, so this skill ships **without
`allowed-tools`** and Claude Code prompts for tool permission normally. A user who wants
pre-approval adds the key to the frontmatter themselves — for a review that is `git`, `gh` and
the diff/read tools:

```yaml
allowed-tools:
  - Bash(git:*)
  - Bash(gh:*)
  - Read
  - Grep
```

Do not ship it: `allowed-tools` is Claude-Code-only and must stay out of the harness-neutral
frontmatter.

## Reviewing

Claude Code ships a built-in **`/review`**, and this skill's runner already targets it:
`<SKILL_DIR>/scripts/review-it --agent auto` detects a Claude Code host from `$CLAUDE_CODE` /
`$CLAUDE_CLI` and selects the same path as `--agent claude`.

- Local work: `/review`
- Branch/PR: the runner writes the diff to a file and prints
  `/review the changes in <diff-file> against <base>`

Leave that behaviour alone. The per-CLI matrix, including this row and the runner's host probes,
stays in [`other-clis.md`](other-clis.md).

## Delegation and completion

An `Agent` call dispatches a child and returns its result to the caller. A child inherits the
parent's cwd — there is no per-child cwd and no worktree argument — and every shell call is a
fresh shell, so hand a child absolute paths.

| Need | Claude Code mechanism |
|---|---|
| Open this skill | the `Skill` tool (a human types `/review-it`) |
| Keep your task list current | `TodoWrite` |
| Run a long build or test | a normal tool call in the current context (no `job_*` equivalent) |
| Dispatch a fresh child | `Agent` |
| Continue a child | **none** — no durable child id and no `send_message` |
| Audit the children | **none** — no `list_agents` equivalent |
| Interrupt a child | no separate primitive; the `Agent` call ends when it returns |
| Hand a file to the user | an absolute path in the reply — there is no `present` |
| Run the reviewer | `/review` |

**What is genuinely missing.** DSH gives every child a durable id, a `send_message` channel and a
`list_agents` audit; Codex reaches the same surface in V2. Claude Code has no equivalent: once an
`Agent` call returns, that child cannot be continued and there is no way to list what was
dispatched. A fan-out review is therefore fire-and-collect — each reviewer gets one self-contained
prompt, and a re-review is a fresh child, not a resumed one. Do not describe these calls as if a
continuation channel existed.

There is no `/goal` and no per-child `toolFilter` / `persona`; a child inherits the parent's
permission mode, and `allowed-tools` restricts which tools a skill may use.

## Optional hard guard

A `PreToolUse` hook can block a command outright — the host-level form of a rule like "never
force-push". It is not required; the skill works with normal permission prompts.
