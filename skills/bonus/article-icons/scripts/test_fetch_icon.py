#!/usr/bin/env python3
"""Unit tests for fetch_icon.py — run with `python3 test_fetch_icon.py`.

No network: the fetcher is exercised through a stubbed `_open`, and every
malicious fixture is checked together with the benign case it must not break.
The script is stdlib-only on purpose, so its test is too.
"""

from __future__ import annotations

import importlib.util
import json
import os
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))


def load_module():
    spec = importlib.util.spec_from_file_location("fetch_icon", os.path.join(HERE, "fetch_icon.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fi = load_module()
failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


def svg_tags(svg: str) -> list[str]:
    """Element names, with ElementTree's `{namespace}` prefix stripped."""
    return [el.tag.rsplit("}", 1)[-1] for el in ET.fromstring(svg).iter()]


# A realistic itshover component: motion wrapper, props, JSX spread, className.
BENIGN = """\
"use client";
import { motion } from "motion/react";
const HeartIcon = ({ size = 24, color = "currentColor", strokeWidth = 2, className = "", ...props }) => (
  <motion.svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    width={size}
    height={size}
    fill="none"
    stroke={color}
    strokeWidth={strokeWidth}
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden="true"
    {...props}
  >
    <title>Heart</title>
    <path d="M12 21C12 21 4 15 4 9a4 4 0 0 1 8-2 4 4 0 0 1 8 2c0 6-8 12-8 12z" />
    <circle cx="12" cy="9" r="2" />
  </motion.svg>
);
export default HeartIcon;
"""


class FakeResponse:
    def __init__(self, payload: bytes, url: str):
        self._payload = payload
        self._url = url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def geturl(self):
        return self._url

    def read(self, n=-1):
        return self._payload if n is None or n < 0 else self._payload[:n]


def with_stubbed_open(url: str, payload: bytes, force_size: int | None = None):
    """Return (result, error) for one `_get` call against a stub reply."""
    original = fi._open
    body = payload if force_size is None else b"x" * force_size
    fi._open = lambda req, timeout: FakeResponse(body, url)
    try:
        try:
            return fi._get(f"{fi.BASE}/heart-icon.json"), None
        except Exception as exc:  # noqa: BLE001 - the test asserts on the message
            return None, exc
    finally:
        fi._open = original


def test_benign_icon_converts():
    svg = fi.convert(BENIGN)
    check("a real component converts", isinstance(svg, str) and svg.startswith("<svg"), str(svg)[:120])
    check("props resolve to literals", 'width="24"' in svg and 'stroke="currentColor"' in svg, svg[:200])
    check("camelCase attributes are kebab-cased", 'stroke-width="2"' in svg, svg[:200])
    check("no React or motion residue",
          "{" not in svg and "motion" not in svg and "className" not in svg)
    check("the geometry survives", "M12 21C12 21" in svg)
    check("the parsed document has only expected elements",
          set(svg_tags(svg)) <= fi.ALLOWED_TAGS, str(svg_tags(svg)))

    # Custom props must land in the output, not stay as placeholders.
    custom = fi.convert(BENIGN, size=48, color="#e11d48", stroke_width=3)
    check("caller sizes and colors are applied",
          'width="48"' in custom and 'stroke="#e11d48"' in custom and 'stroke-width="3"' in custom,
          custom[:200])


def test_attribute_value_cannot_break_out():
    """The reported output-injection flaw: a value carries a quote into the markup."""
    hostile = BENIGN.replace(
        '<path d=',
        """<path fill={'x" onload="alert(1)'} d=""")
    svg = fi.convert(hostile)
    check("the hostile fixture still converts to a document", isinstance(svg, str), str(svg)[:120])
    if isinstance(svg, str):
        root = ET.fromstring(svg)
        attrs = {k: v for el in root.iter() for k, v in el.attrib.items()}
        check("no attribute was injected by the value", "onload" not in attrs, str(attrs))
        check("the quote is escaped, not emitted raw", 'onload="' not in svg, svg[:300])
        check("the value itself survives escaped",
              any("onload=" in v and "alert(1)" in v for v in attrs.values()), str(attrs))

    # Negative control: a benign fill value is passed through unchanged.
    plain = fi.convert(BENIGN.replace('<path d=', '<path fill="#ff0000" d='))
    check("a benign attribute value is untouched", 'fill="#ff0000"' in plain, plain[:200])


def test_non_icon_elements_are_refused():
    """Fail closed: an element an icon never needs must not reach the output."""
    replacements = {
        "script": "<script>alert(1)</script>",
        "foreignObject": '<foreignObject width="1" height="1"></foreignObject>',
        "style": "<style>path{fill:url(javascript:alert(1))}</style>",
        "a": '<a xlink:href="https://evil.example/x">hi</a>',
        "animate": '<animate attributeName="d" to="M0 0" dur="1s" />',
        "image": '<image x="0" y="0" width="1" height="1" xlink:href="https://evil.example/x.png" />',
    }
    for element, markup in replacements.items():
        hostile = BENIGN.replace("<title>Heart</title>", "<title>Heart</title>" + markup)
        check(f"<{element}> is refused", fi.convert(hostile) is None, str(fi.convert(hostile))[:160])

    # Negative control: the same insertion point with a legitimate element converts.
    benign = BENIGN.replace("<title>Heart</title>", "<title>Heart</title><rect x=\"1\" y=\"1\" width=\"2\" height=\"2\" />")
    check("a legitimate element at the same spot still converts",
          fi.convert(benign) is not None, str(fi.convert(benign))[:160])


def test_text_wordmarks_are_allowed():
    """Regression: `facebook-icon` draws its wordmark with <text>, and refusing
    <text> turned a converting icon into a failing one."""
    fixture = BENIGN.replace(
        '<circle cx="12" cy="9" r="2" />',
        '<text x="12" y="2" textAnchor="middle" fontSize="10" fill={color} opacity={0}>'
        '<tspan dx="1">f</tspan></text>')
    svg = fi.convert(fixture)
    check("a <text> wordmark converts", isinstance(svg, str), str(svg)[:160])
    if isinstance(svg, str):
        check("text presentation attributes are kebab-cased",
              'text-anchor="middle"' in svg and 'font-size="10"' in svg, svg[:300])
        check("the <tspan> child survives", "<tspan" in svg)
        check("the document parses", "text" in svg_tags(svg), str(svg_tags(svg)))

    # The capability checks still apply to text: an injected handler is dropped
    # and text content is escaped rather than passed through raw.
    hostile = fixture.replace('<tspan dx="1">', '<tspan onload="alert(1)" dx="1">')
    hostile = hostile.replace(">f</tspan>", ">&lt;script&gt;</tspan>")
    out = fi.convert(hostile)
    check("an event handler on <text> is dropped", out is not None and "onload" not in out, str(out)[:200])
    check("text content is not re-escaped into markup",
          out is not None and "<script" not in out, str(out)[:200])


def test_off_document_href_is_dropped():
    """A javascript:/remote href is the other way markup reaches outside the document."""
    hostile = BENIGN.replace('<path d=', '<use xlink:href="javascript:alert(1)" d=')
    svg = fi.convert(hostile)
    check("the icon still converts", isinstance(svg, str), str(svg)[:120])
    check("the remote href is gone", svg is not None and "javascript" not in svg, str(svg)[:200])

    # Negative control: a same-document reference is legitimate and must be kept.
    good = BENIGN.replace("<title>Heart</title>",
                          '<title>Heart</title><defs><clipPath id="c"><circle cx="1" cy="1" r="1" /></clipPath></defs>')
    good = good.replace('<circle cx="12" cy="9" r="2" />',
                        '<use xlink:href="#c" /><circle cx="12" cy="9" r="2" />')
    kept = fi.convert(good)
    check("a same-document href is kept",
          kept is not None and 'xlink:href="#c"' in kept, str(kept)[:300])


def test_unparseable_markup_is_refused():
    check("an unclosed tag is refused",
          fi.convert(BENIGN.replace("<title>Heart</title>", "<title>Heart")) is None)
    check("a page without an svg is refused", fi.convert("<html><body>hi</body></html>") is None)


def test_names_are_validated():
    for name in ("heart-icon", "brand-anthropic-icon", "a1", "icon-2x"):
        check(f"{name!r} is valid", fi.valid_name(name))
    for name in ("../../etc/passwd", "a/b", "x?y=1", "x#y", "X", "", "a b", "a%2e", "-lead", "trail-", "a--b"):
        check(f"{name!r} is rejected", not fi.valid_name(name))


def test_request_stays_on_the_pinned_host():
    payload = json.dumps({"files": [{"content": BENIGN}]}).encode()
    ok, err = with_stubbed_open("https://itshover.com/r/heart-icon.json", payload)
    check("a same-host reply is read", err is None and ok["files"][0]["content"] == BENIGN, str(err))

    ok, err = with_stubbed_open("https://www.itshover.com/r/heart-icon.json", payload)
    check("the bare-to-www redirect is allowed", err is None, str(err))

    _, err = with_stubbed_open("https://evil.example/r/heart-icon.json", payload)
    check("an off-host redirect is refused", isinstance(err, ValueError) and "refusing" in str(err), str(err))

    _, err = with_stubbed_open("https://itshover.com.evil.example/r/heart-icon.json", payload)
    check("a lookalike host is refused", isinstance(err, ValueError), str(err))

    _, err = with_stubbed_open("http://www.itshover.com/r/heart-icon.json", payload)
    check("a downgrade to http is refused", isinstance(err, ValueError), str(err))

    # A URL outside the pinned base never reaches the network at all.
    original = fi._open
    called = []
    fi._open = lambda req, timeout: called.append(req) or (_ for _ in ()).throw(AssertionError("network used"))
    try:
        raised = False
        try:
            fi._get("https://elsewhere.example/r/x.json")
        except ValueError:
            raised = True
        finally:
            fi._open = original
    finally:
        fi._open = original
    check("a URL outside the base never opens a connection", raised and not called)


def test_reply_size_is_capped():
    _, err = with_stubbed_open("https://itshover.com/r/heart-icon.json", b"",
                               force_size=fi.MAX_BYTES + 1)
    check("an oversized reply is refused", isinstance(err, ValueError) and "bytes" in str(err), str(err))

    # Negative control: a reply of exactly the cap still parses.
    empty = json.dumps({"pad": ""}).encode()
    payload = json.dumps({"pad": "x" * (fi.MAX_BYTES - len(empty))}).encode()
    check("the fixture sits exactly on the cap", len(payload) == fi.MAX_BYTES, str(len(payload)))
    ok, err = with_stubbed_open("https://itshover.com/r/heart-icon.json", payload)
    check("a reply at the limit still parses", err is None and isinstance(ok, dict), str(err))


def test_registry_shape_is_validated():
    original = fi._open
    try:
        fi._open = lambda req, timeout: FakeResponse(json.dumps({"files": []}).encode(),
                                                     "https://itshover.com/r/x.json")
        raised = False
        try:
            fi.fetch_component("x-icon")
        except ValueError:
            raised = True
        check("an empty files[] is refused", raised)
    finally:
        fi._open = original


def test_bundled_list_matches_the_shipped_names():
    known = fi.bundled_names()
    check("the bundled list loads", len(known) > 100, str(len(known)))
    check("every bundled name passes validation",
          all(fi.valid_name(n) for n in known),
          str([n for n in known if not fi.valid_name(n)][:5]))


def test_a_redirect_is_refused_before_it_is_followed():
    """Pin the hop check, not the read check.

    `with_stubbed_open` replaces `_open`, which sits *below* urllib's redirect
    machinery, so the existing cases can only show that a reply is not read --
    never that a request was not sent. Validating each hop is the only place
    that can refuse in time, so that is what these cases exercise.
    """
    handler = fi._PinnedRedirectHandler()
    req = urllib.request.Request("https://itshover.com/r/heart-icon.json")

    for target, why in (
        ("http://169.254.169.254/latest/meta-data/", "an https->http downgrade to a metadata address"),
        ("https://evil.example/r/x.json", "an off-host target"),
        ("https://itshover.com.evil.example/r/x.json", "a lookalike host"),
        ("http://www.itshover.com/r/x.json", "a plain-http same-host hop"),
    ):
        raised = False
        try:
            handler.redirect_request(req, None, 302, "Found", {}, target)
        except ValueError:
            raised = True
        check(f"{why} is refused by the redirect handler", raised, target)

    # Positive control: the handler is not a blanket refusal -- the bare-to-www
    # hop itshover actually performs must still go through.
    followed = handler.redirect_request(req, None, 302, "Found", {},
                                        "https://www.itshover.com/r/heart-icon.json")
    check("the allowed bare-to-www hop is still followed",
          followed is not None and followed.full_url == "https://www.itshover.com/r/heart-icon.json",
          str(followed))

    # `_open` must actually route through that handler; a bare urlopen would
    # follow the redirect and only let `_get` refuse the read.
    opener = getattr(fi, "_OPENER", None)
    check("the module pins its own opener", opener is not None)
    if opener is not None:
        check("the live opener holds the pinned redirect handler",
              any(isinstance(h, fi._PinnedRedirectHandler) for h in opener.handlers),
              str(sorted(type(h).__name__ for h in opener.handlers)))

    # ...and `_open` must route through that opener rather than around it: a bare
    # urlopen would leave every check above green while sending the request. Read
    # the function's own global references so this stays network-free.
    names = fi._open.__code__.co_names
    check("_open routes through the pinned opener rather than a bare urlopen",
          "_OPENER" in names and "urlopen" not in names, str(names))


def main() -> int:
    print("fetch_icon.py tests")
    for test in (test_benign_icon_converts, test_attribute_value_cannot_break_out,
                 test_non_icon_elements_are_refused, test_text_wordmarks_are_allowed,
                 test_off_document_href_is_dropped,
                 test_unparseable_markup_is_refused, test_names_are_validated,
                 test_request_stays_on_the_pinned_host,
                 test_a_redirect_is_refused_before_it_is_followed, test_reply_size_is_capped,
                 test_registry_shape_is_validated, test_bundled_list_matches_the_shipped_names):
        print(f"- {test.__name__}")
        test()
    if failures:
        print(f"\n{len(failures)} failure(s): {', '.join(failures)}")
        return 1
    print("\nok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
