# Simulated Bug Report: Cross-Tenant Resource Existence Enumeration (IDOR)

> **NOTICE:** This is a **simulated example** created specifically to demonstrate professional QA bug-reporting standards and traceability. TestGuard does not currently contain this vulnerability.

---

## 1. Defect Header
- **Bug ID:** `BUG-SIM-20261101-001`
- **Title:** `[Tenancy] Endpoint /api/v1/projects/{id} leaked foreign tenant resource existence via HTTP 403 instead of 404`
- **Module / Subsystem:** `Tenancy / Project Endpoints`
- **Environment / Build:** `Local Test Environment, Python 3.11.18, SQLite / PostgreSQL 16`
- **Date Reported:** `2026-11-01`
- **Reported By:** `Alex Morgan (Lead QA Automation Engineer)`
- **Status:** `Verified Closed`

---

## 2. Classification
- **Severity:** `Critical` (Information Disclosure / Insecure Direct Object Reference)
- **Priority:** `P1 - Immediate`
- **Reproducibility:** `Always (100%)`

---

## 3. Preconditions & Test Data
- **Preconditions:**
  - Tenant Alpha (`tenant_id = 1`) and Tenant Beta (`tenant_id = 2`) both exist in database.
  - Project ID `42` exists and is owned by Tenant Beta.
  - Project ID `999` does not exist in any tenant.
- **Test Data Used:**
  - Caller: `Alice Admin` (`tenant_id = 1`) with valid JWT token.
  - Target IDs: `42` (foreign resource), `999` (nonexistent resource).

---

## 4. Steps to Reproduce
1. Authenticate as Alice Admin (`admin@alpha.com`) and retrieve bearer access token.
2. Send HTTP GET request to `/api/v1/projects/42` with Alice's bearer token.
3. Observe status code and response payload.
4. Send HTTP GET request to `/api/v1/projects/999` with Alice's bearer token.
5. Compare the responses between step 2 and step 4.

---

## 5. Observed vs. Expected Behavior
- **Actual Result (Defect Behavior):**
  - GET `/api/v1/projects/42` returned `HTTP 403 Forbidden` (`{"detail": "You do not have access to this organization's project"}`).
  - GET `/api/v1/projects/999` returned `HTTP 404 Not Found` (`{"detail": "Project not found"}`).
  - **Defect Impact:** An attacker in Tenant Alpha can enumerate valid project IDs in other tenants by differentiating between 403 and 404 status codes.
- **Expected Result (Compliant Behavior):**
  - Both `/api/v1/projects/42` and `/api/v1/projects/999` must return identical `HTTP 404 Not Found` (`{"detail": "Project not found"}`) so that no information is disclosed regarding whether a foreign resource exists.

---

## 6. Diagnostic Evidence & Request Logs
```http
GET /api/v1/projects/42 HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1Ni...
Accept: application/json

HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "detail": "You do not have access to this organization's project"
}
```

---

## 7. Resolution & Traceability
- **Root Cause:** Route handler was retrieving project by ID first without filtering by tenant, and then checking `project.tenant_id == user.tenant_id`, raising 403 if mismatched.
- **Resolution Applied:** Refactored query to filter simultaneously by both `id` AND `tenant_id`:
  ```python
  project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == current_user.tenant_id).first()
  if not project:
      raise ResourceNotFoundException("Project not found")
  ```
- **Automated Regression Test Added:**
  - `tests/tenancy/test_tenant_isolation.py::test_tenant_a_cannot_get_tenant_b_project_returns_404`
  - `tests/regression/test_regression.py::test_reg_001_cross_tenant_access_remains_blocked`
- **Verification Date:** 2026-11-01
