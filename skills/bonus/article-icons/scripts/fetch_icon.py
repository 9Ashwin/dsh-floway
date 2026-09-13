#!/usr/bin/env python3
"""Fetch an itshover icon and emit a clean, static, inline-able SVG.

itshover ships icons as shadcn registry items: each is a React/motion
component (`https://itshover.com/r/<name>.json`). This script downloads that
JSON, isolates the <svg> markup, strips all React/motion-only attributes
(ref, onHover*, className, style, animate, ...), resolves the component props
(size/color/strokeWidth) into literal values, kebab-cases SVG attributes, and
returns plain SVG suitable for embedding directly into HTML or Markdown.

Trust boundary: everything on the wire is treated as untrusted input. The
request is confined to https://itshover.com (names are validated, and a
redirect off that host — including the bare-to-www hop, which is the only one
allowed — is refused before it is followed), the reply is size-capped, and the markup is rebuilt
from a whitelist rather than passed through — an unexpected element fails the
conversion instead of reaching the output. The icon is embedded in HTML or
Markdown afterwards, so an element or attribute that survives this step is one
you have agreed to ship.

Usage:
  python3 fetch_icon.py <icon-name> [--size N] [--color C] [--stroke-width W]
  python3 fetch_icon.py --list                 # print all available icon names
  python3 fetch_icon.py --search <term>        # filter icon names by substring

Examples:
  python3 fetch_icon.py heart-icon --size 32 --color "#e11d48"
  python3 fetch_icon.py brand-anthropic-icon --color "#d97757"
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

BASE = "https://itshover.com/r"
# itshover redirects the bare domain to www, so both are the same service; an
# exact-match set (not a suffix test) is what keeps `itshover.com.evil.example`
# out.
HOSTS = {"itshover.com", "www.itshover.com"}
REGISTRY = f"{BASE}/registry.json"
MAX_BYTES = 256 * 1024  # an icon component is a few KB; anything larger is not one
UA = "stream-it-article-icons (+https://github.com/9Ashwin/stream-it)"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# camelCase React attrs -> kebab-case / lowercase SVG attrs
KEBAB = {
    "strokeWidth": "stroke-width", "strokeLinecap": "stroke-linecap",
    "strokeLinejoin": "stroke-linejoin", "strokeDasharray": "stroke-dasharray",
    "strokeDashoffset": "stroke-dashoffset", "strokeMiterlimit": "stroke-miterlimit",
    "strokeOpacity": "stroke-opacity", "fillOpacity": "fill-opacity",
    "fillRule": "fill-rule", "clipRule": "clip-rule", "clipPath": "clip-path",
    "stopColor": "stop-color", "stopOpacity": "stop-opacity",
    "gradientUnits": "gradientUnits", "gradientTransform": "gradientTransform",
    "xmlnsXlink": "xmlns:xlink", "xlinkHref": "xlink:href",
    "textAnchor": "text-anchor", "fontSize": "font-size", "fontFamily": "font-family",
    "fontWeight": "font-weight", "letterSpacing": "letter-spacing",
    "dominantBaseline": "dominant-baseline",
    "textLength": "textLength", "lengthAdjust": "lengthAdjust",
}

# attributes safe to keep on a static SVG
ALLOWED = {
    "xmlns", "xmlns:xlink", "xlink:href", "viewBox", "width", "height", "fill",
    "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin",
    "stroke-dasharray", "stroke-dashoffset", "stroke-miterlimit",
    "stroke-opacity", "fill-opacity", "fill-rule", "clip-rule", "clip-path",
    "d", "cx", "cy", "r", "rx", "ry", "x", "y", "dx", "dy", "x1", "y1", "x2", "y2",
    "points", "transform", "opacity", "offset", "stop-color", "stop-opacity",
    "gradientUnits", "gradientTransform", "id", "preserveAspectRatio",
    "text-anchor", "font-size", "font-family", "font-weight", "letter-spacing",
    "dominant-baseline", "textLength", "lengthAdjust",
}

# Elements a static icon may use. A sampled 60 icons from itshover use only
# svg/g/path/rect/circle/ellipse/title/defs/clipPath, and the brand icons that
# draw a wordmark add `text` (facebook-icon is the concrete case). The set is
# deliberately minimal rather than generous: an element outside it makes the
# conversion fail closed with a clear message, so widening this list is a
# deliberate act rather than something that happens by drift. Everything not
# listed — <script>, <foreignObject>, <style>, <a>, <image>, animation — is
# refused, because this output is embedded in HTML or Markdown.
ALLOWED_TAGS = {
    "svg", "g", "defs", "title", "desc",
    "path", "circle", "ellipse", "rect", "line", "polyline", "polygon",
    "use", "clipPath", "mask", "pattern",
    "linearGradient", "radialGradient", "stop",
    "text", "tspan",
}


def _escape_attr(value: str) -> str:
    return (value.replace("&", "&amp;").replace("<", "&lt;")
                 .replace(">", "&gt;").replace('"', "&quot;"))


def _escape_text(value: str) -> str:
    """Escape bare ampersands in text nodes, leaving entities alone."""
    return re.sub(r"&(?!#?\w+;)", "&amp;", value)


def valid_name(name: str) -> bool:
    """A name is a single path segment, so it cannot reshape the request URL."""
    return bool(NAME_RE.match(name or ""))


class _PinnedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse a redirect target before the redirect is followed.

    The check in `_get` runs on the response, so by the time it can refuse, the
    request to the redirect target has already been sent — for a metadata
    endpoint a GET alone can be enough. Validating each hop here is what makes
    "the request is confined to HOSTS" true rather than aspirational.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urlparse(newurl)
        if target.scheme != "https" or target.hostname not in HOSTS:
            raise ValueError(f"refusing redirect to {newurl}: it leaves {sorted(HOSTS)}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


# build_opener swaps the default HTTPRedirectHandler for this subclass, so the
# pinned handler is what every request made through `_open` uses.
_OPENER = urllib.request.build_opener(_PinnedRedirectHandler())


def _open(req, timeout):
    """Indirection over urllib so the tests can stub the network out."""
    return _OPENER.open(req, timeout=timeout)


def _get(url):
    if not url.startswith(BASE + "/"):
        raise ValueError(f"refusing to fetch outside {BASE}: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with _open(req, 30) as r:
        final = urllib.parse.urlparse(r.geturl())
        if final.scheme != "https" or final.hostname not in HOSTS:
            raise ValueError(f"{url} resolved to {r.geturl()} — refusing to read it")
        raw = r.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError(f"{url} returned more than {MAX_BYTES} bytes — not an icon")
    return json.loads(raw)


def list_icons():
    return sorted(i["name"] for i in _get(REGISTRY).get("items", []))


def bundled_names():
    """The icon list shipped beside this script, for typos and offline --search."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon_names.json")
    try:
        with open(path, encoding="utf-8") as handle:
            return set(json.load(handle))
    except (OSError, ValueError):
        return set()


def fetch_component(name):
    data = _get(f"{BASE}/{name}.json")
    files = data.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError(f"{name}: registry item has no files[]")
    content = files[0].get("content")
    if not isinstance(content, str):
        raise ValueError(f"{name}: registry item has no files[0].content")
    return content


def _balanced(svg: str) -> bool:
    """Every element opened is closed, in order.

    The rebuild is element-wise, so an upstream `<title>` with no closing tag
    would otherwise come out as malformed markup. This catches that without
    parsing as XML, which would reject a legitimate `xlink:href` whose namespace
    declaration the component left out (browsers accept that inline).
    """
    stack: list[str] = []
    for match in re.finditer(r"<(/?)([A-Za-z][\w:]*)[^>]*?(/?)>", svg):
        close, tag, selfclose = match.group(1), match.group(2), match.group(3)
        if selfclose:
            continue
        if close:
            if not stack or stack.pop() != tag:
                return False
        else:
            stack.append(tag)
    return not stack


def convert(content, size=24, color="currentColor", stroke_width=2):
    """Convert a React/motion icon component's source into a static SVG string.

    Returns None when the source is not an icon this script understands. That
    includes markup containing an element outside ALLOWED_TAGS: a changed
    upstream format and a tampered reply look the same from here, and shipping
    either one into HTML is the failure this function exists to prevent.
    """
    c = content.replace("motion.", "")
    # remove JSX comments {/* ... */}
    c = re.sub(r"\{/\*.*?\*/\}", "", c, flags=re.S)
    m = re.search(r"<svg\b.*?</svg>", c, re.S)
    if not m:
        return None
    block = m.group(0)

    out = []
    for piece in re.split(r"(<[^>]+>)", block):
        if not piece.startswith("<"):
            out.append(_escape_text(piece))
            continue
        tm = re.match(r"<(/?)([\w:]+)(.*?)(/?)>", piece, re.S)
        if not tm:
            return None  # markup this parser cannot account for
        close, tag, attrs, selfclose = tm.groups()
        if tag not in ALLOWED_TAGS:
            return None  # unexpected element -> refuse the whole icon
        if close:
            out.append(f"</{tag}>")
            continue
        kept = []
        # attr=value where value is "...", {...balanced...}, or `...`
        for am in re.finditer(
            r'([\w:-]+)=(\{(?:[^{}]|\{[^{}]*\})*\}|"[^"]*"|`[^`]*`)', attrs
        ):
            k, v = am.group(1), am.group(2)
            k = KEBAB.get(k, k)
            if v.startswith('"'):
                val = v[1:-1]
            elif v.startswith("{"):
                inner = v[1:-1].strip()
                if inner == "size":
                    val = str(size)
                elif inner == "color":
                    val = color
                elif inner == "strokeWidth":
                    val = str(stroke_width)
                elif re.fullmatch(r"-?\d+(\.\d+)?", inner):
                    val = inner
                elif re.fullmatch(r'"[^"]*"', inner) or re.fullmatch(r"'[^']*'", inner):
                    val = inner[1:-1]
                else:
                    continue  # unresolved expression -> drop
            else:
                continue  # backtick template (className) -> drop
            if k in {"href", "xlink:href"} and not val.startswith("#"):
                continue  # only same-document references, never a URL
            if k in ALLOWED:
                kept.append(f'{k}="{_escape_attr(val)}"')
        attrstr = (" " + " ".join(kept)) if kept else ""
        out.append(f"<{tag}{attrstr}{'/' if selfclose else ''}>")

    svg = "".join(out)
    svg = re.sub(r"\s+", " ", svg).strip()
    svg = re.sub(r"\s*>\s*<\s*", "><", svg)
    # guard: reject anything still carrying React residue, or left unbalanced
    if "{" in svg or "motion" in svg or "className" in svg:
        return None
    if not _balanced(svg):
        return None
    return svg


def main():
    ap = argparse.ArgumentParser(description="Fetch an itshover icon as static SVG.")
    ap.add_argument("name", nargs="?", help="icon name, e.g. heart-icon")
    ap.add_argument("--size", type=int, default=24)
    ap.add_argument("--color", default="currentColor")
    ap.add_argument("--stroke-width", type=float, default=2)
    ap.add_argument("--list", action="store_true", help="list all icon names")
    ap.add_argument("--search", help="filter icon names by substring")
    args = ap.parse_args()

    if args.list or args.search:
        names = list_icons()
        if args.search:
            names = [n for n in names if args.search.lower() in n.lower()]
        print("\n".join(names))
        return 0

    if not args.name:
        ap.error("icon name required (or use --list / --search)")

    if not valid_name(args.name):
        known = bundled_names()
        hint = ""
        if known:
            close = sorted(n for n in known if args.name.lower().strip() in n)
            if close:
                hint = " Did you mean: " + ", ".join(close[:5]) + "?"
        print(f"ERROR: {args.name!r} is not a valid icon name "
              f"(lowercase words separated by single hyphens).{hint}", file=sys.stderr)
        return 2

    known = bundled_names()
    if known and args.name not in known:
        print(f"WARNING: {args.name!r} is not in the bundled list — upstream may have "
              f"added it. Run --search {args.name!r} to check.", file=sys.stderr)

    try:
        content = fetch_component(args.name)
    except Exception as e:
        print(f"ERROR: could not fetch '{args.name}': {e}", file=sys.stderr)
        print("Try --search <term> to find the right name.", file=sys.stderr)
        return 1

    svg = convert(content, size=args.size, color=args.color, stroke_width=args.stroke_width)
    if not svg:
        print(f"ERROR: could not convert '{args.name}' to static SVG "
              f"(unexpected markup — not embedding it).", file=sys.stderr)
        return 2
    print(svg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
