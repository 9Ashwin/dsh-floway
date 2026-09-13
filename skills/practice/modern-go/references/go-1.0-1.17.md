# Go 1.0–1.17 rules

Rule catalog for the `modern-go` skill: apply a rule only when `go.mod` declares the
version in its heading or newer. Covers `time.Since`, `time.Until`, loop `strings.Builder`, `errors.Is`, `//go:build` cleanup, `unsafe.Add`/`unsafe.Slice`.

### Go 1.0+ — `time.Since`

| Before | After |
|---|---|
| `time.Now().Sub(start)` | `time.Since(start)` |

```go
// before
elapsed := time.Now().Sub(start)
// after
elapsed := time.Since(start)
```

### Go 1.8+ — `time.Until`

| Before | After |
|---|---|
| `deadline.Sub(time.Now())` | `time.Until(deadline)` |

```go
// before
remaining := deadline.Sub(time.Now())
// after
remaining := time.Until(deadline)
```

### Go 1.10+ — `strings.Builder` (loop concatenation)

| Before | After |
|---|---|
| `s += item` in a loop | `var b strings.Builder; b.WriteString(item)` |

```go
// before
s := ""
for _, item := range items {
    s += item
}
// after
var b strings.Builder
for _, item := range items {
    b.WriteString(item)
}
s := b.String()
```

Only when `+=` concatenation happens inside a loop.

### Go 1.13+ — `errors.Is`

| Before | After |
|---|---|
| `err == io.EOF` | `errors.Is(err, io.EOF)` |

```go
// before
if err == io.EOF {
    return
}
// after
if errors.Is(err, io.EOF) {
    return
}
```

### Go 1.17+ — `//go:build` constraints (plusbuild)

| Before | After |
|---|---|
| `// +build linux` + `//go:build linux` (both present) | keep only `//go:build linux` |

```go
// before
//go:build linux && amd64
// +build linux,amd64

package foo
// after
//go:build linux && amd64

package foo
```

The `plusbuild` modernizer removes obsolete `// +build` constraint lines once the equivalent `//go:build` line is present (the `//go:build` syntax landed in Go 1.17). Only strip the old line when a matching `//go:build` already exists — never drop the sole constraint.

### Go 1.17+ — `unsafe.Add` / `unsafe.Slice` (unsafefuncs)

| Before | After |
|---|---|
| `unsafe.Pointer(uintptr(ptr) + uintptr(n))` | `unsafe.Add(ptr, n)` |
| `(*[n]T)(unsafe.Pointer(p))[:]` slice construction | `unsafe.Slice(p, n)` |

```go
// before — pointer arithmetic via uintptr
p2 := unsafe.Pointer(uintptr(ptr) + uintptr(offset))
// after
p2 := unsafe.Add(ptr, offset)
```

```go
// before — building a slice from a base pointer
s := (*[1 << 30]byte)(unsafe.Pointer(p))[:n:n]
// after
s := unsafe.Slice(p, n)
```

The `unsafefuncs` modernizer (gopls v0.22.0) rewrites error-prone `uintptr` pointer math into `unsafe.Add` / `unsafe.Slice`, which the compiler and `go vet` understand as GC-safe.
