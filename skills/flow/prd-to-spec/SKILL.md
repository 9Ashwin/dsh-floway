---
name: prd-to-spec
description: "Transform a PRD into a technical SPEC document — architecture, API design, data model, error handling, and implementation contracts. Triggers on: prd-to-spec, prd to spec, prd转spec, 需求转设计, 需求转规格, generate spec from prd, design from prd, 技术方案, 设计方案."
user-invocable: true
---

# prd-to-spec — PRD to Technical Specification

Transform a Product Requirements Document (PRD) into a detailed technical SPEC that an engineer or AI agent can implement against. The PRD says *what* to build; the SPEC says *how* to build it.

---

## When to Use

- A `/prd` has been generated and you need to bridge the gap to implementation
- You want architecture decisions documented before coding starts
- Multiple developers/agents will implement the feature and need a shared contract
- You need to validate technical feasibility before committing to a PRD
- You want to catch design issues early — before code is written

---

## The Job

1. **Locate PRD** — find or receive the PRD document
2. **Analyze context (optional)** — if a codebase exists, scan it to understand current architecture, patterns, and constraints
3. **Ask clarifying questions** — resolve technical ambiguities (max 3-5 questions)
4. **Generate SPEC** — produce a structured technical specification
5. **Review** — present to user for feedback and iteration
6. **Save** — write final SPEC to agreed location

---

## Step 1: Locate PRD

Find the input PRD in one of these ways:

```
Provide the PRD to convert:

A. File path (e.g., tasks/prd-priority-system.md)
B. GitHub Issue URL
C. Paste PRD content directly
D. Auto-detect: scan tasks/ directory for recent PRDs
```

If auto-detecting, list available PRDs and let the user choose:

```
Found PRDs in tasks/:
  1. tasks/prd-priority-system.md (2024-03-15)
  2. tasks/prd-user-auth.md (2024-03-10)

Which PRD should I convert? [1/2]
```

---

## Step 2: Analyze Context (Optional)

**Skip this step if no codebase exists yet** (greenfield project). In that case, the SPEC will propose architecture from scratch based on the PRD requirements and clarifying questions.

If a codebase exists, scan it to understand:

- **Existing architecture** — how the current system is structured
- **Tech stack** — languages, frameworks, libraries already in use
- **Patterns** — naming conventions, file organization, error handling approach
- **Database** — current schema, migration tool, ORM
- **API style** — REST/GraphQL/gRPC, authentication method, response format
- **Testing** — test framework, coverage patterns, test utilities

This ensures the SPEC aligns with the existing system rather than proposing incompatible solutions.

---

## Step 3: Clarifying Questions

Ask only when the PRD leaves technical decisions ambiguous. Focus on:

- **Architecture choices** — where does this feature live? New service or extend existing?
- **Data storage** — new table? Extend existing? Cache strategy?
- **API design** — new endpoints? Extend existing? Breaking changes?
- **Dependencies** — any new libraries needed? Version constraints?
- **Performance** — expected load? Latency requirements? Batch size limits?

Format:
```
Technical questions before I generate the SPEC:

1. Where should the priority logic live?
   A. Extend existing TaskService
   B. New PriorityService
   C. Inline in controller
   D. Let me decide based on the codebase

2. Database migration approach?
   A. Add column to existing tasks table
   B. New priority table with FK
   C. JSON field on tasks
   D. Let me decide based on current schema

3. API versioning concern?
   A. Add to existing v1 endpoints
   B. New v2 endpoints
   C. No versioning needed
```

If user selects "let me decide" options, make the best choice based on codebase analysis and document the rationale in the SPEC.

---

## Step 4: SPEC Document Structure

Before writing the SPEC, read [`references/spec-template.md`](references/spec-template.md) — it carries the per-section writing rules, tables and examples. Write from it; don't improvise the section shape. The 11 sections, in order:

1. Summary — what this SPEC covers / PRD reference / design decisions
2. Architecture — system context, components, interactions, file structure
3. Data Model — schema changes, entities, relationships, migration plan
4. API Design — endpoints, request/response schemas, errors, breaking changes
5. Business Logic — algorithms, validation, state machine, edge cases
6. Error Handling — taxonomy, retry strategy, failure modes
7. Security — authentication/authorization, input validation, data protection
8. Performance — expected load, optimization strategy, database considerations
9. Testing Strategy — unit/integration/edge tests, acceptance criteria mapping
10. Implementation Plan — phases, issue mapping, incremental delivery
11. Open Questions & Risks — unresolved questions, risks, assumptions

Before you present the SPEC, run the checklist, edge-case table and anti-patterns in [`references/quality-checks.md`](references/quality-checks.md).

---

## Step 5: Review & Iteration

After generating the SPEC, present it and ask:

```
SPEC generated from PRD. Please review:

- Are the architecture choices appropriate?
- Are there missing edge cases or error scenarios?
- Is the API design consistent with existing patterns?
- Should any section have more/less detail?

Reply OK to save, or provide feedback for iteration.
```

---

## Step 6: Save

Ask user for save location:

```
Where should I save the SPEC?

A. tasks/spec-[feature-name].md (alongside PRD, recommended)
B. docs/spec-[feature-name].md
C. Custom path: [specify]
```
