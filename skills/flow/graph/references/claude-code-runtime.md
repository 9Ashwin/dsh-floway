# Claude Code runtime notes for /graph

Read this when you are about to dispatch a wave under Claude Code, or when a wave misbehaves
there. The body of the skill assumes these facts; this file is where the Claude Code-specific
ones live.

## Skill discovery and loading

- **Roots.** Claude Code discovers a skill at `~/.claude/skills/<name>/SKILL.md` (personal) and
  `<project>/.claude/skills/<name>/SKILL.md` (project). A skill directory holds `SKILL.md` plus any
  `references/`, `scripts/` and `assets/`. Plugins contribute their skills through the plugin
  manifest's `skills` list, which is why this collection ships **one plugin per bucket**
  (`skills/<bucket>/.claude-plugin/plugin.json`, declared in `.claude-plugin/marketplace.json`)
  enumerating its own `./<name>` paths — that is what serves the `skills/<bucket>/<name>/` layout to
  a plugin install, and it is also what makes `npx skills add` group its picker by bucket instead of
  listing all 26 skills flat.
- **Loading.** The model loads a skill through the **`Skill` tool** by name; a human types
  `/graph`. There is no separate host-level "skill" command beyond that. `<SKILL_DIR>` is the
  directory holding the `SKILL.md` the loader read; `references/…` and `scripts/…` resolve against
  it.
- **Frontmatter.** Only `name`, `description` and optionally `allowed-tools` are read. The
  collection keeps host-specific keys out of the frontmatter on purpose, so this skill ships
  **without `allowed-tools`** and Claude Code prompts for tool permission normally — see
  "Pre-approving tools" below if you would rather it did not.

## Delegation

A node is dispatched with the **`Agent` tool**; `subagent_type` selects the agent definition to
run. One `Agent` call runs to completion and hands its result back to the caller.

| Need | Claude Code mechanism |
|---|---|
| Start a node | `Agent` (fresh child; it does not see this conversation) |
| Start N nodes at once | N `Agent` calls in **one** assistant message |
| Wave barrier | every `Agent` call has returned |
| Audit the children | **none** — no `list_agents` equivalent |
| Retry / continue a node | **none** — no durable child id and no `send_message`; dispatch a fresh `Agent` |
| Kill a stuck node | no separate primitive; the `Agent` call ends when it returns |
| Long build or test inside a node | a normal tool call in that node's context (no `job_*` equivalent) |
| Wave progress | `TodoWrite` |
| Hand over the tracker | an **absolute path** to `graph.html` — there is no `present` |

**The missing continuation and audit primitives are a real gap, not a naming difference.** On DSH
the orchestrator gets a durable child id, can `send_message` a node to steer or retry it, and can
`list_agents(scope="descendants")` to see who is still running. Claude Code has none of those: an
`Agent` call returns only its final result, so "retry the node" always means constructing a
complete fresh prompt, and "who is still running" is answered only by which calls have not
returned yet. Plan the wave so this matters as little as possible — small nodes with
self-contained prompts, and an inline retry ladder in the orchestrator rather than a resumed child.

**Unverified, so plan around it:** whether several `Agent` calls in one assistant message are
*dispatched* in parallel. Even if they are serialized, each child runs to completion independently,
so the wave still fans out — it just starts one after another instead of all at once. Do not assume
the fan-out itself is instant, and keep the wave small enough that the stagger does not matter.

## Depth, concurrency, cost

- **Depth.** A node is a leaf: it must not delegate further. Say so in the node prompt. This is a
  convention the skill enforces, not a cap this reference can point at.
- **Concurrency.** This reference does not assume a host cap. The wave cap (Step 2 of the skill,
  default 3–4) is the only brake, so enforce it yourself and keep a wave at 2–3 nodes.
- **Cost shape.** A fresh child inherits the parent's system prompt, tool schemas and skill
  catalog; there is no per-child `toolFilter` / `persona` on the `Agent` call. The lever is the
  same as the other hosts: keep nodes small, and do trivia inline in the orchestrator rather than
  paying a child's fixed overhead for it.

## Workspace and handing back results

- **No per-child cwd and no worktree support** — a child inherits the parent's cwd, and every
  shell call is a fresh shell. That is the same as DSH and Codex, so the body's worktree discipline
  (absolute paths, one worktree per node, `cd <abs worktree> && …`) is unchanged and still
  mandatory.
- **No `present`** — hand the user an **absolute path** (`graph.html`, the wave branch) instead.
- **No `/goal`** — "implement" always means the node child writes the code.
- A child inherits the parent's permission mode; it cannot be tightened per child.

## Pre-approving tools (optional)

`allowed-tools` is Claude Code's permission pre-approval list. This skill ships without it, so the
host prompts for tool permission the first time — the skill works fine that way and needs no
change. A user who wants pre-approval adds the key themselves to this skill's frontmatter; for a
graph run the interesting entries are `git`, `python3` and the file tools:

```yaml
allowed-tools:
  - Bash(git:*)
  - Bash(gh:*)
  - Bash(python3:*)
  - Read
  - Write
  - Edit
```

Per-skill, the list should name only what that skill's own flow needs. Do not ship one: adding it
to `SKILL.md` would put a Claude-Code-only key into the harness-neutral frontmatter.

## Optional hard guard

To make the skill's "never force-push to the default branch" rule a host rule rather than a prompt
rule, add a `PreToolUse` hook that blocks the command outright; `allowed-tools` can also restrict
which tools this skill may use at all. Neither is required — the skill works without it.
