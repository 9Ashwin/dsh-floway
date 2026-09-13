# SPEC document template

Read this before writing the SPEC. It is the per-section contract for the 11 sections listed in
`SKILL.md` Step 4: what each subsection must contain, the tables to fill in, and the file-tree
example. Copy the skeleton below and fill it in; the Mapping Strategy at the end says which PRD
element feeds which section.

Contents: 1. Summary · 2. Architecture · 3. Data Model · 4. API Design · 5. Business Logic ·
6. Error Handling · 7. Security · 8. Performance · 9. Testing Strategy · 10. Implementation Plan ·
11. Open Questions & Risks · Mapping Strategy: PRD → SPEC.

---

```markdown
# SPEC: [Feature Name]

> Technical specification derived from: [PRD filename/link]
> Generated: [date] | Target branch: [branch] | Commit: [short-hash]

## 1. Summary

### 1.1 What This SPEC Covers
[One paragraph: what feature this specifies and the scope of implementation]

### 1.2 PRD Reference
- Source: [path or URL to PRD]
- User Stories covered: [US-001, US-002, ...]
- Functional Requirements covered: [FR-1, FR-2, ...]

### 1.3 Design Decisions Summary
| Decision | Choice | Rationale |
|----------|--------|-----------|
| ... | ... | ... |

---

## 2. Architecture

### 2.1 System Context
[Where this feature fits in the overall system — diagram or description]

### 2.2 Component Design
[New components/modules introduced, their responsibilities, and boundaries]

### 2.3 Module Interactions
[How new components interact with existing ones — sequence or data flow]

### 2.4 File Structure
[New files to create and existing files to modify]

```
src/
├── services/
│   └── priority.service.ts  [NEW]
├── controllers/
│   └── task.controller.ts   [MODIFY: add priority endpoints]
├── models/
│   └── priority.model.ts    [NEW]
└── migrations/
    └── 20240315_add_priority.ts [NEW]
```

---

## 3. Data Model

### 3.1 Schema Changes
[New tables, columns, indexes — with SQL or ORM notation]

### 3.2 Entity Definitions
[TypeScript interfaces / Go structs / Python dataclasses for new entities]

### 3.3 Relationships
[How new entities relate to existing ones — FK, embedded, reference]

### 3.4 Migration Plan
[Migration steps, backward compatibility, rollback strategy]

---

## 4. API Design

### 4.1 Endpoints

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| ... | ... | ... | ... | ... | ... |

### 4.2 Request/Response Schemas
[Detailed shapes with field types, validation rules, and examples]

### 4.3 Error Responses
[Error codes, messages, and HTTP status codes for each failure mode]

### 4.4 Breaking Changes
[Any backward-incompatible changes and migration path for consumers]

---

## 5. Business Logic

### 5.1 Core Algorithms
[Step-by-step logic for key operations — pseudocode or structured description]

### 5.2 Validation Rules
[Input validation, business rule validation, with specific constraints]

### 5.3 State Machine
[If applicable: states, transitions, guards, and side effects]

### 5.4 Edge Cases
[Known edge cases and how they should be handled]

---

## 6. Error Handling

### 6.1 Error Taxonomy
| Error Code | HTTP Status | Condition | User Message |
|------------|-------------|-----------|--------------|
| ... | ... | ... | ... |

### 6.2 Retry Strategy
[Which operations are retryable, backoff policy, max attempts]

### 6.3 Failure Modes
[What happens when dependencies fail — graceful degradation plan]

---

## 7. Security

### 7.1 Authentication & Authorization
[Who can access what, permission model, role checks]

### 7.2 Input Validation
[Sanitization rules, injection prevention, size limits]

### 7.3 Data Protection
[Sensitive fields, encryption at rest/transit, audit logging]

---

## 8. Performance

### 8.1 Expected Load
[Estimated QPS, data volume, growth projection]

### 8.2 Optimization Strategy
[Caching, pagination, lazy loading, batch processing]

### 8.3 Database Considerations
[Index strategy, query patterns, N+1 prevention]

---

## 9. Testing Strategy

### 9.1 Unit Tests
[What to test, test boundaries, mock strategy]

### 9.2 Integration Tests
[API tests, database tests, service interaction tests]

### 9.3 Edge Case Tests
[Specific scenarios to cover based on Section 5.4]

### 9.4 Acceptance Criteria Mapping
| US/FR | Test | Type | Description |
|-------|------|------|-------------|
| US-001 | ... | unit | ... |
| FR-2 | ... | integration | ... |

---

## 10. Implementation Plan

### 10.1 Phases
[Order of implementation — what to build first, dependencies between steps]

### 10.2 Issue Mapping
[Map SPEC sections to PRD Issues for implementation tracking]

| Issue | SPEC Sections | Priority | Depends On |
|-------|--------------|----------|------------|
| #1 | 3.1, 3.4 | high | — |
| #2 | 4.1, 4.2, 5.1 | high | #1 |
| ... | ... | ... | ... |

### 10.3 Incremental Delivery
[How to ship incrementally — feature flags, dark launches, gradual rollout]

---

## 11. Open Questions & Risks

### 11.1 Unresolved Questions
- [Questions that need product/engineering input before implementation]

### 11.2 Technical Risks
| Risk | Impact | Mitigation |
|------|--------|-----------|
| ... | ... | ... |

### 11.3 Assumptions
- [Technical assumptions made during SPEC creation — validate before implementing]
```

---

## Mapping Strategy: PRD → SPEC

How PRD elements translate to SPEC sections:

| PRD Section | SPEC Section(s) | Transformation |
|-------------|-----------------|----------------|
| User Stories | 5. Business Logic, 9.4 Acceptance Mapping | Stories → algorithms + test cases |
| Functional Requirements | 4. API Design, 5. Business Logic | FRs → endpoints + logic |
| Acceptance Criteria | 9. Testing Strategy | Criteria → specific test scenarios |
| Non-Goals | 11.1 Open Questions | Clarify what's explicitly excluded |
| Technical Considerations | 2. Architecture, 8. Performance | Constraints → design decisions |
| Success Metrics | 8.1 Expected Load, 10.3 Delivery | Metrics → monitoring + rollout plan |

