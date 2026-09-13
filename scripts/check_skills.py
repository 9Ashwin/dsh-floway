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

It also guards the two-host split. A skill body must stay harness-neutral, and
the two hosts express "keep this out of the model catalog" in different places:
DSH reads `disable-model-invocation` from the frontmatter, Codex ignores that key
and reads `<skill>/agents/openai.yaml` instead. Shipping only one of the two
silently reverses the intent on the other host, so both are required together —
and the DSH loader string that belongs in a platform reference file, never in a
body, is rejected outright.

Usage: python3 scripts/check_skills.py [skills_root]
Exit code 1 when anything fails.
"""

from __future__ import annotations

import json
import os
import re
import sys

DESCRIPTION_CAP = 500
KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BUCKETS = ("flow", "practice", "meta", "bonus")
OPENAI_YAML = os.path.join("agents", "openai.yaml")
PLUGIN_MANIFEST = os.path.join(".claude-plugin", "plugin.json")
MARKETPLACE_MANIFEST = os.path.join(".claude-plugin", "marketplace.json")
# A DSH loader string. It belongs in `references/dsh-runtime.md`; a body that
# names it has leaked harness mechanics into the harness-neutral half.
DSH_LOADER_STRING = "Base directory for this skill"
ALLOW_IMPLICIT_FALSE = "allow_implicit_invocation: false"


def check_platform_split(skill_dir: str, bucket: str, name: str, fm: dict, text: str) -> list[str]:
    """Enforce the invariants that keep one body usable on both hosts."""
    problems = []
    if "user-invocable" in fm:
        problems.append(
            f"{bucket}/{name}: `user-invocable` is a no-op on DSH (it defaults to true) and "
            f"unknown to Codex — drop it"
        )
    if DSH_LOADER_STRING in text:
        problems.append(
            f"{bucket}/{name}: SKILL.md mentions '{DSH_LOADER_STRING}' — that is a DSH loader "
            f"detail; move it to references/dsh-runtime.md and define <SKILL_DIR> neutrally"
        )
    declared = fm.get("disable-model-invocation") is True
    path = os.path.join(skill_dir, OPENAI_YAML)
    has_meta = os.path.isfile(path)
    if declared and not has_meta:
        problems.append(
            f"{bucket}/{name}: frontmatter sets disable-model-invocation but {OPENAI_YAML} is "
            f"missing — Codex ignores that key and would let the model invoke the skill "
            f"implicitly; add `policy: {{allow_implicit_invocation: false}}`"
        )
    if has_meta and not declared:
        problems.append(
            f"{bucket}/{name}: {OPENAI_YAML} exists without `disable-model-invocation: true` — "
            f"the two hosts would disagree about implicit invocation; fix one of them"
        )
    if has_meta and ALLOW_IMPLICIT_FALSE not in open(path, encoding="utf-8").read():
        problems.append(f"{bucket}/{name}: {OPENAI_YAML} must set `{ALLOW_IMPLICIT_FALSE}`")
    return problems


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
            if name.startswith("."):
                continue  # .claude-plugin and friends are manifests, not skills
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


def check_plugin_manifest(repo_root: str, relative_dirs: set[str]) -> list[str]:
    """The marketplace must group the skills, and every skill must land in a group.

    Two different readers use these manifests, and they fail in opposite
    directions, so both are checked here:

    * `npx skills add` builds its picker groups from the plugin `name` behind
      each skill path (`getPluginGroupings` in the skills CLI). A skill missing
      from every plugin's `skills` list still installs, but it drops into a
      catch-all "Other" group — that is how `mattpocock/skills` ends up with an
      "Other" group holding its in-progress skills.
    * a plugin install reads the manifest inside the plugin directory.

    The trap this exists to prevent: a *root* `.claude-plugin/plugin.json` that
    lists skills. The CLI reads the marketplace first and the root plugin.json
    second, and the second overwrites the first for the same path — so one root
    manifest with a full `skills` list silently collapses every group back into
    one, with no error anywhere.
    """
    marketplace = os.path.join(repo_root, MARKETPLACE_MANIFEST)
    if not os.path.isfile(marketplace):
        return []
    try:
        data = json.load(open(marketplace, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{MARKETPLACE_MANIFEST} is not readable JSON: {exc}"]

    plugins = data.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        return [f"{MARKETPLACE_MANIFEST} declares no plugins"]

    problems: list[str] = []
    if len(plugins) < 2:
        problems.append(
            f"{MARKETPLACE_MANIFEST} declares 1 plugin — the installer would show a single "
            f"group titled after that plugin instead of one group per bucket"
        )

    claimed: dict[str, str] = {}
    for plugin in plugins:
        name = plugin.get("name")
        if not isinstance(name, str) or not name:
            problems.append(f"{MARKETPLACE_MANIFEST} has a plugin without a name")
            continue
        source = plugin.get("source")
        if not isinstance(source, str) or not source:
            problems.append(f"{MARKETPLACE_MANIFEST} plugin {name} has no source")
            continue
        listed = plugin.get("skills")
        if not isinstance(listed, list) or not listed:
            problems.append(
                f"{MARKETPLACE_MANIFEST} plugin {name} has no `skills` list — the installer "
                f"cannot group or find its skills"
            )
            continue
        base = os.path.normpath(source).replace(os.sep, "/").strip("/")
        if base.startswith(".."):
            problems.append(f"{MARKETPLACE_MANIFEST} plugin {name} points outside the repo: {source}")
            continue
        for entry in listed:
            rel = os.path.normpath(os.path.join(base, str(entry))).replace(os.sep, "/")
            if rel in claimed:
                problems.append(
                    f"{MARKETPLACE_MANIFEST} lists {rel} under both {claimed[rel]} and {name} — "
                    f"the installer keeps only the later one"
                )
            claimed[rel] = name
        # The manifest inside the plugin directory is what a plugin install reads,
        # so it has to agree with the marketplace entry rather than drift from it.
        inner_path = os.path.join(repo_root, base, PLUGIN_MANIFEST)
        if not os.path.isfile(inner_path):
            problems.append(
                f"{base}/{PLUGIN_MANIFEST} is missing — {name} would not install as a plugin"
            )
            continue
        try:
            inner = json.load(open(inner_path, encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"{base}/{PLUGIN_MANIFEST} is not readable JSON: {exc}")
            continue
        if inner.get("name") != name:
            problems.append(
                f"{base}/{PLUGIN_MANIFEST} names itself {inner.get('name')!r}, but the "
                f"marketplace calls it {name!r}"
            )
        inner_skills = {
            os.path.normpath(os.path.join(base, str(e))).replace(os.sep, "/")
            for e in inner.get("skills") or []
        }
        expected = {
            os.path.normpath(os.path.join(base, str(e))).replace(os.sep, "/") for e in listed
        }
        if inner_skills != expected:
            problems.append(
                f"{base}/{PLUGIN_MANIFEST} and {MARKETPLACE_MANIFEST} disagree about {name}'s "
                f"skills: only-in-inner={sorted(inner_skills - expected)}, "
                f"only-in-marketplace={sorted(expected - inner_skills)}"
            )

    problems += [
        f"no plugin lists {missing} — the installer would drop it into an 'Other' group"
        for missing in sorted(relative_dirs - set(claimed))
    ]
    problems += [
        f"a plugin lists {extra}, which is not a skill directory"
        for extra in sorted(set(claimed) - relative_dirs)
    ]

    root_manifest = os.path.join(repo_root, PLUGIN_MANIFEST)
    if os.path.isfile(root_manifest):
        try:
            root_data = json.load(open(root_manifest, encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"{PLUGIN_MANIFEST} is not readable JSON: {exc}")
        else:
            if root_data.get("skills"):
                problems.append(
                    f"{PLUGIN_MANIFEST} lists skills, and the installer reads it after "
                    f"{MARKETPLACE_MANIFEST} and overwrites its groups — every skill would "
                    f"collapse into one group named {root_data.get('name')!r}. Keep the skill "
                    f"lists in the plugin directories only."
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
    repo_root = os.path.dirname(root)
    failures.extend(check_bundle_patch(repo_root, {b for b, _, _ in skills}))
    failures.extend(
        check_plugin_manifest(repo_root, {f"skills/{bucket}/{name}" for bucket, name, _ in skills})
    )

    for bucket, name, path in skills:
        text = open(path, encoding="utf-8").read()
        fm = load_frontmatter(path)
        if isinstance(fm, str):
            failures.append(f"{bucket}/{name}: {fm}")
            continue
        failures.extend(check_platform_split(os.path.dirname(path), bucket, name, fm, text))
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
          f"descriptions <= {DESCRIPTION_CAP} chars, bodies harness-neutral, "
          f"implicit-invocation declared per host)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
