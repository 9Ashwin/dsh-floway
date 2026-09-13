# Go 1.22 rules

Rule catalog for the `modern-go` skill: apply a rule only when `go.mod` declares the
version in its heading or newer. Covers `slices.Concat`, range over integer, loop-variable shadow removal, `cmp.Or`, `reflect.TypeFor`, enhanced `http.ServeMux`, `math/rand/v2`.

### Go 1.22+ — `slices.Concat` (appendclipped)

| Before | After |
|---|---|
| `append(append([]T(nil), s1...), s2...)` | `slices.Concat(s1, s2)` |
| `append(slices.Clip(s1), s2...)` for a fresh result | `slices.Concat(s1, s2)` |

```go
// before
all := append(append([]int(nil), a...), b...)
// after
all := slices.Concat(a, b)
```

```go
// before — three-way concat
merged := append(append(append([]string(nil), x...), y...), z...)
// after
merged := slices.Concat(x, y, z)
```

The `appendclipped` modernizer replaces nested `append` concatenation of multiple slices with `slices.Concat`, which allocates a fresh, correctly-sized result. `slices.Concat` was added in Go 1.22. Requires importing `"slices"`. Only apply when the pattern builds a new slice (starts from `[]T(nil)` or a clipped base) — not when it appends in place to an existing slice.

### Go 1.22+ — Range over integer

| Before | After |
|---|---|
| `for i := 0; i < n; i++ { ... }` | `for i := range n { ... }` |
| `for i := 0; i < n; i++ { ... }` (i unused) | `for range n { ... }` |

```go
// before
for i := 0; i < len(items); i++ {
    process(i, items[i])
}
// after
for i := range len(items) {
    process(i, items[i])
}
```

```go
// before
for i := 0; i < n; i++ {
    doWork()
}
// after
for range n {
    doWork()
}
```

### Go 1.22+ — Loop variable shadowing removal

| Before | After |
|---|---|
| `for _, x := range items { x := x; ... }` | `for _, x := range items { ... }` |

```go
// before
for _, x := range items {
    x := x          // capture for goroutine
    go func() { use(x) }()
}
// after
for _, x := range items {
    go func() { use(x) }()
}
```

The `x := x` capture idiom is redundant since Go 1.22.

### Go 1.22+ — `cmp.Or`

| Before | After |
|---|---|
| Chain of `if v == "" { v = fallback }` | `v := cmp.Or(val, fallback1, fallback2, ...)` |

```go
// before
name := os.Getenv("NAME")
if name == "" {
    name = os.Getenv("USER")
}
if name == "" {
    name = "anonymous"
}
// after
name := cmp.Or(os.Getenv("NAME"), os.Getenv("USER"), "anonymous")
```

Requires importing `"cmp"`.

### Go 1.22+ — `reflect.TypeFor`

| Before | After |
|---|---|
| `reflect.TypeOf((*T)(nil)).Elem()` | `reflect.TypeFor[T]()` |

```go
// before
t := reflect.TypeOf((*MyType)(nil)).Elem()
// after
t := reflect.TypeFor[MyType]()
```

### Go 1.22+ — Enhanced `http.ServeMux`

| Before | After |
|---|---|
| `mux.HandleFunc("/api/", h)` + manual path parsing | `mux.HandleFunc("GET /api/{id}", h)` + `r.PathValue("id")` |

```go
// before
mux.HandleFunc("/api/", func(w http.ResponseWriter, r *http.Request) {
    id := strings.TrimPrefix(r.URL.Path, "/api/")
    ...
})
// after
mux.HandleFunc("GET /api/{id}", func(w http.ResponseWriter, r *http.Request) {
    id := r.PathValue("id")
    ...
})
```

### Go 1.22+ — `math/rand/v2`

| Before | After |
|---|---|
| `rand.Intn(n)` | `rand.IntN(n)` |
| `rand.Int63n(n)` / `rand.Int31n(n)` | `rand.Int64N(n)` / `rand.Int32N(n)` |
| `rand.Seed(...)` + global funcs | drop `Seed`; use auto-seeded top-level funcs or `rand.N[T]` |

```go
// before
import "math/rand"
n := rand.Intn(100)
// after
import "math/rand/v2"
n := rand.IntN(100)
```

```go
// before — type-specific bound
d := time.Duration(rand.Int63n(int64(max)))
// after — generic N works for any integer type
d := rand.N(max)
```

`math/rand/v2` (Go 1.22) drops the deprecated global `Seed` (top-level funcs are auto-seeded) and adds generic `rand.N[T]`. **Semantic migration:** the random stream differs from `math/rand`, so do not apply where reproducibility from a fixed seed matters. Flag as a suggestion, not auto-apply.
