# Report Template & Worked Example

The full markdown skeleton to copy when writing the report, followed by a worked example of the summary presented to the user. Read this when generating or presenting the report.

Generate the report in this structure:

```markdown
# Architecture Smell Report

**Project:** [project-name]
**Scope:** [scope description]
**Date:** [date]
**Analyzer:** smell skill (Ducc)

---

## Executive Summary

[2-3 paragraph summary of confirmed findings only: architectural style detected, overall health assessment, and top 3-5 critical issues. Mention candidates separately.]

---

## Architectural Style Detected

[Identify the architectural style: Layered, Modular Monolith, Microservices, Hexagonal, Clean Architecture, or Big Ball of Mud]

### Style Expectations vs. Reality

| Expectation | Reality | Status |
|-------------|---------|--------|
| [e.g., Clear layer separation] | [what was found] | ✅/⚠️/🔴 |

---

## Findings by Category

### 🔴 Critical Issues (Must Fix)

[Issues that fundamentally undermine architecture]

### 🟡 Warnings (Should Fix)

[Issues that degrade maintainability but don't block function]

### 🔵 Suggestions (Nice to Fix)

[Minor improvements that would increase quality]

### Candidates Requiring Measurement

[Static candidates whose runtime impact, change frequency, or workload is not yet established. These do not count toward severity totals.]

---

## Detailed Findings

### Finding #1: [Title]

- **Category:** [Architecture/Coupling/Cohesion/Design/Code/Testing/Naming/Complexity]
- **Severity:** 🔴 Critical / 🟡 Warning / 🔵 Suggestion
- **Anti-Pattern:** [Name of anti-pattern]
- **Location:** [file:line references and relevant callers]
- **Confidence:** [High/Medium]
- **Evidence strength:** [Measured/Observed/Inferred]
- **Failure or change scenario:** [Concrete scenario]
- **Primary principle:** [Most specific principle]
- **Related principles:** [Explanatory only; do not count separately]
- **Description:** [What was found and why it's a problem]
- **Evidence:** [Code, dependency, history, or measurement]
- **Measured/observed impact:** [Reach, frequency, consequence, or baseline]
- **Recommendation:** [Smallest justified refactoring]
- **Verification:** [How to prove behavior and impact]

---

## Dependency Graph Analysis

[Summary of module dependencies, circular dependencies found, coupling hotspots]

---

## Module Health Scorecard

| Module | Lines | God Object Risk | Coupling | Cohesion | Test Coverage | Health |
|--------|-------|----------------|----------|----------|---------------|--------|
| [name] | [N] | [Low/Med/High] | [Low/Med/High] | [Low/Med/High] | [% or N/A] | 🟢/🟡/🔴 |

---

## Smell Distribution

Count only deduplicated confirmed findings by their primary category. Related principles and candidates do not affect these totals.

| Category | Count | Critical | Warning | Suggestion |
|----------|-------|----------|---------|------------|
| Architecture | [N] | [N] | [N] | [N] |
| Coupling | [N] | [N] | [N] | [N] |
| Cohesion | [N] | [N] | [N] | [N] |
| Design | [N] | [N] | [N] | [N] |
| Code | [N] | [N] | [N] | [N] |
| Testing | [N] | [N] | [N] | [N] |
| Naming | [N] | [N] | [N] | [N] |
| Complexity | [N] | [N] | [N] | [N] |

---

## Refactoring Roadmap

Order work by impact, confidence, dependency sequence, and verification cost—not by principle count or smell name. Put only high-confidence, verifiable findings in Immediate Actions; for candidates, recommend the next measurement instead of a rewrite.

### Immediate Actions (This Sprint)
1. [Actionable fix 1]
2. [Actionable fix 2]

### Short-Term (1-3 Months)
1. [Structural improvement 1]
2. [Structural improvement 2]

### Long-Term (3-12 Months)
1. [Architectural transformation 1]
2. [Architectural transformation 2]

---

## Appendix: Anti-Pattern Reference

[A condensed reference of anti-patterns checked, with brief descriptions]
```

---

## Report Output Example

```
🔍 Architecture Smell Analysis Complete

Project: stream-it
Style: Modular Monolith (with some layering violations)
Files Analyzed: 47
Health: 🟡 Fair

Critical: 3  |  Warnings: 6  |  Suggestions: 9

🔴 Critical Issues:
  1. Anemic Domain Model — `models/` classes have only getters/setters,
     all logic in `services/`. Violates DDD Rich Domain Model principle.
  2. N+1 Query Pattern — `services/order.ts:142` fetches user per order in loop;
     should batch-load users by IDs (O(n*m) → O(n+m)).
  3. Static Cling — `util/ApiClient.ts` uses all static methods,
     making consumer code untestable.

🟡 Warnings:
  1. God Object — `services/workflow.ts` at 847 lines handles too many concerns
  2. Nested Loop O(n^2) — `analytics.ts:89` pairwise comparison of events;
     sort+two-pointer would be O(n log n)
  3. Leaky Abstraction — `repositories/user.ts` exposes MongoDB query syntax
  4. Duplicated Code — validation logic duplicated across 4 controllers
  5. Circular Dependency — `auth` ↔ `user` modules depend on each other
  6. Magic Numbers — ~23 hardcoded values without named constants

Full report: tasks/smell-report-2026-05-27-1530.md
```
