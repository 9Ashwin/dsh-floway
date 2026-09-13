---
name: refactor
description: "Refactor toward maintainability without changing behaviour, from Fowler's catalog: smells, composing methods, moving features, simplifying conditionals. Triggers: refactor, 重构, clean up, extract method, simplify."

---

# Refactor — Expert Code Restructuring

Surgical code refactoring based on Martin Fowler's <Refactoring> (2nd Edition) catalog. Improve structure, readability, and maintainability without changing external behavior. Gradual evolution, not revolution.

**This skill is guidance, not a script: the catalog is a menu, and a refactoring that cannot be justified by a named smell is not worth making.** This file carries the rules, the workflow, and the decision rubric; the smell and technique entries are lookup material in `references/`, read one entry at a time once you have named the symptom you are fixing.

## When to Use

This skill activates when:
- Code is hard to understand or maintain
- Functions/classes have grown too large
- Code smells are detected
- Adding features is difficult due to poor structure
- User explicitly requests refactoring, cleanup, or improvement
- User says: refactor, 重构, clean up, improve code, code smell, extract method, rename, simplify

## When NOT to Refactor

| Scenario | Action |
|----------|--------|
| Code works and won't change again | Leave it alone |
| Critical production path with no tests | Write characterization tests first |
| Under tight deadline pressure | Document the smell, refactor later |
| No clear purpose or benefit | Don't refactor for refactoring's sake |
| Code is fundamentally wrong | This is a rewrite, not a refactoring |

## The Golden Rules

These five rules are non-negotiable. Violating any of them turns refactoring into reckless editing.

### 1. Behavior is Preserved

Only *how* the code works changes, never *what* it does. If tests existed before, they must pass after. If the refactoring introduces a behavioral change, it's not refactoring — it's rewriting.

### 2. Small Steps

Each change should be the smallest possible transformation that compiles and passes tests. If a step breaks, you know exactly which change caused it. Refactoring is a series of tiny, safe transformations, not one big rewrite.

### 3. Version Control is Your Friend

Commit before starting. Commit after each successful step. This gives you infinite undo. Branch from a clean state so you can abandon the refactoring without consequences.

### 4. Tests are Essential

"Without tests, you're not refactoring — you're just editing." If tests don't exist for the target code, write characterization tests first. These tests capture the current behavior so you can detect regressions.

### 5. One Thing at a Time

Never mix refactoring with feature changes. Never refactor two unrelated things simultaneously. Each commit should contain exactly one refactoring operation.

## The Safe Refactoring Workflow

1. **Identify the smell.** Name the primary smell before touching code — one root cause, backed by evidence: location, behavior, callers, change history, or measurement. The five families are in `references/smells.md`; their thresholds are candidate signals, not verdicts.
2. **Pick the smallest move.** Choose the least invasive technique that addresses the root cause, and record how behavior preservation and the expected benefit will be verified. The technique catalogs are in `references/`.
3. **Keep behaviour fixed.** Golden Rule 1 is the point of the exercise: only *how* the code works changes, never *what* it does. Make one small change at a time; the code should compile after every change, so if a step breaks you know exactly which change caused it.
4. **Run the tests.** Golden Rule 4: all tests must pass. If tests don't exist for the target code, write characterization tests first; if they fail, undo the last change rather than pressing on.
5. **One refactoring per commit.** Golden Rule 5: never mix refactoring with feature changes, and never refactor two unrelated things simultaneously. Commit with a message like `refactor: extract validateEmail method`.

## The Refactoring Process

### Phase 1: Prepare

1. **Write characterization tests** if they don't exist. These capture current behavior — they don't need to be elegant, just comprehensive enough to catch regressions.
2. **Record a baseline** for the claimed problem: representative behavior, change spread, relevant callers, or a benchmark/profile/query count for performance work. Without a performance baseline, describe a performance idea as a candidate, not a measured improvement.
3. **Commit** current state. Start from a clean working tree.
4. **Create a branch** for the refactoring. Keep it separate from feature work.

### Phase 2: Identify

1. **Smell the code.** Use the smell catalog in `references/smells.md` to classify what's wrong, treating thresholds as candidate signals.
2. **Understand the code.** Read it thoroughly, map relevant callers and dependencies, and identify the concrete failure or change scenario.
3. **Choose a primary principle.** Attach related principles only as explanations; do not split one root cause into multiple findings.
4. **Check counter-pressures.** Confirm that DRY will not create a false abstraction, that OCP/DIP are not speculative, that SRP will not create pass-through fragments, and that composition addresses real inheritance coupling.
5. **Choose the right refactoring.** Pick the smallest technique from the catalog and define how the baseline and behavior will be checked.

### Phase 3: Refactor (Small Steps)

For each step:
1. **Make one small change.** Address one verifiable part of the primary smell; do not bundle unrelated principle cleanups.
2. **Compile.** The code should compile after every change.
3. **Run tests.** All tests must pass. If they don't, you've changed behavior.
4. **Check the seam.** A new interface, adapter, or indirection must remove real caller complexity or support an existing variation; otherwise keep the simpler design.
5. **Commit.** Create a commit with a message like `refactor: extract validateEmail method`.

Repeat until the smell is resolved.

### Phase 4: Verify

1. **Behavior.** All tests, type checks, compilation, and a manual smoke test pass.
2. **Structure.** Compare dependency direction, relevant callers, duplicated knowledge, or change spread against the decision card.
3. **Fail fast semantics.** If validation moved earlier, preserve error types/codes, aggregation, retry, transaction, and cleanup behavior.
4. **Performance.** Re-run the same workload and environment when performance was part of the claim. Report the result and noise range; without a baseline, only report that no obvious regression was observed.
5. **Diff review.** Check for unintended changes and confirm the success condition is met.

### Phase 5: Clean Up

1. **Remove stale comments.** If a refactoring made a comment obvious, delete the comment.
2. **Check for dead code.** After refactorings, unused code may emerge.
3. **Remove speculative seams.** Delete single-implementation interfaces, pass-through modules, or unused extension points that add no current leverage.
4. **Final commit.** Summarize the refactoring sequence.

## Refactoring Decision Rubric

Principles guide judgment; they are not independent reasons to rewrite code. Before choosing a Fowler technique, record one decision card:

| Field | Required answer |
|-------|-----------------|
| **Primary smell** | One root cause, not one entry per principle |
| **Evidence** | Location, behavior, callers, change history, or measurement |
| **Primary principle** | The most specific applicable principle |
| **Related principles** | Explanatory labels only; do not count separately |
| **Expected impact** | Observable reduction in change spread, cognitive load, duplicated knowledge, coupling, delayed failure, or measured runtime cost |
| **Smallest refactoring** | The least invasive Fowler technique that addresses the root cause |
| **Baseline / success condition** | How behavior preservation and the expected benefit will be verified |

Use these four decision lenses:

| Lens | Principles | Questions to answer |
|------|------------|---------------------|
| **Responsibility and dependencies** | SOLID, SRP, OCP, DIP, Separation of Concerns | Are reasons to change mixed? Does a real new variant repeatedly modify stable logic? Does high-level policy depend on concrete mechanism? Do concerns leak across a boundary? |
| **Reuse and structure** | DRY, Composition | Is the same knowledge duplicated, or merely similar syntax? Would composition localize a real variation better than inheritance? |
| **Simplicity and scope** | KISS, YAGNI | Is the proposed structure simpler for today's problem? Is every abstraction backed by an existing variation or boundary? |
| **Runtime and feedback** | Fail Fast, Measure First | Can invalid state fail nearer its source without changing error semantics? What baseline proves the problem and the result? |

`SOLID` is an umbrella. When evidence supports `SRP`, `OCP`, or `DIP`, use that specific lens and do not create a second SOLID issue. LSP and ISP may be labeled `SOLID/LSP` and `SOLID/ISP`. DRY means shared knowledge, not all similar code. Composition is preferred when inheritance creates real coupling, not by default. OCP and DIP never justify speculative layers that violate KISS or YAGNI.

## References

The catalog is lookup material: load the file that matches the smell you named, not all of them at once.

- [`references/smells.md`](references/smells.md) — the five smell families (bloaters, object-orientation abusers, change preventers, dispensables, couplers), each smell with its description and primary refactoring. Read it first, to put a name to the symptom.

The refactoring techniques catalog is organized by category, from Fowler's catalog. Each technique includes its mechanical steps.

- [`references/composing-methods.md`](references/composing-methods.md) — Extract/Inline Method, Extract Variable, Replace Temp with Query, Replace Method with Method Object, Substitute Algorithm, with mechanics and before/after examples. Read it when a method is too long or a name no longer fits.
- [`references/moving-features.md`](references/moving-features.md) — Move Method/Field, Extract/Inline Class, Hide Delegate, Remove Middle Man, foreign methods, and the generalization moves (Pull Up, Push Down, Extract Superclass/Interface, Replace Inheritance with Delegation). Read it when behavior sits in the wrong class or the hierarchy has drifted.
- [`references/organizing-data.md`](references/organizing-data.md) — Self Encapsulate Field, value/reference conversions, Replace Array with Object, type codes, magic numbers, and collection encapsulation. Read it when raw data carries meaning an object should carry instead.
- [`references/simplifying-conditionals-and-method-calls.md`](references/simplifying-conditionals-and-method-calls.md) — Decompose Conditional, guard clauses, Replace Conditional with Polymorphism, Null Object, assertions, and the naming and parameter moves. Read it when conditionals nest deeply or a call site is hard to read.
- [`references/checklist-and-safety.md`](references/checklist-and-safety.md) — the code-quality, structure, conditionals, type-safety, and testing checklist; the before/every-step/if-tests-break/on-completion safety protocol; and the edge-case table. Read it before starting, after each step, and whenever a test breaks.
- [`references/applying-the-catalog.md`](references/applying-the-catalog.md) — common multi-step sequences, design-pattern pairings, and per-language notes (Java, JavaScript/TypeScript, Python, Go, Rust). Read it once the smell is named and you want a known order of steps.

## Resources

- Martin Fowler, *Refactoring: Improving the Design of Existing Code* (2nd Edition, 2018)
- [refactoring.com](https://refactoring.com) — Fowler's online catalog
- [refactoring.guru](https://refactoring.guru) — Illustrated refactoring patterns
- [refactoring.guru/refactoring/catalog](https://refactoring.guru/refactoring/catalog) — full technique catalog (6 categories, 66 techniques) and code-smell taxonomy this skill mirrors
