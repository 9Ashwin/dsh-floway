# Code-Level & Testing Smells

Defects that live inside a file or a test suite, with the remedy for each. Read this when investigating a code-quality or testing smell.

### Code-Level Smells

#### Long Method
- Methods > 50 lines (or whatever suits the language)
- Deep nesting > 3 levels
- Multiple levels of abstraction mixed
- **Remedy:** Extract methods at same abstraction level, compose

#### Long Parameter List
- Methods with > 4 parameters
- Boolean flags controlling behavior
- **Remedy:** Introduce parameter object, split method, remove flag arguments

#### Duplicated Code
- Identical or near-identical logic in 3+ places
- Copy-paste with slight variations
- **Remedy:** Extract shared method, apply Template Method or Strategy pattern

#### Primitive Obsession
Using primitives instead of domain types:
- `string` for Email, PhoneNumber, URL
- `int` for Money, Age, Quantity
- `decimal` without Currency context
- **Remedy:** Create value objects with validation and behavior

#### Magic Numbers/Strings
- Hardcoded literals without explanation
- `if (status == 3)` instead of `if (status == Status.COMPLETED)`
- **Remedy:** Extract named constants or enums

#### Comments as Deodorant
- Comments that explain what code does (code should be self-documenting)
- Commented-out code blocks
- "TODO" comments accumulating without resolution
- **Remedy:** Refactor to make code clear, delete dead code, track TODOs as issues

#### Deep Nesting (Arrow Anti-Pattern)
Loops and conditionals nested so deeply the code drifts rightward into an "arrow" shape:
- `if { if { for { if { ... } } } }` — hard to trace which conditions hold at any point
- Usually > 3 levels of indentation in one function
- **Remedy:** Guard clauses / early returns, extract nested blocks into methods, invert conditions, replace conditional with polymorphism

#### Dead Code
- Unused imports, variables, functions
- Unreachable branches
- Commented-out code in version control
- **Remedy:** Delete it (git history preserves it if needed)

#### Data Class
A class that is only fields plus getters/setters, with no meaningful behavior:
- A "data bag" other classes reach into and manipulate from outside
- Closely related to Anemic Domain Model at the class level
- **Remedy:** Move the behavior that operates on the data into the class ("Tell, Don't Ask")

#### Lazy Class
A class/module that no longer does enough to justify its existence:
- Left over after refactoring, or an abstraction that never grew
- **Remedy:** Inline it into its caller or collapse the hierarchy

#### Speculative Generality
Abstractions, hooks, parameters, or generics added for hypothetical future needs:
- Unused abstract base classes, unused parameters, "just in case" configuration
- Violates YAGNI
- **Remedy:** Remove unused abstraction; add it when a real second use case appears

#### Temporary Field
An instance field that is only set/used in certain circumstances and empty otherwise:
- Fields populated only during one algorithm, confusing readers the rest of the time
- **Remedy:** Extract the field + the methods that use it into their own class (Extract Class / introduce a Method Object)

### Testing Smells

#### No Tests
- Modules with zero test coverage
- Business logic without unit tests
- **Remedy:** Write characterization tests first, then add behavior tests

#### Test-Implementation Coupling
- Tests asserting internal method calls, private state, or implementation details
- Tests breaking on refactoring without behavior changes
- **Remedy:** Test through public APIs, assert behavior not implementation

#### Test Environment Dependency
- Tests depending on file system, network, database, system clock without mocking
- Non-deterministic tests (flaky tests)
- **Remedy:** Use test doubles, control environment, use DI
