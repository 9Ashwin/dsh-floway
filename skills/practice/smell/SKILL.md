---
name: smell
description: "Detect architecture smells, complexity hotspots and anti-patterns, and report them by severity. Triggers: smell, 代码坏味道, 架构坏味道, 反模式, complexity analysis, find anti-patterns."

---

# Smell — Architecture Bad Smell Detector

Analyze a codebase to find violations of software architecture principles, anti-patterns, code "bad smells," and algorithmic complexity hotspots. Produce a comprehensive, actionable markdown report.

**Scope limit:** This skill is guidance, not a checklist: heuristics are candidate signals, not findings, and a report earns nothing by listing more of them. Detect broadly, validate narrowly, and report only what the evidence supports — a short report of confirmed findings beats an exhaustive list of maybes.

**Knowledge base:** This skill encodes architectural patterns, anti-patterns, code smells, and algorithmic complexity heuristics drawn from industry research and practice, including the classic code smells catalog by Martin Fowler / Kent Beck (as organized on refactoring.guru: Bloaters, Object-Orientation Abusers, Change Preventers, Dispensables, Couplers).

---

## When to Use / When Not to Use

Use this skill when:

- Assessing the architecture or design quality of a codebase, module, or recent change set
- Hunting anti-patterns (Big Ball of Mud, God Object, circular dependencies, leaky abstractions)
- Auditing algorithmic complexity hotspots (nested loops, N+1 queries, sort-in-loop)
- Building a prioritized, evidence-backed refactoring roadmap

Do not use this skill when:

- The request is a line-by-line code review or style/lint pass — that is `review-it`
- The request is to apply a behavior-preserving transformation — that is `refactor`
- The request is for a spec or design document rather than a findings report — that is `code-to-spec` or `to-design`
- The scope is a single trivial function; the evidence-gathering overhead is not justified

---

## The Job

1. Understand the scope — ask what part of the project to analyze (full project, specific module, or recent changes)
2. Scan the codebase with the `grep`/`glob` tools (plus shell `find`/`grep` where useful), delegating breadth to `subagent` children, to gather candidate signals and evidence
3. Validate candidates against context, callers, history, workload, and measurements before confirming findings
4. Generate a detailed markdown report saved to `tasks/smell-report-[timestamp].md`
5. Present a summary of confirmed findings and separate candidates to the user

---

## Step 1: Scope Clarification

Ask the user:

```
What scope should I analyze?
  A. Entire project (thorough, may take time)
  B. Specific module/directory: [please specify]
  C. Only recently changed files (git diff)
  D. Only architectural-level issues (skip low-level code smells)
```

If the user doesn't specify, default to option A for small projects (< 100 files) or C for large projects. `references/principles-and-severity.md` carries the fallback handling for unusual scopes (empty or monorepo projects, unsupported languages, quick or single-category runs, filename conflicts).

---

## Step 2: Evidence Gathering

**Delegate the scan to `subagent` children.** DSH has no built-in subagent *types* — there is no `Explore` agent to select, and a child sees none of this conversation, so every prompt must be self-contained (state the directory to scan and exactly what to report). Fire several `subagent` calls in **one** assistant message to run them concurrently; each returns a child id immediately and reports back with a settlement notice, so collect them at the end rather than polling. Delegation depth is capped at 3 — children should scan, not delegate further. Run these explorations:

### Exploration Commands

Run these in parallel to gather evidence efficiently:

1. **Project Structure Scan:** Map the directory tree, identify the architectural style (layered, modular monolith, microservices, etc.)
2. **Dependency Analysis:** Find import/include patterns, check for circular dependencies, identify coupling hotspots
3. **Module/Component Scan:** Identify God Objects (files > 500 lines), check cohesion, check single responsibility violations
4. **Pattern Detection:** Look for known anti-pattern signatures (static cling, service locator abuse, leaky abstractions)
5. **Testing Scan:** Check test coverage patterns, test file locations, test-to-code ratios
6. **Naming & Clarity Scan:** Flag misleading names, overly generic names (Manager, Helper, Util), inconsistent naming conventions
7. **Complexity Scan:** Detect algorithmic complexity hotspots — nested loops, N+1 queries, repeated scans, sort-in-loop, expensive recomputation in render paths

### Key Heuristics

Heuristics are **candidate signals, not findings**. A line-count, nesting, naming, or Big-O match must be validated against the code's responsibility, callers, change history, workload, and intentional constraints. Do not assign severity from a threshold alone.

`references/anti-pattern-catalog.md` holds the full detection table — every architecture, coupling, cohesion, design, code, testing, naming, readability, and complexity smell with its heuristic. Read the relevant row when a specific smell is suspected, not on every invocation.

---

## Step 3: Validate Candidates

Process every candidate in three stages:

1. **Candidate detection:** static patterns, file metrics, and dependency scans produce candidates only.
2. **Context validation:** read the implementation and relevant callers; check change frequency, input size, runtime frequency, framework constraints, generated/vendor status, and existing mitigations.
3. **Finding confirmation:** merge candidates with the same root cause, affected path, failure/change scenario, and remediation direction into one finding.

Count findings by independent root cause, never by the number of principles they implicate. Use one **Primary principle** and optional **Related principles**. `SOLID` is an umbrella label; use `SRP`, `OCP`, or `DIP` as the primary label when the evidence supports a specific lens, without also creating a separate SOLID finding.

A confirmed finding must name its location (`file:line`, plus relevant callers), a concrete failure or change scenario, and how the fix will be verified. Record evidence strength (`Measured`/`Observed`/`Inferred`) separately from confidence (`High`/`Medium`/`Low/Candidate`); evidence strength does not imply severity. Anything whose runtime impact, change frequency, or workload is not yet established stays a candidate, not a finding.

Before merging candidates or assigning severity, read `references/principles-and-severity.md` for the canonical 11-principle matrix (confirming evidence and common false positives), the design-principle refinements, and the severity rubric.

For any performance or complexity candidate, read `references/complexity-heuristics.md` and apply **Measure First** — state what to measure, when the signal becomes a finding, and when not to flag it.

---

## Step 4: Save and Present

Generate the report from the skeleton and worked example in `references/report-template-and-example.md`, whose sections are:

1. **Executive Summary** — confirmed findings only, with candidates mentioned separately
2. **Architectural Style Detected** — the style found, plus expectations vs. reality
3. **Findings by Category** — 🔴 Critical / 🟡 Warning / 🔵 Suggestion, with a separate *Candidates Requiring Measurement* section
4. **Detailed Findings** — category, severity, anti-pattern, location, confidence, evidence strength, failure/change scenario, primary and related principles, description, evidence, measured/observed impact, recommendation, verification
5. **Dependency Graph Analysis** — module dependencies, circular dependencies, coupling hotspots
6. **Module Health Scorecard** — lines, God Object risk, coupling, cohesion, test coverage, health
7. **Smell Distribution** — deduplicated confirmed findings by primary category
8. **Refactoring Roadmap** — ordered by impact, confidence, dependency sequence, and verification cost, with only high-confidence, verifiable findings as Immediate Actions

Save the report to `tasks/smell-report-[YYYY-MM-DD-HHmm].md` and present a brief summary to the user. Lead with confirmed findings and keep candidates in a separate list.

---

## References

Load a reference only when the task reaches its topic; none of these is needed on every invocation.

- `references/anti-pattern-catalog.md` — full detection table mapping every smell to its static heuristic. Read when you need the heuristic for a specific smell.
- `references/architecture-smells.md` — prose catalog of architectural anti-patterns (Big Ball of Mud, Distributed Monolith, Anemic Domain Model, ...) and the Top Ten architecture mistakes, each with symptoms and remedy. Read when investigating an architecture-level smell.
- `references/coupling-and-design-smells.md` — coupling and cohesion smells plus the object-orientation abusers (Switch Statements, Refused Bequest, ...), each with symptoms and remedy. Read when investigating coupling, cohesion, inheritance, or interface design.
- `references/code-and-testing-smells.md` — code-level and testing smells (Long Method, Primitive Obsession, Dead Code, No Tests, ...) with remedies. Read when investigating a code-quality or testing smell.
- `references/complexity-heuristics.md` — the algorithmic complexity catalog with detection, impact, remedy, and correctness checks, plus Measure First and what not to flag. Read before reporting any performance finding.
- `references/principles-and-severity.md` — the 11-principle matrix, design-principle refinements, evidence-strength and severity rubric, and edge-case fallback handling. Read before merging candidates or assigning severity.
- `references/report-template-and-example.md` — the full report skeleton and a worked summary example. Read when writing or presenting the report.
