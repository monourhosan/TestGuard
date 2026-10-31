# TestGuard Database Validation & Integrity Strategy

This document describes the database design principles, relational integrity constraints, and automated SQL-level validation checks implemented in TestGuard.

---

## 1. Relational Integrity Architecture

Multi-tenant data architectures must never rely exclusively on application-level filtering. If application logic suffers a regression (such as an omitted `WHERE tenant_id = :id` clause), the database schema must provide a secondary line of defense.

### 1.1 Composite Foreign Key Guard (Cross-Tenant Attachment Defense)
In standard relational models, a `tasks` table references `projects(id)` and `tenants(id)`. However, this allows a critical defect where a task belongs to Tenant Alpha, but references a `project_id` owned by Tenant Beta.

TestGuard enforces database-level defense via a composite unique constraint and composite foreign key:
1. `projects` defines a unique constraint on `(id, tenant_id)`:
   ```sql
   CONSTRAINT uq_projects_id_tenant_id UNIQUE (id, tenant_id);
   ```
2. `tasks` defines a composite foreign key referencing `(project_id, tenant_id)`:
   ```sql
   CONSTRAINT fk_tasks_project_tenant FOREIGN KEY (project_id, tenant_id)
       REFERENCES projects (id, tenant_id) ON DELETE CASCADE;
   ```
**Integrity Guarantee:** Any SQL attempt to create a task with `tenant_id = 1` and `project_id = 42` (where project 42 belongs to `tenant_id = 2`) triggers an immediate database-level `IntegrityError`.

### 1.2 Tenant-Scoped Project Uniqueness
Project names are unique *within* a tenant, while allowing different tenants to choose identical project names:
```sql
-- Valid: Tenant A has "Platform Redesign"
-- Valid: Tenant B has "Platform Redesign"
-- Rejected: Tenant A creates a second "Platform Redesign" (409 Conflict)
```

---

## 2. Automated Database Validation Test Suite

The test suite in `tests/database/test_database_integrity.py` verifies database guarantees using direct SQL queries:

| Test Case | Method | Verification Concern |
| :--- | :--- | :--- |
| `DB-001` | Direct SQL `SELECT` | Record persistence and exact field mapping |
| `DB-002` | Session commit & fresh query | Entity updates persist cleanly |
| `DB-003` | SQL `DELETE` & `SELECT COUNT` | Cascade deletion purges child tasks |
| `DB-004` | Duplicate tenant slug insert | Slug unique constraint raises `IntegrityError` |
| `DB-005` | Duplicate user email insert | Email unique constraint raises `IntegrityError` |
| `DB-006` | Insert project with invalid tenant | Foreign key raises `IntegrityError` |
| `DB-007` | Cross-tenant task creation | Composite FK raises `IntegrityError` |
| `DB-008` | Direct SQL query on password column | Stored as bcrypt `$2b$` hash; plaintext absent |
| `DB-009` | Nested transaction rollback | Atomic rollback leaves zero partial or orphaned rows |
| `DB-010` | Database URL validation guard | Non-test database URL raises `RuntimeError` |

---

## 3. Production Database Safety Guard

To prevent catastrophic data loss during test runs, `tests/conftest.py` executes `verify_test_database_safety(url)` before any table creation or teardown.

```python
def verify_test_database_safety(url: str) -> None:
    safe_identifiers = ["test", "testguard_test", ":memory:"]
    is_safe = any(identifier in url.lower() for identifier in safe_identifiers)
    if not is_safe:
        raise RuntimeError(f"CRITICAL SAFETY VIOLATION: Refusing to run tests against database '{url}'.")
```
If `DATABASE_URL` or `TEST_DATABASE_URL` points to an instance without one of the approved test identifiers, tests immediately abort with a critical safety violation.
