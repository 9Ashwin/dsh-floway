# Principles, Evidence, Severity & Edge Cases

The reporting contract: the canonical 11-principle matrix with its false-positive constraints, the design-principle refinements, the evidence-strength and severity rubric, and the fallback handling for unusual scopes. Read this before merging candidates into findings or assigning severity.

### Canonical 11-Principle Matrix

| Principle | Confirming evidence | Common false positive / constraint |
|-----------|---------------------|------------------------------------|
| **SOLID** | A design problem spans multiple SOLID lenses or no narrower lens is reliable | Do not duplicate a specific SRP/OCP/DIP finding |
| **DRY** | The same business rule or knowledge must change in multiple places | Similar syntax that is expected to evolve independently |
| **KISS** | Extra layers, indirection, or machinery add cost without observable leverage | A small abstraction that removes real complexity |
| **YAGNI** | Unused extension points, parameters, adapters, or speculative requirements | A tested seam required by an existing boundary or change |
| **SRP** | Multiple independent reasons to change, supported by responsibilities or change history | File size or method count alone |
| **Open/Closed (OCP)** | Adding a known variant repeatedly modifies stable branching logic | One simple, local conditional |
| **Dependency Inversion (DIP)** | High-level policy directly depends on concrete infrastructure, harming replacement or testing | Adding an interface for a single stable implementation |
| **Composition** | Inheritance causes unwanted coupling, refused behavior, or inseparable variation axes | Replacing every valid inheritance relationship mechanically |
| **Separation of Concerns** | Business policy, I/O, presentation, or persistence concerns leak across boundaries | A deliberately thin boundary adapter |
| **Fail Fast** | Invalid input, state, or dependency propagates until a distant operation fails | Intentional aggregation, retry, or deferred validation semantics |
| **Measure First** | A performance, scale, or optimization claim lacks a baseline or representative workload | Static complexity reported as a measured bottleneck |

For each confirmed finding, record evidence strength (`Measured`, `Observed`, or `Inferred`) separately from confidence (`High`, `Medium`, or `Low/Candidate`). Evidence strength does not imply severity.

### Severity Rubric

- **Critical:** correctness, reliability, security, data consistency, or measured system-level impact; normally requires high confidence.
- **Warning:** clear reach or repeated change/runtime cost with a concrete maintenance or runtime consequence.
- **Suggestion:** local, low-frequency, or limited-impact improvement with evidence.
- **Candidate requiring measurement:** static signal with unknown impact; exclude it from severity totals and put it in a separate report section.

### Design Principle Violations

Use the canonical matrix in Step 3 as the reporting contract. These design checks refine candidate detection; they do not create one finding per principle.

- **SOLID umbrella:** Use only when multiple SOLID concerns share one root cause or a narrower lens is not reliable.
- **SRP:** Confirm independent reasons to change; size alone is insufficient.
- **OCP:** Confirm repeated edits for a real variant; do not replace a simple local conditional with speculative polymorphism.
- **LSP:** Subtypes must preserve the base contract's preconditions, postconditions, and invariants. Report as `SOLID/LSP`.
- **ISP:** Confirm clients depend on methods they do not use. Report as `SOLID/ISP`.
- **DIP:** Confirm high-level policy is coupled to concrete mechanism in a way that harms testing or replacement; a single implementation does not automatically justify an interface.
- **DRY:** Deduplicate shared knowledge, not coincidentally similar syntax.
- **KISS and YAGNI:** Reject abstractions whose future variation or leverage is not demonstrated.
- **Composition:** Prefer it when inheritance exposes unwanted behavior or binds independent variation axes—not as a mechanical rule.
- **Separation of Concerns:** Confirm policy, presentation, persistence, or I/O leakage across an intended boundary.
- **Fail Fast:** Detect invalid state near its source while preserving established error, retry, transaction, and cleanup semantics.
- **Measure First:** Lower unmeasured optimization claims to candidates instead of reporting a second "principle violation."

## Edge Cases & Fallback

| Scenario | Handling |
|----------|----------|
| User doesn't specify scope | Default to recent changes (`git diff`) for repos > 200 files, full analysis otherwise |
| Project has no clear architecture | Report "Big Ball of Mud" with evidence, recommend incremental refactoring |
| Empty/monorepo project | Report that architecture analysis requires code; ask user to specify module |
| Language not supported | Report general structural observations; note language-specific checks are limited |
| Report file path conflicts | Append `-2`, `-3`, etc. to filename |
| User wants a quick check | Run only Critical-level scans, skip Code and Naming categories |
| User wants only one category | Focus analysis on that category, skip others |
