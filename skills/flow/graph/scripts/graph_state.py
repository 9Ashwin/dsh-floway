#!/usr/bin/env python3
"""Plan and checkpoint a /graph task graph.

Dependency cycles, dangling edges, scope collisions, wave layering and the
checkpoint transitions are deterministic. Deriving them in prose every wave is
slower and less reliable, so they live here and the skill says "run this and
read the summary".

Subcommands:

  plan --nodes <file> [--state .graph_state] [--max-parallel N] [--keep-shipped]
      Read a nodes file, validate it, layer it into waves, write the checkpoint,
      and print the plan (human summary + Mermaid + the wave-0 dispatch list).
      With --keep-shipped, an existing checkpoint's per-node outcome is carried
      over for every id that survives, so a re-plan does not reset what shipped.

  set --state .graph_state --node N --status <s> [--commit SHA] [--error TEXT]
      Record one node's outcome. Pass --status pending to clear a retry. Prints
      what the orchestrator should do next.

  show --state .graph_state [--json]
      Print the current plan and per-node status.

  prompt --node N [--state .graph_state] [--worktrees DIR]
      Render the node prompt for one node from references/node-prompt.md, with
      the worktree path, branch, title, type, scope and acceptance criteria
      filled in from the checkpoint. Prints the git worktree command first so
      the branch it names is the branch that gets created. The dependency
      summaries are left as a marked gap — only the orchestrator knows them.

Nodes file format:

  {
    "task": "Add user auth",
    "repo": "owner/repo",
    "nodes": [
      {"id": 1, "title": "db schema", "deps": [], "scope": "internal/db"},
      {"id": 2, "title": "API handler", "deps": [1], "scope": "internal/api",
       "hot_files": "internal/api/router.go"}
    ]
  }

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


def save_state(state: dict, path: str) -> None:
    state["updated_at"] = now()
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)


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


def layer(by_id: dict[int, dict]) -> tuple[list[list[int]], list[str]]:
    """Lay nodes into waves: dependencies first, then disjoint scopes.

    A single greedy pass, because the two constraints interact — a node held back
    for a scope clash must not jump ahead of its own dependencies, and its
    dependents must not land in the same wave as it. Only nodes whose deps are
    already placed are candidates, so ordering holds by construction; a candidate
    that clashes on scope simply waits for a later wave.
    """
    notes: list[str] = []
    remaining = set(by_id)
    placed: set[int] = set()
    waves: list[list[int]] = []
    while remaining:
        ready = sorted(nid for nid in remaining if set(by_id[nid]["deps"]) <= placed)
        if not ready:
            cycle = ", ".join(f"#{nid}" for nid in sorted(remaining))
            die(f"dependency cycle among {cycle} — break it and re-plan")
        wave: list[int] = []
        used: set[str] = set()
        for nid in ready:
            scope = scope_set(by_id[nid])
            clash = scope & used
            if clash:
                notes.append(
                    f"#{nid} waits one wave: scope overlaps {sorted(clash)} "
                    f"with a node already in wave {len(waves)}"
                )
                continue
            wave.append(nid)
            used |= scope
        if not wave:  # every ready node clashes; take the lowest id alone
            wave = [ready[0]]
            notes.append(f"#{ready[0]} gets its own wave: every ready node shares its scope")
        waves.append(wave)
        remaining.difference_update(wave)
        placed.update(wave)

        # Hot files are deliberately outside `scope`, so the scope check above
        # cannot see this collision. Warn rather than serialize: keeping these
        # files out of scope is what lets a wave stay parallel at all.
        holders: dict[str, list[int]] = {}
        for nid in wave:
            for path in hot_set(by_id[nid]):
                holders.setdefault(path, []).append(nid)
        for path in sorted(holders):
            editors = holders[path]
            if len(editors) > 1:
                who = ", ".join(f"#{nid}" for nid in editors)
                notes.append(
                    f"wave {len(waves) - 1}: {who} all declare hot file {path} — "
                    f"that only merges cleanly if each edits its own region; "
                    f"serialize them or give one node ownership"
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
    lines = [f"graph: {state.get('task', '(untitled)')} — {total} nodes, "
             f"{len(state['waves'])} waves, {done} shipped"]
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


def carry_over(state: dict, path: str) -> list[str]:
    """Carry a previous checkpoint's per-node outcomes onto a freshly layered plan.

    Re-planning mid-run is normal: a node turns out to be already satisfied,
    another has to move. Resetting every node to `pending` on a re-layer forces
    the orchestrator to re-record what shipped by hand, and hand-kept accounting
    is where drift starts. Ids that survive keep their outcome; ids that are new
    start pending; ids that disappeared are reported rather than silently kept.
    """
    if not os.path.exists(path):
        return ["--keep-shipped: no existing checkpoint to carry over from"]
    previous = load_json(path, "state file")
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


def cmd_plan(args: argparse.Namespace) -> int:
    spec = load_json(args.nodes, "nodes file")
    nodes = spec.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        die("nodes file must contain a non-empty 'nodes' array")

    by_id, warnings = validate(nodes)
    waves, notes = layer(by_id)
    if args.max_parallel and args.max_parallel > 0:
        limited: list[list[int]] = []
        for wave in waves:
            for start in range(0, len(wave), args.max_parallel):
                limited.append(wave[start:start + args.max_parallel])
        if len(limited) != len(waves):
            notes.append(f"waves split to respect --max-parallel {args.max_parallel}")
        waves = limited

    state = {
        "version": 1,
        "updated_at": now(),
        "task": spec.get("task", "(untitled)"),
        "repo": spec.get("repo", ""),
        "waves": waves,
        "current_wave": 0,
        "nodes": {
            str(nid): {
                "title": node.get("title", ""),
                "deps": node.get("deps") or [],
                "type": node.get("type", "task"),
                "scope": sorted(scope_set(node)),
                "hot_files": sorted(hot_set(node)),
                "criteria": node.get("criteria") or [],
                "status": "pending",
            }
            for nid, node in sorted(by_id.items())
        },
    }

    if args.keep_shipped:
        carried = carry_over(state, args.state)
        notes.extend(carried)

    state["current_wave"] = current_wave(state)
    save_state(state, args.state)

    max_par = max(len(wave) for wave in waves)
    print(render(state))
    print(f"\nmax parallelism: {max_par} child agent(s) in one wave")
    print(f"checkpoint: {args.state}")
    for warning in warnings:
        print(f"warning: {warning}")
    for note in notes:
        print(f"note: {note}")
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
    state = load_json(args.state, "state file")
    key = str(args.node)
    if key not in state["nodes"]:
        die(f"node {key} is not in {args.state}")
    node = state["nodes"][key]
    previous = node["status"]
    node["status"] = args.status
    if args.commit:
        node["commit"] = args.commit
    if args.error:
        node["error"] = args.error
        node["attempts"] = int(node.get("attempts", 0)) + 1
    else:
        node.pop("error", None)
    save_state(state, args.state)

    index_of = wave_of(state)
    node_wave = index_of.get(int(key))
    index = current_wave(state)
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
    state = load_json(args.state, "state file")
    key = str(args.node)
    if key not in state["nodes"]:
        die(f"node {key} is not in {args.state}")
    node = state["nodes"][key]

    worktree = os.path.join(worktree_root(args.worktrees), f"node-{key}")
    slug = node_slug(node.get("title", ""), key)
    branch = f"feat/node-{key}-{slug}"

    prompt = load_template(args.template)
    criteria = node.get("criteria") or []
    prompt = prompt.replace(
        "- [ ] {criterion 1}\n- [ ] {criterion 2}",
        "\n".join(f"- [ ] {criterion}" for criterion in criteria)
        or "- [ ] (no criteria recorded — write them from the issue before dispatching)")
    prompt = prompt.replace(
        "{summaries of dependency nodes' outputs, or the referenced PRD/SPEC excerpt}",
        "(FILL THIS IN: one or two lines per dependency — what it added, where, and anything this "
        "node must know. The child cannot read the earlier nodes' conversations, so this is the "
        "only channel the graph has.)")
    for token, value in (
        ("{WT}", worktree),
        ("{N}", key),
        ("{slug}", slug),
        ("{title}", str(node.get("title", ""))),
        ("{type}", str(node.get("type", "task"))),
        ("{scope_hint}", ", ".join(node.get("scope") or []) or "(unscoped)"),
    ):
        prompt = prompt.replace(token, value)

    deps = ", ".join(f"#{dep}" for dep in node.get("deps") or []) or "none"
    hot = node.get("hot_files") or []
    print(f"# node #{key} — {node.get('title', '')}")
    print(f"# deps: {deps}   status: {node.get('status', 'pending')}")
    if hot:
        print(f"# hot files: {', '.join(hot)} — shared; expect a conflict with any other node "
              f"in this wave that declares them unless each edits its own region")
    print("#")
    print("# create the worktree first — this is the branch the prompt below names:")
    print(f'git worktree add -b {branch} "{worktree}" "$BASE"')
    print()
    print(prompt)

    leftovers = sorted(set(re.findall(r"\{[a-z][^}]*\}", prompt)))
    if leftovers:
        print()
        print("# unfilled placeholders: " + ", ".join(leftovers))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    state = load_json(args.state, "state file")
    if args.json:
        print(json.dumps(state, indent=2, ensure_ascii=False))
    else:
        print(render(state))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="validate, layer into waves, write the checkpoint")
    plan.add_argument("--nodes", required=True, help="path to the nodes JSON file")
    plan.add_argument("--state", default=".graph_state", help="checkpoint path (default .graph_state)")
    plan.add_argument("--max-parallel", type=int, default=0, help="split waves wider than this")
    plan.add_argument("--keep-shipped", action="store_true",
                      help="carry an existing checkpoint's per-node outcome onto the new layout")
    plan.set_defaults(func=cmd_plan)

    setter = sub.add_parser("set", help="record one node's outcome")
    setter.add_argument("--state", default=".graph_state")
    setter.add_argument("--node", required=True)
    setter.add_argument("--status", required=True, choices=STATUSES)
    setter.add_argument("--commit")
    setter.add_argument("--error")
    setter.set_defaults(func=cmd_set)

    prompt = sub.add_parser("prompt", help="render one node's dispatch prompt from the checkpoint")
    prompt.add_argument("--state", default=".graph_state")
    prompt.add_argument("--node", required=True)
    prompt.add_argument("--worktrees", help="worktree root (default: <repo parent>/.graph-worktrees)")
    prompt.add_argument("--template", help="override the node prompt template path")
    prompt.set_defaults(func=cmd_prompt)

    show = sub.add_parser("show", help="print the current plan and status")
    show.add_argument("--state", default=".graph_state")
    show.add_argument("--json", action="store_true")
    show.set_defaults(func=cmd_show)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
