# Claude Code runtime notes for to-issues

Read this when publishing Issues under Claude Code, or when the body's "fresh child"
wording needs a tool name. The decomposition itself and the `gh issue create` path are
harness-independent — only discovery, invocation and one dispatch row below are
Claude Code-specific.

## Discovery and invocation

Claude Code discovers a skill at `~/.claude/skills/<name>/SKILL.md` (personal) and
`<project>/.claude/skills/<name>/SKILL.md` (project); a plugin contributes its skills
through the plugin manifest's `skills` list, so the nested `skills/flow/to-issues/` layout
is served by a plugin install unchanged. The model loads a skill through the **`Skill`
tool**; a human types `/to-issues`. There is no separate host-level "skill" command beyond
that. The skill ships no scripts, so the only relative path in play is this file, and the
frontmatter needs nothing Claude-Code-specific — no `allowed-tools` is shipped, so the host
prompts for tool permission normally; a user who wants pre-approval can add the key
themselves.

## Dispatch mapping

The body's "how to run it" table tells the user how to consume the Issues. Only one row maps
to a Claude Code tool:

| Body wording | Claude Code |
|---|---|
| a **fresh child** with the Issue body as a self-contained prompt | `Agent` (`subagent_type` selects the agent definition) |

There is no DSH-style `subagent_fork`: an `Agent` child does not inherit this conversation, and
once the call returns it cannot be continued or listed. The other rows need no mapping:
`/loop-it` and `/graph` are skills this host loads, and a long-running objective has no host
command — the human owns it.
