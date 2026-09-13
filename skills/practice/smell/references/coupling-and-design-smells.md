# Coupling, Cohesion & Object-Orientation Smells

Design-level smells that concern how modules, classes, and hierarchies depend on one another. Read this when investigating coupling, cohesion, inheritance, or interface design.

### Coupling & Cohesion Smells

#### Circular Dependencies
Module A → Module B → Module A. Detected via:
- Import graph analysis
- "Cannot access before initialization" errors
- **Remedy:** Extract shared interface/common module, apply dependency inversion

#### Content Coupling
One module directly modifying another's internal state. Signs:
- Direct field access across module boundaries
- `friend`/package-private abuse
- **Remedy:** Use public APIs, encapsulate internal state

#### Common Coupling (Global State)
Multiple modules depending on shared global mutable state:
- Global variables, singletons with mutable state
- Ambient context (e.g., `CurrentUser` static property)
- **Remedy:** Parameterize, use dependency injection, make state explicit

#### Stamp Coupling
Passing entire data structures when only a few fields needed:
- Functions receiving large DTOs but using one field
- **Remedy:** Create focused parameters or smaller interfaces (ISP)

#### Shotgun Surgery
A single change requires modifications across many files:
- Adding a field touches 5+ files in different modules
- **Remedy:** Consolidate related behavior, apply Single Responsibility

#### Feature Envy
A method that uses another class's methods more than its own:
- Method calls `other.foo()`, `other.bar()`, `other.baz()` with few self-calls
- **Remedy:** Move the method to the class it envies

#### Data Clumps
Same group of fields appearing together in multiple places:
- `(street, city, zip)` appearing in 5 method signatures
- **Remedy:** Extract into a value object

#### Divergent Change
One module/class is repeatedly changed for many *unrelated* reasons (the opposite of Shotgun Surgery):
- "I always change these three methods for DB changes, and those two for UI changes" in the same class
- **Remedy:** Split the class along its axes of change (Single Responsibility)

#### Inappropriate Intimacy
Two classes are too entangled with each other's internals:
- Reaching into another class's private fields, tight bidirectional references
- **Remedy:** Move methods/fields to the class they belong to, extract a shared class, or replace with delegation

#### Message Chains
Long navigation chains like `a.getB().getC().getD().doThing()`:
- Client coupled to the whole object graph; violates the Law of Demeter
- **Remedy:** Hide delegation — add a method on the first object that returns what the client needs

#### Middle Man
A class that delegates almost all of its work to another class:
- Most methods just forward calls; adds indirection without value
- **Remedy:** Remove the middle man and let clients talk to the real object (inline the delegation)

#### Parallel Inheritance Hierarchies
Every time you add a subclass to one hierarchy, you must add one to another:
- `Shape`/`ShapeRenderer`, `Employee`/`EmployeePermission` growing in lockstep
- **Remedy:** Merge hierarchies or make one hierarchy reference the other instead of mirroring it

#### Object-Orientation Abusers (from Fowler / refactoring.guru)

##### Switch Statements (Type-Code Conditionals)
Repeated `switch`/if-else chains that branch on a type code or enum:
- The same conditional structure duplicated in several places
- Adding a new type forces editing every switch (OCP violation)
- **Remedy:** Replace conditional with polymorphism (Strategy/State), or Replace Type Code with Subclasses

##### Refused Bequest
A subclass inherits methods/fields it doesn't need:
- Overrides inherited methods to throw, no-op, or do something unrelated
- Signals the inheritance relationship is wrong
- **Remedy:** Push down unused members, or replace inheritance with delegation

##### Alternative Classes with Different Interfaces
Two classes perform the same role but expose differently-named methods:
- `sort()` vs `arrange()`, `getUser()` vs `fetchUser()` for interchangeable classes
- **Remedy:** Unify the interface (rename methods, extract a common superclass/interface)

##### Incomplete Library Class
A third-party/library class lacks methods you need and can't be modified:
- Scattered helper functions or copy-paste wrappers around the library
- **Remedy:** Introduce a Foreign Method or wrap it in an adapter/local extension class

> Other refactoring.guru smells are documented in their thematic sections above:
> **Divergent Change**, **Data Class**, **Lazy Class**, **Speculative Generality**,
> **Temporary Field**, **Parallel Inheritance Hierarchies**, **Inappropriate Intimacy**,
> **Message Chains**, and **Middle Man**.
