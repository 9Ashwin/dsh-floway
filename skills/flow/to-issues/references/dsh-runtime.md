# DSH runtime notes for to-issues

Read this when publishing Issues under DeepSeek Harness, or when the body's
"fresh child" wording needs a tool name. The decomposition itself and the
`gh issue create` path are harness-independent — only discovery, invocation and
the dispatch rows below are DSH-specific.

## Loading and invoking this skill

DSH discovers a skill at `<root>/<name>/SKILL.md` one level below a scanned root,
so the nested `skills/flow/to-issues/` layout must be flattened on install (the
bundle lists each bucket as its own root; a copied `~/.agents/skills/to-issues`
is already flat). `disable-model-invocation` is the catalog opt-out, and this
skill does not set it. The `skill` tool loads by exact name and returns the body
in a canonical `<skill_content>` block with a `<skill_resources>` resource block
whose directory form reads `Base directory for this skill: <path>` — that
absolute path is what `<SKILL_DIR>` resolves from, though this skill ships no
scripts. Typing `/to-issues` is the human entry point.

## Dispatch mapping

The body's "how to run it" table tells the user how to consume the Issues. Two
body phrasings map to a DSH tool:

| Body wording | DSH |
|---|---|
| a **fresh child** with the Issue body as a self-contained prompt | `subagent` |
| a **forked child** that inherits context | `subagent_fork` |

The GitHub-CLI publishing path needs no mapping: `gh` runs the same way on every
host. The other rows are already neutral — `/loop-it` and `/graph` are DSH skills,
and a long-running objective is the human's `/goal`, not something the model
starts.
