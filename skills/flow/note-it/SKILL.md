---
name: note-it
description: "Capture implementation notes after code implementation and review/fix. Records design decisions, deviations, tradeoffs, and open questions to docs/issue#NNNN.md. Triggers on: /note-it, 记录笔记, implementation notes."
---

# Implementation Notes

After completing implementation and review/fix for an Issue, capture a running implementation notes file that documents how the implementation diverges from or interprets the spec.

**Markdown, not HTML.** The same four categories already go out as a Markdown issue comment when the work ships; a second copy in HTML is a second format that only renders after someone downloads it and opens a browser. Markdown stays readable in the repo, in a diff, and pasted anywhere.

## Triggers

Use when:
- After the implementation and its review/fix are both complete
- User says "记录笔记", "implementation notes", "note-it", "/note-it"
- Before **ship-it** (as a final checkpoint)
- Any time the user wants to capture design rationale

## The Job

1. Determine the Issue number from context (branch name, the objective you are working under, or user input)
2. Review the implementation against the Issue spec / PRD
3. Write the notes file at `docs/issue#NNNN.md`
4. Summarize it for the user

## Notes Structure

The file must cover these four categories, in this order. If a category has nothing to report, write `None` with a brief explanation — never drop the heading.

### 1. Design Decisions

Choices made where the spec was ambiguous or silent:
- What was the ambiguity?
- What choice did you make?
- What was the rationale?

### 2. Deviations

Places where you intentionally departed from the spec:
- What did the spec say?
- What did you implement instead?
- Why was the deviation necessary or better?

### 3. Tradeoffs

Alternatives you considered and why you picked what you did:
- What were the viable alternatives?
- What were the pros/cons of each?
- Why did the chosen approach win?

### 4. Open Questions

Anything you'd want confirmed or revised:
- What assumption are you unsure about?
- What should the user verify?
- What might need follow-up?

## Output

- **Format:** Markdown
- **Location:** `docs/`
- **Filename:** `issue#NNNN.md` (NNNN is the zero-padded Issue number, e.g. `issue#0042.md`)

## Template

````markdown
# Implementation Notes — Issue #NNNN

> {Issue title} · {date} · {branch}

## Design Decisions

**{short decision title}**

- **Ambiguity:** {what the spec left open}
- **Choice:** {what you did}
- **Rationale:** {why}

_None — the spec was explicit here._

## Deviations

**{what diverges}**

- **Spec said:** {the spec's wording}
- **Implemented:** {what actually shipped}
- **Why:** {why the departure was necessary or better}

_None — implementation followed the spec as written._

## Tradeoffs

**{the choice made}**

- **Alternatives:** {what else was viable}
- **Pros/cons:** {of each}
- **Why this won:** {the deciding factor}

_None — no real alternative was on the table._

## Open Questions

- {an assumption worth confirming}
- {something that should be verified before or after shipping}

_None._
````

## Example entry

```markdown
**Used interface-based polymorphism instead of a switch**

- **Ambiguity:** The spec said "handle different types" without specifying how.
- **Choice:** Defined a `Handler` interface with per-type implementations.
- **Rationale:** Adding a new type requires no change to existing code. A switch would grow
  unboundedly and every new case would touch the same function.
```

## How to Determine the Issue Number

1. If the user provides it directly (e.g., `/note-it #42`), use it
2. If on a branch named `feat/issue-42-*` or `fix/issue-42-*`, extract `42`
3. If the objective you are working under targets `#42`, use `42`
4. Otherwise, ask the user: "Which Issue number should I use for the notes file?"

## Edge Cases

| Scenario | Handling |
|----------|----------|
| No Issue number found | Ask the user to specify |
| `docs/` directory does not exist | Auto-create it |
| Notes file already exists for this Issue | Ask: "Update existing notes or overwrite?" — default to update (append new items) |
| No deviations or open questions | Write "None — implementation followed the spec as written." |
| Spec/PRD file not found | Note in Open Questions: "No PRD found at tasks/prd-*.md — verify against original requirements." |
| A pre-existing `.html` note for the same Issue | Leave it alone; write the Markdown file going forward and say so rather than rewriting history |

## Checklist

Before saving:
- [ ] Issue number identified
- [ ] All four categories present, even when some are "None"
- [ ] Design decisions explain rationale, not just what was done
- [ ] Deviations contrast spec against implementation
- [ ] Tradeoffs name the specific alternatives considered
- [ ] Open questions are actionable (answerable with a yes/no or a direction)
- [ ] Saved to `docs/issue#NNNN.md`
