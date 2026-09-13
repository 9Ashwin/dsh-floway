# Go 1.21 rules: `slices` and `maps`

Rule catalog for the `modern-go` skill: apply a rule only when `go.mod` declares the
version in its heading or newer. Covers the `slices` and `maps` packages: `Contains`, `Index`, `SortFunc`, `Max`/`Min`, `Reverse`, `Compact`, `Clip`, `Clone`, `Delete`/`Insert`, `Equal`, and `maps.Clone`/`Copy`/`DeleteFunc`.

### Go 1.21+ — `slices` package

| Before | After |
|---|---|
| Manual loop to find element | `slices.Contains(items, target)` |
| Loop returning index or -1 | `slices.Index(items, target)` |
| `sort.Slice(items, func(i,j int) bool { return items[i] < items[j] })` | `slices.SortFunc(items, cmp.Compare)` |
| Max/min finding loop | `slices.Max(items)` / `slices.Min(items)` |
| Reverse swap loop | `slices.Reverse(s)` |
| Remove consecutive duplicates loop | `slices.Compact(s)` |
| `s[:len(s):len(s)]` | `slices.Clip(s)` |
| `make([]T, len(src)); copy(dst, src)` | `slices.Clone(src)` |

```go
// before → after: slices.Contains(items, target)
found := false
for _, x := range items {
    if x == target {
        found = true
        break
    }
}
```

```go
// before → after: slices.Index(items, target)
for i, x := range items {
    if x == target {
        return i
    }
}
return -1
```

```go
// before → after: slices.SortFunc(items, cmp.Compare)
sort.Slice(items, func(i, j int) bool { return items[i] < items[j] })
```

```go
// before → after: slices.Max(items) / slices.Min(items)
max := items[0]
for _, v := range items[1:] {
    if v > max {
        max = v
    }
}
```

```go
// before → after: slices.Reverse(s)
for i, j := 0, len(s)-1; i < j; i, j = i+1, j-1 {
    s[i], s[j] = s[j], s[i]
}
```

```go
// before → after: slices.Compact(s)
i := 0
for j := 1; j < len(s); j++ {
    if s[j] != s[i] {
        i++
        s[i] = s[j]
    }
}
s = s[:i+1]
```

```go
// before → after: slices.Clip(s)
s = s[:len(s):len(s)]
```

```go
// before → after: slices.Clone(src)
dst := make([]T, len(src))
copy(dst, src)
```

Requires importing `"slices"` and `"cmp"` (for `SortFunc`).

### Go 1.21+ — `slices.Delete` / `slices.Insert`

| Before | After |
|---|---|
| `append(s[:i], s[i+1:]...)` | `slices.Delete(s, i, i+1)` |
| `append(s[:i:i], append([]T{x}, s[i:]...)...)` | `slices.Insert(s, i, x)` |

```go
// before — element removal (classic aliasing/leak footgun)
s = append(s[:i], s[i+1:]...)
// after
s = slices.Delete(s, i, i+1)
```

```go
// before — insert at index i
s = append(s[:i], append([]T{v}, s[i:]...)...)
// after
s = slices.Insert(s, i, v)
```

`slices.Delete` zeroes the tail elements to avoid retaining pointers (the manual `append` form leaks). Requires importing `"slices"`.

### Go 1.21+ — `slices.Equal` / `maps.Equal`

| Before | After |
|---|---|
| `reflect.DeepEqual(a, b)` for comparable slices | `slices.Equal(a, b)` |
| `reflect.DeepEqual(m1, m2)` for comparable maps | `maps.Equal(m1, m2)` |

```go
// before
if reflect.DeepEqual(got, want) { ... }   // got, want are []string
// after
if slices.Equal(got, want) { ... }
```

Faster and type-safe, with no reflection. Only for element types that are directly comparable (use `slices.EqualFunc` / `maps.EqualFunc` otherwise). Requires importing `"slices"` or `"maps"`.

### Go 1.21+ — `maps` package

| Before | After |
|---|---|
| Manual loop to copy a map | `maps.Clone(m)` |
| `for k, v := range src { dst[k] = v }` | `maps.Copy(dst, src)` |
| Loop + conditional delete | `maps.DeleteFunc(m, predicate)` |

```go
// before → after: maps.Clone(m)
dst := make(map[K]V)
for k, v := range src {
    dst[k] = v
}
```

```go
// before → after: maps.Copy(dst, src)
for k, v := range src {
    dst[k] = v
}
```

```go
// before → after: maps.DeleteFunc(m, func(k K, v V) bool { return v == 0 })
for k, v := range m {
    if v == 0 {
        delete(m, k)
    }
}
```

Requires importing `"maps"`.
