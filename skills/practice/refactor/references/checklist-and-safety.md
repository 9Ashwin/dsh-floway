# Checklist, Safety Protocol, and Edge Cases

The mechanical discipline around a refactoring: what to verify before calling it done, what to
do before touching anything and at every step, how to recover when a test breaks, and how to
handle the situations that do not fit the happy path. Read it before starting, after each
step, and whenever a test fails.

## Refactoring Checklist

### Code Quality
- [ ] One primary smell/root cause is being addressed; related principles are not counted as separate work
- [ ] Evidence, expected impact, baseline, and success condition are recorded
- [ ] Functions are appropriately sized for their context (line counts are candidate signals, not limits)
- [ ] Each function does one thing when that improves responsibility boundaries (SRP)
- [ ] No duplicated knowledge (DRY), without merging independently changing code
- [ ] Names describe what, not how
- [ ] No magic numbers or strings
- [ ] Dead code removed

### Structure
- [ ] Related code is grouped together and concerns do not leak across intended boundaries
- [ ] Module boundaries are clear
- [ ] Dependencies flow in one direction (no cycles); DIP abstractions correspond to real boundaries
- [ ] OCP/DIP changes do not introduce speculative layers that violate KISS/YAGNI
- [ ] Composition is preferred only where it reduces real inheritance coupling
- [ ] No circular dependencies

### Conditionals
- [ ] Guard clauses replace deep nesting
- [ ] Complex conditions extracted to named methods
- [ ] Polymorphism replaces type-switching conditionals
- [ ] Null Object pattern where appropriate

### Type Safety (typed languages)
- [ ] Types defined for all public APIs
- [ ] No `any` usage without qualification
- [ ] Nullable types explicitly marked
- [ ] Type codes replaced with classes/enums

### Testing
- [ ] Refactored code is tested
- [ ] Edge cases are covered
- [ ] Invalid input/state fails near its source where appropriate (Fail Fast)
- [ ] Error, retry, transaction, and cleanup semantics remain unchanged
- [ ] All tests pass after each step
- [ ] Characterization tests capture pre-refactoring behavior
- [ ] Performance claims have comparable before/after measurements

## Safety Protocol

### Before You Touch Anything
```
1. Characterization tests  →  capture what the code does now
2. Git commit              →  save a known-good state
3. Branch                  →  isolate refactoring from other work
```

### Every Single Step
```
1. One change              →  one refactoring technique
2. Compile                 →  must compile clean
3. Tests                   →  every test must pass
4. Commit                  →  message: "refactor: <technique> <what>"
```

### If Tests Break
```
1. Undo the last change
2. Understand what broke and why
3. Try a smaller step
4. If the test was wrong and behavior was correct, fix the test FIRST, then retry
```

### On Completion
```
1. Full test suite         →  all tests pass
2. Manual smoke test       →  quick sanity check
3. Self-review diff        →  catch unintended changes
4. Final commit            →  describe the overall transformation
```

## Edge Cases & Gotchas

| Scenario | Handling |
|----------|----------|
| No tests exist | Write characterization tests first. Run the code with various inputs, capture outputs. These are your safety net. |
| Refactoring breaks a distant test | FIRST understand why. Maybe the test relied on implementation detail. If so, fix the test to test behavior, not implementation. Then resume. |
| User wants behavior change + refactor together | REFUSE. Do them separately. Refactor first to make the behavior change easy, commit, then change behavior. |
| Method is too complex to step through | Use Replace Method with Method Object. Turn the whole method into a class where each step can be extracted. |
| Refactoring across a large codebase | Extract a micro-service or module boundary first. Then refactor within the boundary. "There is a refactoring for everything except too many refactorings." |
| IDE automated refactoring available | Use it. Modern IDEs can safely rename, extract method, introduce variable, etc. Only do it manually when the IDE can't. |
| Undo needed | `git stash` or `git reset --hard` back to last commit. Small commits make this painless. |
