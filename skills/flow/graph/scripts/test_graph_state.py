#!/usr/bin/env python3
"""Unit tests for graph_state.py — run with `python3 test_graph_state.py`.

No test framework: the planner is stdlib-only on purpose, so its test is too.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def load_module():
    spec = importlib.util.spec_from_file_location("graph_state", os.path.join(HERE, "graph_state.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gs = load_module()
failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


def nodes(*specs):
    return {int(nid): {"id": nid, "title": f"n{nid}", "deps": list(deps), "scope": scope}
            for nid, deps, scope in specs}


def test_dependencies_hold_across_waves():
    by_id = nodes((1, [], "a"), (2, [], "b"), (3, [1], "c"), (4, [2], "d"), (5, [3, 4], "e"))
    waves, _ = gs.layer(by_id)
    index = {nid: i for i, wave in enumerate(waves) for nid in wave}
    check("dep 1 before 3", index[1] < index[3])
    check("dep 2 before 4", index[2] < index[4])
    check("3 and 4 before 5", index[3] < index[5] and index[4] < index[5])
    check("independent nodes share wave 0", sorted(waves[0]) == [1, 2])


def test_scope_collision_defers_without_breaking_order():
    by_id = nodes((1, [], "internal/db"), (2, [], "internal/db"), (3, [1], "internal/api"))
    waves, notes = gs.layer(by_id)
    index = {nid: i for i, wave in enumerate(waves) for nid in wave}
    check("clashing nodes split", index[1] != index[2])
    check("collision reported", any("waits one wave" in n for n in notes), str(notes))
    check("dependent still after its dep", index[1] < index[3])


def test_cycle_is_fatal():
    by_id = nodes((1, [2], "a"), (2, [1], "b"))
    try:
        gs.layer(by_id)
        check("cycle detected", False, "layer() returned instead of exiting")
    except SystemExit as exc:
        check("cycle detected", exc.code == 1)


def test_missing_dep_is_dropped_with_warning():
    by_id, warnings = gs.validate([{"id": 1, "title": "a", "deps": [99]}])
    check("phantom edge dropped", by_id[1]["deps"] == [])
    check("warning emitted", any("missing node 99" in w for w in warnings), str(warnings))


def test_self_dep_is_dropped():
    by_id, warnings = gs.validate([{"id": 7, "title": "self", "deps": [7]}])
    check("self edge dropped", by_id[7]["deps"] == [])
    check("self warning", any("depends on itself" in w for w in warnings), str(warnings))


def test_end_to_end_plan_and_set():
    with tempfile.TemporaryDirectory() as tmp:
        nodes_path = os.path.join(tmp, "nodes.json")
        state_path = os.path.join(tmp, ".graph_state.json")
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump({"task": "t", "nodes": [
                {"id": 1, "title": "a", "scope": "x"},
                {"id": 2, "title": "b", "scope": "y"},
                {"id": 3, "title": "c", "deps": [1, 2], "scope": "z"},
            ]}, handle)
        code = gs.main() if False else None  # main() is CLI-only; drive the commands directly
        del code
        spec = json.load(open(nodes_path, encoding="utf-8"))
        by_id, _ = gs.validate(spec["nodes"])
        waves, _ = gs.layer(by_id)
        check("two waves", waves == [[1, 2], [3]], str(waves))

        state_obj = {
            "version": 1, "task": "t", "repo": "", "waves": waves, "current_wave": 0,
            "nodes": {str(nid): {"title": f"n{nid}", "deps": [], "status": "pending"} for nid in (1, 2, 3)},
        }
        state_obj["nodes"]["1"]["status"] = "shipped"
        state_obj["nodes"]["2"]["status"] = "shipped"
        check("wave 0 closes", gs.current_wave(state_obj) == 1)
        state_obj["nodes"]["3"]["status"] = "blocked"
        check("all waves terminal", gs.current_wave(state_obj) == len(waves))
        check("render mentions blocked", "blocked: #3" in gs.render(state_obj), gs.render(state_obj))


def test_max_parallel_split_preserves_order():
    by_id = nodes((1, [], "a"), (2, [], "b"), (3, [], "c"), (4, [1], "d"))
    waves, _ = gs.layer(by_id)
    widened = []
    for wave in waves:
        for start in range(0, len(wave), 2):
            widened.append(wave[start:start + 2])
    index = {nid: i for i, wave in enumerate(widened) for nid in wave}
    check("split keeps dep order", index[1] < index[4])
    check("no wave exceeds the cap", all(len(w) <= 2 for w in widened))


def test_closing_a_wave_announces_fan_in_for_that_wave():
    """Regression: the fan-in checklist must describe the wave that just closed."""
    import io, contextlib, tempfile
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".graph_state.json")
        state = {"version": 1, "task": "t", "repo": "", "waves": [[1, 2], [3]], "current_wave": 0,
                 "nodes": {str(n): {"title": f"n{n}", "deps": [], "status": "shipped" if n < 3 else "pending"}
                           for n in (1, 2, 3)}}
        state["nodes"]["2"]["status"] = "in_progress"
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        args = type("A", (), {"state": state_path, "node": "2", "status": "shipped",
                              "commit": "abc1234", "branch": None, "error": None})()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gs.cmd_set(args)
        text = out.getvalue()
        check("fan-in announced for wave 0", "wave 0 is closed. Fan-in now:" in text, text[-300:])
        check("next wave dispatch listed", "dispatch wave 1" in text, text[-300:])
        check("no bogus wave-1 fan-in", "wave 1 is closed" not in text)
        check("pull guarded by an upstream check",
              "git rev-parse --abbrev-ref --symbolic-full-name '@{u}'" in text, text[-400:])
        check("no bare git checkout+pull", "git checkout main && git pull" not in text, text[-400:])
        check("multi-node wave keeps the wave branch",
              "git checkout -b wave-0-<slug>" in text, text[-400:])


def test_single_node_wave_skips_wave_branch():
    """Regression: a one-node wave must not be told to create a wave branch (D4)."""
    import io, contextlib, tempfile
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".graph_state.json")
        state = {"version": 1, "task": "t", "repo": "", "waves": [[1], [2]], "current_wave": 0,
                 "nodes": {"1": {"title": "n1", "deps": [], "status": "in_progress"},
                           "2": {"title": "n2", "deps": [1], "status": "pending"}}}
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        args = type("A", (), {"state": state_path, "node": "1", "status": "shipped",
                              "commit": "abc1234", "branch": None, "error": None})()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gs.cmd_set(args)
        text = out.getvalue()
        check("single-node fan-in announced", "wave 0 is closed. Fan-in now:" in text, text[-300:])
        check("no wave branch for one node", "wave-0-<slug>" not in text, text[-300:])
        check("no wave branch command at all", "git checkout -b wave-" not in text, text[-300:])
        check("single node merges straight in", "a one-node wave skips the wave branch" in text, text[-400:])


def test_hot_file_overlap_warns_without_serializing():
    """Hot files stay out of `scope`, so only this check can see the collision."""
    shared = {1: {"id": 1, "title": "a", "deps": [], "scope": "src/a.ts",
                  "hot_files": "src/router.ts"},
              2: {"id": 2, "title": "b", "deps": [], "scope": "src/b.ts",
                  "hot_files": "src/router.ts"},
              3: {"id": 3, "title": "c", "deps": [], "scope": "src/c.ts",
                  "hot_files": "src/other.ts"}}
    waves, notes = gs.layer(shared)
    check("hot files do not serialize the wave", waves == [[1, 2, 3]], str(waves))
    hit = [n for n in notes if "src/router.ts" in n]
    check("an overlapping hot file is called out", len(hit) == 1, str(notes))
    check("the warning names both editors",
          bool(hit) and "#1" in hit[0] and "#2" in hit[0], str(hit))
    check("a hot file touched once is not reported",
          not any("src/other.ts" in n for n in notes), str(notes))

    # Negative control: the same shape with disjoint hot files must stay silent.
    apart = {1: {"id": 1, "title": "a", "deps": [], "scope": "src/a.ts", "hot_files": "src/r1.ts"},
             2: {"id": 2, "title": "b", "deps": [], "scope": "src/b.ts", "hot_files": "src/r2.ts"}}
    _, quiet = gs.layer(apart)
    check("disjoint hot files produce no note", not any("hot file" in n for n in quiet), str(quiet))


def test_keep_shipped_carries_outcome():
    with tempfile.TemporaryDirectory() as tmp:
        nodes_path = os.path.join(tmp, "nodes.json")
        state_path = os.path.join(tmp, ".graph_state.json")
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "x"},
                                              {"id": 2, "title": "b", "scope": "y"}]}, handle)
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=False))
            gs.cmd_set(gs.argparse.Namespace(state=state_path, node="1", status="shipped",
                                             commit="abc1234", branch="feat/issue-9-reworked",
                                             error=None))
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "x"},
                                              {"id": 2, "title": "b", "scope": "y"},
                                              {"id": 3, "title": "c", "scope": "z"}]}, handle)
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=True))
        carried = json.load(open(state_path, encoding="utf-8"))
        check("shipped survives a re-plan", carried["nodes"]["1"]["status"] == "shipped",
              str(carried["nodes"]["1"]))
        check("the commit survives too", carried["nodes"]["1"].get("commit") == "abc1234")
        # A recorded branch must survive a re-layer even when the nodes file no
        # longer mentions it — otherwise `prompt` falls back to a derived name.
        check("the real branch survives a re-plan",
              carried["nodes"]["1"].get("branch") == "feat/issue-9-reworked",
              str(carried["nodes"]["1"]))
        check("a newly added node starts pending", carried["nodes"]["3"]["status"] == "pending")

        # Negative control: without the flag a re-plan resets the shipped node.
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=False))
        reset = json.load(open(state_path, encoding="utf-8"))
        check("without --keep-shipped the outcome is reset",
              reset["nodes"]["1"]["status"] == "pending", str(reset["nodes"]["1"]))


def test_prompt_renders_from_the_checkpoint():
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".graph_state.json")
        worktrees = os.path.join(tmp, "wt")
        state = {"version": 1, "task": "t", "repo": "", "waves": [[7]], "current_wave": 0,
                 "nodes": {"7": {"title": "wire the router", "deps": [3], "type": "frontend",
                                 "scope": ["src/app.ts"], "hot_files": ["src/router.ts"],
                                 "criteria": ["the route resolves", "lint passes"],
                                 "status": "pending"}}}
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            gs.cmd_prompt(gs.argparse.Namespace(state=state_path, node="7",
                                                worktrees=worktrees, template=None))
        out = buffer.getvalue()
        check("worktree path is named for the node",
              os.path.join(worktrees, "node-7") in out, out[:400])
        check("with nothing recorded, the header and prompt agree on the derived name",
              "feat/node-7-wire-the-router" in out)
        check("criteria render as a checklist",
              "- [ ] the route resolves" in out and "- [ ] lint passes" in out)
        check("scope is filled in", "src/app.ts" in out)
        check("dependency summaries are marked as the orchestrator's job", "FILL THIS IN" in out)
        check("hot files are surfaced", "src/router.ts" in out)
        check("no placeholder is left silently untouched",
              "unfilled placeholders" not in out, out[-300:])


def test_hot_file_colliding_with_a_scope_is_reported():
    """The shape that cost three conflict resolutions: one node owns the file, another edits it."""
    by_id = {1: {"id": 1, "title": "owns the router", "deps": [], "scope": "src/router.ts"},
             2: {"id": 2, "title": "registers a route", "deps": [], "scope": "src/b.ts",
                  "hot_files": "src/router.ts"}}
    waves, notes = gs.layer(by_id)
    check("an owned file plus a hot file does not serialize", waves == [[1, 2]], str(waves))
    hit = [n for n in notes if "src/router.ts" in n]
    check("the cross collision is called out", len(hit) == 1, str(notes))
    check("the warning names both sides",
          bool(hit) and "#1" in hit[0] and "#2" in hit[0], str(hit))
    check("it says who owns the file", bool(hit) and "scope" in hit[0], str(hit))

    # Negative control: same shape, nothing shared -> silent.
    apart = {1: {"id": 1, "title": "a", "deps": [], "scope": "src/x.ts"},
             2: {"id": 2, "title": "b", "deps": [], "scope": "src/b.ts", "hot_files": "src/y.ts"}}
    _, quiet = gs.layer(apart)
    check("no shared interest produces no note",
          not any("merges cleanly" in n for n in quiet), str(quiet))


def test_node_context_fills_the_dependency_slot():
    """The dependency briefing had no way in: a `context` on the node fills it.

    Before this, the slot rendered an unfillable placeholder and the orchestrator had to
    paste the briefing into a temp copy of the prompt — which the next dispatch dropped.
    """
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".graph_state.json")
        worktrees = os.path.join(tmp, "wt")
        briefing = "#191 landed migration 012 in internal/storage; the table already exists."
        state = {"version": 1, "task": "t", "repo": "", "waves": [[7]], "current_wave": 0,
                 "nodes": {"7": {"title": "wire the router", "deps": [3], "type": "frontend",
                                 "scope": ["src/app.ts"], "criteria": ["the route resolves"],
                                 "context": briefing, "status": "pending"}}}
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            gs.cmd_prompt(gs.argparse.Namespace(state=state_path, node="7",
                                                worktrees=worktrees, template=None))
        out = buffer.getvalue()
        check("the briefing reaches the child", briefing in out, out[-600:])
        check("and the placeholder is gone", "FILL THIS IN" not in out, out[-600:])


def test_replan_keeps_criteria_and_context_only_the_checkpoint_holds():
    """Regression: a re-plan rebuilt every node from the nodes file, so a criterion
    recorded only in the checkpoint was silently erased and the child was told to
    "write them from the issue"."""
    with tempfile.TemporaryDirectory() as tmp:
        nodes_path = os.path.join(tmp, "nodes.json")
        state_path = os.path.join(tmp, ".graph_state.json")
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "src/a.ts"}]}, handle)
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=False))
        # the way the orchestrator records them once the issue is filed
        state = json.load(open(state_path, encoding="utf-8"))
        state["nodes"]["1"]["criteria"] = ["migration applies on a fresh database"]
        state["nodes"]["1"]["context"] = "#191 landed migration 012; do not create the table again."
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)

        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=True))
        again = json.load(open(state_path, encoding="utf-8"))
        check("criteria survive a re-plan",
              again["nodes"]["1"].get("criteria") == ["migration applies on a fresh database"],
              str(again["nodes"]["1"]))
        check("context survives a re-plan",
              "migration 012" in (again["nodes"]["1"].get("context") or ""),
              str(again["nodes"]["1"]))


def test_recorded_branch_beats_the_synthesized_name():
    """Regression: `prompt` must not invent a branch a node is not actually on."""
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".graph_state.json")
        worktrees = os.path.join(tmp, "wt")
        state = {"version": 1, "task": "t", "repo": "", "waves": [[7]], "current_wave": 0,
                 "nodes": {"7": {"title": "webui", "deps": [], "scope": ["src/app.ts"],
                                 "branch": "feat/node-7-webui-auth-e2e", "status": "pending"}}}
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gs.cmd_prompt(gs.argparse.Namespace(state=state_path, node="7",
                                                worktrees=worktrees, template=None))
        text = out.getvalue()
        check("the recorded branch is used", "feat/node-7-webui-auth-e2e" in text, text[:400])
        check("the worktree command names the recorded branch",
              "git worktree add -b feat/node-7-webui-auth-e2e" in text, text[:400])
        check("a nonexistent worktree is not called ready",
              "already created and checked out" not in text, text[:400])
        check("the prompt says the branch does not exist yet", "NOT created yet" in text)

        # Negative control: with no recorded branch, the synthesized name is used
        # and the header admits it was derived rather than presenting it as fact.
        state["nodes"]["7"].pop("branch")
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gs.cmd_prompt(gs.argparse.Namespace(state=state_path, node="7",
                                                worktrees=worktrees, template=None))
        text = out.getvalue()
        check("with nothing recorded the name is derived from the title",
              "feat/node-7-webui" in text, text[:400])
        check("the derivation is disclosed", "derived from the title" in text, text[:600])
        check("and offered to the checkpoint", "--branch feat/node-7-webui" in text, text[:600])

        # An existing worktree must not be told to run `git worktree add`.
        os.makedirs(os.path.join(worktrees, "node-7"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gs.cmd_prompt(gs.argparse.Namespace(state=state_path, node="7",
                                                worktrees=worktrees, template=None))
        text = out.getvalue()
        check("an existing worktree is not re-created", "git worktree add" not in text, text[:400])
        check("the prompt says the branch is already checked out",
              "already created and checked out" in text)


def test_set_records_the_branch_for_later_prompts():
    with tempfile.TemporaryDirectory() as tmp:
        nodes_path = os.path.join(tmp, "nodes.json")
        state_path = os.path.join(tmp, ".graph_state.json")
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "x"}]}, handle)
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=False))
            gs.cmd_set(gs.argparse.Namespace(state=state_path, node="1", status="in_progress",
                                             commit=None, branch="feat/a-renamed", error=None))
        check("the branch lands in the checkpoint",
              json.load(open(state_path, encoding="utf-8"))["nodes"]["1"]["branch"] == "feat/a-renamed")

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gs.cmd_prompt(gs.argparse.Namespace(state=state_path, node="1",
                                                worktrees=os.path.join(tmp, "wt"), template=None))
        text = out.getvalue()
        check("the prompt picks it up", "feat/a-renamed" in text, text[:400])
        check("nothing is left to guess", "derived from the title" not in text, text[:600])


def test_max_parallel_persists_and_is_reused_on_replan():
    """Regression: re-planning without the flag silently re-layered the waves."""
    with tempfile.TemporaryDirectory() as tmp:
        nodes_path = os.path.join(tmp, "nodes.json")
        state_path = os.path.join(tmp, ".graph_state.json")
        spec = {"task": "t", "nodes": [{"id": n, "title": f"n{n}", "scope": f"src/{n}.ts"}
                                       for n in range(1, 7)]}
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump(spec, handle)

        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=4, keep_shipped=False))
        first = json.load(open(state_path, encoding="utf-8"))
        check("the cap is written to the checkpoint", first.get("max_parallel") == 4, str(first))
        check("and it shaped the layout", first["waves"] == [[1, 2, 3, 4], [5, 6]], str(first["waves"]))

        # The defect: drop the flag on the re-plan and the layout must not change.
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=True))
        again = json.load(open(state_path, encoding="utf-8"))
        check("re-planning without the flag keeps the cap", again.get("max_parallel") == 4, str(again))
        check("and keeps the same waves", again["waves"] == [[1, 2, 3, 4], [5, 6]], str(again["waves"]))
        note = out.getvalue()
        check("the inheritance is announced, not silent", "reusing the 4 recorded" in note, note[:600])
        check("the render shows the cap", "cap 4" in gs.render(again), gs.render(again))

        # A deliberate change must be applied and reported as a change.
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=6, keep_shipped=True))
        raised = json.load(open(state_path, encoding="utf-8"))
        check("a new cap is applied", raised["waves"] == [[1, 2, 3, 4, 5, 6]], str(raised["waves"]))
        check("the mismatch is reported", "differs from the 4 recorded" in out.getvalue(),
              out.getvalue()[:600])

        # Negative control: an explicit 0 means "no cap" and must not inherit.
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=0, keep_shipped=True))
        free = json.load(open(state_path, encoding="utf-8"))
        check("an explicit 0 clears the cap", free.get("max_parallel") == 0, str(free))
        check("and collapses back to one wave",
              free["waves"] == [[1, 2, 3, 4, 5, 6]], str(free["waves"]))
        check("an explicit 0 is not described as unset",
              "reusing the" not in out.getvalue(), out.getvalue()[:600])

        # The nodes file can carry the cap too, for a plan that outlives one shell.
        spec["max_parallel"] = 2
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump(spec, handle)
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=True))
        from_spec = json.load(open(state_path, encoding="utf-8"))
        check("the nodes file can set the cap",
              from_spec["waves"] == [[1, 2], [3, 4], [5, 6]], str(from_spec["waves"]))


def test_legacy_checkpoint_name_is_still_read():
    """The checkpoint was renamed to .graph_state.json — a graph that is already
    running must not lose its progress because of the rename."""
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            legacy = {"version": 1, "task": "legacy run", "repo": "", "waves": [[1]],
                      "current_wave": 0,
                      "nodes": {"1": {"title": "n1", "deps": [], "status": "shipped"}}}
            with open(gs.LEGACY_STATE, "w", encoding="utf-8") as handle:
                json.dump(legacy, handle)

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                gs.cmd_show(gs.argparse.Namespace(state=gs.STATE_DEFAULT, json=False))
            out = buffer.getvalue()
            check("the pre-rename checkpoint is still read", "legacy run" in out, out[:200])
            check("and the rename is disclosed", "pre-rename" in out, out[:200])

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                gs.cmd_set(gs.argparse.Namespace(state=gs.STATE_DEFAULT, node="1",
                                                 status="in_progress", commit=None,
                                                 branch=None, error=None))
            check("a write migrates to the new name", os.path.exists(gs.STATE_DEFAULT),
                  str(os.listdir(".")))
            migrated = json.load(open(gs.STATE_DEFAULT, encoding="utf-8"))
            check("with the migrated state", migrated["nodes"]["1"]["status"] == "in_progress",
                  str(migrated["nodes"]["1"]))

            # Negative control: once the new file exists it wins, even if the old
            # one is still on disk with different content.
            with open(gs.LEGACY_STATE, "w", encoding="utf-8") as handle:
                json.dump({**legacy, "task": "stale legacy"}, handle)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                gs.cmd_show(gs.argparse.Namespace(state=gs.STATE_DEFAULT, json=True))
            out = buffer.getvalue()
            check("the new checkpoint wins over a stale legacy file", "stale legacy" not in out)
            check("and nothing is reported as pre-rename", "pre-rename" not in out)

            # Absolute paths must resolve the legacy name beside the requested
            # file, not beside the process cwd — that is how /graph is invoked
            # when the checkpoint lives outside the current directory.
            elsewhere = os.path.join(tmp, "elsewhere")
            os.makedirs(elsewhere, exist_ok=True)
            with open(os.path.join(elsewhere, gs.LEGACY_STATE), "w", encoding="utf-8") as handle:
                json.dump({**legacy, "task": "absolute legacy"}, handle)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                gs.cmd_show(gs.argparse.Namespace(
                    state=os.path.join(elsewhere, gs.STATE_DEFAULT), json=True))
            check("an absolute path finds the legacy file beside it",
                  "absolute legacy" in buffer.getvalue(), buffer.getvalue()[:200])
        finally:
            os.chdir(cwd)


def test_nodes_file_can_clear_a_checkpoint_value():
    """The nodes file is the source of truth, including when it says "nothing".

    Presence decides, not truthiness: `"criteria": []` is a deliberate clear, and
    reading it as "not provided" resurrected the checkpoint's value, so criteria
    could never be removed by re-planning.
    """
    with tempfile.TemporaryDirectory() as tmp:
        nodes_path = os.path.join(tmp, "nodes.json")
        state_path = os.path.join(tmp, ".graph_state.json")

        def replan(spec):
            with open(nodes_path, "w", encoding="utf-8") as handle:
                json.dump(spec, handle)
            with contextlib.redirect_stdout(io.StringIO()):
                gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                                  only_pending=False,
                                                  max_parallel=None, keep_shipped=True))
            return json.load(open(state_path, encoding="utf-8"))["nodes"]["1"]

        replan({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "src/a.ts",
                                        "criteria": ["from the plan"]}]})
        # the orchestrator replaces them straight in the checkpoint
        state = json.load(open(state_path, encoding="utf-8"))
        state["nodes"]["1"]["criteria"] = ["written into the checkpoint"]
        state["nodes"]["1"]["context"] = "briefing written into the checkpoint"
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)

        node = replan({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "src/a.ts"}]})
        check("an omitted field falls back to the checkpoint",
              node["criteria"] == ["written into the checkpoint"]
              and "checkpoint" in node["context"], str(node))

        node = replan({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "src/a.ts",
                                               "criteria": [], "context": ""}]})
        check("an explicit empty list clears criteria", node["criteria"] == [], str(node))
        check("an explicit empty string clears context", node["context"] == "", str(node))

        node = replan({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "src/a.ts",
                                               "criteria": ["replaced"],
                                               "context": "replaced"}]})
        check("a value in the nodes file still wins",
              node["criteria"] == ["replaced"] and node["context"] == "replaced", str(node))


def test_only_pending_frees_a_settled_nodes_scope():
    # The bug this guards: re-planning a graph mid-run let nodes that shipped long
    # ago keep holding their scope, so every node still to do that touched the same
    # directory was pushed into a wave of its own. The cost was real — a graph whose
    # tail could fit in four waves laid out as seven.
    by_id = nodes((1, [], "internal/db"), (2, [], "internal/db"), (3, [], "internal/api"))
    without, _ = gs.layer(by_id)
    with_settled, _ = gs.layer(by_id, settled={1})
    before = {nid: i for i, wave in enumerate(without) for nid in wave}
    after = {nid: i for i, wave in enumerate(with_settled) for nid in wave}
    check("a settled owner still serializes without the flag", before[1] != before[2])
    check("the two nodes left share the first wave", after[2] == 0 and after[3] == 0,
          str(with_settled))
    check("settled work leaves the layout it no longer constrains", 1 not in after,
          str(with_settled))


def test_only_pending_still_serializes_two_pending_nodes():
    # Negative control for the above: freeing settled scope must not turn scope
    # collision detection off. Two nodes that will actually run together still split.
    by_id = nodes((1, [], "internal/db"), (2, [], "internal/db"), (3, [], "internal/api"))
    waves, notes = gs.layer(by_id, settled={3})
    index = {nid: i for i, wave in enumerate(waves) for nid in wave}
    check("two pending nodes on one path still split", index[1] != index[2], str(waves))
    check("and the collision is still reported", any("waits one wave" in n for n in notes), str(notes))


def test_only_pending_via_plan_moves_work_into_earlier_waves():
    with tempfile.TemporaryDirectory() as tmp:
        nodes_path = os.path.join(tmp, "nodes.json")
        state_path = os.path.join(tmp, ".graph_state.json")
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "internal/db"},
                                              {"id": 2, "title": "b", "scope": "internal/db"},
                                              {"id": 3, "title": "c", "scope": "internal/db"}]}, handle)
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=False))
            gs.cmd_set(gs.argparse.Namespace(state=state_path, node="1", status="shipped",
                                             commit=None, branch=None, error=None))
        # Without the flag the shipped node still takes a slot of its own.
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=True))
        held = json.load(open(state_path, encoding="utf-8"))
        check("shipped node holds a wave without the flag", len(held["waves"]) == 3,
              str(held["waves"]))
        # With it, the two nodes left can share the first wave they are ready for.
        with contextlib.redirect_stdout(io.StringIO()):
            freed = gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                                      only_pending=True,
                                                      max_parallel=None, keep_shipped=True))
        state = json.load(open(state_path, encoding="utf-8"))
        check("re-planning with the flag succeeds", freed == 0, str(freed))
        check("the layout collapses to the work that is left", len(state["waves"]) == 2,
              str(state["waves"]))
        check("the outcome is still carried", state["nodes"]["1"]["status"] == "shipped")
        check("settled work is out of the wave list",
              all(1 not in wave for wave in state["waves"]), str(state["waves"]))


def test_only_pending_layers_inflight_ahead_of_what_it_blocks():
    # The shape that bit: #208 is running on internal/webui and it is the reason
    # #165/#173/#174/#190 are still pending — but every one of those has a lower id,
    # so id-order tie-breaking laid them out first and would have dispatched them
    # into files #208 was editing at that moment.
    by_id = nodes((165, [], "internal/webui"), (208, [], "internal/webui"))
    plain, _ = gs.layer(by_id)
    guarded, _ = gs.layer(by_id, inflight={208})
    plain_index = {nid: i for i, wave in enumerate(plain) for nid in wave}
    kept_index = {nid: i for i, wave in enumerate(guarded) for nid in wave}
    check("by id alone the blocker is laid out last", plain_index[208] > plain_index[165],
          str(plain))
    check("in-flight work takes the slot it is already using", kept_index[208] == 0, str(guarded))
    check("and what it blocks waits", kept_index[165] == 1, str(guarded))
    check("in-flight work still reserves its scope", kept_index[165] != kept_index[208])


def test_only_pending_does_not_invent_a_cycle_across_settled_nodes():
    # Real shape that broke it: #135 and #140 are both shipped and both touch
    # internal/fleetq/protocol.go; #144 is running and depends on #140. Wiring the
    # in-flight barrier onto the settled #135 closed #135 -> #144 -> #140 -> #135
    # and the whole graph was reported as a dependency cycle.
    by_id = nodes((2, [], "internal/fleetq/protocol.go"),
                  (1, [2], "internal/fleetq/protocol.go"))
    try:
        waves, _ = gs.layer(by_id, settled={2}, inflight={1})
    except SystemExit as exc:
        check("a settled node is never wired to a running one", False,
              f"layer() died with {exc.code}")
        return
    index = {nid: i for i, wave in enumerate(waves) for nid in wave}
    check("layer() survives the settled sibling", sorted(index) == [1], str(waves))
    check("the running node is laid out", index[1] == 0, str(waves))


def test_a_directory_scope_covers_the_files_inside_it():
    # Real pair: #174 is scoped to the whole `internal/config` package and #217 to
    # `internal/config/config.go`. Equality-only comparison called that compatible
    # and put both in one wave, which is two agents editing one directory.
    by_id = nodes((1, [], "internal/config"), (2, [], "internal/config/config.go"))
    waves, notes = gs.layer(by_id)
    index = {nid: i for i, wave in enumerate(waves) for nid in wave}
    check("a directory and a file inside it split", index[1] != index[2], str(waves))
    check("and the collision is reported", any("waits one wave" in n for n in notes), str(notes))

    # Negative control: the fix must not serialize everything sharing a directory.
    # Two different files in one package are exactly what a parallel wave is for.
    siblings = nodes((1, [], "internal/config/a.go"), (2, [], "internal/config/b.go"))
    sibling_waves, _ = gs.layer(siblings)
    sibling_index = {nid: i for i, wave in enumerate(sibling_waves) for nid in wave}
    check("two distinct files in one directory still share a wave",
          sibling_index[1] == sibling_index[2], str(sibling_waves))


def test_scopes_overlap_treats_nesting_as_a_collision():
    check("equal paths collide", gs.scopes_overlap("a/b", "a/b"))
    check("a child path collides with its parent", gs.scopes_overlap("a/b/c.go", "a/b"))
    check("and the other way round", gs.scopes_overlap("a/b", "a/b/c.go"))
    check("siblings do not collide", not gs.scopes_overlap("a/b", "a/c"))
    check("a name prefix is not a path prefix", not gs.scopes_overlap("a/bc", "a/b"))


def main() -> int:
    print("graph_state.py tests")
    for test in (test_dependencies_hold_across_waves, test_scope_collision_defers_without_breaking_order,
                 test_cycle_is_fatal, test_missing_dep_is_dropped_with_warning,
                 test_self_dep_is_dropped, test_end_to_end_plan_and_set,
                 test_max_parallel_split_preserves_order,
                 test_closing_a_wave_announces_fan_in_for_that_wave,
                 test_single_node_wave_skips_wave_branch,
                 test_hot_file_overlap_warns_without_serializing,
                 test_hot_file_colliding_with_a_scope_is_reported,
                 test_keep_shipped_carries_outcome,
                 test_only_pending_frees_a_settled_nodes_scope,
                 test_only_pending_still_serializes_two_pending_nodes,
                 test_only_pending_via_plan_moves_work_into_earlier_waves,
                 test_only_pending_layers_inflight_ahead_of_what_it_blocks,
                 test_only_pending_does_not_invent_a_cycle_across_settled_nodes,
                 test_a_directory_scope_covers_the_files_inside_it,
                 test_scopes_overlap_treats_nesting_as_a_collision,
                 test_prompt_renders_from_the_checkpoint,
                 test_node_context_fills_the_dependency_slot,
                 test_replan_keeps_criteria_and_context_only_the_checkpoint_holds,
                 test_recorded_branch_beats_the_synthesized_name,
                 test_set_records_the_branch_for_later_prompts,
                 test_max_parallel_persists_and_is_reused_on_replan,
                 test_legacy_checkpoint_name_is_still_read,
                 test_nodes_file_can_clear_a_checkpoint_value):
        print(f"- {test.__name__}")
        test()
    if failures:
        print(f"\n{len(failures)} failure(s): {', '.join(failures)}")
        return 1
    print("\nok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
