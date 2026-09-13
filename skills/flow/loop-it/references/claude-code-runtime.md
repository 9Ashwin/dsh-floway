# Claude Code runtime notes for loop-it

Read this when you run the serial loop under Claude Code: the body's neutral actions
(delegate, task list, background job) map to the tools, discovery rules and permission
mechanics below.

## Loading and invoking this skill

Claude Code discovers a skill at `~/.claude/skills/<name>/SKILL.md` (personal) and
`<project>/.claude/skills/<name>/SKILL.md` (project); a plugin contributes its skills through
the plugin manifest's `skills` list, which is how this collection's nested
`skills/flow/loop-it/` layout reaches a plugin install unchanged. The model loads a skill
through the **`Skill` tool** by name, and a human types `/loop-it`. There is no separate
host-level "skill" command beyond that.

`<SKILL_DIR>` is the directory holding the `SKILL.md` the loader read, so `scripts/…` and
`references/…` resolve against it. The collection keeps host-specific keys out of the
frontmatter, so this skill ships **without `allowed-tools`** and Claude Code prompts for tool
permission normally. To pre-approve instead, add the key to this skill's frontmatter yourself —
for the loop that is `git`, `gh` and `python3`:

```yaml
allowed-tools:
  - Bash(git:*)
  - Bash(gh:*)
  - Bash(python3:*)
  - Read
  - Write
  - Edit
```

Do not ship it: `allowed-tools` is Claude-Code-only and must stay out of the harness-neutral
frontmatter.

## Delegation

The loop is serial and inline by default: one issue at a time in the orchestrator's own
context. Reach for an `Agent` child only when a single issue is worth isolating.

| Need | Claude Code mechanism |
|---|---|
| Do one issue inline (the loop default) | the orchestrator itself |
| Start a fresh child | `Agent` (`subagent_type` selects the agent definition) |
| Continue / retry a child | **none** — no durable child id and no `send_message` |
| Audit the children you started | **none** — no `list_agents` equivalent |
| Interrupt a child | no separate primitive; the `Agent` call ends when it returns |
| Keep the task list current | `TodoWrite` |
| Run a long build or test | a normal tool call in the current context (no `job_*` equivalent) |
| Hand the report to the user | an absolute path — there is no `present` |

**The missing continuation and audit primitives are a real gap.** DSH returns a durable child id
immediately, lets you `send_message` a child to steer or retry it, and lets you
`list_agents(scope="descendants")` to see who is still running. Claude Code has none of that: an
`Agent` call returns its result to the caller, and once it returns the child is gone. This suits
the loop's serial default — the orchestrator does the work — but it means an isolated issue is a
single-shot child: retrying it constructs a complete fresh prompt, and there is no audit of what
was dispatched. Prefer inline implementation, and keep any child's prompt self-contained.

## Task list, background work, long-horizon goals

- **Task list.** `TodoWrite` keeps the list, one row per issue; update it on the same state
  transition as `.loop-state.json`, and let the script win on any conflict, exactly as the body
  says.
- **Background work.** Run a long build or test as a normal tool call and let it finish; there is
  no `job_list` / `job_output` / `job_kill` pair to start a job and collect it separately. Do not
  plan around collecting a detached job later — that machinery does not exist here.
- **No `present`.** Hand the loop report over as an absolute path.
- **No `/goal`.** No host here offers the model a long-horizon objective it can start for itself;
  the body already says "implement" means the agent implements inline, and that is the whole story.

## Permissions and hard guards

`allowed-tools` restricts which tools this skill may use; a `PreToolUse` hook can block a command
outright, which is the host-level way to make "never force-push" a rule rather than a prompt
instruction. Neither is required — the loop works with normal permission prompts.
