---
name: code-to-spec
description: "Reverse-engineer a SPEC out of an existing project: read its code, config and tests, then write the specification. Triggers: code-to-spec, 逆向规格, 生成规格文档, reverse spec."
user-invocable: true
---

# to-spec — Reverse-Engineer Project Specification

Analyze an existing codebase and produce a structured SPEC document that captures what the project does, how it's built, and what contracts it exposes. The output is a living specification that could be used to rebuild the project from scratch or onboard new contributors.

---

## When to Use

- You want a comprehensive understanding of an existing project
- Onboarding new team members who need a high-level overview
- Documenting a project that was built without a spec
- Comparing actual implementation against intended design
- Preparing for a rewrite or major refactor
- Auditing what a project actually does vs. what people think it does

---

## The Job

1. **Scope confirmation** — ask user what to analyze (entire repo, specific directory, or specific aspect)
2. **Deep scan** — systematically read project structure, entry points, config, tests, and core logic
3. **Synthesize** — produce a structured SPEC document
4. **Review** — present to user for feedback and iteration
5. **Save** — write final SPEC to agreed location

---

## Step 1: Scope Confirmation

Before scanning, ask the user:

```
What should I analyze?

A. Entire repository (recommended for small-medium projects)
B. Specific directory or module: [path]
C. Specific aspect only (e.g., API surface, data model, auth flow)

Depth level:
1. Overview — high-level architecture + tech stack + key features (fast, ~5 min)
2. Standard — includes API contracts, data models, config, dependencies (default)
3. Deep — adds internal module interactions, error handling patterns, test coverage analysis
```

If the project is large (>500 files), recommend starting with Overview or a specific module.

---

## Step 2: Deep Scan

Systematically analyze the following (adapt to what exists):

**Read `references/scan-checklist.md` in full before scanning.** It carries the per-dimension checklists — what to read and how to judge each finding — plus the heuristics for identifying purpose, architecture, business rules, API contracts and data models. The list below is only the index of dimensions; do not scan from it alone.

1. **Project Identity** — package manifests, README/LICENSE, git history
2. **Architecture** — directory organization, entry points, module boundaries and internal dependency graph
3. **Tech Stack** — languages and versions, frameworks, build tools, runtime requirements
4. **Features & Behavior** — routes, CLI commands, exported functions, business logic modules, background jobs and event handlers
5. **Data Model** — schemas, migrations, ORMs, key structures and relationships, state management
6. **API Surface** — HTTP endpoints, GraphQL/gRPC/WebSocket, CLI interface, exported library API
7. **Configuration & Environment** — environment variables, config file schemas, feature flags
8. **External Dependencies** — third-party services, infrastructure, authentication/authorization providers
9. **Testing & Quality** — test framework and approach, coverage patterns, lint/format/type-check setup
10. **Deployment & Operations** — CI/CD, deployment targets and strategies, monitoring, logging, health checks

---

## Step 3: SPEC Document Structure

Generate the SPEC with these sections. Omit sections that don't apply.

**Read `references/spec-template.md` in full before writing.** It is the exact document skeleton plus the per-section writing requirements, tables and examples; copy its structure instead of improvising one. The list below only names the sections.

1. **Overview** — purpose, key capabilities, architecture style
2. **Tech Stack**
3. **Project Structure**
4. **Data Model** — core entities, state transitions
5. **API Surface** — interfaces, request/response schemas
6. **Configuration**
7. **External Dependencies**
8. **Business Rules & Constraints**
9. **Non-Functional Characteristics** — performance, security, error handling
10. **Testing Strategy**
11. **Known Gaps & Assumptions**
12. **Appendix** — dependency graph, environment setup

---

## Step 4: Review & Iteration

After generating the SPEC, present it and ask:

```
SPEC generated. Please review:

- Are there sections that need more detail?
- Are there inaccuracies I should correct?
- Should I add/remove any sections?
- Is the depth level appropriate?

Reply OK to save, or provide feedback for iteration.
```

Apply feedback and re-present until user confirms.

---

## Step 5: Save

Ask user for save location:

```
Where should I save the SPEC?

A. docs/SPEC.md (recommended)
B. SPEC.md (project root)
C. Custom path: [specify]
```

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Project has no README or documentation | Note this in "Known Gaps"; infer purpose from code |
| Monorepo with multiple services | Ask user which service(s) to analyze; produce one SPEC per service or a unified SPEC with clear boundaries |
| Project uses code generation | Document the generated code's purpose but focus on the source of truth (schemas, proto files, templates) |
| Legacy project with mixed patterns | Document all observed patterns, note inconsistencies in "Known Gaps" |
| Project is a library (no runtime) | Focus on exported API surface, type contracts, and usage patterns from tests |
| Incomplete or broken code | Document what exists, mark broken/incomplete areas explicitly |
| Project >1000 files | Start with entry points and trace key flows; don't exhaustively read every file |
| Multiple languages in one repo | Document each language's role and how they interact |

---

## Quality Criteria

A good reverse-engineered SPEC should pass these checks:

- [ ] A developer unfamiliar with the project could understand its purpose in 60 seconds
- [ ] The tech stack section is complete enough to set up a dev environment
- [ ] API contracts are specific enough to write a client against
- [ ] Data models are complete enough to recreate the schema
- [ ] Business rules are explicit (not buried in "see code")
- [ ] Known gaps are honestly listed (don't invent what you can't determine)
- [ ] The SPEC matches the actual code (not aspirational documentation)

---

## Anti-Patterns to Avoid

- **Don't invent intent.** If you can't determine WHY something exists, say so. Don't fabricate rationale.
- **Don't copy code into the SPEC.** Describe behavior and contracts, don't paste implementations.
- **Don't include transient state.** The SPEC describes the system's design, not its current runtime state.
- **Don't over-specify internals.** Focus on boundaries, contracts, and behavior. Internal implementation details belong in code comments, not specs.
- **Don't assume the README is accurate.** READMEs often lag behind code. Verify claims against actual implementation.
