# Go 1.24 rules

Rule catalog for the `modern-go` skill: apply a rule only when `go.mod` declares the
version in its heading or newer. Covers `t.Context()`, `strings.Lines`/`bytes.Lines`, `os.Root`, `omitzero`, `b.Loop()`.

### Go 1.24+ — `t.Context()` in tests

| Before | After |
|---|---|
| `ctx, cancel := context.WithCancel(context.Background()); defer cancel()` | `ctx := t.Context()` |

```go
// before
func TestFetch(t *testing.T) {
    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()
    result := fetch(ctx)
}
// after
func TestFetch(t *testing.T) {
    result := fetch(t.Context())
}
```

### Go 1.24+ — `strings.Lines` / `bytes.Lines`

| Before | After |
|---|---|
| `bufio.Scanner` line loop over a string/buffer | `for line := range strings.Lines(s)` |

```go
// before
sc := bufio.NewScanner(strings.NewReader(s))
for sc.Scan() {
    process(sc.Text())
}
// after
for line := range strings.Lines(s) {
    process(strings.TrimSuffix(line, "\n"))
}
```

`strings.Lines` / `bytes.Lines` (Go 1.24) return line iterators — no Scanner setup, no default 64KB token-size limit. Note the yielded line **retains its trailing `\n`**, unlike `Scanner.Text()`; trim it if the old code relied on stripped lines. Only apply for in-memory strings/buffers, not streaming `io.Reader`s.

### Go 1.24+ — `os.Root` (directory-scoped filesystem access)

| Before | After |
|---|---|
| manual `filepath.Clean` + prefix check to block traversal | `root, _ := os.OpenRoot(dir); root.Open(name)` |

```go
// before — hand-rolled path-traversal guard
p := filepath.Join(base, name)
if !strings.HasPrefix(filepath.Clean(p), filepath.Clean(base)+string(os.PathSeparator)) {
    return errUnsafePath
}
f, err := os.Open(p)
// after — the OS enforces the boundary
root, err := os.OpenRoot(base)
if err != nil { return err }
defer root.Close()
f, err := root.Open(name) // symlinks/".." escaping base are rejected
```

`os.Root` (Go 1.24) confines all operations to a directory tree, rejecting `..` and symlink escapes at the syscall layer — far more robust than string prefix checks. **Security hardening:** flag as a strong suggestion wherever user-controlled paths are joined to a base directory.

### Go 1.24+ — `omitzero` struct tag

| Before | After |
|---|---|
| `json:"field,omitempty"` (for `time.Time`, `time.Duration`, structs, slices, maps) | `json:"field,omitzero"` |

```go
// before
type Config struct {
    Timeout time.Duration `json:"timeout,omitempty"`
    Labels  []string      `json:"labels,omitempty"`
}
// after
type Config struct {
    Timeout time.Duration `json:"timeout,omitzero"`
    Labels  []string      `json:"labels,omitzero"`
}
```

Only for types where `omitempty` fails: `time.Time`, `time.Duration`, structs, slices, maps. Flag as suggestion, not auto-apply.

### Go 1.24+ — `b.Loop()` in benchmarks

| Before | After |
|---|---|
| `for i := 0; i < b.N; i++ { ... }` | `for b.Loop() { ... }` |

```go
// before
func BenchmarkHash(b *testing.B) {
    for i := 0; i < b.N; i++ {
        hash(input)
    }
}
// after
func BenchmarkHash(b *testing.B) {
    for b.Loop() {
        hash(input)
    }
}
```
