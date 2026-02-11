# Minimus QA — PostgreSQL Image Test Suite

Automated pytest suite that validates the custom **Minimus PostgreSQL** Docker image
(`halex1985/postgresql:latest`) deployed via the Bitnami Helm chart.

Each test targets a specific defect in the custom image by comparing its
runtime behavior against the reference Bitnami PostgreSQL image.

| Test | Bug | What it checks |
|------|-----|----------------|
| `test_filesystem_permissions` | BUG-02 | No `Permission denied` errors in pod logs |
| `test_credential_security` | BUG-03 | No passwords exposed in plain text (CWE-532) |
| `test_excessive_logging` | BUG-04 | No shell trace (`set -x`) enabled by default |
| `test_build_toolchain` | BUG-06 | Standard `gcc (GCC)` toolchain, not MinimOS |

---

## Prerequisites

| Tool | Minimum version | Check |
|------|-----------------|-------|
| Python | 3.9+ | `python --version` |
| kubectl | 1.25+ | `kubectl version --client` |
| Helm | 3.x | `helm version` |
| Kubernetes cluster | any (minikube, kind, Docker Desktop, etc.) | `kubectl cluster-info` |

> **Note:** `kubectl` must be configured and connected to a running cluster
> before you run the tests.

---

## Run Instructions: How to set up and execute the test suite

### Set up

1. **Clone the repository and go into the project folder:**
   ```bash
   git clone https://github.com/almi131/minimus-qa.git
   cd minimus-qa
   ```

2. **Create a virtual environment and install dependencies:**

   **Linux / macOS:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   **Windows (PowerShell):**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

   **Windows (Git Bash):**
   ```bash
   python -m venv .venv
   source .venv/Scripts/activate
   pip install -r requirements.txt
   ```

3. **Add the Bitnami Helm repo (one-time):**
   ```bash
   helm repo add bitnami https://charts.bitnami.com/bitnami
   helm repo update
   ```

### Execute the test suite

From the project root, with the virtual environment activated:

```bash
pytest
```

This deploys the custom image via Helm, collects pod logs, runs all 4 tests, and cleans up. No extra arguments are required.

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/almi131/minimus-qa.git
cd minimus-qa
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv .venv
```

Activate the virtual environment:

- **Linux / macOS:** `source .venv/bin/activate`
- **Windows (PowerShell):** `.\.venv\Scripts\Activate.ps1`
- **Windows (Git Bash):** `source .venv/Scripts/activate`

Then install:

```bash
pip install -r requirements.txt
```

### 3. Add the Bitnami Helm repo (one-time setup)

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### 4. Run the tests

From the project root (with venv activated):

```bash
pytest
```

This will:
1. Create the `minimus-qa` namespace (if it doesn't exist)
2. Deploy `halex1985/postgresql:latest` via `helm install`
3. Wait for PostgreSQL to be ready and collect pod logs
4. Run all 4 tests against the collected logs
5. Clean up the Helm release and PVC automatically

---

## Expected Output

All 4 tests should **FAIL** — each one detects a real defect in the custom image:

```
test_helm_bugs.py::TestHelmBugs::test_filesystem_permissions   FAILED
test_helm_bugs.py::TestHelmBugs::test_credential_security      FAILED
test_helm_bugs.py::TestHelmBugs::test_excessive_logging        FAILED
test_helm_bugs.py::TestHelmBugs::test_build_toolchain          FAILED
```

> **FAIL = defect found** in the custom image.
> If a test passes, it means that specific bug is not present (or has been fixed).

---

## Project Structure

```
minimus-qa/
├── conftest.py          # Helm deploy/teardown fixture (helm_logs)
├── test_helm_bugs.py    # 4 test cases (BUG-02, 03, 04, 06)
├── pytest.ini           # Pytest configuration
├── requirements.txt     # Python dependencies (pytest==9.0.2)
├── .gitignore
└── README.md
```

---

## Running in PyCharm

1. Open the `minimus-qa` folder as a project
2. Set the project interpreter to the `.venv` virtual environment
3. The test runner is already configured to use **pytest**
4. Right-click `test_helm_bugs.py` → **Run 'pytest in test_helm_bugs.py'**
   — or use the **"All Helm Bug Tests"** run configuration from the dropdown
