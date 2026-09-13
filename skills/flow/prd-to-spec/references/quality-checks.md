# SPEC quality checks

Run these before you present the SPEC: the quality checklist, the edge-case/fallback lookup
table, the anti-patterns to avoid, and where this skill sits in the pipeline. They are lookup
material — the drafting rules themselves are in [`spec-template.md`](spec-template.md) and the
skill body.

---

## Quality Criteria

A good SPEC should pass these checks:

- [ ] Every PRD User Story has corresponding SPEC sections
- [ ] Every Functional Requirement maps to an API endpoint or business logic rule
- [ ] Every Acceptance Criterion maps to at least one test case
- [ ] Architecture choices are justified with rationale
- [ ] API schemas are specific enough to generate client code
- [ ] Error handling covers all identified failure modes
- [ ] Implementation order respects dependencies
- [ ] No "TBD" or "TODO" items — resolve or move to Open Questions

---

## Edge Cases & Fallback

| Scenario | Handling |
|----------|----------|
| PRD is vague or incomplete | Generate SPEC with best-effort choices, mark assumptions in Section 11.3 |
| PRD conflicts with existing code | Flag conflicts explicitly, propose resolution in Section 11.1 |
| Feature is too large for one SPEC | Split into multiple SPECs (one per service boundary), link them |
| No existing codebase (greenfield) | Skip Step 2, propose architecture from scratch based on PRD + clarifying questions |
| PRD has no User Stories (just bullet points) | Infer structure, map bullets to SPEC sections, note in Summary |
| User wants SPEC without reading codebase | Skip Step 2, note that assumptions about existing code are unverified |
| Multiple PRDs need one SPEC | Merge PRD inputs, deduplicate requirements, note source for each |

---

## Anti-Patterns to Avoid

- **Don't restate the PRD.** The SPEC adds technical depth, not a copy of requirements in different words.
- **Don't over-specify trivial operations.** CRUD with no special logic doesn't need a full algorithm section.
- **Don't pick technologies without context.** Always check what the project already uses before suggesting new tools.
- **Don't design in isolation.** The SPEC must fit the existing system — same patterns, same conventions, same style.
- **Don't leave decisions implicit.** If you made a choice (e.g., "add column to existing table"), state it and say why.
- **Don't write implementation code.** The SPEC describes contracts and behavior, not code. Pseudocode is acceptable for complex algorithms.

---

## Relationship to Other Skills

```
/prd  →  /prd-to-spec  →  /goal  →  /review-it  →  /ship-it
 │              │              │
 │  Requirements │  Technical   │  Implementation
 │  (what)       │  (how)       │  (code)
```

- **/prd** produces the PRD (input to this skill)
- **/prd-to-spec** produces the SPEC (this skill)
- **/goal** implements Issues with SPEC as the technical reference
- **/code-to-spec** reverse-engineers SPEC from existing code (complementary — forward vs. reverse)
