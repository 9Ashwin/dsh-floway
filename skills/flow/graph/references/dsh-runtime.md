# DSH runtime notes for /graph

Read this when a wave misbehaves, when you are about to spawn nodes, or when you need the
exact mechanics. The body of the skill assumes these facts; this file is where they live so
the body stays short.

## Delegation

`subagent` starts a **fresh** child that does not see this conversation; `subagent_fork` is the
variant that inherits it. Calls run in the background by default and return a durable child id
immediately, so **several `subagent` calls in one assistant message are concurrent**. A
background child reports back through a **settlement notice** — never poll for it, never
busy-wait; when the notice arrives, that node is done.

| Need | Tool |
|---|---|
| Start a node | `subagent` (fresh context) |
| Start N nodes at once | N `subagent` calls in **one** assistant message |
| Wave barrier | wait for every node's settlement notice |
| Audit the tree | `list_agents(scope="descendants")` |
| Retry / continue a node | `send_message(child_id, ...)` |
| Kill a stuck node | `interrupt_agent(child_id)` |
| Long build or test inside a node | background jobs (`job_*`) |
| Wave progress | `todo_write`, and `present` for `graph.html` |

## The two traps, in DSH terms

The body states the harness-independent facts; this is how they bite in DSH:

1. **Relative paths.** `read` / `write` / `edit` resolve a *relative* path against the calling
   session's cwd — the main checkout, not the caller's worktree. A node that writes
   `internal/foo.go` writes into the shared tree. **Inside a node, always pass absolute paths
   under its worktree.**
2. **Fresh shells.** `cd` does not persist between calls. Pass `workdir=<abs worktree>`, or
   prefix `cd <abs worktree> && …` in the same command. A bare `go test ./...` runs in the main
   checkout.

The orchestrator's own leak check (`git status --porcelain` on the shared checkout before
merging) is what proves the discipline held.

## Depth, concurrency, cost

- **Depth.** Delegation depth is capped at 3 by default (the orchestrator is depth 0), so a node
  is depth 1 and must not delegate further. Say so in the node prompt.
- **Concurrency.** The harness does not cap how many continuable children one parent may hold.
  The wave cap (Step 2 of the skill, default 3–4) is the only brake, so enforce it yourself.
- **Cost shape.** A fresh child joins the parent's composition, so it receives the *same* system
  prompt, the *same* full tool schemas and the *same* skill catalog; none of that is trimmed by
  depth, and no token budget exists — round counts are the only bound. Only the deployment can
  trim a child (`toolFilter` / `persona` on the subagent row are plugin config, not skill
  fields; the model-facing `subagent` tool takes no such argument). Every child therefore pays
  that fixed overhead for its whole life, which is why this skill ends a node at "committed"
  instead of extending it into review and shipping, and why trivial work belongs inline in the
  orchestrator rather than in a node.
  A deployment *can* hand nodes a cheaper child: `toolFilter.deny: [skill]` on a second
  `@deepseek-ai/dsh-tool-subagent` row removes that child's catalog and loader outright, because
  the catalog is visibility-matched to the `skill` tool. `references/lean-subagent.md` has the
  paste-ready patch, the measured saving and the caveats — read it before promising a saving.
- **Model routing (opt-in, off by default).** If the deployment enabled the host
  `subagent-model-selection` setting, `subagent` also accepts `provider`, `model` and
  `reasoning_effort`, and `list_subagent_models` appears. When those fields are absent from the
  schema they are not available — every node inherits the parent's route. Do not plan around
  routing you cannot see.

## `/goal` and other skills

`/goal` is a DSH **command**, not a skill: typing it is a human action. The model side of the
same surface is the goal tools (`create_goal` / `update_goal`), but `create_goal` only runs in a
**direct top-level human turn** — a node child, whose authority is a subagent's, cannot mint a
long-horizon goal for itself, and neither can the orchestrator mid-wave. "Implement" always means
the node child writes the code. `/review-it` and `/ship-it` ARE real skills and are callable — by
the orchestrator, once per wave.

`<SKILL_DIR>` in commands is defined once in `SKILL.md`: this skill's own directory (absolute).
DSH prepends a resource block on every skill load (`<skill_resources>` /
`Base directory for this skill: <path>`) telling you to resolve the skill's relative paths
against it. The bundled default is `~/.agents/skills/graph`.

## Branch and worktree layout

```bash
ROOT="$(git rev-parse --show-toplevel)"
# The default branch is not always `main`. Resolve it once and use $BASE everywhere below:
# a repo whose default is `master` fails every command that assumes otherwise.
BASE="$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')"
BASE="${BASE:-$(git rev-parse --abbrev-ref HEAD)}"
mkdir -p "$(dirname "$ROOT")/.graph-worktrees"
WT="$(cd "$(dirname "$ROOT")/.graph-worktrees" && pwd)/node-{N}"
git worktree add -b feat/node-{N}-{slug} "$WT" "$BASE"
echo "$WT"      # this absolute path goes into the node prompt
```

Nodes commit to `feat/node-{N}-{slug}`. The wave integrates them into `wave-{K}-{slug}` off
the default branch (`$BASE`), and that branch is what gets reviewed and shipped. Remove a finished worktree with
`git worktree remove <abs path>`; keep a failed one for investigation.

## State file and tracker

`.graph_state` lives at the repo root and must be in `.gitignore`. Commit that ignore rule before
the first wave: it is a tracked file, so an uncommitted edit would make the Step 4 leak check flag
the orchestrator itself. The planner script owns it — never hand-write it. Its schema:

```json
{
  "version": 1,
  "updated_at": "2026-07-21T10:30:00Z",
  "task": "Add user auth",
  "repo": "owner/repo",
  "waves": [[1, 2], [3, 4], [5]],
  "current_wave": 1,
  "nodes": {
    "1": { "title": "db schema", "deps": [], "scope": ["internal/db"],
           "type": "backend", "criteria": [], "status": "shipped", "commit": "a7b2b8d" },
    "5": { "title": "integration", "deps": [3, 4], "status": "blocked", "error": "dep #3 failed" }
  }
}
```

Statuses: `pending | in_progress | shipped | failed | blocked | skipped`. `shipped` and
`skipped` are complete; `failed` and `blocked` stall dependents but do not hold a wave open
forever — the orchestrator decides whether to retry, skip or stop.

Render the live dashboard any time (it auto-refreshes every 5 s; a `present` call re-surfaces it
in DSH):

```bash
python3 <SKILL_DIR>/scripts/render_graph_html.py .graph_state graph.html
```

On resume: `python3 <SKILL_DIR>/scripts/graph_state.py show`, ask the user about `failed` nodes
(retry or skip), and continue from `current_wave`.

## Why review and ship are wave-scoped

- A per-node `/review-it` is a **self-review**: the agent that just wrote the code re-reads it
  with the same assumptions, on a diff that may not survive integration. The same tokens buy
  much less signal than one review of the integrated diff by a reader who did not write it.
- A per-node `/ship-it` means **N PRs**: N CI runs, N merges, and N chances for a merge conflict
  to stall a wave that was otherwise finished. One wave PR collapses all three to one.
- The harness documents no policy either way; this placement is a judgement about where the
  tokens and the wall-clock actually go, and it is the reason the node prompt stops at commit.

Wave-scoping has real costs, and the skill pays them down rather than pretending they are absent:

- **One squash commit buries N features**, so reverting one means a manual revert. That is why the
  wave PR carries the per-item evidence table (commit, issue, proving test) — the commits are the
  only handle left after the squash.
- **One review pass over N feature diffs dilutes attention.** That is why Step 4 reviews section by
  section and spends the pass on the seams between nodes, which is where a wave review is actually
  stronger than a per-node one.
- **A stalled node can drag a whole wave.** That is why retry-in-place comes first and why a failed
  node is dropped from the wave branch once its dependents are `blocked`: the siblings are
  independent by construction, so holding them back buys nothing.
- **A bigger wave is a bigger blast radius.** Keep waves at 2–3 nodes when the extra parallelism
  does not buy much; per-node PRs remain the right shape when each feature must be independently
  revertible or reviewed.
