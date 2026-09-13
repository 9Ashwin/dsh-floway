# DSH runtime notes for loop-it

Read this when you run the serial loop under DeepSeek Harness: the body's
neutral actions (delegate, task list, background job) map to the tools, config
keys and discovery rules below.

## Loading and invoking this skill

DSH discovers a skill at `<root>/<name>/SKILL.md` or `<root>/<name>.md` one
level below a scanned root. Nested trees such as this repo's
`skills/<bucket>/<name>/` are deliberately not discovered, which is why the
bundle lists every bucket as its own root (`cordis.patch.yml`) and a copied
`~/.agents/skills/loop-it` works flat. Roots are ranked, and the filesystem
provider resolves a duplicate skill name by rank, lowest first:

| Rank | Source | Path |
|---|---|---|
| 100 | project DSH | `<projectRoot>/.dsh/skills` |
| 200 | project agents | `<projectRoot>/.agents/skills` |
| 300 | custom | `Config.customSkillDirs` |
| 400 | user DSH | `$DSH_HOME/skills` (default `~/.dsh/skills`) |
| 500 | user agents | `$DSH_AGENTS_HOME/skills` (default `~/.agents/skills`) |
| 600 | bundled | `bundledSkillDir`, when configured |

`projectRoot` is the nearest ancestor holding `.git`. The `skill` tool loads by
exact name and returns the body in a canonical `<skill_content>` block together
with a `<skill_resources>` resource block; its directory form reads
`Base directory for this skill: <path>`, and that absolute path is what
`<SKILL_DIR>` resolves from. Typing `/loop-it` is the human entry point (a
user-invocable skill is injected directly), and `disable-model-invocation` is
the catalog opt-out. This skill is model-invocable, so both paths work.

## Delegation

| Need | Tool |
|---|---|
| Do one issue inline (the loop default) | — |
| Start a fresh child | `subagent` |
| Start a child that inherits this conversation | `subagent_fork` |
| Continue / retry a child | `send_message(child_id, …)` |
| Interrupt a child's current turn | `interrupt_agent(child_id)` |
| Audit the children you started | `list_agents(scope="descendants")` |

Calls run in the background by default and return a durable child id immediately,
so several calls in one assistant message are concurrent; the parent is notified
when a child settles, and must never poll. Delegation depth is capped at 3 by
default (`maxDepth`), so a child at depth 1 must not delegate further. Per-child
`toolFilter` and `persona` are deployment-level plugin config, not skill fields.
A child's approval policy is pinned to `never`.

## Task list, background work, long-horizon goals

- `todo_write` keeps the task list, one row per issue; `job_*` (`job_list`,
  `job_output`, `job_kill`) runs and collects a long build or test as a
  background job. DSH has no `present` — hand the report over as an absolute
  path.
- `/goal` is a DSH command — the human-facing half of the goal surface — not a
  skill the loop runs. The model-facing half (`create_goal` / `update_goal`) only
  executes for a direct top-level human turn, so the loop must not try to mint a
  long-horizon goal for itself.
