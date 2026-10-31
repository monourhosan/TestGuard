#!/usr/bin/env python3
"""Run Postman test collection with Newman against a live local server.

Automatically seeds the local database, boots a temporary Uvicorn server,
executes Newman via npx, and cleans up.
"""

import os
import subprocess
import sys
import time

import requests


def wait_for_server(url: str, timeout: int = 15) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{url}/health", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.chdir(base_dir)

    print("[1/4] Ensuring database is seeded...")
    env = os.environ.copy()
    if "DATABASE_URL" not in env:
        env["DATABASE_URL"] = "sqlite:///./testguard.db"

    subprocess.run([sys.executable, "app/seed.py"], env=env, check=True)

    print("[2/4] Starting Uvicorn API server on http://localhost:8000...")
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        print("[3/4] Waiting for /health readiness...")
        if not wait_for_server("http://127.0.0.1:8000", timeout=15):
            print("[ERROR] Server failed to start within timeout.")
            sys.exit(1)

        print("[4/4] Executing Newman Postman Collection Runner...")
        collection = os.path.join("postman", "TestGuard.postman_collection.json")
        environment = os.path.join("postman", "TestGuard.local.postman_environment.json")

        cmd = ["npx", "-y", "newman", "run", collection, "-e", environment]
        if sys.platform == "win32":
            # On Windows, npx is a .cmd
            cmd[0] = "npx.cmd"

        result = subprocess.run(cmd, env=env)
        sys.exit(result.returncode)
    finally:
        print("[CLEANUP] Stopping background API server...")
        server.terminate()
        try:
            server.wait(timeout=5)
        except Exception:
            server.kill()


if __name__ == "__main__":
    main()
