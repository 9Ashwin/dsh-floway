# Codex runtime notes for loop-it

Read this when you run the serial loop under Codex: the body's neutral actions
(delegate, task list, background job) map to the tools and config keys below.

## Discovery and invocation

Codex discovers skills recursively to depth 6, so the nested
`skills/flow/loop-it/` layout works under a project `<root>/.codex/skills`, any
`.agents/skills` from the project root down to the cwd, `$CODEX_HOME/skills`,
`~/.agents/skills`, or `/etc/codex/skills`. There is no `skill` tool: the catalog
lists `- name: description (file: <path>/SKILL.md)`, and the model must open that
SKILL.md itself with `exec_command`. Relative paths (`scripts/…`, `references/…`)
resolve against the directory holding it.

Typing `$loop-it` in a prompt injects the skill body as a user-role `<skill>`
block; there is no `codex skill` subcommand. The bundled default is
`~/.agents/skills/loop-it`. Implicit invocation is on by default; turn it off per
skill via `agents/openai.yaml` (`policy.allow_implicit_invocation: false`), since
Codex ignores the frontmatter's `disable-model-invocation`.

## Delegation

The loop is serial and inline by default: one issue at a time in the
orchestrator's own context. Reach for a child only when a single issue is worth
isolating.

| Need | V1 (default) | V2 (opt-in) |
|---|---|---|
| Do one issue inline (the loop default) | orchestrator itself | orchestrator itself |
| Start a fresh child | `spawn_agent` | `spawn_agent` |
| Continue / retry a child | `send_input` | `followup_task` |
| Resume a stopped child | `resume_agent` | — |
| Wait for children | `wait_agent(targets=[…])` | `wait_agent` |
| Audit the children you started | — | `list_agents` |
| Interrupt a child | `close_agent` | `interrupt_agent` |
| Keep the task list current | `update_plan` | `update_plan` |
| Run a long build or test | `exec_command` + `write_stdin` | `exec_command` + `write_stdin` |
| Hand the report to the user | absolute path (no `present`) | absolute path (no `present`) |

V1 is on by default under the `multi_agent_v1` namespace and sets
`agents.max_depth` to 1, so a child must not delegate further. V2 needs
`[features.multi_agent_v2] enabled = true`, has no depth cap, and adds
`list_agents`, `followup_task` and `interrupt_agent`. V2 also exposes
`agents.max_concurrent_threads_per_session` (default 4, so 3 usable children):
that key, not the loop, caps concurrency — it matters only if you fan review or
exploration out. Children report back automatically; a background child is never
polled.

## What Codex does not have

- No `/goal` command: a long-running objective is not available to the model.
- No per-child cwd and no worktree argument: a child inherits the parent's cwd,
  and every shell call is a fresh shell — pass absolute paths.
- No `toolFilter` or `persona`; a child inherits the parent's sandbox and approval
  policy. A `role` may only disable a fixed feature allowlist.
