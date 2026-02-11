"""
Automated tests for Minimus PostgreSQL image - Helm-based deployment.

Each test validates that the custom image behaves correctly.
  PASS = image behaves correctly, no issue
  FAIL = defect found in the custom image

Tests:
  test_filesystem_permissions  - BUG-02: no 'Permission denied' errors
  test_credential_security     - BUG-03: no passwords exposed in logs
  test_excessive_logging       - BUG-04: no shell trace (set -x) by default
  test_build_toolchain         - BUG-06: standard gcc toolchain, not MinimOS
"""


class TestHelmBugs:
    """Test suite for validating the Minimus PostgreSQL custom image."""

    def test_filesystem_permissions(self, helm_logs):
        """
        Test 1 (BUG-02): Init script directories should be readable.

        Expected: No 'Permission denied' errors in pod logs.
        Reference image: no permission errors.
        """
        permission_errors = [
            line for line in helm_logs.splitlines()
            if "Permission denied" in line
        ]

        assert len(permission_errors) == 0, (
            f"Permission denied errors found in logs:\n"
            + "\n".join(permission_errors)
        )

    def test_credential_security(self, helm_logs):
        """
        Test 2 (BUG-03): Passwords must not appear in container logs.

        Expected: No password values visible in plain text in logs.
        Reference image: no credentials in logs.
        CWE-532: Insertion of Sensitive Information into Log File.
        """
        password_lines = [
            line for line in helm_logs.splitlines()
            if "POSTGRES_POSTGRES_PASSWORD=" in line
        ]

        assert len(password_lines) == 0, (
            f"Superuser password exposed in plain text in logs (CWE-532):\n"
            f"{password_lines[0]}"
        )

    def test_excessive_logging(self, helm_logs):
        """
        Test 3 (BUG-04): Default logging should be clean INFO messages.

        Expected: Logs should not start with '+ set -x' shell trace.
        Reference image: clean INFO-level logs, ~30 lines for full startup.
        """
        lines = helm_logs.splitlines()
        first_line = lines[0] if lines else ""

        assert not first_line.startswith("+ set -x"), (
            f"Shell trace (set -x) is enabled by default.\n"
            f"First line of logs: {first_line}\n"
            f"Expected: clean INFO messages (same as reference image)"
        )

    def test_build_toolchain(self, helm_logs):
        """
        Test 4 (BUG-06): PostgreSQL should be compiled with standard gcc.

        Expected: Compiler string should contain 'gcc (GCC)', not MinimOS.
        Reference image: compiled by gcc (GCC) 12.2.0
        """
        minimos_lines = [
            line for line in helm_logs.splitlines()
            if "MinimOS" in line
        ]

        assert len(minimos_lines) == 0, (
            f"Non-standard MinimOS toolchain detected instead of gcc (GCC):\n"
            f"{minimos_lines[0]}"
        )
