#!/usr/bin/env python3
"""Strip the scroll-reveal animation from the usage guides.

Content must never depend on JS, an IntersectionObserver or a completed
animation to become visible. The scroll reveal pre-hid every section element
with opacity:0 + translateY(20px) and revealed it on intersection, which:

  * left everything below the fold invisible in screenshots, print/PDF exports
    and any capture that does not scroll, and
  * drew an element over its neighbour while it animated, because a transform
    does not reserve layout space.

Run with --check to report anchors only; run without it to rewrite in place.
"""

import sys
import pathlib

FILES = ["docs/index_cn.html", "docs/index_en.html"]

REGION_START = "  // ===== 9. SCROLL-TRIGGERED ANIMATIONS"
REGION_END = "  // ===== 10. HOVER ANIMATIONS ====="
REGION_REPLACEMENT = """  // ===== 9. SCROLL-TRIGGERED ANIMATIONS — deliberately absent =====
  // No section is hidden and revealed on scroll. Everything below is painted in
  // its final position from the first frame: a screenshot, a print/PDF export or
  // any capture that never scrolls must show the whole document, and a reveal
  // that translates an element would overlap its neighbour mid-flight.
"""

# (label, old, new); each anchor must appear exactly once per file.
EDITS = [
    (
        "pre-hide",
        """  // Only hide container-level sections for load animation
  // Inner elements are handled by scroll observer
  document.querySelectorAll('.toc, .header, .footer').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(30px)';
  });""",
        """  // Nothing is pre-hidden: every entrance animation below supplies its own start
  // state, so a slow or failed animation can cost the animation only, never the
  // content.""",
    ),
    (
        "toc-animation",
        """  // TOC slide in
  animate('.toc', {
    opacity: [0, 1],
    translateY: [30, 0],
    duration: 800,
    delay: 600,
    ease: 'easeOutCubic',
    onComplete: function() {
      animate('.toc li', {
        opacity: [0, 1],
        translateX: [-20, 0],
        delay: stagger(60),
        duration: 400,
        ease: 'easeOutCubic'
      });
    }
  });""",
        """  // The table of contents is static content: it is painted in place instead of
  // fading in, so it cannot be missing from a screenshot or a print export.""",
    ),
]

STALE_COMMENTS = [
    "  // ===== 3. SECTION DOT — handled by scroll observer via .section-title =====",
    "  // ===== 4. CARD ENTRANCE — handled by scroll observer =====",
    "  // ===== 5. FLOW STEPS — handled by scroll observer =====",
    "  // ===== 6. SVG DIAGRAM — handled by scroll observer =====",
    "  // ===== 7. BADGE — handled by scroll observer =====",
    "  // ===== 8. CODE BLOCK SHIMMER — shimmer runs when code block scrolls in =====",
]
STALE_REPLACEMENT = """  // ===== 3-8. SECTION DOT / CARDS / FLOW STEPS / SVG / BADGE / CODE =====
  // Static by design: painted in place, with no scroll-triggered state."""

FORBIDDEN = ["opacity = '0'", "scrollObserver", "IntersectionObserver", "scrollRevealTargets"]


def apply(path: pathlib.Path, check: bool) -> int:
    text = path.read_text(encoding="utf-8")
    original = text
    problems: list[str] = []

    # Already clean (e.g. a second run, or a page that never had the reveal):
    # nothing forbidden left and neither anchor present.
    forbidden_left = any(text.count(n) for n in FORBIDDEN)
    anchors_left = any(text.count(old) for _, old, _ in EDITS)
    if not forbidden_left and not anchors_left:
        print(f"  ok {path}: already clean")
        return 0

    start = text.find(REGION_START)
    end = text.find(REGION_END)
    if start == -1 or end == -1 or end < start:
        problems.append(f"scroll-reveal region: start={start} end={end}")
    else:
        text = text[:start] + REGION_REPLACEMENT + "\n" + text[end:]

    for label, old, new in EDITS:
        count = text.count(old)
        if count == 0:
            continue
        if count > 1:
            problems.append(f"{label}: expected exactly 1 anchor, found {count}")
            continue
        text = text.replace(old, new)

    if "\n".join(STALE_COMMENTS) in text:
        text = text.replace("\n".join(STALE_COMMENTS), STALE_REPLACEMENT)

    for needle in FORBIDDEN:
        left = text.count(needle)
        if left:
            problems.append(f"{needle} still present x{left}")

    if problems:
        print(f"  x {path}: {'; '.join(problems)}")
        return 1

    changed = text != original
    if not check and changed:
        path.write_text(text, encoding="utf-8")
    print(f"  ok {path}: {'rewritten' if (changed and not check) else 'would change' if changed else 'no-op'}")
    return 0


def main() -> int:
    check = "--check" in sys.argv
    root = pathlib.Path(__file__).resolve().parent.parent
    rc = 0
    for rel in FILES:
        rc |= apply(root / rel, check)
    print("check only" if check else "done")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
