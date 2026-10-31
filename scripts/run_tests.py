#!/usr/bin/env python3
"""Cross-platform test runner utility script for TestGuard."""

import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="TestGuard QA Suite Runner")
    parser.add_argument(
        "--suite",
        choices=["all", "auth", "authz", "tenancy", "api", "database", "regression", "performance"],
        default="all",
        help="Target test suite to execute",
    )
    parser.add_argument("--cov", action="store_true", help="Generate code coverage report")
    parser.add_argument("--html", action="store_true", help="Generate HTML test results report")
    parser.add_argument("--xml", action="store_true", help="Generate JUnit XML report")
    args = parser.parse_args()

    cmd = [sys.executable, "-m", "pytest", "-v"]

    # Target path
    suite_map = {
        "all": "tests",
        "auth": "tests/auth",
        "authz": "tests/authorization",
        "tenancy": "tests/tenancy",
        "api": "tests/api",
        "database": "tests/database",
        "regression": "tests/regression",
        "performance": "tests/performance",
    }
    cmd.append(suite_map[args.suite])

    if args.cov:
        cmd.extend(["--cov=app", "--cov-report=term-missing", "--cov-report=html:reports/htmlcov"])

    if args.html:
        cmd.extend(["--html=reports/report.html", "--self-contained-html"])

    if args.xml:
        cmd.append("--junitxml=reports/junit.xml")

    print(f"[RUNNING] {' '.join(cmd)}")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
