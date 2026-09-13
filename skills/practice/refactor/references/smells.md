# Code Smells Catalog

Based on Fowler's taxonomy. Before refactoring, identify which smell is present. Each row names
a surface symptom, what it usually indicates, and the primary refactoring that addresses it; the
five families group related symptoms. Read the family that matches what you are seeing — if two
rows fit, name the one root cause you have evidence for and treat the other as an explanatory
label only.

Numeric thresholds in this skill—line counts, parameter counts, method counts, and nesting depth—are **context-dependent candidate indicators**. Confirm mixed responsibilities, cognitive cost, repeated change, duplicated knowledge, or measured runtime impact before acting.

The five families: **bloaters** (things that have grown too big), **object-orientation abusers** (misused OO mechanisms), **change preventers** (structure that makes one change ripple), **dispensables** (things that could be removed), and **couplers** (classes that know too much about each other).

### Bloaters

| Smell | Description | Primary Refactoring |
|-------|-------------|-------------------|
| **Long Method** | Candidate: method > 10-15 lines; confirm mixed responsibilities or cognitive cost | Extract Method, Replace Temp with Query |
| **Large Class** | Candidate: many fields/methods; confirm independent reasons to change | Extract Class, Extract Subclass |
| **Primitive Obsession** | Using primitives instead of small objects | Replace Data Value with Object, Replace Type Code with Class |
| **Long Parameter List** | Candidate: > 3-4 parameters; confirm a missing concept or recurring data clump | Introduce Parameter Object, Preserve Whole Object |
| **Data Clumps** | Same group of data appearing together | Extract Class, Introduce Parameter Object |

### Object-Orientation Abusers

| Smell | Description | Primary Refactoring |
|-------|-------------|-------------------|
| **Switch Statements** | Repeated switch/if-else on type codes | Replace Conditional with Polymorphism, Replace Type Code with Subclasses |
| **Temporary Field** | Field only set in certain circumstances | Extract Class, Introduce Null Object |
| **Refused Bequest** | Subclass doesn't use inherited members | Replace Inheritance with Delegation, Push Down Method/Field |
| **Alternative Classes with Different Interfaces** | Classes doing similar things with different names | Rename Method, Move Method, Extract Superclass |

### Change Preventers

| Smell | Description | Primary Refactoring |
|-------|-------------|-------------------|
| **Divergent Change** | One class changed for different reasons | Extract Class |
| **Shotgun Surgery** | One change requires many small changes across classes | Move Method, Move Field, Inline Class |
| **Parallel Inheritance Hierarchies** | Adding a subclass to one hierarchy forces adding to another | Move Method, Move Field |

### Dispensables

| Smell | Description | Primary Refactoring |
|-------|-------------|-------------------|
| **Comments** | Comments explaining what code does (not why) | Extract Method, Rename Variable, Introduce Assertion |
| **Duplicate Code** | Same code structure in multiple places | Extract Method, Pull Up Method, Form Template Method |
| **Lazy Class** | Class doing too little to justify existence | Inline Class, Collapse Hierarchy |
| **Data Class** | Class with only fields and getters/setters | Move Method, Encapsulate Field, Encapsulate Collection |
| **Dead Code** | Unused code, imports, commented-out blocks | Delete it (git history has it) |
| **Speculative Generality** | Code built for "someday" that never came | Inline Class, Collapse Hierarchy, Remove Parameter |

### Couplers

| Smell | Description | Primary Refactoring |
|-------|-------------|-------------------|
| **Feature Envy** | Method uses another class's data more than its own | Move Method, Extract Method + Move Method |
| **Inappropriate Intimacy** | Classes know too much about each other's internals | Move Method, Move Field, Replace Delegation with Hidden Delegate |
| **Message Chains** | `a.getB().getC().getD().doSomething()` | Hide Delegate, Extract Method |
| **Middle Man** | Class delegates everything to another class | Remove Middle Man, Inline Method |
| **Incomplete Library Class** | Library missing methods you need | Introduce Foreign Method, Introduce Local Extension |
