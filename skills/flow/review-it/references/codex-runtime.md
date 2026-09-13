# Codex runtime notes for review-it

Read this when the review is running under Codex: how the skill was loaded, which reviewer to
invoke, and which tool replaces which neutral action. The body of the skill assumes these facts;
this file is where they live so the body stays short.

## Loading and invoking this skill

Codex has no `skill` tool. Discovery searches `<root>/.codex/skills`, every `.agents/skills` from
the project root down to cwd, `$CODEX_HOME/skills`, `~/.agents/skills` and `/etc/codex/skills`,
recursively to depth 6, so the nested `skills/<bucket>/<name>/` layout is found there too. The
catalog entry is `- name: description (file: <path>/SKILL.md)` and the model must open that
`SKILL.md` itself with `exec_command`.

`<SKILL_DIR>` is the directory holding that `SKILL.md`; `scripts/review-it` and everything under
`references/` resolve against it. The bundled default after a flat install is
`~/.agents/skills/review-it`.

Invocation:

- Explicit: `$review-it` in a prompt injects the skill body as a user-role `<skill>` block.
  There is no `codex skill` subcommand.
- Implicit is on by default. Turning it off for this skill uses
  `agents/openai.yaml` → `policy.allow_implicit_invocation: false`; `disable-model-invocation` in
  the frontmatter is ignored by Codex.
- Codex reads only `name`, `description` and `metadata.short-description` from the frontmatter;
  unknown keys are ignored.

## Reviewing

A CLI-based reviewer is invoked as `codex review`. This skill's runner already targets that:
`<SKILL_DIR>/scripts/review-it --agent auto` detects a Codex host from `$CODEX_HOME` and selects
the same path as `--agent codex`.

- Local work: `codex review`
- Branch/PR: the runner writes the diff to a file and prints `codex review <diff-file>`

`$CODEX_HOME` is the Codex state directory a review runs under: skills live at
`$CODEX_HOME/skills` and hard guards at `$CODEX_HOME/rules/default.rules`. The reference does not
assume where `$CODEX_HOME` points when it is unset — Codex resolves that itself. This file also
does not enumerate `codex review` flags; the runner's two command forms above are the verified
ones, so do not add flags you have not confirmed.

## Delegation and completion

Two generations exist. V1 is on by default with namespace `multi_agent_v1` and
`agents.max_depth` defaulting to 1, so only one generation of children is usable. V2 is off by
default and needs `[features.multi_agent_v2] enabled = true`; it has no depth cap and
`agents.max_concurrent_threads_per_session` defaults to 4, which is 3 usable children. V2 is the
right choice when the review fans out at all.

A child reports back automatically when it settles; background children are never polled. As in
DSH, a child inherits the parent's cwd (there is no per-child cwd and no worktree argument) and
every shell call is a fresh shell, so hand a child absolute paths.

| Need | Codex mechanism |
|---|---|
| Open this skill | `exec_command` reading `<SKILL_DIR>/SKILL.md` |
| Keep your task list current | `update_plan` (replaces `todo_write`) |
| Run a long build or test | `exec_command` + `write_stdin` (replaces background jobs) |
| Dispatch a fresh child | `spawn_agent`; V1 `multi_agent_v1`, V2 needs `[features.multi_agent_v2]` |
| Continue a child | `send_input` (V1); `send_message` / `followup_task` (V2) |
| Audit the children | `list_agents` (V2) |
| Interrupt a child | `close_agent` (V1); `interrupt_agent` (V2) |
| Hand a file to the user | an absolute path in the reply — there is no `present` |
| Run the reviewer | `codex review` |

There is no `/goal`, and no `toolFilter` or `persona`: a child inherits the parent's sandbox and
approval policy, and a `role` can only disable a fixed feature allowlist.
