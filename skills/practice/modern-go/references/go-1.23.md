# Go 1.23 rules

Rule catalog for the `modern-go` skill: apply a rule only when `go.mod` declares the
version in its heading or newer. Covers range over function (`iter.Seq`), iterator helpers, `strings.SplitSeq`/`FieldsSeq`, `bytes.SplitSeq`, `slices.Backward`.

### Go 1.23+ — Range over function (iterators)

| Before | After |
|---|---|
| Custom `func Walk(yield func(T) bool)` callback traversal | `func Walk() iter.Seq[T]` returning an iterator |

```go
// before — callback-based iteration
func (t *Tree) Each(fn func(v int)) {
    for _, v := range t.values {
        fn(v)
    }
}
// caller: t.Each(func(v int) { use(v) })

// after — standard iterator, usable with range
func (t *Tree) All() iter.Seq[int] {
    return func(yield func(int) bool) {
        for _, v := range t.values {
            if !yield(v) { return }
        }
    }
}
// caller: for v := range t.All() { use(v) }
```

Adopt the `iter.Seq[T]` / `iter.Seq2[K,V]` protocol (Go 1.23) so custom containers compose with `range`, `slices.Collect`, `maps.Keys`, etc. Requires importing `"iter"`. Flag as a suggestion — it reshapes the API surface.

### Go 1.23+ — Iterator helpers

| Before | After |
|---|---|
| `var keys []K; for k := range m { keys = append(keys, k) }` | `slices.Collect(maps.Keys(m))` |
| `var vals []V; for _, v := range m { vals = append(vals, v) }` | `slices.Collect(maps.Values(m))` |

```go
// before
var keys []string
for k := range m {
    keys = append(keys, k)
}
// after
keys := slices.Collect(maps.Keys(m))
```

```go
// before
var vals []int
for _, v := range m {
    vals = append(vals, v)
}
// after
vals := slices.Collect(maps.Values(m))
```

Requires importing `"slices"` and `"maps"`.

### Go 1.23+ — `strings.SplitSeq` / `strings.FieldsSeq`

| Before | After |
|---|---|
| `for _, part := range strings.Split(s, sep)` | `for part := range strings.SplitSeq(s, sep)` |
| `for _, field := range strings.Fields(s)` | `for field := range strings.FieldsSeq(s)` |

```go
// before
for _, part := range strings.Split(line, ",") {
    process(part)
}
// after
for part := range strings.SplitSeq(line, ",") {
    process(part)
}
```

Only when the loop body does not need the index or the full slice.

### Go 1.23+ — `bytes.SplitSeq` / `bytes.FieldsSeq`

| Before | After |
|---|---|
| `for _, part := range bytes.Split(b, sep)` | `for part := range bytes.SplitSeq(b, sep)` |

```go
// before
for _, part := range bytes.Split(data, sep) {
    process(part)
}
// after
for part := range bytes.SplitSeq(data, sep) {
    process(part)
}
```

### Go 1.23+ — `slices.Backward` (slicesbackward)

| Before | After |
|---|---|
| `for i := len(s) - 1; i >= 0; i-- { use(s[i]) }` | `for _, v := range slices.Backward(s) { use(v) }` |
| reverse loop needing the index too | `for i, v := range slices.Backward(s) { ... }` |

```go
// before
for i := len(items) - 1; i >= 0; i-- {
    process(items[i])
}
// after
for _, v := range slices.Backward(items) {
    process(v)
}
```

```go
// before — index still needed
for i := len(items) - 1; i >= 0; i-- {
    fmt.Println(i, items[i])
}
// after
for i, v := range slices.Backward(items) {
    fmt.Println(i, v)
}
```

The `slicesbackward` modernizer (gopls v0.22.0) replaces manual descending-index loops with the `slices.Backward` iterator. Requires importing `"slices"`. **Caveat:** the rewrite preserves exact semantics in normal cases, but do not apply it when the loop body mutates the slice length or the index is used for out-of-band arithmetic — those edge cases can become unsound.
