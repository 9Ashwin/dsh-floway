# DSH runtime notes for review-it

Read this when the review is running under DeepSeek Harness: how the skill was loaded, which
reviewer to invoke, and which tool replaces which neutral action. The body of the skill assumes
these facts; this file is where they live so the body stays short.

## Loading and invoking this skill

DSH discovers skills from ranked roots, and the lowest rank wins when one name appears in more
than one, so the nearest layer wins:

| Rank | Root |
|---|---|
| 100 | project `<root>/.dsh/skills` |
| 200 | project `<root>/.agents/skills` |
| 300 | custom roots (`customSkillDirs`; the bundle patch's per-bucket entries) |
| 400 | `$DSH_HOME/skills` (`$DSH_HOME` defaults to `~/.dsh`) |
| 500 | `~/.agents/skills` |
| 600 | bundled (`$DSH_BUNDLED_SKILL_DIR`) |

A root is scanned exactly one level deep: `<root>/<name>/SKILL.md`. `skills/flow/review-it/` is
two levels below `skills/`, so it is not a root on its own: `cordis.patch.yml` lists each bucket
as a separate custom root, and `npx skills` flattens `skills/<bucket>/<name>` to
`~/.agents/skills/<name>` on install. That is why a plain source checkout is not a skill root.

The model loads a skill through the `skill` tool. The loader prepends a
`<skill_content name="review-it">` block whose `<skill_resources>` section carries
`Base directory for this skill: <path>` and tells the model to resolve relative paths against it.
That path is `<SKILL_DIR>`; the bundled default is `~/.agents/skills/review-it`. Referenced files
(`scripts/review-it`, `references/…`) load only as needed.

`/review-it` is the human entry point — a direct invocation of this skill — while the model loads
it through the `skill` tool.

## Reviewing

DSH wires up no external review CLI, so the calling agent is the reviewer: it generates the diff
and applies the Review Focus itself. The per-CLI command matrix, including DSH's
`none — review it yourself` row, stays in [`other-clis.md`](other-clis.md). The bundled runner
detects DSH from `DSH_SESSION_ID` / `DSH_HOME` and falls back to DSH when no host probe matches.

## Delegation and completion

`subagent` starts a fresh child that does not see this conversation; `subagent_fork` is the
variant that inherits it. Calls run in the background by default and return a durable child id
immediately, so several calls in one assistant message are concurrent. A background child reports
back through a settle notice the runtime injects into the parent — never poll for it, never
busy-wait. Continue a child with `send_message(child_id, ...)`, stop one with
`interrupt_agent(child_id)`, and audit the whole tree with `list_agents(scope="descendants")`.

Delegation depth is capped at 3, so the orchestrator is depth 0, a node is depth 1, and a node
must not delegate further. A child joins the parent's composition (same system prompt, tool
schemas and skill catalog); only the deployment can trim it, because `toolFilter` and `persona`
are plugin config on the subagent row and the model-facing `subagent` tool accepts no such
argument. Child approval is pinned to `never`. There is no per-child cwd or worktree argument and
every bash call is a fresh shell, so hand a child absolute paths.

| Need | Tool |
|---|---|
| Load this skill | `skill` (loader adds `<skill_content>` + `Base directory for this skill`) |
| Keep your task list current | `todo_write` |
| Run a long build or test | background jobs (`job_*`) |
| Dispatch a fresh child | `subagent` |
| Dispatch a child that inherits this conversation | `subagent_fork` |
| Continue a child | `send_message(child_id, ...)` |
| Audit the children | `list_agents(scope="descendants")` |
| Interrupt a child | `interrupt_agent(child_id)` |
| Hand a file to the user | `present` |
| Run the reviewer | none — the calling agent reviews |
