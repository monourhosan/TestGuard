# TestGuard Test Reports & Quality Metrics

This directory contains test execution artifacts, JUnit XML reports, and test coverage outputs generated during automated test runs.

---

## 1. How to Generate Reports

### Run All Tests with Coverage & JUnit XML
```bash
pytest -v --cov=app --cov-report=term-missing --cov-report=html:reports/htmlcov --junitxml=reports/junit.xml
```

### Run All Tests with HTML Report
```bash
pytest --html=reports/report.html --self-contained-html
```

### Targeted Test Suite Executions
```bash
# Authentication tests only
pytest tests/auth -v

# Authorization tests only
pytest tests/authorization -v

# Tenant isolation tests only
pytest tests/tenancy -v

# Database integrity tests only
pytest tests/database -v

# Regression safety suite only
pytest tests/regression -v

# Performance smoke test only
pytest tests/performance -v
```

---

## 2. Report Artifacts Structure
- `reports/junit.xml`: Machine-readable JUnit XML test execution report (used by GitHub Actions CI).
- `reports/htmlcov/index.html`: Interactive line-by-line code coverage report.
- `reports/report.html`: Self-contained visual HTML test results summary.

> **Note:** Generated HTML and XML reports are excluded from Git version control via `.gitignore`.
