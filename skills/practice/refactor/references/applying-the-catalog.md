# Applying the Catalog

Common sequences for the larger refactorings, the design patterns they implement, and
per-language notes. Read this once the smell is named and you want a known order of steps or the
idioms of the language you are in.

## Common Refactoring Sequences

### Extract Method Sequence
1. Create a new method named after intent
2. Copy code fragment into new method
3. Identify local variables → parameters / return values
4. Call new method from original location
5. Test

### Replace Conditional with Polymorphism Sequence
1. Create subclasses for each variant
2. Create a factory method that returns the right subclass
3. Move the conditional body to the appropriate subclass method
4. Delete the conditional

### Extract Class Sequence
1. Identify a coherent subset of fields and methods
2. Create a new class
3. Create an instance from the old class
4. Move fields and methods one at a time
5. Update references in old class
6. Test after each move

### Inline Class Sequence
1. Identify all callers of the target class
2. Move all methods/fields to the absorbing class
3. Redirect all references to the absorbing class
4. Delete the empty class
5. Test

## Design Patterns in Refactoring

### Strategy Pattern
Replace a conditional that chooses an algorithm. **Smell:** Switch on type code with different behavior per branch. **Technique:** Replace Conditional with Polymorphism + Extract Method.

### Template Method
Extract common algorithm skeleton to superclass, letting subclasses fill in the variants. **Smell:** Duplicate code with slight variations. **Technique:** Form Template Method.

### State Pattern
Replace a state-based conditional by extracting each state's behavior into a class. **Smell:** Switch on status field with behavior variation. **Technique:** Replace Type Code with State/Strategy.

### Composite Pattern
Treat individual objects and groups uniformly. **Smell:** Client code has special handling for single vs. collection cases. **Technique:** Extract Interface + Create Composite.

### Decorator Pattern
Add behavior dynamically by wrapping objects. **Smell:** Conditional logic for optional behaviors. **Technique:** Extract Class + use composition.

### Null Object Pattern
Replace null checks with a default object. **Smell:** Repeated `if (x == null)` checks. **Technique:** Introduce Null Object.

## Language-Specific Guidance

### Java
- Prefer `final` for locals that shouldn't change
- Use IDE automated refactorings (Eclipse/IntelliJ) for mechanical steps
- Leverage the type system: enums, records (Java 14+), sealed classes (Java 17+)

### JavaScript/TypeScript
- Use destructuring to reduce parameter count
- Prefer `const` over `let` for immutable bindings
- Use TypeScript union types instead of type codes
- Nullish coalescing (`??`) and optional chaining (`?.`) eliminate null-check noise

### Python
- Use type hints for documenting intent during refactoring
- Use `dataclasses` to replace tuple/data-class patterns
- Use `@property` to replace getters
- Context managers for resource cleanup patterns

### Go
- Small interfaces preferred: accept interfaces, return structs
- Use named return values when they improve clarity
- Table-driven tests pair well with refactoring
- Avoid deep nesting with early returns

### Rust
- Use `Result` and `Option` instead of error codes and null
- Pattern matching replaces if-else chains
- `From` trait implementations clean up type conversions
- Derive macros reduce boilerplate
