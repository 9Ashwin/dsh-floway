# Anti-Pattern & Smell Detection Catalog

The complete lookup table of smell candidates and their static detection heuristics. Nothing in it is a finding on its own: a line-count, nesting, naming, or Big-O match must be validated against the code's responsibility, callers, change history, workload, and intentional constraints before it is reported, and severity never follows from a threshold alone.

Read the row for a specific smell when investigating it. The validating workflow is in `SKILL.md`; the prose definitions behind each smell are in the other reference files.

| Category | Smell | Detection Heuristic |
|----------|-------|-------------------|
| **Architecture** | Big Ball of Mud | No clear directory structure; everything in root or one flat folder; no separation of concerns |
| **Architecture** | Violated Layer Boundaries | Inner layers importing outer layers; infrastructure code in domain/core layer |
| **Architecture** | Missing Architecture | No `src/`, `lib/`, `core/` separation; SQL inline with UI code; HTTP handlers mixed with business logic |
| **Architecture** | Distributed Monolith | Microservices sharing a database; services that can't deploy independently |
| **Architecture** | Anemic Domain Model | Model/entity classes with only getters/setters and no behavior; all logic in services |
| **Architecture** | CQRS Without Need | Separate read/write models for simple CRUD; unnecessary complexity |
| **Architecture** | Over-Layered Architecture | Excessive layers/tiers that add pass-through code with no real value |
| **Architecture** | Over-Abstraction | So many indirections/interfaces/generics that you get lost following the code |
| **Architecture** | Futuristic Architecture | Speculative flexibility for requirements that may never come (predicting the future) |
| **Architecture** | Technology-Enthusiast Architecture | Shiny/unproven tech adopted in production because it's new, not because it fits |
| **Architecture** | Overkill Architecture | Heavyweight architecture/tech thrown at a simple problem |
| **Architecture** | Cloud/Visio Architecture | Diagrams disconnected from the actual code and runtime reality |
| **Coupling** | Circular Dependencies | Module A imports B, B imports A; detected via import graph analysis |
| **Coupling** | Content Coupling | One module directly accesses another's internal/private members |
| **Coupling** | Common Coupling | Excessive global variables/shared mutable state; singleton abuse |
| **Coupling** | Stamp Coupling | Passing large data structures when only a few fields are needed |
| **Cohesion** | God Object | Single class/module > 500 lines; > 20 public methods; handles unrelated concerns |
| **Cohesion** | Shotgun Surgery | A single change requires touching 5+ files across unrelated modules |
| **Cohesion** | Feature Envy | Method calls foreign class methods more than its own class methods |
| **Cohesion** | Data Clumps | Same group of 3+ parameters appearing together in multiple method signatures |
| **Design** | Leaky Abstractions | Implementation details (DB queries, HTTP calls) exposed through interfaces |
| **Design** | Static Cling | Excessive use of static methods; static state that prevents testability |
| **Design** | Service Locator Abuse | DI container passed around instead of proper constructor injection |
| **Design** | Violated SOLID | SRP violations, OCP violations (switch/if-else chains on types), ISP violations (fat interfaces) |
| **Design** | Switch Statements | Same `switch`/if-else chain on a type code appearing in multiple places; should be polymorphism |
| **Design** | Refused Bequest | Subclass inherits methods/fields it doesn't use or overrides them to throw/no-op |
| **Design** | Alternative Classes w/ Different Interfaces | Two classes do the same thing but have differently-named methods |
| **Design** | Parallel Inheritance Hierarchies | Creating a subclass in one hierarchy forces a matching subclass in another |
| **Design** | Speculative Generality | Unused abstract classes, hooks, params, or generics "for future needs" (YAGNI) |
| **Design** | Incomplete Library Class | Wrapping/patching a third-party class because it lacks needed methods |
| **Cohesion** | Divergent Change | One module changed for many unrelated reasons (opposite of Shotgun Surgery) |
| **Cohesion** | Data Class | Class with only fields + getters/setters, no behavior (anemic data bag) |
| **Cohesion** | Lazy Class | Class/module that does too little to justify its existence |
| **Coupling** | Inappropriate Intimacy | Two classes access each other's private/internal parts too much |
| **Coupling** | Message Chains | Long call chains `a.getB().getC().getD()` (Law of Demeter violation) |
| **Coupling** | Middle Man | Class that only delegates every call to another class |
| **Code** | Temporary Field | Instance field set/used only in certain circumstances, empty otherwise |
| **Code** | Duplicated Code | Identical/similar logic appearing in 3+ places; copy-paste patterns |
| **Code** | Long Method | Methods > 50 lines; deep nesting (> 3 levels) |
| **Code** | Long Parameter List | Methods with > 4 parameters |
| **Code** | Primitive Obsession | Using strings/ints instead of domain types (e.g., `string email` instead of `Email` type) |
| **Code** | Magic Numbers/Strings | Hardcoded literals without named constants |
| **Code** | Comments as Deodorant | Excessive comments explaining bad code instead of refactoring |
| **Code** | Dead Code | Unused imports, unreachable code, commented-out blocks |
| **Testing** | No Tests | Modules with zero test coverage |
| **Testing** | Test-Implementation Coupling | Tests that assert internal implementation details instead of behavior |
| **Testing** | Slow Tests | Tests doing real I/O, database calls, network requests without mocking |
| **Naming** | Vague Names | `Manager`, `Handler`, `Processor`, `Helper`, `Util`, `Service`, `Data`, `Info` used excessively without context |
| **Naming** | Inconsistent Naming | Snake_case and camelCase mixed; different patterns for same concept |
| **Readability** | Deep Nesting (Arrow Anti-Pattern) | Loops/conditionals nested > 3 levels deep; rightward-drifting "arrow" shape hard to trace |
| **Complexity** | Nested Loops (O(n^2)+) | Loop inside loop; forEach inside for; map inside map; nested iteration suggesting polynomial complexity |
| **Complexity** | Repeated Linear Scan | `includes()`/`indexOf()`/`.find()` inside a loop; O(n*m) membership check on list instead of Set/Map |
| **Complexity** | Sort-in-Loop | `.sort()` or `sorted()` called inside iterative code; repeated O(n log n) when sort-once suffices |
| **Complexity** | N+1 Query Pattern | Database/API/HTTP call inside a loop; `fetch`/`query`/`execute`/`findMany` per iteration instead of batch |
| **Complexity** | Render-Path Recompute | `.filter().map().sort()` chains in component render body; expensive transforms without memoization |
| **Complexity** | Pairwise Comparison | Nested iteration comparing every element with every other; O(n^2) when sort+two-pointer would be O(n log n) |
| **Complexity** | Unnecessary Recompute | Same expensive computation repeated without caching; missing `useMemo`/`memo`/lazy eval |
| **Complexity** | Wrong Data Structure | Array used where Set/Map would give O(1) lookup; List where Queue/Heap/Stack is natural fit |
