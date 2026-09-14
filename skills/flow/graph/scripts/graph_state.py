#!/usr/bin/env python3
"""Plan and checkpoint a /graph task graph.

Dependency cycles, dangling edges, scope collisions, wave layering and the
checkpoint transitions are deterministic. Deriving them in prose every wave is
slower and less reliable, so they live here and the skill says "run this and
read the summary".

Subcommands:

  plan [--nodes <file>] [--state .graph_state.json] [--max-parallel N] [--keep-shipped] [--only-pending]
      Read a nodes file, validate it, layer it into waves, write the checkpoint,
      and print the plan (human summary + Mermaid + the wave-0 dispatch list).
      Without --nodes the graph is rebuilt from the checkpoint itself, which holds
      every declarative field a plan reads; the nodes file is then needed only when
      the graph changes (a new node, a moved dependency). The first plan of a graph
      still needs --nodes, because there is no checkpoint to re-layer from yet.
      With --keep-shipped, an existing checkpoint's per-node outcome is carried
      over for every id that survives, so a re-plan does not reset what shipped.
      With --only-pending, nodes a previous checkpoint already settled (shipped
      or skipped) stop reserving their scope, so remaining work may share a wave
      with them. Their files are already on the branch; only a node still running
      can collide with them. Nodes the checkpoint has in_progress keep their
      scope and are layered ahead of pending work that shares it, so a re-plan
      never dispatches a child into files another child is editing right now.
      Pair it with --keep-shipped, which is what puts the settled outcomes in
      place to read.
      The cap is persisted: omitting --max-parallel on a later plan reuses the
      recorded one instead of silently re-layering the waves.

  set --state .graph_state.json --node N --status <s> [--commit SHA] [--branch NAME] [--error TEXT]
      Record one node's outcome, and optionally the branch it actually lives on.
      Pass --status pending to clear a retry. Prints what the orchestrator should
      do next.

  show --state .graph_state.json [--json]
      Print the current plan and per-node status.

  prompt --node N [--state .graph_state.json] [--worktrees DIR]
      Render the node prompt for one node from references/node-prompt.md, with
      the worktree path, branch, title, type, scope and acceptance criteria
      filled in from the checkpoint. A `branch` recorded by `plan` or `set` is
      used verbatim; only an unrecorded node gets a name derived from its title,
      and then the header says so. The worktree command printed first matches
      what the prompt claims about the branch — including whether it exists.
      The dependency summaries are left as a marked gap — only the orchestrator
      knows them.

Nodes file format:

  {
    "task": "Add user auth",
    "repo": "owner/repo",
    "max_parallel": 4,
    "nodes": [
      {"id": 1, "title": "db schema", "deps": [], "scope": "internal/db",
       "criteria": ["migration applies on a fresh database"]},
      {"id": 2, "title": "API handler", "deps": [1], "scope": "internal/api",
       "hot_files": "internal/api/router.go", "branch": "feat/issue-42-api",
       "context": "#1 landed migration 012; the table already exists."}
    ]
  }

`criteria` is the node's acceptance checklist, copied into the child's prompt
verbatim. `context` is the orchestrator's briefing for the child: one or two
lines per dependency — what it added, where, and anything the node must know.
Both may also be written straight into the checkpoint. A re-plan keeps the
checkpoint's value only for a field the nodes file does not mention; an explicit
empty list/string in the nodes file clears it (presence decides, not truthiness).

`scope` is a comma-separated list of files/directories a node expects to touch.
Two nodes with no dependency edge but overlapping scope are not independent:
the planner serializes the higher id into a later wave.

`hot_files` is the opposite list: shared wiring files (a router, a `main`, a
route table, a DI container, a type union) that the node *will* touch but that
must stay out of `scope`, because listing them there would serialize the whole
graph into a chain. The planner does not serialize on them — it warns when two
nodes in one wave declare the same hot file, because that is the shape that
conflicts: "append-only edits merge cleanly" only holds while each node edits
its own region. Two nodes appending to one import block, or writing one route
table, are not append-only and will conflict at integration.

`branch` (optional, per node) is the branch the node actually lives on. When it
is absent the checkpoint records none and `prompt` derives a name from the
title, disclosing that it did; a node whose real branch differs from the derived
name should have it recorded, or `prompt` will hand the child a name that does
not exist.

Statuses: pending | in_progress | shipped | failed | blocked | skipped
(`shipped` and `skipped` are complete; `failed` and `blocked` stall their
dependents but do not hold a wave open forever — the orchestrator decides.)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

STATUSES = ("pending", "in_progress", "shipped", "failed", "blocked", "skipped")
WAVE_DONE = {"shipped", "skipped", "failed", "blocked"}

# The checkpoint was called `.graph_state` (no extension) before it was renamed
# to match the sibling `.loop-state.json`. The old name is still read so a graph
# that is already running does not lose its progress; it is never written.
STATE_DEFAULT = ".graph_state.json"
LEGACY_STATE = ".graph_state"
# The rendered board lives beside the checkpoint and is refreshed by every write.
BOARD_NAME = "graph.html"


def die(message: str) -> None:
    print(f"graph_state: {message}", file=sys.stderr)
    raise SystemExit(1)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: str, what: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        die(f"{what} not found: {path}")
    except json.JSONDecodeError as exc:
        die(f"{what} is not valid JSON ({path}): {exc}")


def legacy_path_for(requested: str) -> str:
    """The pre-rename checkpoint that sits beside `requested`.

    Resolved from the requested path, not from the process cwd, so
    `--state /work/repo/.graph_state.json` finds `/work/repo/.graph_state`.
    """
    directory = os.path.dirname(requested)
    return os.path.join(directory, LEGACY_STATE) if directory else LEGACY_STATE


def read_state(requested: str) -> tuple[dict, str | None]:
    """Load the checkpoint, falling back to the pre-rename name.

    Only the default file name falls back: an explicit `--state foo.json` means
    the caller named the file it wants, and quietly reading a different one
    would be worse than saying it is missing.
    """
    legacy = legacy_path_for(requested)
    if (not os.path.exists(requested) and os.path.basename(requested) == STATE_DEFAULT
            and os.path.exists(legacy)):
        return (load_json(legacy, "state file"),
                f"read the pre-rename checkpoint {legacy}; the next write goes to {requested}")
    return load_json(requested, "state file"), None


def read_previous(requested: str) -> tuple[dict | None, str | None]:
    """Same fallback as read_state, but a missing checkpoint is not an error."""
    if os.path.exists(requested):
        return load_json(requested, "state file"), None
    legacy = legacy_path_for(requested)
    if os.path.basename(requested) == STATE_DEFAULT and os.path.exists(legacy):
        return (load_json(legacy, "state file"),
                f"read the pre-rename checkpoint {legacy}; the next write goes to {requested}")
    return None, None


def save_state(state: dict, path: str) -> str:
    """Write the checkpoint and refresh the board beside it.

    The board is a snapshot — it inlines the checkpoint — so a write that skips
    the refresh leaves a page that silently disagrees with the state. That is not
    hypothetical: the board sat eight hours stale while nodes were added and
    shipped, because "re-render" was an obligation attached to finishing a wave
    and the work after that was not a wave. Putting the refresh in the write
    itself removes the step someone has to remember. It is best effort: a
    checkpoint that saved must not be reported as failed over a display file.
    """
    state["updated_at"] = now()
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)
    return render_board(path)


def render_board(path: str) -> str:
    """Refresh BOARD_NAME beside `path`. Returns a note to print, or ""."""
    board = os.path.join(os.path.dirname(os.path.abspath(path)) or ".", BOARD_NAME)
    renderer = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_graph_html.py")
    if not os.path.exists(renderer):
        return f"note: {os.path.basename(renderer)} is missing, so {BOARD_NAME} was not refreshed"
    result = subprocess.run([sys.executable, renderer, path, board],
                            capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        return (f"note: {BOARD_NAME} was not refreshed "
                f"({detail[-1] if detail else 'unknown error'}); the checkpoint itself is saved")
    return ""


def scope_set(node: dict) -> set[str]:
    raw = node.get("scope") or ""
    if isinstance(raw, list):
        parts = raw
    else:
        parts = raw.split(",")
    return {p.strip().rstrip("/") for p in parts if p and p.strip()}


def hot_set(node: dict) -> set[str]:
    """Shared wiring files the node expects to touch but that stay out of `scope`."""
    raw = node.get("hot_files") or ""
    if isinstance(raw, list):
        parts = raw
    else:
        parts = raw.split(",")
    return {p.strip().rstrip("/") for p in parts if p and p.strip()}


def validate(nodes: list[dict]) -> tuple[dict[int, dict], list[str]]:
    warnings: list[str] = []
    by_id: dict[int, dict] = {}
    for node in nodes:
        try:
            node_id = int(node["id"])
        except (KeyError, TypeError, ValueError):
            die(f"node without a usable integer id: {node!r}")
        if node_id in by_id:
            die(f"duplicate node id {node_id}")
        if not str(node.get("title", "")).strip():
            warnings.append(f"node {node_id} has no title")
        by_id[node_id] = node

    for node_id, node in by_id.items():
        kept = []
        for dep in node.get("deps") or []:
            dep = int(dep)
            if dep not in by_id:
                warnings.append(f"node {node_id} depends on missing node {dep}; edge dropped")
            elif dep == node_id:
                warnings.append(f"node {node_id} depends on itself; edge dropped")
            else:
                kept.append(dep)
        node["deps"] = sorted(set(kept))
    return by_id, warnings


def scopes_overlap(a: str, b: str) -> bool:
    """Whether two scope entries name the same path or one contains the other.

    Scope entries are directories as often as files, and two nodes writing into
    one directory collide whether they own it wholesale or name different files
    inside it. Comparing with `==` misses that, which let a node scoped to
    `internal/config` share a wave with one scoped to
    `internal/config/config.go` — the pair two agents would have edited at once.
    """
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def scope_clash(scope: set[str], used: set[str]) -> list[str]:
    """The entries in `scope` that collide with anything in `used`."""
    return sorted({entry for entry in scope for other in used if scopes_overlap(entry, other)})


def layer(by_id: dict[int, dict], settled: set[int] | None = None,
          inflight: set[int] | None = None) -> tuple[list[list[int]], list[str]]:
    """Lay nodes into waves: dependencies first, then disjoint scopes.

    A single greedy pass, because the two constraints interact — a node held back
    for a scope clash must not jump ahead of its own dependencies, and its
    dependents must not land in the same wave as it. Only nodes whose deps are
    already placed are candidates, so ordering holds by construction; a candidate
    that clashes on scope simply waits for a later wave.

    `settled` names nodes that are already finished (shipped or skipped). They are
    still placed, so the layout keeps their positions and their dependents keep
    their ordering, but they reserve no scope: a scope clash only matters between
    two nodes that could run at the same time, and a settled node has already
    landed on the branch. Without this, re-planning mid-run lets long-finished
    nodes hold their files against the work that is actually left, which silently
    serializes the tail of a graph into one node per wave.

    `inflight` names nodes that are running right now. They are placed before
    equally-ready pending nodes, because that tie used to be broken by id alone —
    and id order runs the wrong way here. A running node is usually the reason the
    nodes sharing its files are still pending, and those nodes have the lower id
    about half the time, so they would be layered *ahead* of the work they were
    waiting on and dispatched into a file another child is editing at that moment.

    That collision is recorded as an edge rather than filtered inside the wave
    loop. Filtering deadlocks: the pending node waits for a running node whose own
    dependencies are not placed yet, no candidate survives, and the graph is
    reported as a cycle. As an edge the layering places the running node first
    wherever its dependencies allow, and its colliding dependents follow — which
    is the same "wait for it to finish" with the ordering solver doing the work.
    """
    settled = settled or set()
    inflight = inflight or set()
    deps = {nid: set(node["deps"]) for nid, node in by_id.items()}
    for runner in sorted(inflight):
        if runner not in by_id:
            continue
        runner_scope = scope_set(by_id[runner])
        for nid in by_id:
            # Only work that can still run needs the barrier. Wiring it onto a
            # settled node invents an edge across history and can close a cycle
            # through real dependencies — #135 and #140 both touch protocol.go,
            # and #144 depends on #140, so "wait for #144" turned into
            # #135 -> #144 -> #140 -> #135.
            if nid == runner or nid in inflight or nid in settled:
                continue
            if scope_set(by_id[nid]) & runner_scope:
                deps[nid].add(runner)
    notes: list[str] = []
    # Settled work is done, so it neither reserves scope nor occupies a wave: a
    # pending node whose only unfinished dependency was settled is ready *now*, not
    # after the layout has walked the settled node's own dependency chain. Without
    # this the tail stays serialized even though the scopes were freed — #144 sits
    # at the end of a deep chain, so #146, which depends on it and on nothing
    # unfinished, was still pushed to a late wave while an unrelated #217 floated
    # ahead of it. The layout therefore describes the work that is left; settled
    # nodes stay in the node table with their status, which is what the board's
    # counts and any later `set` read.
    remaining = set(by_id) - settled
    placed: set[int] = set(settled)
    waves: list[list[int]] = []
    while remaining:
        ready = sorted(nid for nid in remaining if deps[nid] <= placed)
        if not ready:
            cycle = ", ".join(f"#{nid}" for nid in sorted(remaining))
            die(f"dependency cycle among {cycle} — break it and re-plan")
        wave: list[int] = []
        used: set[str] = set()
        for nid in ready:
            scope = scope_set(by_id[nid])
            clash = scope_clash(scope, used)
            if clash:
                notes.append(
                    f"#{nid} waits one wave: scope overlaps {sorted(clash)} "
                    f"with a node already in wave {len(waves)}"
                )
                continue
            wave.append(nid)
            if nid not in settled:
                used |= scope
        if not wave:  # every ready node clashes; take the lowest id alone
            wave = [ready[0]]
            notes.append(f"#{ready[0]} gets its own wave: every ready node shares its scope")
        waves.append(wave)
        remaining.difference_update(wave)
        placed.update(wave)

        # Hot files are deliberately outside `scope`, so the scope check above
        # cannot see this collision — and it is not enough to compare hot lists
        # to each other either. The dangerous shape is a node that *owns* a file
        # (`scope`) sharing a wave with a node that *edits* it (`hot_files`):
        # that is exactly "one node owns the route table, three others append to
        # it", which is how a wave resolves the same import block three times.
        # Warn rather than serialize: keeping these files out of scope is what
        # lets a wave stay parallel at all.
        for path in sorted({p for nid in wave if nid not in settled for p in hot_set(by_id[nid])}):
            hot = sorted({nid for nid in wave if nid not in settled and path in hot_set(by_id[nid])})
            # A scope entry may be a directory (`internal/config`) while the hot
            # file is one file inside it, so this compares by nesting rather than
            # by equality — the equality form missed exactly that pair.
            owners = sorted({nid for nid in wave if nid not in settled
                             and any(scopes_overlap(entry, path) for entry in scope_set(by_id[nid]))})
            interested = sorted(set(hot) | set(owners))
            if len(interested) < 2:
                continue  # only one node cares about this file
            who = ", ".join(f"#{nid}" for nid in interested)
            shape = (f"{who} all touch {path} and {', '.join(f'#{nid}' for nid in owners)} "
                     f"have it in scope" if owners else f"{who} all declare {path} as a hot file")
            notes.append(
                f"wave {len(waves) - 1}: {shape} — that only merges cleanly if each edits its "
                f"own region; serialize them or give one node ownership"
            )
    return waves, notes


def wave_of(state: dict) -> dict[int, int]:
    return {nid: index for index, wave in enumerate(state["waves"]) for nid in wave}


def current_wave(state: dict) -> int:
    for index, wave in enumerate(state["waves"]):
        if any(state["nodes"][str(nid)]["status"] not in WAVE_DONE for nid in wave):
            return index
    return len(state["waves"])


def render(state: dict) -> str:
    index_of = wave_of(state)
    done = sum(1 for node in state["nodes"].values() if node["status"] in {"shipped", "skipped"})
    total = len(state["nodes"])
    cap = int(state.get("max_parallel") or 0)
    lines = [f"graph: {state.get('task', '(untitled)')} — {total} nodes, "
             f"{len(state['waves'])} waves, {done} shipped" + (f", cap {cap}" if cap else "")]
    for index, wave in enumerate(state["waves"]):
        parts = []
        for nid in wave:
            node = state["nodes"][str(nid)]
            mark = {"shipped": "ok", "failed": "FAIL", "blocked": "blocked", "skipped": "skipped",
                    "in_progress": "running"}.get(node["status"], "pending")
            ref = f" [{node['commit']}]" if node.get("commit") else ""
            parts.append(f"#{nid} {node['title']} ({mark}){ref}")
        marker = "  <-- current" if index == current_wave(state) and index < len(state["waves"]) else ""
        lines.append(f"  wave {index} (x{len(wave)}): " + "; ".join(parts) + marker)
    blocked = [nid for nid, node in state["nodes"].items() if node["status"] == "blocked"]
    if blocked:
        lines.append("  blocked: " + ", ".join(f"#{nid}" for nid in sorted(blocked, key=int)))
    # Settled work that the layout no longer carries. It is still part of the run,
    # so the CLI summary names it rather than letting the waves above imply the
    # graph is only what is left.
    scheduled = {nid for wave in state["waves"] for nid in wave}
    off_layout = sorted((nid for nid in state["nodes"] if int(nid) not in scheduled), key=int)
    if off_layout:
        marks = {"shipped": "ok", "skipped": "skipped", "failed": "FAIL",
                 "blocked": "blocked", "in_progress": "running"}
        shown = ", ".join(
            f"#{nid} ({marks.get(state['nodes'][nid]['status'], state['nodes'][nid]['status'])})"
            for nid in off_layout)
        lines.append(f"  settled, not in the layout: {shown}")
    return "\n".join(lines)


def mermaid(state: dict) -> str:
    index_of = wave_of(state)
    lines = ["```mermaid", "graph LR"]
    for nid, node in sorted(state["nodes"].items(), key=lambda kv: int(kv[0])):
        label = str(node["title"]).replace('"', "'")
        lines.append(f'  n{nid}["#{nid} {label}"]')
        for dep in node.get("deps") or []:
            lines.append(f"  n{dep} --> n{nid}")
    lines.append("```")
    return "\n".join(lines)


def dispatch_list(state: dict, index: int) -> list[str]:
    wave = state["waves"][index]
    out = []
    for nid in wave:
        node = state["nodes"][str(nid)]
        deps = ", ".join(f"#{d}" for d in node.get("deps") or []) or "none"
        hot = node.get("hot_files") or []
        hot_note = f" — hot: {', '.join(hot)}" if hot else ""
        out.append(f"  #{nid} [{node.get('type', 'task')}] {node['title']} — deps: {deps} "
                   f"— scope: {', '.join(sorted(scope_set(node))) or '(unscoped)'}{hot_note}")
    return out


def carry_over(state: dict, previous: dict | None, path: str) -> list[str]:
    """Carry a previous checkpoint's per-node outcomes onto a freshly layered plan.

    Re-planning mid-run is normal: a node turns out to be already satisfied,
    another has to move. Resetting every node to `pending` on a re-layer forces
    the orchestrator to re-record what shipped by hand, and hand-kept accounting
    is where drift starts. Ids that survive keep their outcome; ids that are new
    start pending; ids that disappeared are reported rather than silently kept.
    """
    if previous is None:
        return ["--keep-shipped: no existing checkpoint to carry over from"]
    old_nodes = previous.get("nodes") or {}
    notes: list[str] = []
    carried = 0
    for key, node in state["nodes"].items():
        old = old_nodes.get(key)
        if not isinstance(old, dict):
            continue
        for field in ("status", "branch", "commit", "attempts", "error", "error_class"):
            if field in old:
                node[field] = old[field]
        carried += 1
    if carried:
        notes.append(f"--keep-shipped: carried the outcome of {carried} node(s) from {path}")
    dropped = sorted(set(old_nodes) - set(state["nodes"]), key=lambda k: (len(str(k)), str(k)))
    if dropped:
        notes.append("--keep-shipped: dropped " + ", ".join(f"#{key}" for key in dropped)
                     + " (no longer in the nodes file)")
    return notes


def nodes_from_state(state: dict) -> list[dict]:
    """Rebuild the planner's input from a checkpoint.

    The checkpoint is a strict superset of the nodes file: every declarative field
    a plan reads — title, deps, scope, hot_files, type, criteria, context, and a
    branch that is already known — is on the node record, and the outcome fields
    `set` owns are disjoint from them. So a checkpoint can be re-layered without
    the nodes file it was built from.

    That matters because the nodes file is a scratch input: gitignored, easy to
    lose, and until now the one thing whose absence made re-planning impossible —
    which is exactly when `--only-pending` is worth the most.
    """
    return [
        {
            "id": int(key),
            "title": node.get("title", ""),
            "deps": node.get("deps") or [],
            "scope": node.get("scope") or [],
            "hot_files": node.get("hot_files") or [],
            "type": node.get("type", "task"),
            "criteria": node.get("criteria") or [],
            "context": node.get("context", ""),
            # Carried, never synthesized: the checkpoint holds a branch only once
            # one exists, and the state builder below drops an empty value anyway.
            "branch": node.get("branch"),
        }
        for key, node in state["nodes"].items()
    ]


def cmd_plan(args: argparse.Namespace) -> int:
    # The previous checkpoint is read first either way: `--only-pending` needs its
    # outcomes before layering can decide whose scope still counts, and without a
    # nodes file it is also where the graph itself comes from.
    previous, legacy_note = read_previous(args.state)
    from_state_note = ""
    if args.nodes:
        spec = load_json(args.nodes, "nodes file")
        nodes = spec.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            die("nodes file must contain a non-empty 'nodes' array")
    else:
        if not previous:
            die(f"nothing to layer: no nodes file given and no checkpoint at {args.state} — "
                f"pass --nodes on the first plan of a graph")
        spec = {"task": previous.get("task", "(untitled)"),
                "repo": previous.get("repo", ""),
                "max_parallel": previous.get("max_parallel")}
        nodes = nodes_from_state(previous)
        from_state_note = (f"no --nodes: re-layered the {len(nodes)} node(s) recorded in "
                           f"{args.state}")

    by_id, warnings = validate(nodes)

    checkout_nodes = (previous or {}).get("nodes") or {}
    settled: set[int] = set()
    inflight: set[int] = set()
    if args.only_pending:
        for key, old in checkout_nodes.items():
            if not isinstance(old, dict):
                continue
            if old.get("status") in {"shipped", "skipped"}:
                settled.add(int(key))
            elif old.get("status") == "in_progress":
                inflight.add(int(key))
        settled &= set(by_id)
        inflight &= set(by_id)
        if previous is None:
            notes_later = "--only-pending: no existing checkpoint, so nothing is settled"
        elif not settled:
            notes_later = "--only-pending: the checkpoint has no shipped or skipped node"
        else:
            notes_later = (f"--only-pending: {len(settled)} settled node(s) no longer "
                           f"reserve their scope")
            if inflight:
                notes_later += (f"; {len(inflight)} in-flight node(s) "
                                f"({', '.join(f'#{nid}' for nid in sorted(inflight))}) keep theirs")
    else:
        notes_later = ""
    waves, notes = layer(by_id, settled, inflight)
    if notes_later:
        notes.append(notes_later)

    # The concurrency cap shapes the layout, so it belongs in the checkpoint:
    # re-planning without it would silently re-layer the waves and nobody would
    # see the change, because every node's status is preserved either way.
    # The checkpoint is the only place a criterion sometimes lives (issues are filed
    # and criteria pasted straight into it). Re-planning must not be destructive.
    previous_criteria = {k: v.get("criteria") for k, v in checkout_nodes.items() if v.get("criteria")}
    previous_context = {k: v.get("context") for k, v in checkout_nodes.items() if v.get("context")}
    if legacy_note:
        notes.append(legacy_note)
    if from_state_note:
        notes.append(from_state_note)
    recorded = int((previous or {}).get("max_parallel") or 0)
    if args.max_parallel is not None:
        limit = args.max_parallel
        if recorded and limit != recorded:
            notes.append(f"--max-parallel {limit} differs from the {recorded} recorded in "
                         f"{args.state} — the wave layout will change")
    else:
        limit = int(spec.get("max_parallel") or 0)
        if not limit and recorded:
            limit = recorded
            notes.append(f"--max-parallel not given: reusing the {recorded} recorded in {args.state}")
    if limit > 0:
        limited: list[list[int]] = []
        for wave in waves:
            for start in range(0, len(wave), limit):
                limited.append(wave[start:start + limit])
        if len(limited) != len(waves):
            notes.append(f"waves split to respect --max-parallel {limit}")
        waves = limited

    state = {
        "version": 1,
        "updated_at": now(),
        "task": spec.get("task", "(untitled)"),
        "repo": spec.get("repo", ""),
        "max_parallel": limit,
        "waves": waves,
        "current_wave": 0,
        "nodes": {
            str(nid): {
                "title": node.get("title", ""),
                "deps": node.get("deps") or [],
                "type": node.get("type", "task"),
                "scope": sorted(scope_set(node)),
                "hot_files": sorted(hot_set(node)),
                # Re-planning rebuilds every node from the nodes file, so anything
                # recorded only in the checkpoint is silently lost. Criteria are the
                # case that bites: they are usually written straight into the
                # checkpoint when the issue is filed, and a later re-plan used to
                # erase them (the child prompt then says "write them from the issue").
                # Fall back to the checkpoint so re-planning is not destructive.
                # Presence decides, not truthiness: an explicit `"criteria": []`
                # in the nodes file is a deliberate clear, and treating it as
                # "not provided" would resurrect the checkpoint's value.
                "criteria": (node["criteria"] if "criteria" in node
                             else previous_criteria.get(str(nid))) or [],
                "context": (node["context"] if "context" in node
                            else previous_context.get(str(nid))) or "",
                # A branch is recorded only when it is known. Synthesizing one at
                # plan time would put a name in the checkpoint that nothing has
                # created yet, and `prompt` would then present it as fact.
                **({"branch": str(node["branch"])} if node.get("branch") else {}),
                "status": "pending",
            }
            for nid, node in sorted(by_id.items())
        },
    }

    if args.keep_shipped:
        notes.extend(carry_over(state, previous, args.state))

    state["current_wave"] = current_wave(state)
    board_note = save_state(state, args.state)

    max_par = max(len(wave) for wave in waves)
    print(render(state))
    print(f"\nmax parallelism: {max_par} child agent(s) in one wave")
    print(f"checkpoint: {args.state}")
    for warning in warnings:
        print(f"warning: {warning}")
    for note in notes:
        print(f"note: {note}")
    if board_note:
        print(board_note)
    print("\n" + mermaid(state))
    index = current_wave(state)
    if index < len(state["waves"]):
        print(f"\nwave {index} — dispatch these together, one child each:")
        for line in dispatch_list(state, index):
            print(line)
        print("\nnext: render the tracker with render_graph_html.py, then dispatch this wave.")
    else:
        print("\nevery wave is already closed — nothing to dispatch.")
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    if args.status not in STATUSES:
        die(f"unknown status {args.status!r} (expected one of: {', '.join(STATUSES)})")
    state, legacy_note = read_state(args.state)
    key = str(args.node)
    if key not in state["nodes"]:
        die(f"node {key} is not in {args.state}")
    node = state["nodes"][key]
    previous = node["status"]
    node["status"] = args.status
    if args.branch:
        node["branch"] = args.branch
    if args.commit:
        node["commit"] = args.commit
    if args.error:
        node["error"] = args.error
        node["attempts"] = int(node.get("attempts", 0)) + 1
    else:
        node.pop("error", None)
    # `current_wave` is derived, and the board reads it. Only a plan used to
    # refresh it, so recording the last node of a wave left the file pointing at
    # the wave that had just closed.
    state["current_wave"] = current_wave(state)
    board_note = save_state(state, args.state)

    index_of = wave_of(state)
    node_wave = index_of.get(int(key))
    index = current_wave(state)
    if legacy_note:
        print(f"note: {legacy_note}")
    if board_note:
        print(board_note)
    print(f"node #{key}: {previous} -> {args.status}")
    print(render(state))

    if node_wave is None:  # unreachable for a well-formed state, but stay honest
        print("\nnode is not in any wave — re-plan.")
        return 0

    wave = state["waves"][node_wave]
    if all(state["nodes"][str(nid)]["status"] in WAVE_DONE for nid in wave):
        print(f"\nwave {node_wave} is closed. Fan-in now:")
        print("  1. leak check: git status --porcelain must be clean on the shared checkout")
        print('  2. integrate: git checkout "$BASE"')
        print("     pull only when an upstream is configured — a bare `git pull` exits 1 without one:")
        print("     git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1 && git pull")
        if len(wave) > 1:
            print(f"     git checkout -b wave-{node_wave}-<slug>, then merge each node branch with --no-ff")
        else:
            print("     merge the one node branch with --no-ff (a one-node wave skips the wave branch)")
        print("     and run the project's gates on the integrated tree")
        print("  3. review the wave ONCE (git diff against the default branch), fix, re-run the gates")
        print("  4. ship the wave ONCE with the ship-it skill, close the issues it satisfied")
        next_index = node_wave + 1
        if next_index < len(state["waves"]):
            print(f"  5. render the tracker, then dispatch wave {next_index}:")
            for line in dispatch_list(state, next_index):
                print(line)
        else:
            print("  5. every wave is done — write the final summary and clean up the worktrees.")
    else:
        outstanding = [f"#{nid}" for nid in wave
                       if state["nodes"][str(nid)]["status"] not in WAVE_DONE]
        print(f"\nwave {node_wave} still open — waiting on {', '.join(outstanding)}")
        if index != node_wave:
            print(f"(wave {index} is already current; wave {node_wave} just needs closing)")
    return 0


def node_slug(title: str, node_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(title).lower()).strip("-")
    return slug[:40] or f"node-{node_id}"


def worktree_root(override: str | None) -> str:
    """Where node worktrees go: a sibling of the repo root, matching the skill's recipe."""
    if override:
        return os.path.abspath(override)
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True,
                             capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        die("not inside a git repository — pass --worktrees to say where the worktrees go")
    return os.path.join(os.path.dirname(top), ".graph-worktrees")


def load_template(override: str | None) -> str:
    """The node prompt body, read from the skill's own reference file.

    One source of truth: the script renders exactly the template a human would
    copy, so the two cannot drift apart.
    """
    path = override or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references", "node-prompt.md")
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        die(f"node prompt template is unreadable ({path}): {exc}")
    match = re.search(r"```markdown\n(.*?)\n```", text, re.S)
    if not match:
        die(f"no ```markdown template block in {path}")
    return match.group(1)


def cmd_prompt(args: argparse.Namespace) -> int:
    state, legacy_note = read_state(args.state)
    key = str(args.node)
    if key not in state["nodes"]:
        die(f"node {key} is not in {args.state}")
    node = state["nodes"][key]

    worktree = os.path.join(worktree_root(args.worktrees), f"node-{key}")
    slug = node_slug(node.get("title", ""), key)
    # The checkpoint is the only place a real branch name can come from: a child
    # that renamed it (or a node whose branch was created before the plan was
    # written) must not be contradicted by a name this script invented from the
    # title. Synthesis is a fallback for a branch nobody has created yet, and the
    # header says so instead of presenting it as fact.
    recorded = node.get("branch")
    branch = str(recorded) if recorded else f"feat/node-{key}-{slug}"
    exists = os.path.isdir(worktree)

    prompt = load_template(args.template)
    criteria = node.get("criteria") or []
    prompt = prompt.replace(
        "- [ ] {criterion 1}\n- [ ] {criterion 2}",
        "\n".join(f"- [ ] {criterion}" for criterion in criteria)
        or "- [ ] (no criteria recorded — write them from the issue before dispatching)")
    # `context` on a node is the orchestrator's dependency briefing. It existed as a
    # placeholder with no way to fill it, which meant every dispatch had the text
    # hand-appended to a temp copy of the prompt — an easy step to skip and a silent
    # quality loss (the child cannot read the earlier nodes' conversations).
    context = str(node.get("context") or "").strip()
    prompt = prompt.replace(
        "{summaries of dependency nodes' outputs, or the referenced PRD/SPEC excerpt}",
        context or "(FILL THIS IN: one or two lines per dependency — what it added, where, and "
        "anything this node must know. The child cannot read the earlier nodes' conversations, so "
        "this is the only channel the graph has.)")
    for token, value in (
        ("{WT}", worktree),
        ("{N}", key),
        ("{slug}", slug),
        ("{branch}", branch),
        ("{branch_state}", "already created and checked out" if exists else
         "NOT created yet — create it with the command above before you start"),
        ("{title}", str(node.get("title", ""))),
        ("{type}", str(node.get("type", "task"))),
        ("{scope_hint}", ", ".join(node.get("scope") or []) or "(unscoped)"),
    ):
        prompt = prompt.replace(token, value)

    deps = ", ".join(f"#{dep}" for dep in node.get("deps") or []) or "none"
    hot = node.get("hot_files") or []
    if legacy_note:
        print(f"note: {legacy_note}")
    print(f"# node #{key} — {node.get('title', '')}")
    print(f"# deps: {deps}   status: {node.get('status', 'pending')}")
    if hot:
        print(f"# hot files: {', '.join(hot)} — shared; expect a conflict with any other node "
              f"in this wave that declares them unless each edits its own region")
    print("#")
    if exists:
        print(f"# the worktree already exists; the prompt below names the branch it should hold:")
        print(f'# confirm with: git -C "{worktree}" rev-parse --abbrev-ref HEAD')
    else:
        print("# create the worktree first — the prompt below names this branch:")
        print(f'git worktree add -b {branch} "{worktree}" "$BASE"')
    if not recorded:
        print("# (that branch name was derived from the title and does not exist yet —")
        print(f"#  once it does, record it so later prompts stop guessing: "
              f"graph_state.py set --node {key} --status <same> --branch {branch})")
    print()
    print(prompt)

    leftovers = sorted(set(re.findall(r"\{[a-z][^}]*\}", prompt)))
    if leftovers:
        print()
        print("# unfilled placeholders: " + ", ".join(leftovers))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    state, legacy_note = read_state(args.state)
    if legacy_note and not args.json:
        print(f"note: {legacy_note}")
    if args.json:
        print(json.dumps(state, indent=2, ensure_ascii=False))
    else:
        print(render(state))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="validate, layer into waves, write the checkpoint")
    plan.add_argument("--nodes", default=None,
                      help="path to the nodes JSON file; omit to re-layer from the checkpoint itself")
    plan.add_argument("--state", default=STATE_DEFAULT,
                      help=f"checkpoint path (default {STATE_DEFAULT})")
    plan.add_argument("--max-parallel", type=int, default=None,
                      help="split waves wider than this (reused from the checkpoint when omitted)")
    plan.add_argument("--keep-shipped", action="store_true",
                      help="carry an existing checkpoint's per-node outcome onto the new layout")
    plan.add_argument("--only-pending", action="store_true",
                      help="let shipped/skipped nodes stop reserving their scope when re-layering")
    plan.set_defaults(func=cmd_plan)

    setter = sub.add_parser("set", help="record one node's outcome")
    setter.add_argument("--state", default=STATE_DEFAULT)
    setter.add_argument("--node", required=True)
    setter.add_argument("--status", required=True, choices=STATUSES)
    setter.add_argument("--commit")
    setter.add_argument("--branch", help="record the branch this node actually lives on")
    setter.add_argument("--error")
    setter.set_defaults(func=cmd_set)

    prompt = sub.add_parser("prompt", help="render one node's dispatch prompt from the checkpoint")
    prompt.add_argument("--state", default=STATE_DEFAULT)
    prompt.add_argument("--node", required=True)
    prompt.add_argument("--worktrees", help="worktree root (default: <repo parent>/.graph-worktrees)")
    prompt.add_argument("--template", help="override the node prompt template path")
    prompt.set_defaults(func=cmd_prompt)

    show = sub.add_parser("show", help="print the current plan and status")
    show.add_argument("--state", default=STATE_DEFAULT)
    show.add_argument("--json", action="store_true")
    show.set_defaults(func=cmd_show)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
