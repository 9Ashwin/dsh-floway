# Node prompt template

Paste this into each wave's child dispatch, substituting every `{…}` placeholder. It is
self-contained on purpose: a fresh child sees none of the orchestrator's conversation, so
anything it needs must be in the prompt.

Keep it this short. A node's own context is where its tokens go, and the three numbered steps
are the whole contract — implement, prove, commit. Review and shipping happen once per wave,
so they must not appear here.

```markdown
You are implementing ONE node of a task graph, working in an ISOLATED git worktree.

Worktree (ABSOLUTE path — use it verbatim): {WT}
Branch:    feat/node-{N}-{slug}   (already created and checked out)
Node #{N}: {title}
Type:      {type}
Scope:     {scope_hint}  — stay within these files; do not touch other nodes' scope

WORKING-DIRECTORY DISCIPLINE (read this twice — getting it wrong corrupts other nodes):
- Your file tools resolve RELATIVE paths against the ORCHESTRATOR's checkout, NOT this
  worktree. ALWAYS pass absolute paths: `{WT}/internal/foo.go`, never `internal/foo.go`.
- Every bash call starts a FRESH shell; `cd` does NOT persist between calls.
  Pass `workdir={WT}` if your shell tool takes a working directory, or prefix
  `cd {WT} && …` in the same command.
- Never run a bare `go test ./...` / `npm test` / `cargo test` without one of those,
  or you will build and test the main checkout while a sibling node edits it.
- Sanity check before you finish: `git -C {WT} status --short` must list your own edits.

Acceptance criteria (all must pass):
- [ ] {criterion 1}
- [ ] {criterion 2}

Context (dependency nodes are already merged into the default branch):
{summaries of dependency nodes' outputs, or the referenced PRD/SPEC excerpt}

Your job — implement, prove, commit. Nothing else:
1. IMPLEMENT (inline — you write the code): read the node + any referenced PRD/SPEC,
   read adjacent code, implement to satisfy EVERY acceptance criterion.
2. PROVE IT: run the project's own gates inside the worktree and iterate until green
   (e.g. `cd {WT} && go build ./... && go vet ./... && go test ./...`). Add or update
   the tests the criteria imply — a criterion you did not test is not satisfied.
3. COMMIT on your branch: `git -C {WT} add -A`, then commit with a message that names
   the node (`feat(node-{N}): {title}`). Check `git -C {WT} status --short` first and
   keep build junk out of the commit.
   Do NOT push, do NOT open a PR, do NOT merge, and do NOT run the **review-it**,
   **ship-it** or **implement** skills — the orchestrator reviews and ships the whole wave
   once, after integration. Reviewing here would only be you re-reading your own work.
   Those three numbered steps above ARE your whole contract.

Constraints:
- Work ONLY inside your worktree. Do NOT edit files outside {scope_hint}.
- "implement" means YOU write the code — there is no command that does it for you.
- Do NOT dispatch your own child agents: this node is a leaf.
- If you cannot satisfy a criterion, STOP and report what's blocking — don't fake it. A
  clean FAIL with a precise reason is worth more than a green claim the gates contradict.

Return your report in two parts.

**Prose first**, for the human reading it: what you did, anything that surprised you, and
anything the orchestrator needs to know that the block below cannot carry.

**Then the structured block**, as the very last thing in your reply: a fenced ```json block
holding exactly these keys and nothing else. It is parsed, so it has to be valid JSON and it has
to be last — a missing key, a second block after it, or prose after it means the orchestrator has
to read the whole report by hand, which is the cost this block exists to remove.

```json
{
  "node": 3,
  "status": "PASS",
  "commit": "a1b2c3d",
  "files": ["src/text.py", "tests/test_text.py"],
  "gates": [{"command": "python3 -m unittest discover -s tests -q", "exit": 0}],
  "new_work": []
}
```

- `node` — the node id, as a number.
- `status` — `"PASS"` only if every acceptance criterion is met and the gates are green.
  Anything else is `"FAIL"`, with the reason in your prose.
- `commit` — the commit sha on your branch, or `null` if you did not commit.
- `files` — every file you changed, as repo-relative paths.
- `gates` — the exact commands you ran and their exit codes. Empty only if the project has no
  gates, and then say so in the prose.
- `new_work` — titles of work you discovered that the graph does not capture, or `[]`. Do not
  invent entries to look thorough; `[]` is the normal answer.
```

## Filling the placeholders

- `{WT}` — the absolute worktree path the orchestrator just created. Never a relative path.
- `{scope_hint}` — the node's `scope` from the plan, as a human-readable list. It is a promise
  about which files merge cleanly; a node that needs to leave it should say so in its report
  instead of silently editing elsewhere.
- `{summaries …}` — one or two lines per dependency: what it added, where, and anything the
  node must know. The child cannot read the earlier nodes' conversations, so this is the only
  channel the graph has. Keep it factual; the integration diff is not a substitute.
- `{criterion …}` — copy the criteria verbatim from the plan. Vague criteria produce vague
  reports, and the wave review is where that becomes visible.

## Reading the report

A node report is evidence, not a verdict. Before merging: the gate command it names should be
the project's real gate, the leak check should be clean, and `NEW_WORK:` lines drive the
re-plan. If a node reports PASS while the integrated gates fail, treat the integration as the
truth — the node tested its worktree, not the combination.
