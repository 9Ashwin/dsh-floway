# Deep Scan Checklist

### 2.1 Project Identity
- `package.json`, `go.mod`, `Cargo.toml`, `pyproject.toml`, `pom.xml`, etc.
- README, LICENSE
- Git history (first commit date, recent activity, contributor count)

### 2.2 Architecture
- Directory structure and organization pattern (monorepo, layered, hexagonal, etc.)
- Entry points (main files, CLI commands, server bootstrap)
- Module boundaries and dependency graph (internal)

### 2.3 Tech Stack
- Language(s) and version constraints
- Frameworks and major libraries
- Build tools and bundlers
- Runtime requirements (Node version, Docker, etc.)

### 2.4 Features & Behavior
- Route definitions / CLI commands / exported functions
- Business logic modules and their responsibilities
- Background jobs, cron tasks, event handlers

### 2.5 Data Model
- Database schemas, migrations, ORMs
- Key data structures and their relationships
- State management approach

### 2.6 API Surface
- HTTP endpoints (method, path, request/response shapes)
- GraphQL schema / gRPC protos / WebSocket events
- CLI interface (commands, flags, arguments)
- Exported library API (public functions, classes, types)

### 2.7 Configuration & Environment
- Environment variables and their purpose
- Config files and their schema
- Feature flags, toggles

### 2.8 External Dependencies
- Third-party services (databases, queues, APIs)
- Infrastructure requirements (cloud services, storage)
- Authentication/authorization providers

### 2.9 Testing & Quality
- Test framework and approach (unit, integration, e2e)
- Coverage patterns (what's tested, what's not)
- Linting, formatting, type checking setup

### 2.10 Deployment & Operations
- CI/CD configuration
- Deployment targets and strategies
- Monitoring, logging, health checks

---

## Analysis Heuristics

### Identifying Purpose
- Look at README first line, package description field, CLI help text
- Check the main entry point — what does it bootstrap?
- Look at test descriptions — they often describe expected behavior in plain language

### Discovering Architecture
- Map `import`/`require` statements to build dependency graph
- Identify layers by directory naming: `controllers`, `services`, `models`, `routes`, `handlers`, `domain`, `infra`
- Check for dependency injection patterns, middleware chains, plugin registrations

### Extracting Business Rules
- Look for validation functions, guard clauses, assertion statements
- Check error messages — they often describe what went wrong in business terms
- Examine test assertions — they encode expected behavior

### Finding API Contracts
- Route registrations (Express: `app.get()`, FastAPI: `@app.get()`, Go: `mux.HandleFunc()`)
- OpenAPI/Swagger files if present
- Request validation schemas (Joi, Zod, Pydantic, struct tags)
- CLI flag/argument definitions (cobra, argparse, yargs)

### Detecting Data Models
- ORM model definitions (Prisma, SQLAlchemy, GORM, TypeORM)
- Migration files (in chronological order)
- Type/interface definitions for core domain objects
- Database seed files
