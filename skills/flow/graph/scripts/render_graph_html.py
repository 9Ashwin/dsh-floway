#!/usr/bin/env python3
"""Render a light-theme graph.html dashboard from a .graph_state.json state file.

Usage:
    render_graph_html.py [state.json] [graph.html]
    render_graph_html.py --state state.json --out graph.html

Defaults to reading ./.graph_state.json and writing ./graph.html. Both spellings
work because the skill's docs use positional arguments while people reach for
flags; before this, `--state x` was taken as a *path* and the run died on
FileNotFoundError: '--state', which says nothing about the real mistake.

Called by the /graph skill at every checkpoint: `plan` and `set` run it after each
write, so the page tracks the checkpoints without anyone remembering to re-render.
The state is inlined, so the page is a snapshot of the last write — an open tab
reloads itself every 5s and therefore follows the checkpoints, but nothing between
two writes shows up. No third-party dependencies — stdlib only.
"""
import argparse
import html
import json
import os
import sys
from datetime import datetime

STATE_DEFAULT = ".graph_state.json"
LEGACY_STATE = ".graph_state"

STATUS = {
    "pending":     ("Pending",     "#8C8579", "#EFECE3"),
    "in_progress": ("In Progress", "#CC785C", "#F7E9E2"),
    "shipped":     ("Shipped",     "#3D7A5A", "#DFEEE4"),
    "failed":      ("Failed",      "#B54A3E", "#F6DEDA"),
    "blocked":     ("Blocked",     "#9A6C3A", "#F2E6D4"),
    "skipped":     ("Skipped",     "#8C8579", "#EFECE3"),
}


def esc(s):
    return html.escape(str(s if s is not None else ""))


def node_card(nid, n):
    st = n.get("status", "pending")
    label, fg, bg = STATUS.get(st, STATUS["pending"])
    deps = n.get("deps") or []
    deps_str = ", ".join(f"#{d}" for d in deps) if deps else "no deps"
    meta = []
    if n.get("pr"):
        meta.append(f'PR #{esc(n["pr"])}')
    if n.get("branch"):
        meta.append(f'<code>{esc(n["branch"])}</code>')
    if n.get("attempts"):
        meta.append(f'attempt {esc(n["attempts"])}')
    meta_html = " · ".join(meta)
    err = f'<div class="err">{esc(n["error"])}</div>' if n.get("error") else ""
    return f"""
      <div class="node" style="border-left:4px solid {fg}">
        <div class="node-top">
          <span class="nid">#{esc(nid)}</span>
          <span class="badge" style="color:{fg};background:{bg}">{label}</span>
        </div>
        <div class="title">{esc(n.get('title','(untitled)'))}</div>
        <div class="deps">{esc(deps_str)}</div>
        {f'<div class="meta">{meta_html}</div>' if meta_html else ''}
        {err}
      </div>"""


def mermaid(state):
    lines = ["graph LR"]
    nodes = state.get("nodes", {})
    for nid, n in nodes.items():
        t = n.get("title", "")
        lines.append(f'  n{nid}["#{nid} {t}"]')
    for nid, n in nodes.items():
        for d in (n.get("deps") or []):
            lines.append(f"  n{d} --> n{nid}")
    # color by status
    for st, (_, fg, bg) in STATUS.items():
        ids = [f"n{nid}" for nid, n in nodes.items() if n.get("status") == st]
        if ids:
            lines.append(f"  classDef {st} fill:{bg},stroke:{fg},color:#33312B;")
            lines.append(f"  class {','.join(ids)} {st};")
    return "\n".join(lines)


TERMINAL = {"shipped", "skipped", "failed", "blocked"}


def current_wave(state):
    """The wave still waiting on work — derived, never read from the file.

    `state['current_wave']` is a cached copy that only a plan/set refreshes, so a
    board that trusted it could mark the wrong wave (recording the last node of a
    wave used to leave it pointing at the wave that had just closed). Node
    statuses are the source of truth.
    """
    waves = state.get("waves", [])
    nodes = state.get("nodes", {})
    for index, wave in enumerate(waves):
        if any(nodes.get(str(nid), {}).get("status", "pending") not in TERMINAL for nid in wave):
            return index
    return len(waves)


def render(state, source: str = STATE_DEFAULT):
    # Stamped into the footer so a stale board is visibly stale: the page is a
    # snapshot, and the reload every 5s cannot change it on its own.
    rendered_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nodes = state.get("nodes", {})
    total = len(nodes)
    counts = {k: 0 for k in STATUS}
    for n in nodes.values():
        counts[n.get("status", "pending")] = counts.get(n.get("status", "pending"), 0) + 1
    shipped = counts.get("shipped", 0)
    pct = int(shipped / total * 100) if total else 0
    waves = state.get("waves", [])
    cur = current_wave(state)

    wave_line = (f"wave {cur} of {max(len(waves) - 1, 0)}" if cur < len(waves)
                 else "every wave closed")

    legend = "".join(
        f'<span class="lg"><i style="background:{bg};border-color:{fg}"></i>{label}</span>'
        for label, fg, bg in STATUS.values()
    )

    # Waves are the scheduling layout, and `--only-pending` deliberately drops
    # settled nodes from them — so a board that read `waves` alone lost every
    # completed node the moment the graph was re-layered. A node the layout no
    # longer carries still belongs on the board, so it renders in a trailing
    # section instead of vanishing. It is not put back into a numbered wave: those
    # numbers are not recoverable. `--only-pending` compacts the layout, so the
    # index a re-plan hands out is not the index the node ran under — grouping by
    # the stale one merged finished work into a wave of live work under a single
    # number, which reads as one wave that never existed.
    scheduled = {nid for wave in waves for nid in wave}
    loose = sorted((int(key) for key in nodes if int(key) not in scheduled), key=int)

    wave_html = ""
    for index, wave in enumerate(waves):
        state_cls = "cur" if index == cur else ("done" if index < cur else "future")
        running = ' <span class="pill">running</span>' if index == cur else ""
        cards = "".join(node_card(str(nid), nodes.get(str(nid), {"title": f"#{nid}"})) for nid in wave)
        wave_html += f"""
      <section class="wave {state_cls}">
        <h2>Wave {index} <span class="wcount">×{len(wave)} parallel</span>{running}</h2>
        <div class="nodes">{cards}</div>
      </section>"""

    if loose:
        cards = "".join(node_card(str(nid), nodes.get(str(nid), {"title": f"#{nid}"})) for nid in loose)
        wave_html += f"""
      <section class="wave done">
        <h2>Settled <span class="wcount">×{len(loose)} · no longer in the layout</span></h2>
        <div class="nodes">{cards}</div>
      </section>"""

    stat = lambda k: f'<b style="color:{STATUS[k][1]}">{counts.get(k,0)}</b> {STATUS[k][0].lower()}'
    stats = " · ".join(stat(k) for k in ["shipped", "in_progress", "failed", "blocked", "skipped", "pending"])

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- Reloads every 5s. The state below is inlined at render time, so a reload only shows
     checkpoints: `plan` and `set` re-render this file on every write, and nothing between two
     writes appears here. -->
<meta http-equiv="refresh" content="5">
<title>graph · {esc(state.get('task','execution'))}</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<style>
  :root {{ --paper:#F5F4EE; --card:#FFFFFF; --ink:#33312B; --muted:#8C8579;
           --coral:#CC785C; --line:#E7E3D9; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--paper); color:var(--ink);
    font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:32px 24px 64px; }}
  header {{ border-bottom:1px solid var(--line); padding-bottom:20px; margin-bottom:24px; }}
  h1 {{ font-size:22px; margin:0 0 4px; font-weight:650; }}
  .sub {{ color:var(--muted); font-size:13px; }}
  .bar {{ height:8px; background:var(--line); border-radius:99px; margin:16px 0 8px; overflow:hidden; }}
  .bar>i {{ display:block; height:100%; width:{pct}%; background:var(--coral); border-radius:99px; }}
  .stats {{ font-size:13px; color:var(--muted); }}
  .legend {{ display:flex; gap:14px; flex-wrap:wrap; margin:14px 0 4px; font-size:12px; color:var(--muted); }}
  .lg {{ display:inline-flex; align-items:center; gap:6px; }}
  .lg i {{ width:12px; height:12px; border-radius:3px; border:1px solid; display:inline-block; }}
  .diagram {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px; margin:20px 0; overflow:auto; }}
  .wave {{ margin:22px 0; }}
  .wave h2 {{ font-size:15px; margin:0 0 12px; display:flex; align-items:center; gap:10px; }}
  .wcount {{ font-weight:400; color:var(--muted); font-size:12px; }}
  .pill {{ font-size:11px; color:#fff; background:var(--coral); padding:2px 9px; border-radius:99px; }}
  .wave.future {{ opacity:.55; }}
  .nodes {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:12px; }}
  .node {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px 14px; }}
  .node-top {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }}
  .nid {{ font-weight:650; color:var(--muted); font-size:13px; }}
  .badge {{ font-size:11px; padding:2px 8px; border-radius:99px; font-weight:600; }}
  .title {{ font-weight:550; margin-bottom:6px; }}
  .deps {{ font-size:12px; color:var(--muted); }}
  .meta {{ font-size:12px; color:var(--muted); margin-top:6px; }}
  .meta code, .node code {{ background:var(--paper); padding:1px 5px; border-radius:5px; font-size:11px; }}
  .err {{ font-size:12px; color:#B54A3E; margin-top:6px; white-space:pre-wrap; }}
  footer {{ margin-top:32px; color:var(--muted); font-size:12px; text-align:center; }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>{esc(state.get('task','Task Graph Execution'))}</h1>
      <div class="sub">{esc(state.get('repo',''))} · {wave_line} · updated {esc(state.get('updated_at',''))}</div>
      <div class="bar"><i></i></div>
      <div class="stats">{shipped}/{total} shipped ({pct}%) &nbsp;—&nbsp; {stats}</div>
      <div class="legend">{legend}</div>
    </header>
    <div class="diagram"><pre class="mermaid">{esc(mermaid(state))}</pre></div>
    {wave_html}
    <footer><strong>Snapshot</strong> of the last checkpoint, rendered {rendered_at} by /graph from
      <code>{esc(source)}</code>. Every <code>plan</code> and <code>set</code> re-renders this file, so an
      open tab — it reloads every 5s — follows the checkpoints; work between two writes does not
      appear until the next one.</footer>
  </div>
  <script>mermaid.initialize({{ startOnLoad:true, theme:"neutral" }});</script>
</body>
</html>"""


def resolve_state(path: str) -> str:
    """Fall back to the pre-rename checkpoint sitting beside `path`."""
    directory = os.path.dirname(path)
    legacy = os.path.join(directory, LEGACY_STATE) if directory else LEGACY_STATE
    if not os.path.exists(path) and os.path.basename(path) == STATE_DEFAULT and os.path.exists(legacy):
        print(f"note: reading the pre-rename checkpoint {legacy}", file=sys.stderr)
        return legacy
    return path


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Accept the documented positionals and the flags people actually type.

    `nargs="?"` on both positionals keeps `render.py a.json b.html` working while
    `--state`/`--out` name the same two values. An unknown flag now fails with
    argparse's own message instead of being read as a filename.
    """
    parser = argparse.ArgumentParser(
        description="Render graph.html from a /graph checkpoint.",
        epilog="Positional and flag spellings are equivalent.")
    parser.add_argument("state_pos", nargs="?", metavar="STATE", help="checkpoint to read")
    parser.add_argument("out_pos", nargs="?", metavar="OUT", help="dashboard to write")
    parser.add_argument("--state", dest="state_flag", help="checkpoint to read")
    parser.add_argument("--out", dest="out_flag", help="dashboard to write")
    args = parser.parse_args(argv)
    if args.state_pos and args.state_flag:
        parser.error("give the checkpoint once, as STATE or --state, not both")
    if args.out_pos and args.out_flag:
        parser.error("give the output once, as OUT or --out, not both")
    args.state = args.state_flag or args.state_pos or STATE_DEFAULT
    args.out = args.out_flag or args.out_pos or "graph.html"
    return args


def main():
    args = parse_args(sys.argv[1:])
    src = resolve_state(args.state)
    dst = args.out
    if not os.path.exists(src):
        print(f"render_graph_html: no checkpoint at {src} — run graph_state.py plan first",
              file=sys.stderr)
        return 1
    with open(src, encoding="utf-8") as f:
        state = json.load(f)
    state.setdefault("updated_at", datetime.now().isoformat(timespec="seconds"))
    with open(dst, "w", encoding="utf-8") as f:
        f.write(render(state, source=src))
    print(f"wrote {dst} from {src}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
