"""
Pytest configuration and fixtures for Minimus PostgreSQL image testing.

This module provides a session-scoped fixture that:
  1. Deploys the custom image via the Bitnami PostgreSQL Helm chart
  2. Waits for PostgreSQL to fully start
  3. Collects pod logs (used by all tests)
  4. Cleans up the Helm release after all tests complete
"""

import subprocess
import time
import pytest

# ── Configuration ──────────────────────────────────────────────────────────

NAMESPACE = "minimus-qa"
IMAGE_REPOSITORY = "halex1985/postgresql"
IMAGE_TAG = "latest"
CHART = "bitnami/postgresql"
RELEASE = "pg-test-auto"
USERNAME = "myuser"
PASSWORD = "mypass"
DATABASE = "mydb"


# ── Helper ─────────────────────────────────────────────────────────────────

def run_cmd(cmd):
    """Run a shell command and return (exit_code, combined output)."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    output = result.stdout.strip()
    if result.stderr.strip():
        output = output + "\n" + result.stderr.strip() if output else result.stderr.strip()
    return result.returncode, output


def helm_cleanup():
    """Remove Helm release and associated PVC."""
    run_cmd(f"helm uninstall {RELEASE} -n {NAMESPACE}")
    run_cmd(
        f"kubectl delete pvc -n {NAMESPACE} "
        f"-l app.kubernetes.io/instance={RELEASE}"
    )
    run_cmd(f"kubectl delete pod -n {NAMESPACE} -l run")


# ── Fixture ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def helm_logs():
    """
    Session-scoped fixture: deploy the custom image via Helm,
    wait for startup, collect logs, yield them to tests, then clean up.
    """
    pod = f"{RELEASE}-postgresql-0"

    # ── Setup ──────────────────────────────────────────────────────────
    print("\n--- SETUP: Deploying custom image via Helm ---")

    # Create namespace if needed
    run_cmd(f"kubectl get ns {NAMESPACE} || kubectl create ns {NAMESPACE}")

    # Clean previous release
    helm_cleanup()

    # Install Helm chart with custom image
    exit_code, output = run_cmd(
        f"helm install {RELEASE} {CHART} "
        f"--namespace {NAMESPACE} "
        f"--set auth.username={USERNAME} "
        f"--set auth.password={PASSWORD} "
        f"--set auth.database={DATABASE} "
        f"--set image.repository={IMAGE_REPOSITORY} "
        f"--set image.tag={IMAGE_TAG} "
        f"--set global.security.allowInsecureImages=true "
        f"--wait --timeout 120s"
    )
    assert exit_code == 0, f"Helm install failed:\n{output}"

    # Wait for pod to be ready
    run_cmd(f"kubectl wait --for=condition=Ready pod/{pod} -n {NAMESPACE} --timeout=60s")

    # Wait for PostgreSQL to print all startup messages
    for _ in range(30):
        _, logs = run_cmd(f"kubectl logs {pod} -n {NAMESPACE}")
        if "database system is ready to accept connections" in logs:
            break
        time.sleep(2)
    time.sleep(3)

    # Collect final logs
    _, logs = run_cmd(f"kubectl logs {pod} -n {NAMESPACE}")
    print(f"--- Pod logs collected ({len(logs.splitlines())} lines) ---\n")

    # ── Yield logs to tests ────────────────────────────────────────────
    yield logs

    # ── Teardown ───────────────────────────────────────────────────────
    print("\n--- TEARDOWN: Cleaning up Helm release ---")
    helm_cleanup()
    print("--- Cleanup complete ---")
