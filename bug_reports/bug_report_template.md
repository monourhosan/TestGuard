# Defect Report Template

## 1. Defect Header
- **Bug ID:** `BUG-YYYYMMDD-XXX`
- **Title:** `[Module] Brief, descriptive summary of defect behavior`
- **Module / Subsystem:** `[Authentication | Authorization | Tenancy | Projects | Tasks | Database]`
- **Environment / Build:** `[e.g., Local Docker v1.0.0, Python 3.11, PostgreSQL 16]`
- **Date Reported:** `YYYY-MM-DD`
- **Reported By:** `[QA Engineer Name]`
- **Status:** `[New | In Progress | Ready for Retest | Verified Closed | Deferred | Rejected]`

---

## 2. Classification
- **Severity:** `[Critical | Major | Moderate | Minor]`
- **Priority:** `[P1 - Immediate | P2 - High | P3 - Normal | P4 - Low]`
- **Reproducibility:** `[Always (100%) | Intermittent | Once Only]`

---

## 3. Preconditions & Test Data
- **Preconditions:**
  - 
- **Test Data Used:**
  - Caller Identity: `[e.g., Member User in Tenant Alpha (id=1)]`
  - Target Resource: `[e.g., Project ID 42 belonging to Tenant Beta (id=2)]`
  - Payload / Parameters: `[e.g., JSON payload or query string]`

---

## 4. Steps to Reproduce
1. Step 1...
2. Step 2...
3. Step 3...

---

## 5. Observed vs. Expected Behavior
- **Actual Result:**
  - What the system actually returned or did (including HTTP status code and response body).
- **Expected Result:**
  - What the system should have returned per API contract and security specifications.

---

## 6. Evidence & Diagnostic Logs
```http
POST /api/v1/... HTTP/1.1
Host: localhost:8000
Authorization: Bearer <TOKEN>
Content-Type: application/json

{ ... }
```

```json
HTTP/1.1 500 Internal Server Error
{
  "detail": "..."
}
```

---

## 7. Traceability & Root Cause Analysis
- **Related Test Case ID:** `[e.g., TENANT-001 or AUTHZ-006]`
- **Automated Regression Test:** `[e.g., tests/regression/test_regression.py::test_reg_... ]`
- **Suspected Root Cause:** `[Preliminary technical hypothesis]`
- **Impact Assessment:** `[Security impact, data integrity impact, user experience]`
