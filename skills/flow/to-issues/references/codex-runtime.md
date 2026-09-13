# Codex runtime notes for to-issues

Read this when publishing Issues under Codex, or when the body's "fresh child"
wording needs a tool name. The decomposition itself and the `gh issue create`
path are harness-independent — only discovery, invocation and one dispatch row
below are Codex-specific.

## Discovery and invocation

Codex discovers skills recursively to depth 6, so the nested
`skills/flow/to-issues/` layout works under a project `<root>/.codex/skills`, any
`.agents/skills` from the project root down to the cwd, `$CODEX_HOME/skills`,
`~/.agents/skills`, or `/etc/codex/skills`. There is no `skill` tool: the catalog
lists `- name: description (file: <path>/SKILL.md)`, and the model opens that
SKILL.md itself with `exec_command`. Typing `$to-issues` in a prompt injects the
body as a user-role `<skill>` block. The skill ships no scripts, so the only
relative path in play is this file.

## Dispatch mapping

The body's "how to run it" table tells the user how to consume the Issues. Only
one row maps to a Codex tool:

| Body wording | Codex |
|---|---|
| a **fresh child** with the Issue body as a self-contained prompt | `spawn_agent` (V2: `followup_task` continues it) |

The other rows need no mapping: `/loop-it` and `/graph` are catalog skills, and a
long-running objective has no Codex command — the human owns it.
