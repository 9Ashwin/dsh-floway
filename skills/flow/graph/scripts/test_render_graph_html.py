#!/usr/bin/env python3
"""Unit tests for render_graph_html.py — run with `python3 test_render_graph_html.py`.

The board is the artifact the user actually reads, so what these check is that it
cannot claim something the checkpoint does not say. No test framework: the
renderer is stdlib-only on purpose, so its test is too.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def load_module():
    spec = importlib.util.spec_from_file_location(
        "render_graph_html", os.path.join(HERE, "render_graph_html.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rh = load_module()
failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


def board(state, source=None):
    return rh.render(state, source=source) if source else rh.render(state)


def marked_current(html: str) -> int:
    """The wave index the board marks as running, or -1."""
    for match in re.finditer(r'<section class="wave ([a-z]+)">', html):
        if match.group(1) == "cur":
            return html[:match.start()].count('<section class="wave')
    return -1


def stale_state():
    """A checkpoint whose cached `current_wave` is behind its node statuses.

    This is the shape a real run produces: recording the last node of wave 0 with
    `set` did not refresh the cached field.
    """
    return {
        "version": 1, "task": "t", "repo": "owner/repo", "current_wave": 0,
        "waves": [[1], [2]],
        "nodes": {
            "1": {"title": "a", "status": "shipped", "commit": "aaa1111"},
            "2": {"title": "b", "status": "pending"},
        },
    }


def test_current_wave_is_derived_not_read():
    """Regression: the board trusted `state['current_wave']`, which only a
    plan/set refreshes, so it highlighted the wave that had just closed."""
    html = board(stale_state())
    check("the wave with unfinished work is the current one", marked_current(html) == 1,
          f"marked={marked_current(html)}")
    check("the finished wave is not marked running", "wave done" in html, html[:200])
    check("the subtitle counts from the derived wave", "wave 1 of 1" in html,
          re.search(r'<div class="sub">.*?</div>', html).group(0) if '<div class="sub">' in html else "")

    # Negative control: a checkpoint that is genuinely at wave 0 still says so.
    fresh = stale_state()
    fresh["nodes"]["1"]["status"] = "in_progress"
    check("a genuinely current wave 0 is still wave 0", marked_current(board(fresh)) == 0)


def test_finished_graph_says_so():
    state = stale_state()
    state["nodes"]["1"]["status"] = "shipped"
    state["nodes"]["2"]["status"] = "shipped"
    state["current_wave"] = 99  # stale in the other direction
    html = board(state)
    check("no wave is marked running once everything is terminal", marked_current(html) == -1,
          f"marked={marked_current(html)}")
    check("the subtitle says the graph is closed", "every wave closed" in html)
    check("and it never claims a wave beyond the last", "wave 2 of 1" not in html)


def settled_out_of_layout_state():
    """The shape `plan --keep-shipped --only-pending` writes.

    Once work settles the layout stops carrying it, so `waves` describes only what
    is left while every node stays in the node table with its status.
    """
    return {
        "version": 1, "task": "t", "repo": "owner/repo", "current_wave": 0,
        "waves": [[3]],
        "nodes": {
            "1": {"title": "a", "status": "shipped", "commit": "aaa1111"},
            "2": {"title": "b", "status": "shipped", "commit": "bbb2222"},
            "3": {"title": "c", "status": "pending"},
        },
    }


def test_settled_nodes_stay_on_the_board():
    """Regression: `waves` is the scheduling layout and `--only-pending` drops
    settled nodes from it, so a board that read `waves` alone lost every finished
    node the moment the graph was re-layered. The mermaid kept them green — it
    walks the node table — while the cards below simply stopped existing, which
    made a half-finished run look like a graph that had only ever had one wave."""
    html = board(settled_out_of_layout_state())
    for nid in ("1", "2"):
        check(f"settled #{nid} still has a card", f'<span class="nid">#{nid}</span>' in html)
    check("and is reported as settled rather than dropped",
          '<h2>Settled <span class="wcount">×2' in html,
          re.search(r"<h2>Settled.*?</h2>", html, re.S).group(0) if "Settled" in html else "")
    check("the live wave is still the one marked running", marked_current(html) == 0,
          f"marked={marked_current(html)}")

    # Negative control: no wave number is invented for the settled work. The index
    # it ran under is gone — `--only-pending` compacts the layout — and reusing the
    # fresh one would draw a wave that never existed.
    check("no wave number is invented for them", "Wave 1" not in html,
          html[html.find("Settled"):][:160])

    # Negative control: a graph with nothing off-layout gains no extra section.
    intact = settled_out_of_layout_state()
    intact["waves"] = [[1, 2], [3]]
    check("nothing settled means no settled section", "<h2>Settled" not in board(intact))


def test_footer_names_the_real_source():
    """The footer used to hardcode the default name, so a board rendered from a
    per-run checkpoint claimed to come from `.graph_state.json`."""
    html = board(stale_state(), source=".graph_state-prd015")
    footer = re.search(r"<footer>(.*?)</footer>", html, re.S).group(1)
    check("the footer names the file that was rendered", ".graph_state-prd015" in footer, footer[:200])
    check("and not the default name", ".graph_state.json" not in footer, footer[:200])

    # Negative control: the default is still what an unlabelled render reports.
    default = board(stale_state())
    check("a render with no source names the default",
          rh.STATE_DEFAULT in re.search(r"<footer>(.*?)</footer>", default, re.S).group(1))


def test_snapshot_is_stated_and_stamped():
    html = board(stale_state())
    footer = re.search(r"<footer>(.*?)</footer>", html, re.S).group(1)
    check("the footer calls itself a snapshot", "Snapshot" in footer, footer[:120])
    check("it carries a render timestamp", re.search(r"rendered \d{4}-\d\d-\d\d \d\d:\d\d:\d\d", footer) is not None,
          footer[:200])
    check("the page states that a 5s reload follows the checkpoints",
          "reloads every 5s" in footer and "re-renders this file" in footer, footer[:260])
    # Negative control for the sentence this replaced: the board used to tell the
    # reader that reloading "never shows new progress", which stopped being true
    # once plan/set began re-rendering it on every write.
    check("it no longer claims reloading cannot show progress",
          "never\n      shows new progress" not in footer and "never shows new progress" not in footer,
          footer[:260])


def test_both_argument_spellings_work():
    """`--state x` used to be read as a *path*, so the run died on
    FileNotFoundError: '--state' and said nothing about the real mistake."""
    positional = rh.parse_args(["a.json", "b.html"])
    check("positional STATE is the state", positional.state == "a.json", str(positional))
    check("positional OUT is the output", positional.out == "b.html", str(positional))
    flagged = rh.parse_args(["--state", "a.json", "--out", "b.html"])
    check("--state names the same field", flagged.state == "a.json", str(flagged))
    check("--out names the same field", flagged.out == "b.html", str(flagged))
    check("flags are never mistaken for a filename",
          not any(value.startswith("--") for value in (flagged.state, flagged.out)), str(flagged))
    defaulted = rh.parse_args([])
    check("no arguments falls back to the documented defaults",
          defaulted.state == rh.STATE_DEFAULT and defaulted.out == "graph.html", str(defaulted))


def test_a_repeated_value_is_refused():
    # Each value has two spellings, so giving both is ambiguous rather than a
    # silent last-one-wins. The positional OUT case needs a leading positional
    # STATE, otherwise the first bare argument fills STATE instead.
    for argv in (["a.json", "--state", "b.json"],
                 ["a.json", "b.html", "--out", "c.html"]):
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                rh.parse_args(argv)
            check(f"{argv} refused", False, "parse_args accepted the value twice")
        except SystemExit as exc:
            check(f"{argv} refused", exc.code == 2, str(exc.code))


def test_an_unknown_flag_is_refused():
    try:
        with contextlib.redirect_stderr(io.StringIO()) as err:
            rh.parse_args(["--bogus", "a.json"])
        check("unknown flag refused", False, "parse_args accepted --bogus")
    except SystemExit as exc:
        check("unknown flag refused", exc.code == 2, str(exc.code))
        check("and argparse names it", "--bogus" in err.getvalue(), err.getvalue())


def test_missing_checkpoint_reports_instead_of_raising():
    with tempfile.TemporaryDirectory() as tmp:
        missing = os.path.join(tmp, "nope.json")
        err = io.StringIO()
        saved_argv = sys.argv
        sys.argv = ["render_graph_html.py", missing, os.path.join(tmp, "out.html")]
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                code = rh.main()
        finally:
            sys.argv = saved_argv
        check("a missing checkpoint exits non-zero", code == 1, str(code))
        check("and says how to produce one", "graph_state.py plan" in err.getvalue(), err.getvalue())


def main() -> int:
    print("render_graph_html.py tests")
    for test in (test_current_wave_is_derived_not_read, test_finished_graph_says_so,
                 test_settled_nodes_stay_on_the_board,
                 test_footer_names_the_real_source, test_snapshot_is_stated_and_stamped,
                 test_both_argument_spellings_work, test_a_repeated_value_is_refused,
                 test_an_unknown_flag_is_refused, test_missing_checkpoint_reports_instead_of_raising):
        print(f"- {test.__name__}")
        test()
    if failures:
        print(f"\n{len(failures)} failure(s): {', '.join(failures)}")
        return 1
    print("\nok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
