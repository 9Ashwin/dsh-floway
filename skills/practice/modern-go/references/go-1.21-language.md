# Go 1.21 rules: language, `sync` and `context`

Rule catalog for the `modern-go` skill: apply a rule only when `go.mod` declares the
version in its heading or newer. Covers `min`/`max`, `clear`, `sync.OnceFunc`/`OnceValue`, `context.AfterFunc`, `context.WithTimeoutCause`.

### Go 1.21+ — `min` / `max`

| Before | After |
|---|---|
| `if a < b { v = a } else { v = b }` | `v = min(a, b)` |
| `if a > b { v = a } else { v = b }` | `v = max(a, b)` |
| `if x < lo { x = lo }; if x > hi { x = hi }` | `x = min(max(x, lo), hi)` |

```go
// before
lo := a
if b < lo {
    lo = b
}
// after
lo := min(a, b)
```

```go
// before
if x < 0 {
    x = 0
}
if x > 100 {
    x = 100
}
// after
x = min(max(x, 0), 100)
```

### Go 1.21+ — `clear`

| Before | After |
|---|---|
| `for k := range m { delete(m, k) }` | `clear(m)` |
| `for i := range s { s[i] = zero }` | `clear(s)` |

```go
// before
for k := range m {
    delete(m, k)
}
// after
clear(m)
```

```go
// before
for i := range s {
    s[i] = 0
}
// after
clear(s)
```

### Go 1.21+ — `sync.OnceFunc` / `sync.OnceValue`

| Before | After |
|---|---|
| `var once sync.Once; once.Do(func() { ... })` | `f := sync.OnceFunc(func() { ... }); f()` |
| `sync.Once` + stored result variable | `sync.OnceValue(func() T { return val })` |

```go
// before
var once sync.Once
func init() { once.Do(func() { setup() }) }

// after
var initOnce = sync.OnceFunc(func() { setup() })
```

```go
// before
var once sync.Once
var cfg *Config
func getConfig() *Config {
    once.Do(func() { cfg = loadConfig() })
    return cfg
}
// after
var getConfig = sync.OnceValue(func() *Config { return loadConfig() })
```

### Go 1.21+ — `context.AfterFunc`

| Before | After |
|---|---|
| `go func() { <-ctx.Done(); cleanup() }()` | `stop := context.AfterFunc(ctx, cleanup)` |

```go
// before
go func() {
    <-ctx.Done()
    conn.Close()
}()
// after
stop := context.AfterFunc(ctx, func() { conn.Close() })
```

### Go 1.21+ — `context.WithTimeoutCause` / `WithDeadlineCause`

| Before | After |
|---|---|
| `context.WithTimeout(parent, d)` | `context.WithTimeoutCause(parent, d, err)` |

```go
// before
ctx, cancel := context.WithTimeout(parent, 5*time.Second)
// after
ctx, cancel := context.WithTimeoutCause(parent, 5*time.Second, ErrTimeout)
```

Only apply when a meaningful cause error is available.
