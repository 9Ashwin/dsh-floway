---
name: graph
description: "Parallel implementation: plan the DAG by script, one subagent per node per wave in its own git worktree, then review and ship each wave once. Triggers: graph, 并发实现, 并行实现, 任务图, DAG, fan-out."

---

# graph — DAG → parallel waves

Turn a task (or PRD / SPEC / issue set) into a directed acyclic graph of work units, layer it
into waves, and implement each wave's independent nodes concurrently by dispatching one fresh
child per node, one git worktree each. Between waves a fan-in barrier integrates, reviews and
ships **once**.

**This skill is guidance, not a script.** The ordering arithmetic — cycle detection, scope
collisions, wave layering, checkpoint transitions — belongs to `scripts/graph_state.py`, which
is tested. Run it and read its summary; do not re-derive the layering by hand.

## When to use it

Use it when the work has **genuine parallelism**: two or more units that do not depend on each
other and do not edit the same logic. That is the whole value — a wave only pays for itself if
the nodes inside it are truly independent.

Do not use it when:

- the whole change fits one context window — just implement it;
- there is one unit, or two that share files — dispatch one fresh child directly, or use the
  **loop-it** skill;
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
to stall on a merge conflict. The **walkthrough** is wave-scoped for the same reason: it proves
the integrated result, and its review gate produces the single PR body the wave ships. Per-node PRs remain available when the user explicitly wants a
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
the planner detects that two dependency-free nodes are not actually independent.

`hot_files` is the opposite list: shared *wiring* files (a router, a `main`, a route table, a DI
container, a type union) the node **will** touch but that must stay **out** of `scope`, because
listing them there would serialize the whole graph into a chain. The planner does not serialize on
them — it warns when two nodes in one wave declare the same hot file.

That warning exists because "append-only edits merge cleanly" has a premise, and the premise is
**each node edits its own region**. Two nodes appending to one import block, writing one route
table, or extending one type union are not append-only, and they will conflict at integration —
that is not a merge accident, it is the shape of the change. When the warning fires, either
serialize those nodes into different waves, or give one node ownership of the file and let the
others expose a registration hook for it. Treating the file as append-only when it is not is how
a wave ends up resolving the same conflict three times.

## Step 2: Plan, then confirm with the user

`<SKILL_DIR>` is this skill's own directory (absolute) — resolve it from the path the harness
reported when it loaded this skill. The bundled default is `~/.agents/skills/graph`.

```bash
python3 <SKILL_DIR>/scripts/graph_state.py plan --nodes nodes.json --max-parallel 4
python3 <SKILL_DIR>/scripts/render_graph_html.py .graph_state.json graph.html
```

The planner validates (cycles are fatal, phantom and self edges are dropped with warnings),
layers the waves so dependencies and disjoint scopes both hold, writes `.graph_state.json`, and
prints the plan, a Mermaid diagram and the dispatch list for the current wave. It also warns when
two nodes in one wave declare the same hot file.

**Re-planning mid-run keeps what shipped.** Add `--keep-shipped` when a node turns out to be
already satisfied, a node has to move, or the graph grew: every id that survives keeps its
`status`, `branch`, `commit` and error history, only new ids start pending, and ids you removed
are reported rather than silently dropped. Without the flag a re-plan resets everything to
pending, which is why re-planning used to mean re-recording the shipped nodes by hand.

`--max-parallel` is written into the checkpoint (`max_parallel`), so a later re-plan that omits
the flag reuses it instead of silently re-layering the waves; a re-plan that changes it says so.
The nodes file can carry `"max_parallel": 4` for the same reason — the cap shapes the layout, and
a layout nobody can reproduce is a layout nobody can check.


Keep the plan input out of git along with the checkpoint it produces:
`grep -qxF '.graph_state*' .gitignore || printf 'nodes.json\n.graph_state*\ngraph.html\n' >> .gitignore`,
then **commit that ignore rule before the first wave**. Step 4's leak check wants a clean shared
checkout, and an uncommitted `.gitignore` edit would make the orchestrator flag itself as the leak.
(If you would rather not commit an ignore rule, put the same lines in the untracked
`.git/info/exclude` instead.)

`.graph_state*` is a pattern on purpose, not a list of today's names. It covers the checkpoint under
every name a run can give it — the default `.graph_state.json`, the pre-rename `.graph_state` (still
**read**, so an in-flight graph keeps its progress and migrates on its next write), a per-run name
like `--state .graph_state-prd015`, and the transient `<path>.tmp` the script writes before
`os.replace`. The other two names are yours to choose: if this run passes `--state`/an output name
that is not the default, add those exact names too (`nodes-prd015.json`, `graph-prd015.html`) —
`git status --porcelain` after the first write is the check that nothing slipped through.

Show the user the plan and let them adjust nodes, edges or the concurrency cap **before** any
child starts. Then hand `graph.html` to the user so they can watch it live.

## Step 3: Run a wave

Create one worktree per node in the wave, capturing each **absolute** path:

```bash
ROOT="$(git rev-parse --show-toplevel)"
# The default branch is not always `main`. Resolve it once and use $BASE everywhere below:
# a repo whose default is `master` fails every command that assumes otherwise.
BASE="$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')"
BASE="${BASE:-$(git rev-parse --abbrev-ref HEAD)}"
mkdir -p "$(dirname "$ROOT")/.graph-worktrees"
WT="$(cd "$(dirname "$ROOT")/.graph-worktrees" && pwd)/node-{N}"
git worktree add -b feat/node-{N}-{slug} "$WT" "$BASE"   # `prompt` prints this exact line
```

Then dispatch: **one child per node, all in a single assistant message** — that is what makes
them concurrent. Each prompt is self-contained (a fresh child sees none of this conversation).

Render each node's prompt from the checkpoint rather than hand-writing it:

```bash
python3 <SKILL_DIR>/scripts/graph_state.py prompt --node {N}
```

That fills the worktree path, the branch, the title, the type, the scope, the hot files and the
acceptance criteria straight out of `.graph_state.json`, and prints the `git worktree add` line for the
branch it names. **The branch is the checkpoint's, not the script's:** if a `branch` is recorded
for the node it is used verbatim, and only an unrecorded node gets a name derived from its title —
in which case the header says the name was derived and that the branch does not exist yet. So
record the real name as soon as it exists, especially if it diverges from the derived one:

```bash
python3 <SKILL_DIR>/scripts/graph_state.py set --node {N} --status in_progress --branch {real-branch}
```

Two things are still left for you, and the render says so: the **dependency summaries** (no script
can know what an earlier node actually produced) and anything the issue body adds. Read the
rendered prompt before sending it: the generator removes the transcription errors, not the
judgement.

A deployment may trim a node child's tools — a node needs no skill, because the node prompt
already carries its whole contract, while the full-strength path is what a wave reviewer or a
research child needs. The optional lean-delegation cost lever lives in
`references/lean-subagent.md` and `references/dsh-runtime.md`.

Every node reports back in two parts: prose, then a structured block with a fixed key set
(`node` / `status` / `commit` / `files` / `gates` / `new_work`). Read the block for the mechanical
fields — it transcribes straight into the checkpoint — and read the prose for what the block
cannot carry. The block is the node's own account, so it is **not** evidence: the leak check, the
diffstat against the `files` it claims, and the integrated gates are what actually verify the
wave. A report whose `files` list disagrees with its diffstat is the cheapest possible catch, and
it only works if you compare rather than trust.

Two facts the node prompt must carry, because **a child gets no working directory of its own**
(both harnesses behave the same way): file tools resolve relative paths against the
**orchestrator's** checkout, and every shell call is a fresh shell. Both are why the worktree
path is passed as an absolute path and every command runs with the worktree as its working
directory (`cd <abs worktree> && …`).

Do not poll. Do the wave bookkeeping while the children run; **the parent is notified when a
child settles**. **Audit the children** you started to see who is still running.

## Step 4: Fan in — barrier, integrate, review, ship

The barrier is **every** node's child having settled. Then, in order:

**A wave of one node has nothing to integrate.** Skip the wave branch and the merge ceremony
for it — review and ship that node's branch directly against the default branch (`$BASE`). The wave exists to combine
nodes; with one node it is pure ceremony.

1. **Leak check, then mark.** `git status --porcelain` on the shared checkout must be clean and
   each node's files must exist only on its branch — that is the evidence the absolute-path
   discipline held. (Untracked files belonging to *another* session are not a leak; a modified
   *tracked* file is.) That is exactly why Step 2 commits the ignore rule up front: an
   uncommitted `.gitignore` edit would make the orchestrator flag itself as the leak.
   Record each outcome with the planner, **including the branch the node actually
   worked on** — everything downstream (the merge list below, a later re-plan, a
   rendered prompt) reads it from the checkpoint, so an unrecorded branch falls
   back to a name derived from the title:
   ```bash
   python3 <SKILL_DIR>/scripts/graph_state.py set --node {N} --status shipped --commit {sha} --branch {branch}
   ```
   It prints whether the wave is still open, and on the last node it prints the fan-in checklist.
2. **Integrate and verify the combination, not the parts.** Merge only the nodes that `shipped`
   — a `failed` node's branch is never merged:
   ```bash
   git checkout "$BASE"
   git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1 && git pull   # only with an upstream
   git checkout -b wave-{K}-{slug}              # skipped when the wave has one node
   git merge --no-ff feat/node-{N}-{slug}      # once per shipped node, using each node's recorded branch
   <the project's gates>                        # e.g. ./run_all.sh, on the integrated tree
   ```
   Every node passing alone while the integration fails is a normal outcome. Fix it here, in the
   wave. If a node failed, see Step 5 — the rest of the wave still ships when nothing in it
   depends on the failure.
3. **Review the wave once, node by node.** Target `git diff "$BASE"...wave-{K}-{slug}` (or the
   single node's branch). Read it as **one section per node**, in planned order, and give the
   *seams* — shared interfaces, wiring/setup files, config and state that two nodes both touch —
   more attention than the nodes' interiors: that is the class of defect a per-node review
   structurally cannot see. The orchestrator reads it inline when it is small — it already holds
   the context, so it is the cheapest reader — and hands it to **one** fresh child when the
   diff is large or independence matters more. Apply `/review-it`'s Review Focus section by
   section, fix what is accepted, re-run the gates. This is the only review the wave gets; never
   skip it, and never let one feature's section absorb the whole pass.
4. **Write the walkthrough, then ship the wave once.** Run the **walkthrough** skill over the
   integrated diff — what changed, what you ran and what it printed, and the visual proof of the
   demo path. Its review gate hands you the PR body and the merge checklist, which the **ship-it**
   skill then opens: one commit/PR, merge, close the issues the wave satisfied. One squash commit buries N features, so the PR body must carry `ship-it`'s
   per-item evidence table (commit, issue, the test that proves it, manual-acceptance status) —
   without it neither you nor the user can audit or revert a single feature afterwards.
5. Remove finished worktrees (keep failed ones), re-render the tracker, and checkpoint.
6. **Re-plan.** Read each node's `NEW_WORK:` line; if any is not `none`, add the node(s) and
   re-layer the remaining work with the planner before the next wave. Show the user the delta.

## Step 5: When a node fails

Retry in place first — **continue that child** with a follow-up that names what failed and what
to fix: it reuses the node's own context instead of paying for a fresh child. If it fails again,
keep its worktree, mark it `failed`, and mark every dependent node `blocked` (the planner prints
them). Reuse `/loop-it`'s error classes from `../loop-it/references/error-recovery.md` rather
than inventing new ones.

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
- **Never force-push to the default branch.** Nodes commit to their own branches; the wave ships one PR.
- **Respect the depth budget** — a node must not dispatch children of its own; a node is a leaf.
- **Cap concurrency** (3–4 by default), **prefer waves of 2–3 nodes**, and **keep the child count honest** — the wave is the blast radius of one bad integration, so do trivia inline.
- **Confirm the plan** before the first fan-out, and keep `.graph_state.json` + `graph.html` current.

## References

- `references/dsh-runtime.md` — the DSH side: delegation mechanics, the two workspace traps in DSH terms, depth/concurrency/cost, branch layout, state schema, and why review and ship are wave-scoped.
- `references/codex-runtime.md` — the Codex side: skill discovery and loading, V1/V2 delegation mapping, depth and concurrency defaults, and the optional `git push` guard. Read it before running a wave under Codex.
- `references/claude-code-runtime.md` — the Claude Code side: plugin/skill discovery, `Agent` dispatch, the missing continuation/audit primitives, depth and concurrency, and the optional `allowed-tools` pre-approval. Read it before running a wave under Claude Code.
- `references/node-prompt.md` — the node prompt template, how to fill it, and how to read a node's report.
- `references/lean-subagent.md` — DSH-only deployment patch that strips a node child's skill catalog (optional cost lever), with its caveats.
- `scripts/graph_state.py` (`plan` / `set` / `prompt` / `show`) — validation, layering,
  checkpoints, and the node prompt rendered from them. `set --branch` records where a node
  actually lives; `prompt` prefers that over a name derived from the title.
- `scripts/test_graph_state.py` — the planner's unit tests; run them after any edit to it.
- `scripts/render_graph_html.py` — the live `graph.html` dashboard.
