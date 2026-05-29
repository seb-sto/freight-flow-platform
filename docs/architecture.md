# Architecture & Design Decisions

This document explains the key architectural choices made in the Freight Flow Intelligence Platform, including the trade-offs considered and alternatives rejected.

---

## Medallion Architecture (Bronze / Silver / Gold)

The platform follows a three-layer medallion architecture where data is progressively refined from raw to business-ready.

**Why medallion over a single-hop approach?**

A single-hop pipeline (raw CSV → aggregated table) is faster to build but creates several problems at scale: debugging failures is harder because you can't inspect intermediate state, re-running transformations requires re-ingesting raw data, and schema changes in source data cascade unpredictably into business tables.

The medallion pattern solves this by making each layer independently queryable and replayable. If a dbt model in the gold layer is wrong, you fix and re-run just that model — the bronze and silver layers are untouched. This also means data quality gates can be applied at each transition, catching problems as early as possible.

**Layer responsibilities:**
- **Bronze** — raw data exactly as received, never modified, partitioned by source and date
- **Silver** — cleaned, typed, deduplicated, normalized; safe to query but not yet aggregated
- **Gold** — business-ready aggregations optimized for dashboard queries

---

## Airflow over Prefect / Dagster

All three are mature orchestration tools. Airflow was chosen for this project for one primary reason: it is the most widely deployed orchestration platform in the job postings this project targets (OxyChem, Kyndryl). Demonstrating Airflow fluency has higher signal value for those interviews than demonstrating Prefect or Dagster.

**Trade-offs accepted:**
- Airflow's UI is older and less polished than Prefect Cloud or Dagster's asset-based UI
- Airflow's local setup is heavier (requires its own Postgres metadata database)
- The TaskFlow API in Airflow 2.x significantly improves the developer experience over the older operator-heavy syntax

**When Prefect would be better:** greenfield projects where team familiarity isn't a constraint, or projects that need dynamic task generation at runtime (Prefect handles this more elegantly).

---

## MinIO over Direct Postgres Staging

Raw files are landed in MinIO (S3-compatible object storage) before being loaded into Postgres, rather than loading directly from the download into Postgres.

**Why the extra hop?**

Object storage as a bronze layer provides three things a direct-load approach doesn't:

1. **Immutable raw archive** — the original file is always available for reprocessing. If a dbt model has a bug that corrupts the silver layer, you can replay from bronze without re-downloading from the source.

2. **Decoupled ingestion and transformation** — the ingestion job and the dbt transformation job are independent. Ingestion can succeed even if Postgres is temporarily unavailable.

3. **Cost-effective storage** — in a cloud deployment, S3 storage is cheaper than RDS Postgres storage for large raw CSV files.

**Trade-off:** adds operational complexity (another service to run) and an extra step in the pipeline. For very small datasets this overhead is unnecessary.

---

## dbt over Raw SQL

Transformations are implemented in dbt rather than raw SQL scripts executed by Airflow operators.

**Why dbt?**

- **Dependency graph** — dbt automatically determines model execution order based on `ref()` calls. No manual dependency management.
- **Built-in testing** — `not_null`, `unique`, `accepted_values`, and `relationships` tests run as part of `dbt test` with no extra code.
- **Documentation** — column descriptions in YAML files generate a data catalog automatically.
- **Reproducibility** — `dbt build` is idempotent; running it twice produces the same result.

**Trade-off:** dbt adds a learning curve and requires a separate project structure. For one-off queries or very simple transformations, raw SQL is faster to write.

---

## Great Expectations over dbt Tests Alone

Both dbt tests and Great Expectations are used for data quality, serving different purposes.

**dbt tests** validate the *output* of transformations — they check that the models produce correct results (unique keys, no nulls, referential integrity). They run after dbt transforms.

**Great Expectations** validates the *input* data before transformations run — it checks that the raw data from the source matches expectations (row counts, value ranges, schema conformity). It acts as a gate between layers.

Using only dbt tests would mean a corrupted source file could silently propagate through the pipeline before being caught. GE catches problems at the bronze → silver boundary before any transformation work is done.

**Trade-off:** GE is a heavy dependency with a steep configuration curve. For simpler pipelines, dbt tests alone are sufficient.

---

## SHA-256 Deduplication

Every ingested file is hashed with SHA-256 before upload. If the hash matches the stored metadata on an existing MinIO object, the upload is skipped.

**Why this matters:** the FAF5 dataset is 291 MB. Without deduplication, every pipeline run would re-upload 291 MB to MinIO even if the source file hasn't changed. At quarterly refresh cadence this is manageable, but for weekly indicator data it adds up.

The hash is stored as object metadata (`ExtraArgs={"Metadata": {"sha256": hash}}`) alongside the file, making it retrievable without downloading the file itself.

---

## TransBorder Manual Download

The BTS TransBorder data cannot be downloaded programmatically because the BTS website is protected by Akamai's bot detection system, which returns HTTP 403 for automated requests regardless of headers.

**Approaches considered:**

1. **Browser automation (Selenium/Playwright)** — would work but adds significant complexity (browser binary, driver management, fragile selectors) for a low-frequency download task.

2. **Rotating proxies / header spoofing** — unreliable and against the spirit of responsible data access.

3. **Manual download + local processing** — chosen approach. Files are downloaded once via browser and saved to `data/raw/transborder/` with a standardized naming convention. The ingestor handles all subsequent processing automatically.

This is a legitimate pattern in production data engineering. Many enterprise source systems have access controls that require human-initiated downloads (SFTP with MFA, portal downloads behind SSO). Pipelines are designed to process files once they arrive locally rather than assuming end-to-end automation.

**Mitigation:** a clear error message with download instructions is raised if the expected file is not found locally, so the manual step is never silently skipped.

**Note on url_builder.py:** a utility module was initially built to programmatically construct candidate BTS URLs, accounting for the inconsistent naming patterns observed across months (e.g., `Feb2025.zip` vs `February2025.zip`). Once the Akamai 403 issue was confirmed, this module became dead code and was removed. The URL pattern logic is documented here for reference should the BTS access policy change in future.

---

## Docker Compose over Kubernetes

The entire stack runs in Docker Compose rather than Kubernetes.

**Why:** this is a local development and portfolio project. Kubernetes adds significant operational overhead (cluster management, ingress, persistent volume claims, service accounts) that is unnecessary when running on a single machine. Docker Compose provides sufficient service isolation, networking, and volume management for this use case.

**Path to Kubernetes:** the Terraform configuration (optional stretch goal) targets AWS ECS Fargate, which provides container orchestration without the Kubernetes overhead. A full Kubernetes migration would be the next step for a production multi-tenant deployment.

---

## Python Version Pinning

The project pins Python 3.11 via a `.python-version` file in the repository root. This ensures all contributors use the same Python version regardless of their system Python.

**Why 3.11 over 3.12?** boto3 and several other dependencies had stability issues with 3.12 at the time of development. 3.11 is the current LTS-equivalent for the AWS SDK ecosystem.
