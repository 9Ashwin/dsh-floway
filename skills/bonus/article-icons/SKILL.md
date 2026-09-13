---
name: article-icons
description: "Illustrate an article (Markdown, HTML, etc.) with animated-style icons from itshover.com/icons. Fetches icons as clean inline SVG and places them at section headings, key concepts, lists, and callouts. Triggers on: /article-icons, 配图, 给文章配图标, add icons to article, illustrate with icons."
# 只可能被手敲的人用工具：不进模型目录，省下每个会话与每个子代理的固定成本。
disable-model-invocation: true
---

# Article Icons (itshover)

Add tasteful icons to an article using the [itshover](https://www.itshover.com/icons) icon set. itshover publishes 263 icons as shadcn registry components; this skill downloads them and converts each into a clean, static, inline **SVG** that drops straight into Markdown or HTML — no React, no `motion`, no build step.

## Triggers

Use when the user wants to illustrate a document with icons:
- `/article-icons <file>`
- "给这篇文章配图标", "给文章配图", "add icons to this article", "illustrate with icons"

## Inputs

- **Target file** — the article to illustrate (`.md`, `.html`, `.mdx`, ...). If not given, ask.
- **Style preferences** (optional) — color, size, where icons go. Otherwise use sensible defaults below.

## The Tool

`scripts/fetch_icon.py` is the only moving part. It fetches an icon and prints static SVG to stdout.

```bash
# Get one icon (defaults: size 24, color currentColor, stroke-width 2)
python3 scripts/fetch_icon.py heart-icon

# Customize
python3 scripts/fetch_icon.py rocket-icon --size 32 --color "#d97757" --stroke-width 1.5

# Discover names (do this FIRST — names must match exactly)
python3 scripts/fetch_icon.py --list
python3 scripts/fetch_icon.py --search arrow
python3 scripts/fetch_icon.py --search brand
```

`scripts/icon_names.json` is a cached list of all 263 names for offline reference.

Most icon names end in `-icon` (e.g. `heart-icon`, `rocket-icon`, `database-icon`), and brands use `brand-<name>-icon` (e.g. `brand-anthropic-icon`). But the convention is **not** universal — real names include `shield-check`, `credit-card`, `down-chevron`, `apple-brand-logo`, `skull-emoji`. **Never guess a name. Always resolve it with `--search` first** — a wrong guess just wastes a 404.

### Trust boundary

This is the one skill in the set that **calls a third-party service at runtime**: `itshover.com` (an external shadcn registry, not a Vercel- or host-maintained domain). Say so when you use it, and treat everything it returns as untrusted input:

- The request is confined to `https://itshover.com/r/<name>.json` — the name is validated as a single lowercase-hyphenated path segment, so it cannot reshape the URL; a redirect anywhere except the same service's `www` host is refused before it is followed, and the reply is size-capped.
- The markup is **rebuilt from a whitelist**, not passed through: only static SVG elements (`svg`, `g`, `defs`, `path`, `circle`, `rect`, `line`, `polyline`, `polygon`, `ellipse`, `use`, `clipPath`, `mask`, `pattern`, gradients, `text`, `tspan`, `title`, `desc`) and a fixed attribute list survive; attribute values are XML-escaped, and `href`/`xlink:href` must be same-document (`#id`). The list is minimal on purpose — a new element upstream fails the conversion instead of sliding through.
- An unexpected element, a malformed reply, or an unbalanced result makes the script **print an error and return non-zero** instead of emitting the SVG. That is the intended outcome, not a bug to work around: the icon gets embedded into HTML or Markdown, so anything that survives this step is something you have agreed to ship. Do not paste a hand-edited "fixed" version of the markup from the registry into the article.
- If the fetch fails (no network, or the host is down), report it and stop — do not hand-write icon SVG, and do not substitute a different remote source.

## Workflow

1. **Read the article.** Identify its structure: title, section headings (`#`/`##`/`<h1>`/`<h2>`), key concepts, list groups, callouts/warnings, and any tech/brand mentions (React, GitHub, AI tools...).

2. **Plan the icon map.** For each placement, choose a semantically matching icon. Match meaning, not just keywords — a "performance" section → `rocket-icon` or `zap-icon`; a "security" section → `shield-icon` or `lock-icon`; a warning callout → `alert-triangle-icon`. Prefer **one consistent icon family** (all outline, one color) so the article looks designed, not decorated. Resolve every name with `--search`.

3. **Confirm the plan** with the user before editing — show the heading→icon mapping. This is cheap and avoids reworking a whole document.

4. **Fetch and embed.** Run `fetch_icon.py` for each chosen icon and inline the SVG at its placement. Fetch a handful at a time rather than all at once — the registry starts resetting connections on a large burst (see Edge Cases). See embedding rules below.

5. **Verify.** Re-read the edited file; for HTML, open it / screenshot to confirm icons render and align. Report the mapping you applied.

## Embedding Rules

**HTML** — inline the SVG directly. Wrap heading icons so they align with text:

```html
<h2 style="display:flex;align-items:center;gap:.5rem;">
  <svg ...>...</svg> Performance
</h2>
```

**Markdown** — GitHub-flavored Markdown renders inline HTML, so embed the raw SVG. Keep it on one line and size it small (16–20px) for inline use, 24–28px beside headings:

```markdown
## <svg ... width="22" height="22" ...>...</svg> Getting Started
```

If the target renderer strips inline SVG (some strict Markdown engines do), fall back to saving each SVG into an `assets/icons/` folder next to the article and referencing it: `![](assets/icons/rocket-icon.svg)`. Ask which the user prefers if unsure.

### Defaults
- **Size:** 24px beside `h1`, 20–22px beside `h2`/`h3`, 16px inline in text.
- **Color:** `currentColor` so icons inherit text color. Override with `--color` only when the user wants accent colors.
- **Density:** one icon per heading + a few for genuinely key concepts. Do **not** icon every bullet or sentence — restraint reads as polish.
- **Alignment:** always `display:flex;align-items:center;gap:.4–.5rem` for heading icons in HTML.

## Icon Selection Cheatsheet

These names are verified to exist, but the set changes — always reconfirm with `--search` before fetching.

| Theme | Real icon names |
|-------|------|
| intro / overview | `book-icon`, `home-icon`, `globe-icon`, `map-pin-icon` |
| performance / speed | `rocket-icon`, `gauge-icon`, `clock-icon` |
| security | `shield-check`, `lock-icon` |
| data / charts | `database`-family via `--search`, `chart-bar-icon`, `chart-line-icon`, `chart-pie-icon`, `cloud-1-icon` |
| settings / config | `gear-icon`, `sliders-horizontal-icon` |
| warning / note | `triangle-alert-icon`, `info-circle-icon`, `filled-bell-icon` |
| success / done | `checked-icon`, `double-check-icon`, `simple-checked-icon` |
| ideas | `brain-circuit-icon`, `sparkles-icon`, `star-icon`, `bulb-svg` |
| AI / brands | `brand-anthropic-icon`, `brand-gemini-icon`, ... (`--search brand`) |
| navigation | `arrow-narrow-*-icon`, `down-chevron`, `right-chevron` |

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Icon name not found (404) | Run `--search <term>`; pick the closest real name. Never invent names. |
| Icon won't convert (rare; ~2/263 use a JS map for paths) | Script prints a clear error. Pick an alternative icon with similar meaning. |
| Error mentions *unexpected markup* | The reply carried an element outside the static-SVG whitelist — either the registry changed its format or the response was tampered with. Report it; do not hand-patch the SVG into the article. |
| `WARNING: … not in the bundled list` | The name is well-formed but newer than `icon_names.json`; the fetch still runs. Verify with `--list` afterwards. |
| `SSL: UNEXPECTED_EOF_WHILE_READING` / connection reset | The registry throttles bursts — a 263-icon sweep saw 18–24 of these. Re-run that one icon on its own; it is a transport reset, not a converter problem. |
| No network access | Cannot fetch SVGs; tell the user the skill needs network access to itshover.com. |
| Markdown renderer strips inline SVG | Fall back to `assets/icons/*.svg` + image references. |
| Article already has icons | Ask whether to replace, supplement, or skip those sections. |
| Very long article | Confirm the mapping for the first few sections, then apply the same family consistently throughout. |

## Checklist

Before finishing:
- [ ] Every icon name was resolved with `--search`/`--list` (no guessed names)
- [ ] One consistent icon family/color across the article
- [ ] Icons placed at headings + genuinely key points, not everywhere
- [ ] Heading icons vertically aligned with text (flex + gap)
- [ ] Edited file re-read; HTML visually verified to render
- [ ] Every embedded SVG came out of `fetch_icon.py` unmodified (no hand-patched markup, no ignored `ERROR:`/`WARNING:`)
- [ ] Mapping summary reported to the user
