---
name: modern-go
description: "Modernize Go code to version-appropriate idioms, Go 1.0→1.27+, reading go.mod for the target version. Triggers: 现代化, 现代Go语言, modernize, gofix, idiomatic, update Go code."

---

# modern-go

Modernize Go source code by applying version-appropriate idioms, APIs, and language features. Works like `go fix` plus additional transformations curated from the Go team's modernize analysis passes and community best practices.

**This skill is guidance, not a script.** The version-by-version rule catalog is lookup material, not body content: it lives in `references/`, one file per version band, and you load only the bands your `go.mod` version makes eligible (see [References](#references)). Work through those bands one rule at a time — do not read, or apply, the catalog as a checklist.

## Scope limit

This skill changes *how* Go code is written, never *what* it does. Concretely:

- **Behaviour-preserving only.** A rewrite keeps observable behaviour identical, including error values, ordering and allocation semantics.
- **Never exceed the declared Go version.** A rule gated at, say, Go 1.24 is not eligible for a `go 1.22` module. Never apply a transformation that requires a version higher than the project declares.
- **No version bump, no new requirement, no functional change.** Do not raise the `go` directive, add a module dependency, or fold a bug fix or feature into a modernization.
- **One rule per commit.** Never mix a modernization with a functional change, and never bundle several rules into one commit.
- **Suggestions are not edits.** Rules the catalog marks as semantic migrations (`math/rand/v2`, `iter.Seq`, `os.Root`, `omitzero`) are pointed out and applied only if the user opts in.

## When to use it

Invoke this skill when the user asks to modernize Go code. By default, modernize the entire project; the user may specify a file or directory instead.

Do not use it when:

- the user wants a behaviour change — that is an ordinary edit, and mixing it with a modernization is exactly what this skill forbids;
- nothing declares the target version and the user will not name one — without a `go.mod` `go` directive you cannot decide which rules are eligible;
- the change is a single rename or signature edit — apply it directly; the catalog adds nothing.

## Workflow

Follow the phases in order.

### Phase 1: Detect

Read `go.mod` to extract the Go version (`go 1.xx` line). If no `go.mod` is found, default to `go 1.21`.

### Phase 2: Gather files

Find all `.go` files in the target scope (project root, or user-specified file/directory). Exclude `vendor/`, `.git/`, and `testdata/` directories.

### Phase 3: Determine eligible rules

Load the `references/` band(s) whose version range is at or below the detected version (see [References](#references)). Each transformation includes a **Go version** gate—only apply when the project's `go.mod` version ≥ that version. Never apply a transformation that requires a version higher than the project's Go version.

### Phase 4: Apply transformations

For each `.go` file, apply all transformations for versions ≤ the detected Go version. Process files sequentially. For each file:

1. Read the file content.
2. Identify applicable transformations by scanning for the "Before" patterns.
3. Apply each transformation using the Edit tool.
4. Run `goimports -w` (or `gofmt -w`) on the file after all edits.

Apply **one rule at a time**, oldest gate to newest, and keep the build and the `go vet`/test gates green after each one:

- run `go build ./...` and `go vet ./...`, plus the project's tests;
- if a rule turns any of them red, revert that rule — do not patch around a modernization;
- commit each rule on its own, and never mix a modernization with a functional change.

### Phase 5: Report

Print a summary table showing:

- **File**: path relative to project root
- **Transformations applied**: list of transformation names per file
- **Total files modified** and **total transformations applied**
- **Skipped transformations** (available but not applicable due to version constraints) and their required Go version

## Example Summary Output

```
## Modernization Summary

| File | Transformations |
|---|---|
| main.go | any, strings.Cut, min/max (2 occurrences) |
| pkg/handler.go | range over int (3), slices.Contains, t.Context() |
| pkg/util.go | new(expr) (1), errors.AsType → errors.Is |

**3 files modified, 10 transformations applied**

Skipped (requires higher Go version):
- new(expr): requires go 1.26 (project is go 1.24)
- WaitGroup.Go: requires go 1.25 (project is go 1.24)
```

## Safety Rules

- Never apply transformations that change semantics in edge cases without the user's awareness.
- Do not apply `omitzero` blindly—it changes JSON serialization behavior; flag it as a suggestion instead.
- Treat semantic migrations as suggestions, not auto-applies: `math/rand/v2` (changes the random stream), `iter.Seq` iterators (reshapes the API), `os.Root` (behavior/error-path change). Point them out and let the user opt in.
- When replacing a `bufio.Scanner` loop with `strings.Lines`/`bytes.Lines`, remember the yielded line keeps its trailing `\n`; add a `TrimSuffix` if the old code relied on `Scanner.Text()` semantics.
- Do not apply `strings.SplitSeq` or `bytes.SplitSeq` when the loop body references the index or the full slice elsewhere.
- Do not apply `strings.Builder` if the concatenation happens outside a loop (single `+=` is fine).
- When a transformation requires a new import, ensure the import is added to the file.
- After all edits, run `goimports -w` on each modified file to clean up imports.
- If `goimports` is not available, fall back to `gofmt -w`.
- If the project has no `go.mod`, ask the user for the target Go version before proceeding.

## Automated tooling (Go 1.27+)

Many of these transformations are now shipped as official modernizers in `gopls`/`go fix`. On Go 1.27+ the whole set can be applied across a module with:

```sh
go fix ./...
```

gopls v0.22.0 added four notable passes covered above:

| Modernizer | Min Go | Transformation |
|---|---|---|
| `unsafefuncs` | 1.17 | `uintptr` pointer math → `unsafe.Add` / `unsafe.Slice` |
| `atomictypes` | 1.19 | primitive `atomic.*` funcs → typed `atomic.Int32`/`Pointer[T]` wrappers |
| `slicesbackward` | 1.23 | descending-index loops → `slices.Backward` iterator |
| `embedlit` | 1.27 | redundant embedded-field literals → promoted-field init |

Other modernizers in the same suite that this catalog covers: `minmax`, `efaceany`, `fmtappendf`, `stringscut`, `stringsseq`, `sortslice`/`slicescontains`, `mapsloop`, `stditerators`, `forvar`, `rangeint`, `testingcontext`, `bloop`, `waitgroup`, `newexpr`, `errorsastype`, `appendclipped` (→ `slices.Concat`), and `plusbuild` (→ drop obsolete `// +build`).

To disable an over-eager pass (e.g. `slicesbackward` rewriting loops that mutate the slice), scope the run with `-fixes` or exclude that analyzer in your editor's gopls settings.

## References

Load only the bands your `go.mod` version makes eligible: a band is eligible when the detected version is at or above its version range, and a rule inside it applies only when its own heading's version gate is met.

- `references/go-1.0-1.17.md` — `time.Since`/`time.Until`, loop `strings.Builder`, `errors.Is`, `//go:build` cleanup, `unsafe.Add`/`unsafe.Slice`. Read for every module.
- `references/go-1.18-1.20.md` — `any`, `strings.Cut`/`bytes.Cut`, `fmt.Appendf`, typed atomics, `strings.Clone`/`bytes.Clone`, `CutPrefix`/`CutSuffix`, `errors.Join`, `context.WithCancelCause`. Read for `go 1.18`+.
- `references/go-1.21-slices-maps.md` — the `slices` and `maps` packages: `Contains`, `Index`, `SortFunc`, `Max`/`Min`, `Reverse`, `Compact`, `Clip`, `Clone`, `Delete`/`Insert`, `Equal`, and `maps.Clone`/`Copy`/`DeleteFunc`. Read for `go 1.21`+.
- `references/go-1.21-language.md` — `min`/`max`, `clear`, `sync.OnceFunc`/`OnceValue`, `context.AfterFunc`, `context.WithTimeoutCause`. Read for `go 1.21`+.
- `references/go-1.22.md` — `slices.Concat`, range over integer, loop-variable shadow removal, `cmp.Or`, `reflect.TypeFor`, enhanced `http.ServeMux`, `math/rand/v2`. Read for `go 1.22`+.
- `references/go-1.23.md` — range over function (`iter.Seq`), iterator helpers, `strings.SplitSeq`/`FieldsSeq`, `bytes.SplitSeq`, `slices.Backward`. Read for `go 1.23`+.
- `references/go-1.24.md` — `t.Context()`, `strings.Lines`/`bytes.Lines`, `os.Root`, `omitzero`, `b.Loop()`. Read for `go 1.24`+.
- `references/go-1.25-1.27.md` — `sync.WaitGroup.Go`, `new` with expressions, `errors.AsType`, embedded field literals. Read for `go 1.25`+.
