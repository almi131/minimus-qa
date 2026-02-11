# Test Report – Minimus PostgreSQL Image Validation

## Summary

The custom image `halex1985/postgresql:latest` was tested against the reference image
`bitnami/postgresql:latest` by running both as Docker (OCI) containers and deploying them
via the Bitnami PostgreSQL Helm chart.

**6 defects were identified** (2 Critical, 2 High, 2 Medium), including 2 security vulnerabilities.
Basic PostgreSQL functionality (CRUD, data types, persistence, configuration) works correctly
under Helm. The image is completely unusable as a standalone Docker container.

## Environment

- Docker Desktop with Kubernetes enabled.
- Helm chart: `bitnami/postgresql` v18.2.6 (APP VERSION 18.1.0).
- Namespace: `minimus-qa`.
- Configuration: `username=myuser`, `password=mypass`, `database=mydb`.

## Test Results Summary

| TC# | Test Case | Result |
|-----|-----------|--------|
| TC-01 | OCI – Container Startup | **FAIL** (custom image crashes) |
| TC-02 | OCI – Basic SQL | **FAIL** (custom image not running) |
| TC-03 | OCI – Lifecycle (Stop/Start/Restart) | **FAIL** (custom image never recovers) |
| TC-04 | OCI – Log Comparison | **FAIL** (multiple defects found) |
| TC-05 | Helm – Deployment and Basic SQL | **PASS** |
| TC-06 | Helm – Log Comparison | **FAIL** (defects found in logs) |
| TC-07 | Helm – Data Persistence | **PASS** |
| TC-08 | Helm – PostgreSQL Configuration Comparison | **PASS** |
| TC-09 | Helm – CRUD and Data Types | **PASS** |
| TC-10 | Helm – Init Script Functionality | **PASS** (ConfigMap mount overrides permission issue) |

---

## Defects

---

### BUG-01: OCI container fails to start due to filesystem permission errors (Critical)

**Severity**: Critical
**Area**: OCI / Docker
**Related test cases**: TC-01, TC-02, TC-03, TC-04

**Preparation**:
- Ensure Docker is running.
- Pull the latest images:
  `docker pull bitnami/postgresql:latest`
  `docker pull halex1985/postgresql:latest`
- Remove any existing test container: `docker rm -f pg-test-oci`

**Steps to Reproduce**:
1. `docker run -d --name pg-test-oci -e POSTGRESQL_USERNAME=myuser -e POSTGRESQL_PASSWORD=mypass -e POSTGRESQL_DATABASE=mydb -p 5434:5432 halex1985/postgresql:latest`
2. `docker ps --filter "name=pg-test-oci"` — container is not listed (not running).
3. `docker ps -a --filter "name=pg-test-oci"` — container shows `Exited (1)`.
4. `docker logs --tail 20 pg-test-oci`

**Actual Results**:
- Container exits immediately with code 1.
- `docker logs` shows:
  ```
  postgresql 15:40:22.18 INFO  ==> ** Starting PostgreSQL setup **
  + /opt/bitnami/scripts/postgresql/setup.sh
  postgresql 15:40:22.20 INFO  ==> Validating settings in POSTGRESQL_* env vars..
  postgresql 15:40:22.21 WARN  ==> You set the environment variable ALLOW_EMPTY_PASSWORD=yes. For safety reasons, do not use this flag in a production environment.
  postgresql 15:40:22.23 INFO  ==> Loading custom pre-init scripts...
  find: '/docker-entrypoint-preinitdb.d/': Permission denied
  postgresql 15:40:22.24 INFO  ==> Initializing PostgreSQL database...
  mkdir: cannot create directory '/bitnami/postgresql/data': Permission denied
  ```
- Two permission errors occur:
  1. `find: '/docker-entrypoint-preinitdb.d/': Permission denied` — cannot read pre-init scripts directory.
  2. `mkdir: cannot create directory '/bitnami/postgresql/data': Permission denied` — cannot create data directory (fatal).
- PostgreSQL never starts. Container cannot be recovered with `docker start` or `docker restart`.
- Reference image starts successfully with the same configuration and shows no permission errors.

**Expected Results**:
- Container starts with STATUS `Up`.
- Logs show `database system is ready to accept connections`.
- No `Permission denied` errors (same as reference image).

---

### BUG-02: Helm deployment shows permission errors on init script directories (High)

**Severity**: High
**Area**: Helm
**Related test cases**: TC-06, TC-10

**Preparation**:
- Kubernetes cluster running, Bitnami Helm repo added, namespace `minimus-qa` created.
- No previous `pg-test` release:
  `helm uninstall pg-test -n minimus-qa; kubectl delete pvc -n minimus-qa -l app.kubernetes.io/instance=pg-test`

**Steps to Reproduce**:
1. `helm install pg-test bitnami/postgresql --namespace minimus-qa --set auth.username=myuser --set auth.password=mypass --set auth.database=mydb --set image.repository=halex1985/postgresql --set image.tag=latest --set global.security.allowInsecureImages=true --wait`
2. `kubectl get pods -n minimus-qa` — verify `pg-test-postgresql-0` is `1/1 Running`.
3. `kubectl logs pg-test-postgresql-0 -n minimus-qa`

**Actual Results**:
- Pod starts and PostgreSQL runs successfully (Helm provides a PVC for the data directory).
- However, `kubectl logs` shows two permission errors:
  ```
  postgresql 15:41:32.28 INFO  ==> Loading custom pre-init scripts...
  find: '/docker-entrypoint-preinitdb.d/': Permission denied
  postgresql 15:41:32.38 INFO  ==> Initializing PostgreSQL database...
  ...
  postgresql 15:41:49.11 INFO  ==> Loading custom scripts...
  find: '/docker-entrypoint-initdb.d/': Permission denied
  ...
  postgresql 15:41:49.60 INFO  ==> ** Starting PostgreSQL **
  ...
  2026-02-11 15:41:50.223 GMT [1] LOG:  database system is ready to accept connections
  ```
- Two permission errors:
  1. `find: '/docker-entrypoint-preinitdb.d/': Permission denied` — cannot read pre-init scripts directory.
  2. `find: '/docker-entrypoint-initdb.d/': Permission denied` — cannot read init scripts directory.
- Note: The data directory error from BUG-01 does **not** occur under Helm because the PVC provides
  `/bitnami/postgresql/data` with correct permissions. This allows the container to continue past the
  point where it crashes in OCI, reaching the init scripts step.
- When init scripts are mounted via Helm's `primary.initdb.scriptsConfigMap`, the Kubernetes
  ConfigMap mount overrides the broken directory and scripts execute correctly (TC-10 passed).
- Reference image shows **no** permission errors under the same Helm configuration.

**Expected Results**:
- `Loading custom pre-init scripts...` and `Loading custom scripts...` complete without errors.
- No `Permission denied` in logs (same as reference image).

---

### BUG-03: Security vulnerability — sensitive information leakage via shell trace in logs (Critical)

**Severity**: Critical (Security vulnerability — CWE-532: Insertion of Sensitive Information into Log File)
**Area**: OCI + Helm
**Related test cases**: TC-04, TC-06

**Preparation**:
- Kubernetes cluster running, Bitnami Helm repo added, namespace `minimus-qa` created.
- No previous `pg-test` release:
  `helm uninstall pg-test -n minimus-qa; kubectl delete pvc -n minimus-qa -l app.kubernetes.io/instance=pg-test`

**Steps to Reproduce**:
1. Deploy custom image via Helm:
   `helm install pg-test bitnami/postgresql --namespace minimus-qa --set auth.username=myuser --set auth.password=mypass --set auth.database=mydb --set image.repository=halex1985/postgresql --set image.tag=latest --set global.security.allowInsecureImages=true --wait`
2. `kubectl logs pg-test-postgresql-0 -n minimus-qa`
3. Search for lines containing `PASSWORD` or script paths.

**Actual Results**:
- Due to `set -x` shell tracing enabled in the entrypoint, container logs expose:
  - **Database superuser password in plain text**:
    `++ export POSTGRES_POSTGRES_PASSWORD=PRsU0QFU7Z`
  - **Application user password**:
    `++ export POSTGRESQL_PASSWORD=mypass`
  - **Secret file paths**:
    `POSTGRES_PASSWORD_FILE=/opt/bitnami/postgresql/secrets/password`
    `POSTGRES_POSTGRES_PASSWORD_FILE=/opt/bitnami/postgresql/secrets/postgres-password`
  - **Internal script paths**:
    `+ /opt/bitnami/scripts/postgresql/setup.sh`
    `++ . /opt/bitnami/scripts/libpostgresql.sh`
  - **Library paths**:
    `NSS_WRAPPER_LIB=/opt/bitnami/common/lib/libnss_wrapper.so`
  - **OS/compiler version**: `MinimOS 15.2.0-r2` (useful for CVE lookups by attackers).
- In production environments, container logs are typically shipped to centralized logging systems
  (ELK, Splunk, Datadog). Anyone with access to these systems — including operations teams,
  monitoring dashboards, and third-party SaaS providers — can read the database passwords.
- This happens automatically on every container start, without any user action.

**Expected Results**:
- No passwords, secret file paths, internal script paths, or filesystem details visible in logs.
- Reference image does not expose any of this information.
- Sensitive data should never appear in default log output.

---

### BUG-04: Excessive default logging due to shell trace (Medium)

**Severity**: Medium
**Area**: OCI + Helm (usability / observability)
**Related test cases**: TC-04, TC-06

**Preparation**: Same as BUG-03.

**Steps to Reproduce**:
1. Deploy custom image via Helm (same as BUG-03 step 1).
2. `kubectl logs pg-test-postgresql-0 -n minimus-qa`
3. Observe the first line and overall log volume.

**Actual Results**:
- The entrypoint script starts with `+ set -x`, enabling shell tracing for the entire startup.
- This produces hundreds of lines like:
  ```
  ++ . /opt/bitnami/scripts/liblog.sh
  +++ RESET='\033[0m'
  +++ RED='\033[38;5;1m'
  ++ export BITNAMI_ROOT_DIR=/opt/bitnami
  ```
- Important messages (errors, warnings) are buried in this noise.
- Reference image produces ~30 clean INFO-level lines for a full startup.

**Expected Results**:
- Default log output should contain only INFO-level messages (same as reference image).
- Detailed shell tracing should only be enabled when a debug flag (e.g. `BITNAMI_DEBUG=true`) is set.

---

### BUG-05: Security vulnerability — ALLOW_EMPTY_PASSWORD=yes enables unauthenticated access (High)

**Severity**: High (Security vulnerability — CWE-287: Improper Authentication)
**Area**: OCI + Helm
**Related test cases**: TC-04, TC-06

**Preparation**: Same as BUG-03.

**Steps to Reproduce**:
1. Deploy custom image via Helm with explicit passwords (same as BUG-03 step 1).
2. `kubectl logs pg-test-postgresql-0 -n minimus-qa`
3. Search for `ALLOW_EMPTY_PASSWORD`.

**Actual Results**:
- Logs show:
  ```
  WARN ==> You set the environment variable ALLOW_EMPTY_PASSWORD=yes. For safety reasons,
  do not use this flag in a production environment.
  ```
- The image sets `ALLOW_EMPTY_PASSWORD=yes` even when passwords are properly provided via
  Helm secrets.
- **Security impact**: if password secrets fail to mount (due to misconfiguration, RBAC issue,
  or secret deletion):
  - **Reference image**: refuses to start → safe, operator notices immediately.
  - **Custom image**: starts without any password → database is accessible to anyone on the
    network without authentication.
- This creates a fail-open condition that could lead to unauthorized data access in production.

**Expected Results**:
- No `ALLOW_EMPTY_PASSWORD` warning when passwords are provided via Helm secrets.
- Image should refuse to start if no password is configured (fail-closed, same as reference image).
- Reference image does not show this warning under the same Helm configuration.

---

### BUG-06: Non-standard build toolchain — supply chain risk (Medium)

**Severity**: Medium (Supply chain risk)
**Area**: OCI + Helm (build / compatibility)
**Related test cases**: TC-04, TC-06, TC-08

**Preparation**:
- Same as BUG-03, plus reference image also deployed:
  `helm install pg-ref bitnami/postgresql --namespace minimus-qa --set auth.username=myuser --set auth.password=mypass --set auth.database=mydb --wait`

**Steps to Reproduce**:
1. Deploy both images via Helm.
2. `kubectl logs pg-ref-postgresql-0 -n minimus-qa` — find `starting PostgreSQL` line.
3. `kubectl logs pg-test-postgresql-0 -n minimus-qa` — find `starting PostgreSQL` line.
4. Compare the `compiled by` portion.

**Actual Results**:
- Reference: `compiled by gcc (GCC) 12.2.0, 64-bit`
- Custom: `compiled by x86_64-pc-linux-gnu-gcc (MinimOS 15.2.0-r2) 15.2.0, 64-bit`
- PostgreSQL version is the same (18.1), but the build toolchain differs.
- No functional differences were observed in basic tests (TC-08, TC-09), but the non-standard
  toolchain means the binary is not identical to the official Bitnami build.
- **Supply chain risk**: The MinimOS toolchain and version (15.2.0-r2) may have its own set of
  known CVEs. Customers cannot verify the build against Bitnami's published checksums or
  security advisories because the binary was compiled with a different compiler.

**Expected Results**:
- Both images compiled with the same toolchain (`gcc (GCC) 12.2.0`).
- Build provenance should match the official Bitnami image for security verification.

---

## Areas with No Defects

| Area | Result |
|------|--------|
| Basic SQL functionality (Helm) | CREATE, INSERT, SELECT, UPDATE, DELETE all work correctly |
| Data types (SERIAL, TEXT, INT, BOOLEAN, NUMERIC, TIMESTAMP, NULL) | All handled correctly |
| Data persistence across pod restart (Helm) | Data survives pod restart via PVC |
| PostgreSQL configuration | All runtime settings match reference (fsync, wal_level, max_connections, etc.) |
| Init script via ConfigMap (Helm) | Scripts execute correctly when mounted via ConfigMap |
| Pod readiness, liveness probes, events | Identical to reference — no warnings or failures |
| PVC configuration | Both images use identical PVC (8Gi, RWO, Bound) |
