# Go 1.25–1.27 rules

Rule catalog for the `modern-go` skill: apply a rule only when `go.mod` declares the
version in its heading or newer. Covers `sync.WaitGroup.Go`, `new` with expressions, `errors.AsType`, embedded field literals.

### Go 1.25+ — `sync.WaitGroup.Go`

| Before | After |
|---|---|
| `wg.Add(1); go func() { defer wg.Done(); fn() }()` | `wg.Go(fn)` |

```go
// before
var wg sync.WaitGroup
for _, item := range items {
    wg.Add(1)
    go func(item Item) {
        defer wg.Done()
        process(item)
    }(item)
}
wg.Wait()
// after
var wg sync.WaitGroup
for _, item := range items {
    wg.Go(func() { process(item) })
}
wg.Wait()
```

### Go 1.26+ — `new` with expressions

| Before | After |
|---|---|
| `v := val; &v` | `new(val)` |
| Helper `func ptr[T any](v T) *T { return &v }` | `new(val)` directly |

```go
// before
timeout := 30
debug := true
cfg := Config{
    Timeout: &timeout,
    Debug:   &debug,
}
// after
cfg := Config{
    Timeout: new(30),
    Debug:   new(true),
}
```

```go
// before
func ptr[T any](v T) *T { return &v }
cfg := Config{Count: ptr(10)}

// after
cfg := Config{Count: new(10)}
```

### Go 1.26+ — `errors.AsType`

| Before | After |
|---|---|
| `var t *T; errors.As(err, &t)` | `t, ok := errors.AsType[*T](err)` |

```go
// before
var pathErr *os.PathError
if errors.As(err, &pathErr) {
    log.Println(pathErr.Path)
}
// after
if pathErr, ok := errors.AsType[*os.PathError](err); ok {
    log.Println(pathErr.Path)
}
```

### Go 1.27+ — Embedded field literals (embedlit)

| Before | After |
|---|---|
| `T{U: U{x: 1}}` (redundant embedded-type specifier) | `T{x: 1}` |

```go
type Base struct {
    ID   int
    Name string
}
type User struct {
    Base
    Age int
}

// before
u := User{
    Base: Base{ID: 1, Name: "alice"},
    Age:  30,
}
// after
u := User{
    ID:   1,
    Name: "alice",
    Age:  30,
}
```

The `embedlit` modernizer (gopls v0.22.0, `EmbedLitAnalyzer`) strips redundant embedded-struct field-type specifiers from composite literals. Go 1.27 lets you initialize promoted fields directly without the nested literal. Only apply when the promoted field names don't collide with the outer struct's own fields.
