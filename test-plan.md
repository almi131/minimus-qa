# Test Plan – Minimus PostgreSQL Image Validation

## Objective

Validate the custom PostgreSQL image against the official Bitnami reference image by running both
as Docker (OCI) containers and deploying them via the Bitnami PostgreSQL Helm chart.
Identify defects introduced in the custom image.

## Environment

- **Platform**: Linux development environment with Docker, Helm, kubectl, and a Kubernetes cluster.
- **Helm chart**: `bitnami/postgresql` (APP VERSION 18.1.0).
- **Namespace**: `minimus-qa`.
- **Reference image**: `bitnami/postgresql:latest`
- **Image under test**: `halex1985/postgresql:latest`
- **Common configuration**: `username=myuser`, `password=mypass`, `database=mydb`.

---

## Test Cases

---

### TC-01: OCI – Container Startup

**Objective**: Confirm both images start successfully as Docker containers with identical configuration.

**Preparation**:
- Ensure Docker is running.
- Reference image: `bitnami/postgresql:latest`
- Image under test: `halex1985/postgresql:latest`
- Remove any existing containers: `docker rm -f pg-ref pg-test-oci`

**Steps to Reproduce**:
1. Start reference container:
   `docker run -d --name pg-ref -e POSTGRESQL_USERNAME=myuser -e POSTGRESQL_PASSWORD=mypass -e POSTGRESQL_DATABASE=mydb -p 5433:5432 bitnami/postgresql:latest`
   — Docker prints a container ID, confirming the container was created.
2. Start custom container:
   `docker run -d --name pg-test-oci -e POSTGRESQL_USERNAME=myuser -e POSTGRESQL_PASSWORD=mypass -e POSTGRESQL_DATABASE=mydb -p 5434:5432 halex1985/postgresql:latest`
   — Docker prints a container ID, confirming the container was created.
3. `docker ps` — verify both containers have STATUS `Up`.
4. `docker logs --tail 50 pg-ref` — wait until logs show `database system is ready to accept connections`.
5. `docker logs --tail 50 pg-test-oci` — wait until logs show `database system is ready to accept connections`.

**Expected Results**:
- Both containers have STATUS `Up`.
- Both logs show `database system is ready to accept connections`.
- No `Permission denied` or other errors in either log.

---

### TC-02: OCI – Basic SQL

**Objective**: Confirm both images accept basic SQL operations (connect, create, insert, select).

**Preparation**: TC-01 passed (both containers are running).

**Steps to Reproduce**:
1. Connect to reference and run SQL:
   `docker exec -it pg-ref psql -U myuser -d mydb -c "CREATE TABLE test1 (id INT PRIMARY KEY, note TEXT); INSERT INTO test1 VALUES (1, 'hello'); SELECT * FROM test1; DROP TABLE test1;"`
2. Connect to custom and run the same SQL:
   `docker exec -it pg-test-oci psql -U myuser -d mydb -c "CREATE TABLE test1 (id INT PRIMARY KEY, note TEXT); INSERT INTO test1 VALUES (1, 'hello'); SELECT * FROM test1; DROP TABLE test1;"`

**Expected Results**:
- Both commands succeed: table created, row inserted, row `(1, 'hello')` returned, table dropped.
- No errors on either image.

---

### TC-03: OCI – Container Lifecycle (Stop / Start / Restart)

**Objective**: Verify both images handle stop, start, and restart gracefully without data corruption.

**Preparation**: TC-01 passed (both containers are running).

**Steps to Reproduce**:
1. `docker stop pg-ref` then `docker logs --tail 20 pg-ref` — verify logs show `database system is shut down`.
2. `docker start pg-ref` then `docker logs --tail 20 pg-ref` — verify logs show `database system is ready to accept connections`.
3. `docker restart pg-ref` then `docker logs --tail 20 pg-ref` — verify logs show shutdown followed by `database system is ready to accept connections`.
4. `docker exec -it pg-ref psql -U myuser -d mydb -c "SELECT 1;"` — verify SQL still works.
5. Repeat steps 1–4 for `pg-test-oci`.

**Expected Results**:
- Both containers shut down cleanly and restart successfully.
- Logs show `database system is shut down` on stop and `database system is ready to accept connections` on start/restart.
- `SELECT 1` returns `1` after restart for both images.

---

### TC-04: OCI – Log Comparison

**Objective**: Compare startup logs of both images to identify differences in behavior, warnings, or errors.

**Preparation**: TC-01 passed (both containers are running).

**Steps to Reproduce**:
1. `docker logs pg-ref` — save or review reference logs.
2. `docker logs pg-test-oci` — save or review custom image logs.
3. Compare side by side, looking for:
   - `Permission denied` errors
   - Excessive debug output (`set -x` shell trace)
   - Password or credential exposure
   - Unexpected warnings (e.g. `ALLOW_EMPTY_PASSWORD`)
   - Differences in welcome message, compiler/toolchain string

**Expected Results**:
- Both images produce similar log output with only INFO-level messages.
- No `Permission denied` errors, no credential exposure, no unnecessary warnings.

---

### TC-05: Helm – Deployment and Basic SQL

**Objective**: Deploy both images via the Bitnami Helm chart and verify basic PostgreSQL functionality.

**Preparation**:
- Kubernetes cluster is running. Bitnami Helm repo is added (`helm repo add bitnami https://charts.bitnami.com/bitnami`).
- Reference image: `bitnami/postgresql:latest`
- Image under test: `halex1985/postgresql:latest`
- Remove previous releases and PVCs:
  `helm uninstall pg-ref -n minimus-qa; helm uninstall pg-test -n minimus-qa`
  `kubectl delete pvc -n minimus-qa -l app.kubernetes.io/instance=pg-ref`
  `kubectl delete pvc -n minimus-qa -l app.kubernetes.io/instance=pg-test`

**Steps to Reproduce**:
1. Install reference:
   `helm install pg-ref bitnami/postgresql --namespace minimus-qa --set auth.username=myuser --set auth.password=mypass --set auth.database=mydb --wait`
2. Install custom:
   `helm install pg-test bitnami/postgresql --namespace minimus-qa --set auth.username=myuser --set auth.password=mypass --set auth.database=mydb --set image.repository=halex1985/postgresql --set image.tag=latest --set global.security.allowInsecureImages=true --wait`
3. `kubectl get pods -n minimus-qa` — verify both pods are `1/1 Running`.
4. Run SQL on reference:
   `kubectl run pg-ref-client --rm -i --tty --restart=Never --namespace minimus-qa --image bitnami/postgresql:latest --env="PGPASSWORD=mypass" --env="PAGER=" --command -- psql --host pg-ref-postgresql -U myuser -d mydb -p 5432 -c "CREATE TABLE test1 (id INT PRIMARY KEY, note TEXT); INSERT INTO test1 VALUES (1, 'hello'); SELECT * FROM test1; DROP TABLE test1;"`
5. Run SQL on custom:
   `kubectl run pg-test-client --rm -i --tty --restart=Never --namespace minimus-qa --image halex1985/postgresql:latest --env="PGPASSWORD=mypass" --env="PAGER=" --command -- psql --host pg-test-postgresql -U myuser -d mydb -p 5432 -c "CREATE TABLE test1 (id INT PRIMARY KEY, note TEXT); INSERT INTO test1 VALUES (1, 'hello'); SELECT * FROM test1; DROP TABLE test1;"`

**Expected Results**:
- Both pods are `1/1 Running` with no restarts.
- SQL commands succeed on both: table created, row inserted, row returned, table dropped.

---

### TC-06: Helm – Log Comparison

**Objective**: Compare pod logs of both Helm deployments to identify defects in the custom image.

**Preparation**: TC-05 completed (both Helm releases running).

**Steps to Reproduce**:
1. `kubectl logs pg-ref-postgresql-0 -n minimus-qa` — save or review reference logs.
2. `kubectl logs pg-test-postgresql-0 -n minimus-qa` — save or review custom image logs.
3. Compare side by side, looking for:
   - `Permission denied` errors on `/docker-entrypoint-preinitdb.d/` or `/docker-entrypoint-initdb.d/`
   - Shell trace output (`set -x`)
   - Password or credential exposure in logs
   - `ALLOW_EMPTY_PASSWORD=yes` warning
   - Differences in welcome message, compiler/toolchain string

**Expected Results**:
- Both pods produce similar log output with clean INFO-level messages.
- No `Permission denied` errors, no credential exposure, no unnecessary warnings.
- Both show "Welcome to the Bitnami postgresql container" and same compiler string.

---

### TC-07: Helm – Data Persistence Across Pod Restart

**Objective**: Verify that data persists when pods are restarted for both images.

**Preparation**: TC-05 completed (both Helm releases running).

**Steps to Reproduce**:
1. Insert data into reference:
   `kubectl run pg-ref-insert --rm -i --tty --restart=Never --namespace minimus-qa --image bitnami/postgresql:latest --env="PGPASSWORD=mypass" --env="PAGER=" --command -- psql --host pg-ref-postgresql -U myuser -d mydb -p 5432 -c "DROP TABLE IF EXISTS persist_test; CREATE TABLE persist_test (id INT PRIMARY KEY, note TEXT); INSERT INTO persist_test VALUES (1, 'before_restart'); SELECT * FROM persist_test;"`
2. Insert data into custom:
   `kubectl run pg-test-insert --rm -i --tty --restart=Never --namespace minimus-qa --image halex1985/postgresql:latest --env="PGPASSWORD=mypass" --env="PAGER=" --command -- psql --host pg-test-postgresql -U myuser -d mydb -p 5432 -c "DROP TABLE IF EXISTS persist_test; CREATE TABLE persist_test (id INT PRIMARY KEY, note TEXT); INSERT INTO persist_test VALUES (1, 'before_restart'); SELECT * FROM persist_test;"`
3. Verify both return `(1, 'before_restart')`.
4. Delete both pods:
   `kubectl delete pod pg-ref-postgresql-0 pg-test-postgresql-0 -n minimus-qa`
5. `kubectl get pods -n minimus-qa -w` — wait until both pods return to `1/1 Running`, then press Ctrl+C.
6. Check reference:
   `kubectl run pg-ref-check --rm -i --tty --restart=Never --namespace minimus-qa --image bitnami/postgresql:latest --env="PGPASSWORD=mypass" --env="PAGER=" --command -- psql --host pg-ref-postgresql -U myuser -d mydb -p 5432 -c "SELECT * FROM persist_test;"`
7. Check custom:
   `kubectl run pg-test-check --rm -i --tty --restart=Never --namespace minimus-qa --image halex1985/postgresql:latest --env="PGPASSWORD=mypass" --env="PAGER=" --command -- psql --host pg-test-postgresql -U myuser -d mydb -p 5432 -c "SELECT * FROM persist_test;"`

**Expected Results**:
- Both queries return `(1, 'before_restart')` after pod restart.
- Data is preserved via PVC for both images.

---

### TC-08: Helm – PostgreSQL Configuration Comparison

**Objective**: Verify that runtime PostgreSQL settings match between both images.

**Preparation**: TC-05 completed (both Helm releases running).

**Steps to Reproduce**:
1. Run on reference:
   `kubectl run pg-ref-config --rm -i --tty --restart=Never --namespace minimus-qa --image bitnami/postgresql:latest --env="PGPASSWORD=mypass" --env="PAGER=" --command -- psql --host pg-ref-postgresql -U myuser -d mydb -p 5432 -c "SELECT version(); SHOW fsync; SHOW wal_level; SHOW password_encryption; SHOW timezone; SHOW listen_addresses; SHOW synchronous_commit; SHOW max_connections; SHOW client_min_messages;"`
2. Run on custom:
   `kubectl run pg-test-config --rm -i --tty --restart=Never --namespace minimus-qa --image halex1985/postgresql:latest --env="PGPASSWORD=mypass" --env="PAGER=" --command -- psql --host pg-test-postgresql -U myuser -d mydb -p 5432 -c "SELECT version(); SHOW fsync; SHOW wal_level; SHOW password_encryption; SHOW timezone; SHOW listen_addresses; SHOW synchronous_commit; SHOW max_connections; SHOW client_min_messages;"`
3. Compare all values side by side.

**Expected Results**:
- All settings match between both images:
  fsync=on, wal_level=replica, password_encryption=scram-sha-256, timezone=GMT,
  listen_addresses=*, synchronous_commit=on, max_connections=100, client_min_messages=error.
- PostgreSQL version is the same (18.1).

---

### TC-09: Helm – CRUD and Data Types

**Objective**: Verify that the custom image supports various SQL operations and data types.

**Preparation**: TC-05 completed (custom Helm release running).

**Steps to Reproduce**:
1. Connect to the custom Helm pod via client:
   `kubectl run pg-test-crud --rm -i --tty --restart=Never --namespace minimus-qa --image halex1985/postgresql:latest --env="PGPASSWORD=mypass" --env="PAGER=" --command -- psql --host pg-test-postgresql -U myuser -d mydb -p 5432`
2. Execute:
   ```
   CREATE TABLE type_test (id SERIAL PRIMARY KEY, name TEXT, age INT, active BOOLEAN, score NUMERIC(5,2), created_at TIMESTAMP DEFAULT now());
   INSERT INTO type_test (name, age, active, score) VALUES ('Alice', 30, true, 95.50);
   INSERT INTO type_test (name, age, active, score) VALUES ('Bob', NULL, false, 78.25);
   SELECT * FROM type_test;
   UPDATE type_test SET age = 31 WHERE name = 'Alice';
   SELECT * FROM type_test WHERE name = 'Alice';
   DELETE FROM type_test WHERE name = 'Bob';
   SELECT * FROM type_test;
   SELECT name, age IS NULL AS age_is_null FROM type_test;
   DROP TABLE type_test;
   ```

**Expected Results**:
- All operations complete without error.
- INSERT, SELECT, UPDATE, DELETE behave correctly.
- Data types (SERIAL, TEXT, INT, BOOLEAN, NUMERIC, TIMESTAMP) work as expected.
- NULL handling is correct.

---

### TC-10: Helm – Init Script Functionality

**Objective**: Mount a custom init script via Helm and verify it executes during startup.
This directly tests whether the `/docker-entrypoint-initdb.d/` permission issue has real impact.

**Preparation**:
- Reference image: `bitnami/postgresql:latest`
- Image under test: `halex1985/postgresql:latest`
- Remove previous init releases:
  `helm uninstall pg-ref-init -n minimus-qa; helm uninstall pg-test-init -n minimus-qa`
  `kubectl delete pvc -n minimus-qa -l app.kubernetes.io/instance=pg-ref-init`
  `kubectl delete pvc -n minimus-qa -l app.kubernetes.io/instance=pg-test-init`
- Create a ConfigMap with a simple init script:
  `kubectl create configmap pg-init-script -n minimus-qa --from-literal=init.sql="CREATE TABLE init_test (id INT PRIMARY KEY, note TEXT); INSERT INTO init_test VALUES (1, 'created_by_init_script');"`

**Steps to Reproduce**:
1. Install reference with init script:
   `helm install pg-ref-init bitnami/postgresql --namespace minimus-qa --set auth.username=myuser --set auth.password=mypass --set auth.database=mydb --set primary.initdb.scriptsConfigMap=pg-init-script --wait`
2. Verify init script ran on reference:
   `kubectl run pg-ref-init-check --rm -i --tty --restart=Never --namespace minimus-qa --image bitnami/postgresql:latest --env="PGPASSWORD=mypass" --env="PAGER=" --command -- psql --host pg-ref-init-postgresql -U myuser -d mydb -p 5432 -c "SELECT * FROM init_test;"`
3. Install custom with init script:
   `helm install pg-test-init bitnami/postgresql --namespace minimus-qa --set auth.username=myuser --set auth.password=mypass --set auth.database=mydb --set image.repository=halex1985/postgresql --set image.tag=latest --set global.security.allowInsecureImages=true --set primary.initdb.scriptsConfigMap=pg-init-script --wait`
4. Verify init script ran on custom:
   `kubectl run pg-test-init-check --rm -i --tty --restart=Never --namespace minimus-qa --image halex1985/postgresql:latest --env="PGPASSWORD=mypass" --env="PAGER=" --command -- psql --host pg-test-init-postgresql -U myuser -d mydb -p 5432 -c "SELECT * FROM init_test;"`
5. Clean up:
   `helm uninstall pg-ref-init pg-test-init -n minimus-qa`
   `kubectl delete pvc -n minimus-qa -l app.kubernetes.io/instance=pg-ref-init`
   `kubectl delete pvc -n minimus-qa -l app.kubernetes.io/instance=pg-test-init`
   `kubectl delete configmap pg-init-script -n minimus-qa`

**Expected Results**:
- Both images: `SELECT * FROM init_test` returns `(1, 'created_by_init_script')`.
- Init scripts execute successfully on both images.

---

## Automation Scope

Per the assignment, the automated test suite covers **Helm-based deployment only** and includes
tests that:
- Validate basic PostgreSQL functionality (connect, CRUD).
- Reproduce the 5 bugs visible in Helm deployment:
  1. Permission errors on init directories (`/docker-entrypoint-preinitdb.d/` and `/docker-entrypoint-initdb.d/`)
  2. Security information leakage via `set -x` (passwords, secret paths, internal paths)
  3. Excessive default logging (`set -x` shell trace)
  4. `ALLOW_EMPTY_PASSWORD=yes` warning when passwords are provided
  5. Non-standard build toolchain (MinimOS)

The OCI-only bug (container startup failure due to data directory permissions) is documented
in the Test Report based on manual testing.

## Out of Scope

Performance benchmarking, HA/replication, backup/restore, TLS, LDAP, and advanced PostgreSQL features.
