# Architecture Anti-Patterns

Architecture-level smells, their symptoms, and their remedies. Read this when a finding is at the architecture or layering level rather than inside a single class or function.

### Architectural Anti-Patterns

#### Big Ball of Mud
The most common de-facto architecture. A haphazardly structured, sprawling system with no perceivable architecture. Characterized by:
- Promiscuous sharing of information between distant elements
- Global or duplicated important state
- Structure eroded beyond recognition or never defined
- Repeated expedient repair ("duct tape and bailing wire")
- Forces: Time pressure, cost, inexperience, complexity, change, scale
- **Remedy:** Define architecture boundaries, refactor incrementally, apply SHEARING LAYERS, KEEP IT WORKING

#### Distributed Monolith
Microservices that must be deployed together. Symptoms:
- Services share a database
- Synchronous chains of service calls
- Changes require coordinated deployments
- **Remedy:** Decouple data stores, introduce async messaging, enforce bounded contexts

#### Anemic Domain Model
Domain objects with only getters/setters (data bags), all logic in services. Violates:
- "Tell, Don't Ask" principle
- Rich Domain Model pattern from DDD
- **Remedy:** Move behavior into domain objects, use domain services only for cross-aggregate operations

#### God Object
A class that knows too much or does too much. Characteristics:
- > 500 lines or > 20 public methods
- Handles unrelated concerns
- Difficult to test in isolation
- Single Responsibility Principle violation
- **Remedy:** Extract cohesive groups of methods into dedicated classes

#### Leaky Abstractions
Abstractions that expose implementation details. Signs:
- Interface methods named after implementation (e.g., `SaveToPostgres`, `FetchFromRedis`)
- Consumers catching implementation-specific exceptions
- Configuration details exposed through abstractions
- **Remedy:** Design interfaces from the consumer's perspective, hide implementation details

#### Static Cling
Excessive use of static methods/state. Problems:
- Untestable (can't mock static calls)
- Hidden dependencies
- Thread-safety issues with static state
- **Remedy:** Use dependency injection, convert stateless statics to instance methods

#### Service Locator Abuse
Using a service locator instead of dependency injection. Issues:
- Hidden dependencies (dependencies not visible in constructor)
- Runtime errors instead of compile-time errors
- Testing difficulty
- **Remedy:** Use constructor injection, register dependencies at composition root

#### Violated Layer Boundaries (Clean/Onion/Hexagonal Architecture)
In layered architectures:
- **Clean Architecture:** Outer layers (frameworks) leaking into inner layers (use cases, entities)
- **Onion Architecture:** Infrastructure concerns in domain core
- **Hexagonal Architecture:** Business logic coupled to specific adapters instead of ports
- **Remedy:** Apply dependency inversion, define clear port interfaces

#### CQRS Overuse
Applying CQRS to simple CRUD. Signs:
- Separate read/write models for trivial data access
- Event sourcing when events don't add business value
- Unnecessary complexity
- **Remedy:** Use CQRS only when read/write models genuinely differ or have different scaling needs

#### Vertical Slice Contamination
In Vertical Slice Architecture:
- Cross-slice coupling (one feature directly calling another)
- Shared service classes undermining slice independence
- **Remedy:** Use events/messages for cross-slice communication, duplicate simple logic if needed

### Top Ten Software Architecture Mistakes

A set of architecture-level anti-patterns describing over- and under-engineering. The common thread: **architecture disconnected from real needs and reality.** The opposite extreme (too little architecture) is equally a smell.

#### Over-Layered / Multitier Architecture
"Layers on layers on layers." Adding tiers beyond what the problem needs:
- Each layer just forwards calls to the next with no transformation or value
- Simple read requires touching 6+ classes across 4 layers
- **Remedy:** Collapse pass-through layers; keep only layers that carry real responsibility

#### Over-Abstraction
Abstraction piled on until the code is impossible to follow:
- Excessive interfaces, generics, factories, and indirection for single implementations
- You can't tell what actually runs without stepping through many hops
- **Remedy:** Inline single-implementation abstractions; abstract only at real variation points (rule of three)

#### Futuristic Architecture
Solution built for imagined future requirements that no one can actually predict:
- Extensibility points, plugin systems, config knobs nothing uses
- Most speculative flexibility is wasted effort — closely related to Speculative Generality and YAGNI
- **Remedy:** Build for today's known requirements; add flexibility when a real second case arrives

#### Technology-Enthusiast Architecture
New/shiny technology put into production because the architect liked it:
- Unproven tech adopted without validating it fits the problem or scales
- Chasing trends over stability
- **Remedy:** Evaluate tech against actual requirements; prefer proven tools; prototype before committing

#### Overkill Architecture
A simple problem solved with a disproportionate amount of architecture and technology:
- Microservices, event sourcing, k8s for a CRUD app with a handful of users
- **Remedy:** Match architecture weight to problem size (KISS); start simple, evolve when justified

#### Cloud / Visio Architecture
"Architecture" that exists only in nice diagrams, disconnected from the code and runtime reality:
- Diagrams don't match what's actually deployed; boxes and arrows with no code correspondence
- **Remedy:** Keep architecture docs grounded in and verified against the real system

> **Note on the opposite extreme:** total *lack* of architecture (no boundaries, no structure) is equally a smell — see [Big Ball of Mud](#big-ball-of-mud) and Missing Architecture. Both under- and over-engineering are failures.
