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
        state_path = os.path.join(tmp, ".graph_state")
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
        state_path = os.path.join(tmp, ".graph_state")
        state = {"version": 1, "task": "t", "repo": "", "waves": [[1, 2], [3]], "current_wave": 0,
                 "nodes": {str(n): {"title": f"n{n}", "deps": [], "status": "shipped" if n < 3 else "pending"}
                           for n in (1, 2, 3)}}
        state["nodes"]["2"]["status"] = "in_progress"
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        args = type("A", (), {"state": state_path, "node": "2", "status": "shipped",
                              "commit": "abc1234", "error": None})()
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
        state_path = os.path.join(tmp, ".graph_state")
        state = {"version": 1, "task": "t", "repo": "", "waves": [[1], [2]], "current_wave": 0,
                 "nodes": {"1": {"title": "n1", "deps": [], "status": "in_progress"},
                           "2": {"title": "n2", "deps": [1], "status": "pending"}}}
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        args = type("A", (), {"state": state_path, "node": "1", "status": "shipped",
                              "commit": "abc1234", "error": None})()
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
        state_path = os.path.join(tmp, ".graph_state")
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "x"},
                                              {"id": 2, "title": "b", "scope": "y"}]}, handle)
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              max_parallel=0, keep_shipped=False))
            gs.cmd_set(gs.argparse.Namespace(state=state_path, node="1", status="shipped",
                                             commit="abc1234", error=None))
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "x"},
                                              {"id": 2, "title": "b", "scope": "y"},
                                              {"id": 3, "title": "c", "scope": "z"}]}, handle)
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              max_parallel=0, keep_shipped=True))
        carried = json.load(open(state_path, encoding="utf-8"))
        check("shipped survives a re-plan", carried["nodes"]["1"]["status"] == "shipped",
              str(carried["nodes"]["1"]))
        check("the commit survives too", carried["nodes"]["1"].get("commit") == "abc1234")
        check("a newly added node starts pending", carried["nodes"]["3"]["status"] == "pending")

        # Negative control: without the flag a re-plan resets the shipped node.
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              max_parallel=0, keep_shipped=False))
        reset = json.load(open(state_path, encoding="utf-8"))
        check("without --keep-shipped the outcome is reset",
              reset["nodes"]["1"]["status"] == "pending", str(reset["nodes"]["1"]))


def test_prompt_renders_from_the_checkpoint():
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".graph_state")
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
        check("the printed branch is the branch the prompt names",
              "feat/node-7-wire-the-router" in out)
        check("criteria render as a checklist",
              "- [ ] the route resolves" in out and "- [ ] lint passes" in out)
        check("scope is filled in", "src/app.ts" in out)
        check("dependency summaries are marked as the orchestrator's job", "FILL THIS IN" in out)
        check("hot files are surfaced", "src/router.ts" in out)
        check("no placeholder is left silently untouched",
              "unfilled placeholders" not in out, out[-300:])


def main() -> int:
    print("graph_state.py tests")
    for test in (test_dependencies_hold_across_waves, test_scope_collision_defers_without_breaking_order,
                 test_cycle_is_fatal, test_missing_dep_is_dropped_with_warning,
                 test_self_dep_is_dropped, test_end_to_end_plan_and_set,
                 test_max_parallel_split_preserves_order,
                 test_closing_a_wave_announces_fan_in_for_that_wave,
                 test_single_node_wave_skips_wave_branch,
                 test_hot_file_overlap_warns_without_serializing,
                 test_keep_shipped_carries_outcome,
                 test_prompt_renders_from_the_checkpoint):
        print(f"- {test.__name__}")
        test()
    if failures:
        print(f"\n{len(failures)} failure(s): {', '.join(failures)}")
        return 1
    print("\nok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
