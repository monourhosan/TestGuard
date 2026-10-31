# Architecture & Engineering Decisions Record (ADRs)

This document records the foundational engineering, architectural, and quality assurance decisions made for **TestGuard**.

---

## ADR-001: Separation of System Under Test (SUT) and QA Test Suite

- **Status:** Accepted
- **Context:** TestGuard needs to demonstrate QA automation for a multi-tenant SaaS REST API. The demo application and the test automation suite must be decoupled to reflect production repository structure.
- **Decision:** The demo API lives under `app/`, containing FastAPI routers, Pydantic schemas, SQLAlchemy models, and core services. The automated test suite lives in `tests/`, organized strictly by QA concern (`api/`, `auth/`, `authorization/`, `tenancy/`, `database/`, `regression/`, `performance/`).
- **Consequences:** Tests interact with the API through clean HTTP client interfaces (`FastAPI TestClient` / `HTTPX`) without importing route handler logic directly, ensuring genuine black-box and grey-box API testing.

---

## ADR-002: Multi-Tenant Scoping and Isolation Strategy

- **Status:** Accepted
- **Context:** In a multi-tenant SaaS application, data leakage across tenant boundaries is a critical vulnerability.
- **Decision:**
  1. The user's `tenant_id` is derived strictly from the authenticated JWT token context (server-side trusted identity), never from client-supplied query parameters, headers, or request payloads.
  2. Any client-supplied `tenant_id` in request payloads is ignored or validated to match the token tenant.
  3. Every database query for projects and tasks filters strictly by `tenant_id`.
  4. Cross-tenant resource queries return HTTP `404 Not Found` rather than `403 Forbidden` to prevent resource-existence enumeration (IDOR prevention).
  5. Task creation strictly verifies that the parent `project_id` belongs to the authenticated tenant.
- **Consequences:** Prevents Horizontal Privilege Escalation and cross-tenant data leaks.

---

## ADR-003: Role-Based Access Control (RBAC) Hierarchy

- **Status:** Accepted
- **Context:** Users within a tenant can hold different roles with varying privileges.
- **Decision:**
  - `admin`: Can create, view, update, and delete projects and tasks within their own tenant.
  - `member`: Can view projects and tasks within their own tenant, create tasks, and update tasks. Cannot create, update, or delete projects. Cannot delete tasks.
  - Unauthenticated requests return `401 Unauthorized`. Authenticated requests exceeding role permissions return `403 Forbidden`. Cross-tenant requests return `404 Not Found`.
- **Consequences:** Clear, deterministic authorization matrix validated by automated test suites.

---

## ADR-004: Dual-Engine Database Strategy (PostgreSQL & SQLite Test Isolation)

- **Status:** Accepted
- **Context:** The production and containerized database is PostgreSQL (managed via SQLAlchemy and Alembic). However, running local tests should be fast, zero-configuration, and robust across diverse environments (including environments without an active Docker daemon).
- **Decision:**
  - Production / Docker Compose uses PostgreSQL via `psycopg2`.
  - The test harness supports both PostgreSQL and SQLite. In local test execution where `TEST_DATABASE_URL` is omitted, tests automatically use an isolated SQLite test database with `PRAGMA foreign_keys = ON;` enabled on every connection.
  - In CI (GitHub Actions) or environments with PostgreSQL, `TEST_DATABASE_URL` can point to PostgreSQL, running against a dedicated test database (`testguard_test`).
  - Strict database safety check in `conftest.py`: Destructive fixture teardown/cleanup is blocked unless the database URL or name explicitly contains `test`.
- **Consequences:** Tests can execute instantly in any developer environment while remaining 100% compatible with PostgreSQL in CI and Docker.

---

## ADR-005: Security & Password Hashing

- **Status:** Accepted
- **Context:** User passwords and access tokens must follow standard security best practices.
- **Decision:**
  - Passwords are encrypted using standard `bcrypt` with automated salt generation. Plaintext passwords are never persisted or logged.
  - JWT tokens are signed using `HS256` with configurable secret keys and explicit expiration (`access_token_expire_minutes`).
  - User response schemas strictly exclude `password_hash`.
- **Consequences:** Meets industry security guidelines for credential storage and token transmission.

---

## ADR-006: Defect Documentation and Traceability

- **Status:** Accepted
- **Context:** Portfolio QA projects must demonstrate structured defect reporting and traceability between functional requirements, test cases, and automated execution.
- **Decision:**
  - Maintain a formal test case matrix (`test_cases/test_case_matrix.md`) with unique identifiers (`AUTH-xxx`, `AUTHZ-xxx`, `TENANT-xxx`, `API-xxx`, `DB-xxx`, `REG-xxx`).
  - Maintain a requirements traceability matrix (`test_cases/traceability_matrix.md`).
  - Maintain an industry-standard bug report template (`bug_reports/bug_report_template.md`) and a documented, simulated bug report example.
- **Consequences:** Complete transparency and auditability for QA reviewers and recruiters.
