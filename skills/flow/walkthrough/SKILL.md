---
name: walkthrough
description: "Write the walkthrough artifact before merging: what changed, the commands you actually ran and what they printed, visual proof of the demo path, and a review gate with the diff stat, a paste-ready PR body and a merge checklist. Proof, not a diff dump. Triggers: walkthrough, 走查, 生成走查文档, 交付前走查, write the walkthrough."
---

# walkthrough — prove the change before it merges

Once implementation and its verification pass are done, write one Markdown file that lets a reader
who has not seen the work catch up on **what changed** and **what is proven to work**, and
staging-check the diff before merging.

The point is evidence, not assertion. A diff says what the code looks like; a walkthrough says what
you ran, what it printed, and what you saw.

## When to use

**Scope: one walkthrough per batch or per wave — the same scope as the review and the ship, never
per issue.** A per-issue walkthrough proves a diff that may not survive integration and costs a
screenshot round each, and its review gate produces the PR body — a batch or a wave has exactly
one PR. Per-issue *rationale* is the **note-it** skill's job, and that one does stay per issue.

- After implementation and its verification pass are complete — an implementation skill ran, the
  project's gates are green, and **review-it** has had its pass.
- Before **ship-it**, as the last checkpoint before commit/PR/merge.
- The user says "walkthrough", "走查", "生成走查文档", "交付前走查", "write the walkthrough".

## When not to use

- **A one-line or purely mechanical change.** The artifact costs screenshots and a verification
  transcript; if there is no demo path and nothing to catch up on, hand the diff over instead.
- **Before review.** A walkthrough of code that is about to change is a walkthrough you rewrite.
- **As a substitute for the project's gates.** It records gate output; it does not replace running
  them.

## The job

1. **Fix the scope** — which feature / issue / branch is being walked through.
2. **Write the change summary** — read the diff and describe it in human terms.
3. **Run and record the verification steps** — execute the tests and commands, capture real output.
4. **Capture visual proof** — screenshot or record the demo path you verified.
5. **Build the review gate** — diff stat, a paste-ready PR body, and a merge checklist.
6. **Save and hand over** — write the file, summarize it for the user.

## Section by section

### 1. Change summary

For someone who has not seen the work.

- Read the diff (`git diff`, `git log`) and the issue/PRD it serves.
- 3–6 bullets: what was built, refactored, added or removed.
- Name the key files and components, and the shape of what is new (modules, endpoints, data
  structures).
- State the requirement it satisfies and link the issue / PRD.

### 2. Verification steps

What you ran and what it printed.

- **Commands and tests.** Run the project's gates (or the targeted subset), then paste the exact
  command and its real output — truncate noise, keep pass counts.
  ```bash
  go test ./...
  ```
  ```
  ok  	github.com/example/app	0.042s
  ```
- **UI scenarios.** If the change has a surface, drive the demo path and record each step as
  action → observed result → pass/fail:
  ```
  Scenario: a user sets a task's priority
    1. open /tasks — list renders
    2. pick "High" on task #3
    3. reload — task still shows High  ✓
  ```
- A skipped step is stated, never hidden. No tests in the repo, no UI to drive — say so. **Never
  turn an unverified claim into a checked box.**

### 3. Visual proof

Screenshots or a short recording of the demo path, so a reader sees the behaviour rather than
trusting a sentence about it.

- Capture during the walkthrough above. On macOS, `screencapture` grabs a window; for a web page,
  browser automation is better (`npx playwright screenshot <url> tasks/shot.png`).
- **Default to relative paths** — `![caption](tasks/shot-priority.png)` — and commit the images
  alongside. The file stays small and the diff stays reviewable.
- **Use base64 data URIs only when the artifact must survive on its own** (a file pasted into a
  chat, an issue comment, anywhere the images will not travel with it):
  ```markdown
  ![Task priority — set to High](data:image/png;base64,<base64>)
  ```
  Say which mode you used; a base64 walkthrough is megabytes and should be a deliberate choice.
- Prefer 2–4 shots that prove the path (before → action → after) over a screenshot dump.
- No visual surface? Write "None — backend/CLI only" rather than forcing one.

### 4. Review gate

What a reader checks before merging.

- **Diff stat and file list**: `git status`, `git diff --stat HEAD`, `git diff --name-status`.
- **High-risk notes**: force-pushed history, migrations, config changes, wide refactors.
- **Draft PR body**: paste-ready, summary + test plan + `Closes #N`, matching what **ship-it** will
  open.
- **Merge checklist**: gates green, review pass done, no stray artifacts in `git status`, commit
  messages reference the issue.

## Output

- **Format:** Markdown, one file.
- **Location:** `tasks/` by default (the collection's default for working artifacts).
- **Filename:** `tasks/walkthrough-<feature>.md`, kebab-case.

## Template

````markdown
# Walkthrough — {feature / issue title}

> generated {date} · branch {branch} · {commit range}

## Change summary

{2–4 sentences for a reader who has not seen this}

- {what was built / refactored / added / removed}
- {key files, components, endpoints, data structures}
- {the requirement it satisfies — link the issue / PRD}

## Verification steps

### Commands and tests

```bash
{exact command}
```
```
{real output — pass counts, ok lines}
```

### UI scenarios

| # | Scenario | Action | Observed result | Status |
|---|----------|--------|-----------------|--------|
| 1 | {demo step} | {clicks / inputs} | {what happened} | ✅ / ❌ |

_{or: N/A — no UI surface}_

## Visual proof

![{caption}](tasks/{shot}.png)

_{or: None — backend/CLI only}_

## Review gate

```bash
git status
git diff --stat HEAD
git diff --name-status
```
```
{output}
```

### Draft PR

{summary / test plan / Closes #N}

### Merge checklist

- [ ] Gates green (evidence above)
- [ ] UI demo path verified where the change has a surface
- [ ] Review pass complete
- [ ] No stray artifacts in `git status`
- [ ] Commit messages reference the issue
- [ ] Manual acceptance status stated honestly
````

## Determining the feature name

1. The user gave one (`walkthrough user-auth`) — use it.
2. The branch is `feat/issue-42-*` or `fix/issue-42-*` — derive it from the branch, dropping the
   prefix and issue number.
3. A PRD/SPEC exists in `tasks/` (`prd-*.md`, `spec-*.md`) — reuse its feature name.
4. Otherwise ask.

## Edge cases

| Scenario | Handling |
|---|---|
| Nothing changed (`git diff` empty) | Say so plainly; do not fabricate a walkthrough |
| No automated tests | Note "no automated tests in repo" and lean on the manual/UI evidence |
| No UI surface | Visual proof = "None — backend/CLI only"; the UI table = N/A |
| Image cannot be embedded | Fall back to relative paths and list the files to commit alongside |
| `tasks/` does not exist | Create it |
| A walkthrough already exists for this feature | Ask: update in place or overwrite; default overwrite (a fresh snapshot) |
| Verification could not be completed | Record it as a blocker in the review gate — never mark unverified work as proven |

## Relationship to other skills

```
per issue / per node:   implement ──► commit on its own branch
                        (note-it: one docs/issue#N.html per issue)

batch end / wave fan-in, once:
                        review-it ──► walkthrough ──► ship-it
                            │             │              │
                         find/fix     proven +       commit + PR
                                      review gate
```

- **review-it** fixes what it finds; a walkthrough assumes that pass already happened.
- **note-it** records design rationale per issue; a walkthrough records proof and a summary —
  complementary, and neither replaces the other.
- **understand** explains what the new code does; a walkthrough is the artifact you hand to a
  reviewer.
- **ship-it** consumes it: the review gate's draft PR body and checklist feed straight into the
  shipping step.

## Checklist

- [ ] The change summary reads for a fresh reader, not as a diff dump
- [ ] Every verification step shows the actual command and its actual output
- [ ] UI scenarios carry pass/fail outcomes wherever a UI exists
- [ ] Visual proof is attached (relative paths by default) or explicitly "None"
- [ ] The review gate carries the diff stat, the draft PR body and the merge checklist
- [ ] Nothing unverified is written as verified
- [ ] Saved to `tasks/walkthrough-<feature>.md`
