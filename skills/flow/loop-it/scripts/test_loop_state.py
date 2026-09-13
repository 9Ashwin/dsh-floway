#!/usr/bin/env python3
"""Tests for loop_state.py — run with `python3 test_loop_state.py`.

Plain-python, no pytest, no network: the script is stdlib-only on purpose, so
its test is too. Exercises the parsing/ordering/resume helpers and the four
subcommands end to end against temp fixtures.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))


def load_module():
    spec = importlib.util.spec_from_file_location("loop_state", os.path.join(HERE, "loop_state.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ls = load_module()
failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


def run(*argv: str) -> tuple[int, str, str]:
    """Run the CLI in-process and capture (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            ls.main([str(a) for a in argv])
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
    return code, out.getvalue(), err.getvalue()


def write_issues(tmp: str, specs: list[tuple[int, str, str]]) -> str:
    """specs: (number, title, body). Returns the fixture path."""
    payload = [
        {"number": number, "title": title, "body": body, "labels": []}
        for number, title, body in specs
    ]
    path = os.path.join(tmp, "issues.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    return path


def read_state(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def test_parse_dependencies_variants():
    check("Dependencies: #3, #5", ls.parse_deps("Dependencies: #3, #5") == [3, 5])
    check("Depends on: #3", ls.parse_deps("Depends on: #3") == [3])
    check("depends on #3 inline", ls.parse_deps("The view depends on #3 to render.") == [3])
    check("requires #3", ls.parse_deps("requires #3") == [3])
    check("and-joined list", ls.parse_deps("Depends on: #3 and #5") == [3, 5])
    check("multiple phrases merge", ls.parse_deps("Dependencies: #1\nrequires #4") == [1, 4])
    check("list stops at prose", ls.parse_deps("depends on #3, see the PRD for details") == [3])
    check("no deps", ls.parse_deps("Just a normal issue body.") == [])
    check("empty body", ls.parse_deps("") == [])
    check("self reference dropped", ls.parse_deps("Depends on: #7", 7) == [])
    check("only the referenced section", ls.parse_deps("Dependencies: #2\n\n#9 is unrelated") == [2])


def test_topological_order():
    numbers = [5, 1, 2, 3]
    deps = {1: set(), 2: {1}, 3: {2}, 5: set()}
    order, warnings = ls.topology(numbers, deps)
    check("chain + independent order", order == [1, 2, 3, 5], str(order))
    check("no warnings without a cycle", warnings == [], str(warnings))

    order, _ = ls.topology([4, 2, 3, 1], {4: {2, 3}, 2: {1}, 3: {1}, 1: set()})
    index = {n: i for i, n in enumerate(order)}
    check("diamond keeps deps first", index[1] < index[2] and index[1] < index[3]
          and index[2] < index[4] and index[3] < index[4], str(order))


def test_cycle_breaking():
    deps = {4: {5}, 5: {4}, 6: {5}}
    order, warnings = ls.topology([4, 5, 6], deps)
    check("cycle members all ordered", sorted(order) == [4, 5, 6], str(order))
    check("lowest number goes first", order[0] == 4, str(order))
    check("dependent still after its dep", order.index(5) < order.index(6), str(order))
    check("cycle warning printed", any("循环依赖" in w for w in warnings), str(warnings))
    check("warning names the break", any("#4" in w and "#5" in w for w in warnings), str(warnings))


def test_resume_from_existing_state():
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".loop-state.json")
        previous = {
            "version": 1,
            "started_at": "2025-06-09T10:00:00Z",
            "updated_at": "2025-06-09T10:30:00Z",
            "repo": "owner/repo",
            "total_issues": 2,
            "issues": {
                "1": {"status": "shipped", "branch": "feat/issue-1-add-priority", "attempts": 2,
                      "started_at": "2025-06-09T10:00:00Z", "completed_at": "2025-06-09T10:10:00Z"},
                "9": {"status": "skipped", "attempts": 0},
            },
        }
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(previous, handle)
        issues = write_issues(tmp, [
            (1, "Add priority field", "No deps."),
            (2, "Display indicator", "Dependencies: #1"),
        ])
        code, out, err = run("scan", "--issues", issues, "--state", state_path, "--repo", "owner/repo")
        check("scan exits 0", code == 0, err)
        state = read_state(state_path)
        check("recorded status preserved", state["issues"]["1"]["status"] == "shipped")
        check("branch preserved", state["issues"]["1"]["branch"] == "feat/issue-1-add-priority")
        check("attempts preserved", state["issues"]["1"]["attempts"] == 2)
        check("closed issue kept", state["issues"]["9"]["status"] == "skipped")
        check("new issue added pending", state["issues"]["2"]["status"] == "pending")
        check("new issue deps recorded", state["issues"]["2"]["deps"] == [1])
        check("title recorded", state["issues"]["1"]["title"] == "Add priority field")
        check("repo preserved", state["repo"] == "owner/repo")
        check("total counts tracked issues", state["total_issues"] == 3)
        check("checkpoint name in output", ".loop-state.json" in out, out)

        code, out, err = run("next", "--state", state_path)
        check("next after resume is #2", "#2" in out and "📊 next: #2" in out, out)
        check("next explains the wait", "#9" not in out, out)


def test_corrupt_state_is_refused():
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".loop-state.json")
        corrupt = "{ this is not json"
        with open(state_path, "w", encoding="utf-8") as handle:
            handle.write(corrupt)
        issues = write_issues(tmp, [(1, "One", "no deps")])
        code, out, err = run("scan", "--issues", issues, "--state", state_path)
        check("corrupt state is a hard error", code != 0, out)
        check("error names the file", state_path in err, err)
        with open(state_path, encoding="utf-8") as handle:
            check("corrupt file not overwritten", handle.read() == corrupt)
        code, _, err = run("set", "--issue", 1, "--status", "shipped", "--state", state_path)
        check("set also refuses corrupt state", code != 0, err)
        code, _, err = run("next", "--state", os.path.join(tmp, "missing.json"))
        check("missing checkpoint for next is an error", code != 0, err)


def test_blocked_and_next_computation():
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".loop-state.json")
        issues = write_issues(tmp, [
            (1, "Foundation", "no deps"),
            (2, "Middle", "Depends on: #1"),
            (3, "Top", "Dependencies: #2"),
        ])
        code, out, err = run("scan", "--issues", issues, "--state", state_path, "--repo", "o/r")
        check("scan exits 0", code == 0, err)
        check("first actionable is #1", "📊 next: #1" in out, out)
        check("blocked list mentions #2 and #3", "🔒 blocked:" in out and "#2" in out and "#3" in out, out)

        code, out, err = run("set", "--issue", 1, "--status", "in_progress", "--state", state_path)
        state = read_state(state_path)
        check("attempts incremented", state["issues"]["1"]["attempts"] == 1, str(state["issues"]["1"]))
        check("started_at stamped", bool(state["issues"]["1"].get("started_at")))
        check("phase defaults to implement", state["issues"]["1"]["phase"] == "implement")
        check("next stays on the in_progress issue", "📊 next: #1" in out and "恢复" in out, out)

        run("set", "--issue", 1, "--status", "in_progress", "--state", state_path)
        state = read_state(state_path)
        check("retry increments attempts", state["issues"]["1"]["attempts"] == 2, str(state["issues"]["1"]))

        code, out, err = run("set", "--issue", 1, "--status", "shipped",
                             "--branch", "feat/issue-1-foundation", "--state", state_path)
        state = read_state(state_path)
        check("shipped recorded", state["issues"]["1"]["status"] == "shipped")
        check("branch recorded", state["issues"]["1"]["branch"] == "feat/issue-1-foundation")
        check("completed_at stamped", bool(state["issues"]["1"].get("completed_at")))
        check("next moves to #2", "📊 next: #2" in out, out)
        check("#3 still waiting on #2", "#3" in out and "等待" in out, out)

        code, out, err = run("set", "--issue", 2, "--status", "failed",
                             "--error-class", "build_failure", "--error", "boom",
                             "--state", state_path)
        state = read_state(state_path)
        check("failed recorded", state["issues"]["2"]["status"] == "failed")
        check("error class recorded", state["issues"]["2"]["error_class"] == "build_failure")
        check("last_error recorded", state["issues"]["2"]["last_error"] == "boom")
        check("failed clears completed_at", "completed_at" not in state["issues"]["2"])
        check("no actionable issue left", "📊 next: (无可执行项)" in out, out)
        check("failed reason printed", "上次失败" in out and "build_failure" in out, out)

        code, out, err = run("summary", "--state", state_path)
        check("summary exits 0", code == 0, err)
        check("summary counts shipped", "shipped:    1" in out, out)
        check("summary counts failed with reason", "failed:     1" in out and "build_failure" in out, out)
        check("summary lists blocked #3", "blocked:    1" in out and "#3" in out, out)

        code, out, err = run("set", "--issue", 2, "--status", "in_progress", "--state", state_path)
        state = read_state(state_path)
        check("retry clears completed_at only", state["issues"]["2"]["status"] == "in_progress")
        check("next resumes #2", "📊 next: #2" in out, out)


def test_untracked_dependency_waits():
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".loop-state.json")
        issues = write_issues(tmp, [(2, "Needs a closed issue", "Depends on: #99")])
        code, out, err = run("scan", "--issues", issues, "--state", state_path)
        check("scan exits 0", code == 0, err)
        check("untracked dep reported", "#99" in out and "不在本批" in out, out)
        check("untracked dep blocks next", "📊 next: (无可执行项)" in out, out)


def main() -> int:
    print("loop_state.py tests")
    for test in (
        test_parse_dependencies_variants,
        test_topological_order,
        test_cycle_breaking,
        test_resume_from_existing_state,
        test_corrupt_state_is_refused,
        test_blocked_and_next_computation,
        test_untracked_dependency_waits,
    ):
        print(f"- {test.__name__}")
        test()
    if failures:
        print(f"\n{len(failures)} failure(s): {', '.join(failures)}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
