# OmniBioAI HPC Policy Engine

`omnibioai-hpc-policy-engine` is a production-oriented compute governance and quota enforcement service for the OmniBioAI ecosystem.

It provides:

* HPC-aware authorization
* GPU/CPU quota enforcement
* cluster partition access control
* compute governance
* workload policy evaluation
* zero-trust execution decisions
* scheduler-aware workload validation

The service is designed for distributed bioinformatics, AI, and HPC workflows running across:

* local infrastructure
* Slurm clusters
* DGX systems
* Kubernetes
* cloud batch systems

---

# Architecture Role

This service is NOT an authentication system.

Authentication and identity belong to:

* `omnibioai-auth`
* `omnibioai-iam-client`

Authorization logic belongs to:

* `omnibioai-policy-engine`

This service specifically handles:

> Compute-aware resource governance and execution feasibility.

This service does not currently authenticate JWTs itself. The policy and
quota request models accept a caller-supplied `roles` list, so the API must
only be exposed behind a trusted gateway or service that has already
authenticated the caller and populated those roles. Do not expose these
routes as a public authorization boundary until local IAM verification is
added.

---

# Core Responsibilities

The HPC Policy Engine evaluates whether a workload can execute safely and within governance constraints.

Examples:

* GPU access restrictions
* CPU-hour quota enforcement
* DGX partition authorization
* project compute budgets
* concurrent job limits
* cluster routing policies
* expensive workload prevention

---

# Example Decision Flow

```text
User Request
     ↓
API Gateway
     ↓
IAM Authentication
     ↓
Policy Engine (RBAC/ABAC)
     ↓
HPC Policy Engine
     ↓
TES / Scheduler
```

---

# Features

## Compute Governance

* CPU quota validation
* GPU quota validation
* memory governance
* concurrent job control

## HPC-Aware Policies

* DGX partition restrictions
* Slurm partition governance
* GPU role enforcement
* cluster-specific access policies

## Distributed Architecture

* FastAPI-based async APIs
* Redis configuration reserved for future decision caching
* scalable stateless design
* scheduler abstraction layer

## Zero-Trust Execution

Every workload request is evaluated independently.

No implicit trust exists between services.

---

# Repository Structure

```text
omnibioai-hpc-policy-engine/
│
├── app/
│   ├── api/
│   │   ├── routes_policy.py
│   │   ├── routes_quota.py
│   │   └── deps.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── gpu.py
│   │   ├── policies.py
│   │   ├── quota.py
│   │   └── scheduler.py
│   │
│   ├── db/
│   │   ├── models.py
│   │   └── session.py
│   │
│   ├── models/
│   │   ├── decision.py
│   │   ├── job.py
│   │   └── quota.py
│   │
│   ├── services/
│   │   ├── quota_service.py
│   │   ├── scheduler_service.py
│   │   └── usage_service.py
│   │
│   └── main.py
│
├── tests/
├── requirements.txt
└── README.md
```

---

## Testing

```bash
cd ~/Desktop/machine/omnibioai-hpc-policy-engine
pytest tests/ -v --cov=.

# Covers quota service, usage service, policy routes,
# quota routes, and HPC job evaluation. Review the measured test output
# rather than relying on a fixed count or coverage percentage.
```

---

# API Endpoints

---

## Health Check

### GET `/health`

Returns service health status.

```json
{"status": "ok"}
```

---

# Quota APIs

---

## POST `/quota/check`

Evaluates whether a workload exceeds compute quotas.

### Request

```json
{
  "user_id": "u123",
  "cpu_hours": 12,
  "gpu_hours": 2,
  "gpus": 1,
  "roles": ["gpu_user"]
}
```

### Response

```json
{
  "allow": true,
  "reason": "quota ok",
  "remaining_cpu_hours": 108,
  "remaining_gpu_hours": 22
}
```

---

# Job Evaluation APIs

---

## POST `/jobs/evaluate`

Evaluates HPC-specific execution policies.

### Request

```json
{
  "user_id": "u123",
  "partition": "dgx-a100",
  "gpus": 1,
  "memory_gb": 128,
  "roles": ["gpu_user", "dgx_access"]
}
```

### Response

```json
{
  "allow": true,
  "reason": "job approved",
  "partition": "dgx-a100"
}
```

---

# Policy Examples

---

## GPU Access Control

```python
if request.gpus > 0:
    if "gpu_user" not in roles:
        deny("GPU access denied")
```

---

## DGX Partition Enforcement

```python
if request.partition == "dgx-a100":
    if "dgx_access" not in roles:
        deny("DGX partition denied")
```

---

## CPU Quota Enforcement

```python
if request.cpu_hours > remaining_cpu:
    deny("CPU quota exceeded")
```

---

# Scheduler Integration

The scheduler layer is abstracted through:

```text
app/core/scheduler.py
```

This enables future integrations with:

* Slurm
* Kubernetes
* AWS Batch
* Azure Batch
* PBS/Torque
* custom HPC schedulers

---

# Database

Current implementation uses SQLAlchemy.

The current implementation constructs a MySQL/PyMySQL URL directly in
`app/db/session.py`. MySQL-compatible deployments are supported today.
MariaDB and PostgreSQL are not currently selectable without code changes.

---

# Environment Variables

| Variable              | Description          | Default              |
| --------------------- | -------------------- | -------------------- |
| `MYSQL_HOST`          | Database host        | `mysql`              |
| `MYSQL_PORT`          | Database port        | `3306`               |
| `MYSQL_DB`            | Database name        | `omnibioai_hpc`      |
| `MYSQL_USER`          | Database user        | `root`               |
| `MYSQL_PASSWORD`      | Database password    | `root`               |
| `REDIS_URL`           | Redis URL            | `redis://redis:6379` |
| `DEFAULT_CPU_HOURS`   | Default CPU quota    | `120`                |
| `DEFAULT_GPU_HOURS`   | Default GPU quota    | `24`                 |
| `MAX_CONCURRENT_JOBS` | Concurrent job limit | `5`                  |

The application reads the `MYSQL_*` variables above. The current Studio
Compose entry uses `DB_HOST`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` for
this service, so those names must be reconciled before relying on custom
database credentials in Compose; otherwise the application falls back to
its `MYSQL_*` defaults.

---

## Running

### Via OmniBioAI Studio (recommended)

```bash
cd ~/Desktop/machine/omnibioai-studio
docker compose up -d hpc-policy-engine
```

Access (internal only):
`http://hpc-policy-engine:8003` (Docker internal network)

The service also exposes `/` with a running-status response and `/docs` with
the generated Swagger UI. The health endpoint is `/health`.

### Standalone (development)

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

### Health check

```bash
curl http://localhost:8003/health
# {"status": "ok"}
```

### Current schema behavior

The application currently calls `Base.metadata.create_all()` during startup.
This creates missing tables but is not a versioned migration workflow. Treat
the database as service-owned and verify schema changes carefully before
production deployment; Alembic migrations are not currently included in this
repository.

---

## Roadmap

| Feature | Status |
|---------|--------|
| CPU/GPU quota enforcement | ✓ Stable |
| DGX partition access control | ✓ Stable |
| Concurrent job limits | ✓ Stable |
| MySQL-backed quota tracking | ✓ Stable |
| Prometheus metrics endpoint | Not exposed yet |
| Redis decision caching | Planned |
| Cost-aware routing | Planned v0.4 |
| Per-team quotas | Planned v0.5 |
| Fair-share scheduling | Planned v0.5 |

---

# Ecosystem Integration

Designed to integrate with:

* `omnibioai-auth`
* `omnibioai-policy-engine`
* `omnibioai-api-gateway`
* `omnibioai-security-audit`
* `omnibioai-tes`
* `omnibioai-workbench`

---

# Security Model

This service follows a zero-trust architecture:

* every request evaluated independently by the policy checks
* authentication is expected to happen upstream
* no implicit scheduler trust
* policy enforcement before execution
* distributed compute governance
* centralized execution auditing

---

## Related Services

| Service | Role |
|---------|------|
| `omnibioai-api-gateway` | Calls `/jobs/evaluate` for compute requests |
| `omnibioai-policy-engine` | RBAC/ABAC decisions (called before HPC check) |
| `omnibioai-auth` | Identity source (user roles) |
| `omnibioai-tes` | Primary consumer — submits jobs after HPC approval |
| `omnibioai-security-audit` | Receives HPC governance audit events |
| `omnibioai-studio` | Manages hpc-policy-engine container lifecycle |

---

# License

Apache License 2.0

---

# OmniBioAI Ecosystem

OmniBioAI is a modular AI-native bioinformatics platform designed for:

* genomics
* transcriptomics
* metabolomics
* multi-omics
* AI-assisted biomedical analysis
* scalable HPC workflows
* distributed scientific computing

This service provides the compute governance layer of the ecosystem.
