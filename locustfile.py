"""Locust Performance Smoke Test for TestGuard Demo API

Executes non-destructive, read-heavy workloads against local demo API.
Usage:
    locust -f locustfile.py --headless -u 5 -r 1 -t 15s --host http://localhost:8000
"""

import os

from locust import HttpUser, between, task


class TestGuardUser(HttpUser):
    wait_time = between(1, 2)
    token = None

    def on_start(self):
        """Authenticate on start and store JWT token for subsequent requests."""
        email = os.getenv("LOCUST_USER_EMAIL", "admin@alpha.com")
        password = os.getenv("LOCUST_USER_PASSWORD", "AdminPassword123!")
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
            name="/api/v1/auth/login",
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token")

    @task(3)
    def health_check(self):
        """Monitor /health endpoint availability and latency."""
        self.client.get("/health", name="/health")

    @task(2)
    def list_projects(self):
        """Monitor tenant project listing performance."""
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.get("/api/v1/projects", headers=headers, name="/api/v1/projects")

    @task(2)
    def list_tasks(self):
        """Monitor tenant task listing performance."""
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.get("/api/v1/tasks", headers=headers, name="/api/v1/tasks")
