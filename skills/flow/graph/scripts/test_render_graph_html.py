#!/usr/bin/env python3
"""Unit tests for render_graph_html.py — run with `python3 test_render_graph_html.py`.

The board is the artifact the user actually reads, so what these check is that it
cannot claim something the checkpoint does not say. No test framework: the
renderer is stdlib-only on purpose, so its test is too.
"""

from __future__ import annotations

import importlib.util
import os
import re

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
    check("the reload comment says re-rendering is what updates it",
          "not a live feed" in html, html[:200])


def main() -> int:
    print("render_graph_html.py tests")
    for test in (test_current_wave_is_derived_not_read, test_finished_graph_says_so,
                 test_footer_names_the_real_source, test_snapshot_is_stated_and_stamped):
        print(f"- {test.__name__}")
        test()
    if failures:
        print(f"\n{len(failures)} failure(s): {', '.join(failures)}")
        return 1
    print("\nok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
