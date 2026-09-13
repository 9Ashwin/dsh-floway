#!/usr/bin/env python3
"""Validate every skill's frontmatter the way the DeepSeek Harness does.

Layout: `skills/<bucket>/<name>/SKILL.md`, with `<bucket>` one of `flow`,
`practice`, `meta` or `bonus`. DSH discovers a skill at `<root>/<name>/SKILL.md`
— exactly one level below a configured root — so `cordis.patch.yml` lists every
bucket as its own root. That makes two mistakes invisible until someone notices
a skill is gone:

  * a skill left at `skills/<name>/SKILL.md` (top level) is served by
    `npx skills`, which scans recursively and flattens on install, but NOT by
    the bundle patch, which only knows the buckets;
  * an invalid frontmatter (for example an unquoted `left: foo`) or a
    description longer than `catalogDescriptionMaxLength` (default 500, whose
    tail is truncated in the catalog) makes DSH drop the skill with only a
    logger warning.

This script fails loudly on both, and on any bucket it does not know.

Usage: python3 scripts/check_skills.py [skills_root]
Exit code 1 when anything fails.
"""

from __future__ import annotations

import os
import re
import sys

DESCRIPTION_CAP = 500
KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BUCKETS = ("flow", "practice", "meta", "bonus")


def load_frontmatter(path: str) -> dict | str:
    text = open(path, encoding="utf-8").read()
    if not text.startswith("---"):
        return "file does not start with a YAML frontmatter fence"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "frontmatter fence is not closed"
    try:
        import yaml
    except ImportError:  # pragma: no cover - dependency is optional
        return "PyYAML is not installed (pip install pyyaml)"
    try:
        data = yaml.safe_load(parts[1])
    except Exception as exc:  # noqa: BLE001 - report whatever the parser said
        return f"YAML error: {exc.__class__.__name__}: {exc}"
    if not isinstance(data, dict):
        return "frontmatter is not a mapping"
    return data


def discover(root: str) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Return (bucket, name, path) triples plus layout problems."""
    found: list[tuple[str, str, str]] = []
    problems: list[str] = []
    for entry in sorted(os.listdir(root)):
        full = os.path.join(root, entry)
        if not os.path.isdir(full):
            continue
        if os.path.isfile(os.path.join(full, "SKILL.md")):
            problems.append(
                f"{entry}: sits at the top level of skills/ — move it into a bucket "
                f"({'/'.join(BUCKETS)}), or the bundle patch will not serve it"
            )
            continue
        if entry not in BUCKETS:
            problems.append(f"{entry}: unknown bucket (expected one of {', '.join(BUCKETS)})")
            continue
        for name in sorted(os.listdir(full)):
            skill_dir = os.path.join(full, name)
            if not os.path.isdir(skill_dir):
                continue
            path = os.path.join(skill_dir, "SKILL.md")
            if os.path.isfile(path):
                found.append((entry, name, path))
            else:
                problems.append(f"{entry}/{name}: no SKILL.md (skills are one level below a bucket)")
    return found, problems


def check_bundle_patch(repo_root: str, buckets: set[str]) -> list[str]:
    """Every bucket must appear as its own customSkillDirs root in the bundle patch."""
    path = os.path.join(repo_root, "cordis.patch.yml")
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        return [f"cordis.patch.yml is unreadable: {exc}"]
    problems = []
    for bucket in sorted(buckets):
        # The root expression ends in `..., 'skills', '<bucket>'`.
        if f"'skills', '{bucket}'" not in text:
            problems.append(
                f"cordis.patch.yml does not list '{bucket}' as a customSkillDirs root — "
                f"the bundle install would serve none of the skills under skills/{bucket}"
            )
    return problems


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills"
    )
    skills, failures = discover(root)
    if not skills and not failures:
        print(f"no skills found under {root}", file=sys.stderr)
        return 1
    failures.extend(check_bundle_patch(os.path.dirname(root), {b for b, _, _ in skills}))

    for bucket, name, path in skills:
        fm = load_frontmatter(path)
        if isinstance(fm, str):
            failures.append(f"{bucket}/{name}: {fm}")
            continue
        if fm.get("name") != name:
            failures.append(f"{bucket}/{name}: frontmatter name {fm.get('name')!r} != directory name")
        if not KEBAB.match(str(fm.get("name", ""))):
            failures.append(f"{bucket}/{name}: name is not kebab-case")
        description = fm.get("description")
        if not isinstance(description, str) or not description.strip():
            failures.append(f"{bucket}/{name}: description is missing or empty")
            continue
        if len(description) > DESCRIPTION_CAP:
            failures.append(
                f"{bucket}/{name}: description is {len(description)} chars, over the "
                f"{DESCRIPTION_CAP} catalog cap — its tail is truncated in the model catalog"
            )

    if failures:
        print(f"{len(failures)} problem(s) across {len(skills)} skills:")
        for line in failures:
            print(f"  - {line}")
        return 1

    per_bucket = ", ".join(
        f"{bucket}: {sum(1 for b, _, _ in skills if b == bucket)}" for bucket in BUCKETS
    )
    print(f"ok: {len(skills)} skills valid ({per_bucket}; frontmatter parses, names match, "
          f"descriptions <= {DESCRIPTION_CAP} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
