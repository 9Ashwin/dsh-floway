# Go 1.18–1.20 rules

Rule catalog for the `modern-go` skill: apply a rule only when `go.mod` declares the
version in its heading or newer. Covers `any`, `strings.Cut`/`bytes.Cut`, `fmt.Appendf`, typed atomics, `strings.Clone`/`bytes.Clone`, `CutPrefix`/`CutSuffix`, `errors.Join`, `context.WithCancelCause`.

### Go 1.18+ — `any`

| Before | After |
|---|---|
| `interface{}` | `any` |

```go
// before
func decode(v interface{}) error { ... }
// after
func decode(v any) error { ... }
```

### Go 1.18+ — `strings.Cut`

| Before | After |
|---|---|
| `i := strings.Index(s, sep); ... s[:i], s[i+len(sep):]` | `key, val, found := strings.Cut(s, sep)` |

```go
// before
if i := strings.Index(s, "="); i >= 0 {
    key, val := s[:i], s[i+1:]
}
// after
if key, val, found := strings.Cut(s, "="); found {
    ...
}
```

### Go 1.18+ — `bytes.Cut`

| Before | After |
|---|---|
| `i := bytes.Index(b, sep); ... b[:i], b[i+len(sep):]` | `before, after, found := bytes.Cut(b, sep)` |

```go
// before
if i := bytes.Index(b, sep); i >= 0 {
    before, after := b[:i], b[i+len(sep):]
}
// after
before, after, found := bytes.Cut(b, sep)
```

### Go 1.19+ — `fmt.Appendf`

| Before | After |
|---|---|
| `buf = append(buf, fmt.Sprintf(...)...)` | `buf = fmt.Appendf(buf, ...)` |

```go
// before
buf = append(buf, fmt.Sprintf("x=%d", x)...)
// after
buf = fmt.Appendf(buf, "x=%d", x)
```

### Go 1.19+ — Type-safe atomics (atomictypes)

| Before | After |
|---|---|
| `atomic.StoreInt32(&v, 1)` / `atomic.LoadInt32(&v)` | `var v atomic.Int32; v.Store(1); v.Load()` |
| `atomic.AddInt64(&v, 1)` | `var v atomic.Int64; v.Add(1)` |
| `atomic.Value` + type assertion | `atomic.Pointer[T]` |

```go
// before
var ready int32
atomic.StoreInt32(&ready, 1)
if atomic.LoadInt32(&ready) == 1 { ... }

// after
var ready atomic.Int32
ready.Store(1)
if ready.Load() == 1 { ... }
```

```go
// before
var cache atomic.Value
cache.Store(&Config{})
cfg := cache.Load().(*Config)

// after
var cache atomic.Pointer[Config]
cache.Store(&Config{})
cfg := cache.Load()
```

The `atomictypes` modernizer (gopls v0.22.0, `AtomicTypesAnalyzer`) rewrites both the variable declaration and every call site. Typed wrappers (`atomic.Int32/Int64/Uint32/Uint64/Bool/Pointer[T]`) have identical performance but prevent accidental non-atomic access and fix 64-bit alignment crashes on 32-bit architectures.

### Go 1.20+ — `strings.Clone`

| Before | After |
|---|---|
| `string([]byte(s))` | `strings.Clone(s)` |

```go
// before
s2 := string([]byte(s)) // force copy
// after
s2 := strings.Clone(s)
```

### Go 1.20+ — `bytes.Clone`

| Before | After |
|---|---|
| `make([]byte, len(src)); copy(dst, src)` | `bytes.Clone(src)` |

```go
// before
dst := make([]byte, len(src))
copy(dst, src)
// after
dst := bytes.Clone(src)
```

### Go 1.20+ — `strings.CutPrefix` / `strings.CutSuffix`

| Before | After |
|---|---|
| `if strings.HasPrefix(s, p) { s = s[len(p):] }` | `if rest, ok := strings.CutPrefix(s, p); ok { s = rest }` |
| `if strings.HasSuffix(s, sf) { s = s[:len(s)-len(sf)] }` | `if rest, ok := strings.CutSuffix(s, sf); ok { s = rest }` |

```go
// before
if strings.HasPrefix(s, "pre_") {
    s = s[len("pre_"):]
}
// after
if rest, ok := strings.CutPrefix(s, "pre_"); ok {
    s = rest
}
```

```go
// before
if strings.HasSuffix(s, ".txt") {
    s = s[:len(s)-len(".txt")]
}
// after
if rest, ok := strings.CutSuffix(s, ".txt"); ok {
    s = rest
}
```

### Go 1.20+ — `errors.Join`

| Before | After |
|---|---|
| `fmt.Errorf("...: %w: %w", err1, err2)` | `errors.Join(err1, err2)` |

```go
// before
return fmt.Errorf("load config: %w: %w", err1, err2)
// after
return errors.Join(fmt.Errorf("load config"), err1, err2)
```

### Go 1.20+ — `context.WithCancelCause`

| Before | After |
|---|---|
| `ctx, cancel := context.WithCancel(parent)` + bare `cancel()` | `ctx, cancel := context.WithCancelCause(parent)` + `cancel(err)` |

```go
// before
ctx, cancel := context.WithCancel(parent)
// ... somewhere ...
cancel()

// after
ctx, cancel := context.WithCancelCause(parent)
cancel(ErrShutdown)
// caller: context.Cause(ctx) → ErrShutdown
```
