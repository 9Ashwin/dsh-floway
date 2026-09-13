---
name: graph
description: "Parallel implementation: plan the DAG by script, one subagent per node per wave in its own git worktree, then review and ship each wave once. Triggers: graph, 并发实现, 并行实现, 任务图, DAG, fan-out."
user-invocable: true
---

# graph — DAG → parallel waves

Turn a task (or PRD / SPEC / issue set) into a directed acyclic graph of work units, layer it
into waves, and implement each wave's independent nodes concurrently with `subagent` children,
one git worktree each. Between waves a fan-in barrier integrates, reviews and ships **once**.

**This skill is guidance, not a script.** The ordering arithmetic — cycle detection, scope
collisions, wave layering, checkpoint transitions — belongs to `scripts/graph_state.py`, which
is tested. Run it and read its summary; do not re-derive the layering by hand.

## When to use it

Use it when the work has **genuine parallelism**: two or more units that do not depend on each
other and do not edit the same logic. That is the whole value — a wave only pays for itself if
the nodes inside it are truly independent.

Do not use it when:

- the whole change fits one context window — just implement it;
- there is one unit, or two that share files — call `subagent` directly, or use `/loop-it`;
- the units are layered rather than independent (schema → API → UI, each waiting on the last) —
  that is a chain, and `/loop-it` is the right shape;
- you would be spawning a node for something you could finish inline in a few tool calls. Every
  child pays the parent's full prompt, tool schemas and skill catalog for its whole life
  (`references/dsh-runtime.md` explains the cost shape), so a trivial node costs far more than
  it saves.

## The contract: three scopes

| Scope | Does | Does not |
|-------|------|----------|
| **node** | implement, prove with the project's gates, commit on its own branch | push, open a PR, merge, review itself |
| **wave** | leak check, integrate, gates on the integrated tree, **review once**, **ship once** | — |
| **run** | final summary, close out the tracker, re-plan leftovers | — |

Review and ship are wave-scoped on purpose. A per-node `/review-it` is a self-review of a diff
that may not survive integration, and a per-node `/ship-it` means N PRs, N CI runs and N chances
to stall on a merge conflict. Per-node PRs remain available when the user explicitly wants a
reviewable PR per node — that is the expensive mode; say so and confirm before using it.

## Step 1: Decompose into nodes

Accept a free-form task, a PRD/SPEC, or an existing issue set. Reuse `/to-issues`' rules: one
node per user story, split large stories, merge tiny ones, and give every node real acceptance
criteria.

Write a nodes file — this is the planner's only input:

```json
{
  "task": "Add user auth",
  "repo": "owner/repo",
  "nodes": [
    {"id": 1, "title": "db schema", "deps": [], "scope": "internal/db",
     "type": "backend", "criteria": ["migration applies on a fresh database"]},
    {"id": 2, "title": "API handler", "deps": [1], "scope": "internal/api", "type": "backend"}
  ]
}
```

`scope` is the comma-separated set of files/directories the node expects to touch. It is how
the planner detects that two dependency-free nodes are not actually independent. Keep a shared
*wiring* file (a router, a `main`, a DI container) **out** of every scope: append-only edits to
such files merge cleanly, and listing them would serialize the whole graph into a chain.

## Step 2: Plan, then confirm with the user

```bash
python3 <SKILL_DIR>/scripts/graph_state.py plan --nodes nodes.json --max-parallel 4
python3 <SKILL_DIR>/scripts/render_graph_html.py .graph_state graph.html
```

The planner validates (cycles are fatal, phantom and self edges are dropped with warnings),
layers the waves so dependencies and disjoint scopes both hold, writes `.graph_state`, and
prints the plan, a Mermaid diagram and the wave-0 dispatch list. `<SKILL_DIR>` is this skill's
own directory — the loader states it as `Base directory for this skill`.

Keep the plan input out of git along with the checkpoint it produces:
`grep -qxF 'nodes.json' .gitignore || printf 'nodes.json\n.graph_state\ngraph.html\n' >> .gitignore`.
The nodes file is per-run working state, like `.graph_state`; committing it would make every
wave look dirty.

Show the user the plan and let them adjust nodes, edges or the concurrency cap **before** any
subagent starts. Then `present` `graph.html` so they can watch it live.

## Step 3: Run a wave

Create one worktree per node in the wave, capturing each **absolute** path:

```bash
ROOT="$(git rev-parse --show-toplevel)"
mkdir -p "$(dirname "$ROOT")/.graph-worktrees"
WT="$(cd "$(dirname "$ROOT")/.graph-worktrees" && pwd)/node-{N}"
git worktree add -b feat/node-{N}-{slug} "$WT" main
```

Then dispatch: **one delegation call per node, all in a single assistant message** — that is
what makes them concurrent. Each prompt is self-contained (a fresh child sees none of this
conversation); copy `references/node-prompt.md` and fill the placeholders.

If your tool list carries **`subagent_lean`** (a deployment-provided lean delegation tool that
withholds the skill catalog and the spawning tools), use it for nodes — a node needs no skill,
because the node prompt already carries its whole contract. Otherwise use `subagent`. Keep the
normal `subagent` for children that *do* load skills: a wave reviewer, a research child.

Two facts the node prompt must carry, because DSH gives a child no cwd of its own: file tools
resolve relative paths against **this** checkout, and every bash call is a fresh shell. Both are
why the worktree path is passed as an absolute path and every command runs with
`workdir=<abs worktree>` or `cd <abs worktree> && …`.

Do not poll. Do the wave bookkeeping while the children run; each one reports back with a
settlement notice. `list_agents(scope="descendants")` audits who is still running.

## Step 4: Fan in — barrier, integrate, review, ship

The barrier is the arrival of **every** node's settlement notice. Then, in order:

**A wave of one node has nothing to integrate.** Skip the wave branch and the merge ceremony
for it — review and ship that node's branch directly against `main`. The wave exists to combine
nodes; with one node it is pure ceremony.

1. **Leak check, then mark.** `git status --porcelain` on the shared checkout must be clean and
   each node's files must exist only on its branch — that is the evidence the absolute-path
   discipline held. (Untracked files belonging to *another* session are not a leak; a modified
   *tracked* file is.) Record each outcome with the planner:
   ```bash
   python3 <SKILL_DIR>/scripts/graph_state.py set --node {N} --status shipped --commit {sha}
   ```
   It prints whether the wave is still open, and on the last node it prints the fan-in checklist.
2. **Integrate and verify the combination, not the parts.** Merge only the nodes that `shipped`
   — a `failed` node's branch is never merged:
   ```bash
   git checkout main && git pull
   git checkout -b wave-{K}-{slug}              # skipped when the wave has one node
   git merge --no-ff feat/node-{N}-{slug}      # once per shipped node in the wave
   <the project's gates>                        # e.g. ./run_all.sh, on the integrated tree
   ```
   Every node passing alone while the integration fails is a normal outcome. Fix it here, in the
   wave. If a node failed, see Step 5 — the rest of the wave still ships when nothing in it
   depends on the failure.
3. **Review the wave once, node by node.** Target `git diff main...wave-{K}-{slug}` (or the
   single node's branch). Read it as **one section per node**, in planned order, and give the
   *seams* — shared interfaces, wiring/setup files, config and state that two nodes both touch —
   more attention than the nodes' interiors: that is the class of defect a per-node review
   structurally cannot see. The orchestrator reads it inline when it is small — it already holds
   the context, so it is the cheapest reader — and hands it to **one** fresh `subagent` when the
   diff is large or independence matters more. Apply `/review-it`'s Review Focus section by
   section, fix what is accepted, re-run the gates. This is the only review the wave gets; never
   skip it, and never let one feature's section absorb the whole pass.
4. **Ship the wave once** with `/ship-it`: one commit/PR, merge, close the issues the wave
   satisfied. One squash commit buries N features, so the PR body must carry `ship-it`'s
   per-item evidence table (commit, issue, the test that proves it, manual-acceptance status) —
   without it neither you nor the user can audit or revert a single feature afterwards.
5. Remove finished worktrees (keep failed ones), re-render the tracker, and checkpoint.
6. **Re-plan.** Read each node's `NEW_WORK:` line; if any is not `none`, add the node(s) and
   re-layer the remaining work with the planner before the next wave. Show the user the delta.

## Step 5: When a node fails

Retry in place first — `send_message(child_id, "<what failed + what to fix>")` reuses that
node's own context instead of paying for a fresh child. If it fails again, keep its worktree,
mark it `failed`, and mark every dependent node `blocked` (the planner prints them). Reuse
`/loop-it`'s error classes from `../loop-it/references/error-recovery.md` rather than inventing
new ones.

**A wave is not all-or-nothing.** Once the failed node's dependents are `blocked`, drop that
node from the wave branch and ship the rest — its siblings are independent by construction, so
making them wait for a re-plan buys nothing. Never merge the failed branch, and never mark it
`shipped` just to keep the wave moving. Offer the user the ladder in order: retry in place, retry
as a fresh node, then drop.

## Safety guards

- **Worktree isolation is mandatory** — two nodes implementing in one checkout corrupt each other.
- **Absolute paths inside a node are mandatory** — the failure mode is silent and it corrupts a wave.
- **Leak check before every merge** — a modified *tracked* file in the shared checkout means a node escaped its worktree; untracked files from another session are not a leak.
- **One review and one ship per wave** — per-node review is self-review; per-node PRs are the expensive mode.
- **Never force-push to `main`.** Nodes commit to their own branches; the wave ships one PR.
- **Respect the depth budget** — nodes are depth 1 and must not spawn their own subagents.
- **Cap concurrency** (3–4 by default), **prefer waves of 2–3 nodes**, and **keep the child count honest** — the wave is the blast radius of one bad integration, so do trivia inline.
- **Confirm the plan** before the first fan-out, and keep `.graph_state` + `graph.html` current.

## References

- `references/dsh-runtime.md` — delegation mechanics, the two workspace traps, depth/concurrency/cost, branch layout, state schema, and why review and ship are wave-scoped.
- `references/node-prompt.md` — the node prompt template, how to fill it, and how to read a node's report.
- `references/lean-subagent.md` — the deployment patch that strips a node child's skill catalog (optional cost lever), with its caveats.
- `scripts/graph_state.py` (`plan` / `set` / `show`) — validation, layering and checkpoints.
- `scripts/test_graph_state.py` — the planner's unit tests; run them after any edit to it.
- `scripts/render_graph_html.py` — the live `graph.html` dashboard.
