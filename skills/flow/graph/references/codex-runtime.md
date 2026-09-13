# Codex runtime notes for /graph

Read this when you are about to dispatch a wave under Codex, or when a wave misbehaves there.
The body of the skill assumes these facts; this file is where the Codex-specific ones live.

## Skill discovery and loading

- **Roots.** Codex discovers skills in `<project>/.codex/skills`, every `.agents/skills` from the
  project root down to cwd, `$CODEX_HOME/skills`, `~/.agents/skills` and `/etc/codex/skills`,
  recursively to depth 6 — so this collection's nested `skills/<bucket>/<name>/` layout is served
  as-is.
- **No `skill` tool.** The catalog lists each entry as
  `- name: description (file: <path>/SKILL.md)`; open that `SKILL.md` yourself with
  `exec_command` when you need it. Relative paths (`scripts/…`, `references/…`) resolve against
  the directory holding that `SKILL.md`, i.e. `<SKILL_DIR>`.
- **Explicit invocation.** `$graph` in a prompt injects the skill body as a user-role `<skill>`
  block. There is no `codex skill` subcommand.
- **Implicit invocation** is on by default and turned off per skill with
  `<skill>/agents/openai.yaml` → `policy.allow_implicit_invocation: false`. Only `name`,
  `description` and `metadata.short-description` are read from frontmatter; a
  `disable-model-invocation` key is ignored by Codex.

## Delegation

Codex ships two delegation generations. **V1 is on by default; V2 is off by default and is the
one this skill wants** — `list_agents` exists only in V2, and V2 gives the flat (un-namespaced)
tool names. Turn it on in `$CODEX_HOME/config.toml` (default `~/.codex/config.toml`):

```toml
[features.multi_agent_v2]
enabled = true
```

| Need | V2 (recommended) | V1 (default) |
|---|---|---|
| Start a node | `spawn_agent` | `multi_agent_v1.spawn_agent` |
| Start N nodes at once | N `spawn_agent` calls in **one** message | N `multi_agent_v1.spawn_agent` calls in one message |
| Wave barrier | children report back automatically; `wait_agent` only when you must block | `multi_agent_v1.wait_agent(targets[])` |
| Audit the children | `list_agents` | (no equivalent) |
| Retry / continue a node | `followup_task` | `multi_agent_v1.send_input` / `resume_agent` |
| Kill a stuck node | `interrupt_agent` | `multi_agent_v1.close_agent` |
| Long build or test inside a node | `exec_command` + `write_stdin` (background job) | same |
| Wave progress / task list | `update_plan` | `update_plan` |
| Hand over the tracker | an **absolute path** to `graph.html` (no `present`) | same |

Do not poll: Codex reports a child's completion back to the parent automatically, the same way
DSH does.

**Unverified, so plan around it:** whether several `spawn_agent` calls in one assistant message
are *dispatched* in parallel depends on `supports_parallel_tool_calls`, which is off by default.
If they are serialized, the children still run concurrently once started — the wave just starts
one after another instead of all at once. Do not assume the fan-out itself is instant, and keep
the wave small enough that the stagger does not matter.

## Depth, concurrency, cost

- **Depth.** V1 caps delegation at `agents.max_depth` (default **1**), so a node cannot delegate
  further — say so in the node prompt. V2 documents **no depth cap**, so "a node is a leaf" is a
  convention this skill enforces, not a limit the harness enforces.
- **Concurrency.** V2 caps live children at `agents.max_concurrent_threads_per_session`
  (default **4**): the parent's own thread plus **3 usable children**. That matches the skill's
  3–4 wave cap; keep a wave at 2–3 nodes anyway.
- **Cost shape.** A fresh child inherits the parent's prompt, tool schemas and skill catalog.
  There is no per-spawn `toolFilter` / `persona`; a `role` may only disable a fixed feature
  allowlist. The lever is the same as DSH's: keep nodes small and do trivia inline in the
  orchestrator.

## Workspace and handing back results

- **No per-child cwd and no worktree support** — a child inherits the parent's cwd, and every
  shell call is a fresh shell. That is the same as DSH, so the body's worktree discipline
  (absolute paths, one worktree per node) is unchanged and still mandatory.
- **No `present`** — hand the user an **absolute path** (`graph.html`, the wave branch) instead.
- **No `/goal`** — "implement" always means the node child writes the code.
- A child inherits the parent's sandbox and approval policy; it cannot be tightened per child.

## Optional hard guard

To make the skill's "never force-push to the default branch" rule a harness rule rather than a
prompt rule, add to `$CODEX_HOME/rules/default.rules`:

```text
prefix_rule(pattern=["git", "push"], decision="forbidden")
```

A trusted `PreToolUse` hook that exits 2 does the same job. Neither is required — the skill works
without it.
