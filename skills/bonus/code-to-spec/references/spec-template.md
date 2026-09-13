# SPEC Template

```markdown
# SPEC: [Project Name]

> Reverse-engineered specification — generated [date] from commit [short-hash]

## 1. Overview

### 1.1 Purpose
[One paragraph: what problem this project solves and for whom]

### 1.2 Key Capabilities
- [Bullet list of what the system can do, from a user's perspective]

### 1.3 Architecture Style
[e.g., "Monolithic Express.js API with React SPA frontend", "CLI tool with plugin system", "Microservices communicating over gRPC"]

---

## 2. Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | ... | ... |
| Framework | ... | ... |
| Database | ... | ... |
| Build | ... | ... |
| Test | ... | ... |
| Deploy | ... | ... |

---

## 3. Project Structure

[Directory tree with annotations explaining each top-level directory's purpose]

---

## 4. Data Model

### 4.1 Core Entities
[For each entity: name, fields, relationships, constraints]

### 4.2 State Transitions
[If applicable: lifecycle states and valid transitions]

---

## 5. API Surface

### 5.1 [Interface Type: REST / CLI / Library / etc.]

[For each endpoint/command/function:]
| Method | Path/Command | Description | Auth |
|--------|-------------|-------------|------|
| ... | ... | ... | ... |

### 5.2 Request/Response Schemas
[Key request/response shapes with field types]

---

## 6. Configuration

| Variable / Key | Required | Default | Description |
|---------------|----------|---------|-------------|
| ... | ... | ... | ... |

---

## 7. External Dependencies

| Service | Purpose | Failure Impact |
|---------|---------|----------------|
| ... | ... | ... |

---

## 8. Business Rules & Constraints

- [Numbered list of invariants, validation rules, and business logic constraints discovered in the code]

---

## 9. Non-Functional Characteristics

### 9.1 Performance
[Observed patterns: caching, pagination, batch processing, etc.]

### 9.2 Security
[Auth mechanism, input validation patterns, secrets management]

### 9.3 Error Handling
[Error strategy: custom error types, error codes, retry policies]

---

## 10. Testing Strategy

| Type | Framework | Coverage Pattern |
|------|-----------|-----------------|
| Unit | ... | ... |
| Integration | ... | ... |
| E2E | ... | ... |

---

## 11. Known Gaps & Assumptions

- [Things that are unclear from the code alone]
- [Assumptions made during analysis]
- [Areas with no tests or documentation]

---

## 12. Appendix

### A. Dependency Graph
[Key module dependencies, import relationships]

### B. Environment Setup
[Steps to run the project locally, derived from config and scripts]
```
