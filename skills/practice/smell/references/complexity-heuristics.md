# Algorithmic Complexity Heuristics

The complexity/performance catalog with detection, impact, remedy, and correctness checks for each pattern, plus the Measure First workflow and the list of cases not to flag. Read this before reporting any performance or complexity finding.

### Complexity Smells (Algorithmic Anti-Patterns)

A static complexity pattern is a candidate, not proof of a bottleneck. Apply **Measure First**:

1. Establish actual input size, call frequency, I/O latency, and whether the path is hot.
2. Prefer a profiler, representative benchmark, query log, trace, or explicit operation count.
3. Promote the candidate to a finding only when the workload and impact justify it.
4. Re-measure the same workload after a fix; without a baseline, do not claim a performance improvement.

For every complexity candidate, state **what to measure**, **when it becomes a finding**, and **when not to flag it**. Keep the Big-O analysis and correctness checks below, but do not infer severity from syntax alone.

#### Nested Loops (O(n^2) and Worse)
Two or more loops nested inside each other, producing polynomial complexity.
- **Detection:** `for`/`while` inside another `for`/`while`; `forEach`/`map` inside `forEach`/`map`; loop containing another loop (any depth)
- **Impact:** O(n^2) for double-nested, O(n^3) for triple; explodes with moderate data sizes
- **Remedy:**
  - Build a Map/Set index for the inner collection → O(n+m)
  - Sort + two-pointer approach → O(n log n)
  - Group/bucket data before iterating
  - Sweep-line for interval/range problems
- **Correctness checks:** Does order matter? Are there duplicate keys? Is the original picking first/last/all matches?

#### N+1 Query Pattern
A database query, API call, or I/O operation inside a loop body.
- **Detection:** `fetch()`/`axios()`/`query()`/`execute()`/`findMany()`/`findOne()`/`findUnique()`/`select()`/`where()` inside any loop construct
- **Impact:** 1 + N round-trips instead of 1; network latency multiplied by item count
- **Remedy:**
  - Batch fetch by IDs: `SELECT * FROM x WHERE id IN (...)` then join in memory
  - Use ORM eager-loading / `include` / `preload` / DataLoader
  - Bulk API endpoints accepting arrays
  - Preserve: auth filters, tenancy isolation, ordering, pagination, error semantics
- **Correctness checks:** Don't fetch records the original per-item logic wouldn't authorize; preserve missing-record behavior

#### Repeated Linear Scan (Missing Index)
Linear search (`includes`, `indexOf`, `.find`, `in_array`) inside a loop, where a Set/Map would give O(1) lookup.
- **Detection:** `.includes()` / `.indexOf()` / `.find()` / `.findIndex()` / `in_array()` / `contains()` inside a loop body
- **Impact:** O(n*m) instead of O(n+m) — each iteration scans the entire collection
- **Remedy:** Build a `Set` (for membership) or `Map` (for key→value lookup) once before the loop
- **Correctness checks:** Does equality semantics change after Set conversion? JavaScript object identity vs. value equality; Python hashability

#### Sort-in-Loop
Sorting inside a loop body, repeating O(n log n) work unnecessarily.
- **Detection:** `.sort()` / `sorted()` / `sort()` inside any iterative block
- **Impact:** O(k * n log n) instead of O(n log n) — sort repeated k times
- **Remedy:**
  - Sort once outside the loop
  - Maintain a heap (PriorityQueue) if incremental top-K is needed
  - Use binary search/insertion into sorted collection
- **Correctness checks:** Is each intermediate sorted state externally observable? Does comparator depend on loop-local state?

#### Render-Path Recompute (UI Complexity)
Expensive data transformation (filter→map→sort chains) inside UI component render bodies, recomputed on every render.
- **Detection:** `.filter().map().sort().reduce()` chains inside React/Vue/Svelte component function bodies; inside `function Component()` or `const Component = () =>` in JSX/TSX
- **Impact:** Re-derivation on every state change even if inputs unchanged; jank with large collections
- **Remedy:**
  - `useMemo` / `computed` / `derived` with correct dependency arrays
  - Move derivation to selectors, loaders, or server-side
  - Virtualize long lists (windowing)
  - Stabilize callbacks and object props only when child renders are affected
- **Correctness checks:** Dependency arrays must include every semantic input; memoization must not hide mutations of mutable inputs

#### Pairwise Comparison
Comparing every element with every other element using double-nested iteration.
- **Detection:** Two nested loops iterating the same or similar collections, comparing pairs
- **Impact:** O(n^2) for pair matching, overlap detection, conflict checking, nearest-neighbor
- **Remedy:**
  - Sort + two-pointer for pair/range matching
  - Sweep-line for interval overlaps
  - Spatial hashing or grid bucketing for proximity
  - Union-find for connectivity
- **Correctness checks:** Order stability; tie-breaking in equality cases

#### Unnecessary Recompute (Missing Memoization)
Same pure computation repeated with same inputs without caching.
- **Detection:** Identical function calls with same arguments in hot paths; repeated expensive transforms; recursive calls without memoization
- **Impact:** Linear/polynomial wasted work; especially bad with recursive Fibonacci-style patterns (O(2^n) → O(n) with memo)
- **Remedy:** Add memoization/caching with proper invalidation; use `lru_cache`/`memoize`/`useMemo` as appropriate

#### Wrong Data Structure
Using a suboptimal data structure for the access pattern.
- **Detection:**
  - Array/List used for frequent membership tests → should be Set
  - Array/List used for key-value lookups → should be Map/Object
  - Array used as queue with `shift()`/`pop(0)` (O(n) per dequeue) → should use proper Queue
  - Sorted insertion into array (O(n) per insert) → should use Heap
- **Remedy:** Replace with the data structure whose complexity matches the access pattern:
  - Set → O(1) has/add/delete
  - Map → O(1) get/set
  - Heap → O(log n) push/pop for priority
  - Queue/Deque → O(1) enqueue/dequeue

#### What NOT to Flag
- **Cold paths:** Complexity that only runs on startup, config loading, or tiny N (< 100) is rarely worth fixing
- **Intentional tradeoffs:** Clear, readable O(n) code where O(n log n) would add complexity with no measurable gain
- **Already optimized:** Map/Set already in use; batch loading already implemented; memoization already present
