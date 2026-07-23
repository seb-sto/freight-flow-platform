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

## uv over pip / Poetry

Python dependency management uses `uv` rather than a `requirements.txt` + `pip` workflow or Poetry.

**Why uv?**

- **Speed** — uv resolves and installs dependencies significantly faster than pip, which matters when `great-expectations` alone pulls in a large dependency tree.
- **Single source of truth** — `pyproject.toml` plus a committed `uv.lock` gives every contributor byte-identical dependency versions, which `requirements.txt` alone doesn't guarantee.
- **Built-in virtualenv management** — `uv sync` creates and populates `.venv` in one step, replacing the manual `python -m venv` + `pip install -r requirements.txt` sequence.

**Trade-off:** uv is newer than pip/Poetry and less universally known, though it is rapidly becoming a standard in the Python data engineering ecosystem.

---

## Great Expectations over dbt Tests Alone

Both dbt tests and Great Expectations are used for data quality, serving different purposes.

**dbt tests** validate the *output* of transformations — they check that the models produce correct results (unique keys, no nulls, referential integrity). They run after dbt transforms.

**Great Expectations** validates the *input* data before transformations run — it checks that the raw data from the source matches expectations (row counts, value ranges, schema conformity). It acts as a gate between layers.

Using only dbt tests would mean a corrupted source file could silently propagate through the pipeline before being caught. GE catches problems at the bronze → silver boundary before any transformation work is done.

**Trade-off:** GE is a heavy dependency with a steep configuration curve. For simpler pipelines, dbt tests alone are sufficient.

### GE v1.x programmatic API over CLI/file-based suites

The project originally planned to store Great Expectations suites as versioned JSON files under `src/quality/expectations/` and `src/quality/checkpoints/`, following the pre-1.0 GE convention. During implementation it became clear that **GE v1.x removed the CLI (`great_expectations init`) and the file-based expectation suite workflow entirely**, replacing it with a fully programmatic Python API (`gx.get_context()`, `context.suites.add()`, `context.checkpoints.add()`).

The two quality gates (`src/quality/bronze_silver_checkpoint.py` and `src/quality/silver_gold_checkpoint.py`) define their expectation suites, batch definitions, and checkpoints entirely in code and run as standalone scripts returning a process exit code — `0` for pass, `1` for fail — which Airflow's `BashOperator` interprets natively. The originally planned `expectations/` and `checkpoints/` folders were removed since they have no role in the v1.x workflow.

**Trade-off:** less separation between expectation configuration and code compared to the old JSON-suite pattern, but avoids maintaining two parallel definitions of the same checks.

---

## SHA-256 Deduplication

Every ingested file is hashed with SHA-256 before upload. If the hash matches the stored metadata on an existing MinIO object, the upload is skipped.

**Why this matters:** the FAF5 dataset is 291 MB. Without deduplication, every pipeline run would re-upload 291 MB to MinIO even if the source file hasn't changed. At quarterly refresh cadence this is manageable, but for weekly indicator data it adds up.

The hash is stored as object metadata (`ExtraArgs={"Metadata": {"sha256": hash}}`) alongside the file, making it retrievable without downloading the file itself. Every ingestion run — whether it uploads or skips — also appends an entry to a `manifest.json` file in the bronze bucket, giving full data lineage: source URL, filename, MinIO path, timestamp, row count, hash, and whether the run was skipped.

---

## curl subprocess over Python HTTP clients for downloads

Both the FAF5 and TransBorder ingestors originally used `httpx` to download source files. In practice, `httpx` (and subsequently `requests`/`urllib3`) failed with TLS-level connection resets (`ConnectError`, `Connection reset by peer`) when downloading from `faf.ornl.gov`, and returned HTTP 403 from an Akamai bot-detection layer when downloading from `bts.gov` regardless of headers set (User-Agent, Accept, Referer).

Since `curl` succeeded against both endpoints where every Python HTTP client failed, both ingestors call `curl` via `subprocess.run()` for the actual file download, then hand off to Python (`pandas`, `zipfile`) for validation and processing. This is a deliberate trade-off of "pure Python" purity for pragmatism — curl's TLS and HTTP/2 stack handles edge cases (ALPN negotiation, connection reuse patterns) that some Python HTTP libraries are more sensitive to when talking to certain server configurations.

**Trade-off:** introduces a dependency on the `curl` binary being present in both the local dev environment and the Docker image, rather than a pure pip-installable dependency. This is documented so it isn't mistaken for an oversight.

---

## TransBorder Manual Download

The BTS TransBorder data cannot be downloaded programmatically because the BTS website is protected by Akamai's bot detection system, which returns HTTP 403 for automated requests regardless of headers, even when using `curl` with a full browser-like header set.

**Approaches considered:**

1. **Browser automation (Selenium/Playwright)** — would work but adds significant complexity (browser binary, driver management, fragile selectors) for a low-frequency download task.

2. **Rotating proxies / header spoofing** — unreliable and against the spirit of responsible data access.

3. **Manual download + local processing** — chosen approach. Files are downloaded once via browser and saved to `data/raw/transborder/` with a standardized naming convention (`transborder_{yyyy}_{mm}.zip`). The ingestor checks for the file locally first and raises a clear, actionable error with the exact expected path and source URL if it's missing, rather than attempting a download that will fail.

This is a legitimate pattern in production data engineering. Many enterprise source systems have access controls that require human-initiated downloads (SFTP with MFA, portal downloads behind SSO). Pipelines are designed to process files once they arrive locally rather than assuming end-to-end automation.

**Note on url_builder.py:** a utility module was initially built to programmatically construct candidate BTS URLs, accounting for the inconsistent naming patterns observed across months (e.g., `Feb2025.zip` vs `February2025.zip` vs `March2026.zip`). Once the Akamai 403 issue was confirmed to block all programmatic access regardless of URL correctness, this module became dead code and was removed. The URL pattern logic is documented here for reference should BTS's access policy change in future.

---

## Supply Chain Indicators: dataset pivot after discovering silent data quality failure

The Week 7 build plan called for ingesting the BTS Supply Chain & Freight Indicators dataset (Socrata dataset ID `h7pv-kjj5`) to power disruption anomaly detection. The file downloaded successfully, passed schema validation (all expected columns present), and loaded cleanly into Postgres — but every single value in the `pct_change_from_baseline` column was `0`. The dataset was a COVID-era dashboard feed that appears to no longer be updated with real values.

This is a genuine data quality failure that schema validation alone cannot catch: the file was well-formed and structurally correct, but analytically worthless. The downstream `fct_disruption_indicators` model built on this data produced a Z-score calculation with zero variance — every anomaly check silently returned `NULL` rather than an error, because standard deviation of a constant is zero and the model divides by it.

**Resolution:** switched to the BTS Transportation Services Index dataset (Socrata dataset ID `bw6n-ddqk`), an actively-maintained monthly index covering truck VMT, rail carloads, pipeline throughput, waterborne freight, and a composite Freight TSI back to January 2000. This required rebuilding the ingestor's expected schema, the raw Postgres table (63 columns from the TSI feed vs. 5 from the original), and the silver/gold models — but produced real, verifiable signal: April 2020 shows a truck VMT Z-score of -3.89 against its seasonal baseline, correctly flagged as a `HIGH` severity anomaly and clearly attributable to COVID-19.

**Lesson applied going forward:** schema validation (columns present, types correct) is necessary but not sufficient. Value-distribution sanity checks — even a simple "is there any variance in this column" — would have caught this before building downstream models on top of it.

---

## Wide-to-long unpivot materialized as a table, not a view

FAF5 stores tonnage, value, and ton-mile metrics in wide format — one column per year (`tons_2017` ... `tons_2024`). The `stg_faf_shipments_long` model unpivots this into long format (one row per shipment per year) using a Jinja `{% for year in years %}` loop generating a `UNION ALL` across 8 years, expanding 2.67M wide rows into 21.3M long rows.

This model was initially materialized as a `view` (the default for the staging layer). Because `fct_corridor_flows` joins against it with a `GROUP BY` across multiple dimension tables, every run of `fct_corridor_flows` was re-executing the full 21M-row unpivot from scratch, contributing to a ~4 minute build time.

Overriding the materialization to `table` specifically for `stg_faf_shipments_long` in `dbt_project.yml` (while every other staging model remains a `view`) means the unpivot runs once (~35 seconds) and `fct_corridor_flows` reads from a physical table instead. This did not eliminate the multi-minute gold-layer build time — the bottleneck is the join and window-function work on 21M rows on a single local Postgres instance without partitioning — but it removed one redundant full-table scan per run.

**Trade-off:** the table must be explicitly rebuilt (`dbt run --select stg_faf_shipments_long`) whenever `stg_faf_shipments` changes, whereas a view would always reflect the latest upstream data automatically.

---

## Post-build indexes via dbt post-hooks, not pre-built indexes

An early attempt at improving `fct_corridor_flows` build performance added B-tree indexes directly on `stg_faf_shipments_long` (the 21M-row source table) before running the gold model. This made the build **slower** — 527 seconds versus 216 seconds without the indexes — because Postgres has to maintain every index on each row during the table's own `CREATE TABLE AS SELECT`, and the gold model rebuilds this table from scratch on every run rather than incrementally updating it.

The indexes were reverted on the source table. Instead, `fct_corridor_flows` uses a dbt `post-hook` in `dbt_project.yml` to create indexes (`origin_state`, `commodity_category`, `year`) **after** the table is fully built:

```yaml
fct_corridor_flows:
  +post-hook:
    - "CREATE INDEX IF NOT EXISTS idx_cf_origin_state ON {{ this }} (origin_state)"
```

This correctly separates the write-heavy build phase (no indexes, fast bulk insert) from the read-heavy query phase (indexed, fast Grafana dashboard queries) — indexes only pay for themselves when a table is queried far more often than it's rewritten, which is true for Grafana's dashboard refreshes but not true for dbt's full-rebuild-every-run pattern on this dataset.

---

## Docker service networking: dual dbt/GE targets for local vs. containerized execution

Every component that connects to Postgres or MinIO — the Python ingestors, the two GE checkpoint scripts, and dbt itself — needs a different hostname depending on where it's running:

- **Local execution** (`python -m src.ingestion.faf_ingestor` from a Mac terminal, or `dbt run --target dev`) needs `localhost`, since Docker's internal service names aren't resolvable from the host machine.
- **Containerized execution** (the same code running inside an Airflow task) needs the Docker Compose service name (`postgres`, `minio`), since `localhost` inside a container refers to the container itself, not the host or sibling containers.

This was resolved with two parallel mechanisms:

1. **Python code** (`src/utils/s3_client.py`, the GE checkpoint scripts) reads `POSTGRES_HOST` and `MINIO_ENDPOINT` from environment variables rather than hardcoding either value. The `.env` file (used for local runs via `python-dotenv`) sets these to `localhost`; `docker-compose.yml`'s `x-airflow-common` environment block overrides `POSTGRES_HOST` to `postgres` specifically for the Airflow containers, so the same code resolves correctly in both contexts without any code branching.

2. **dbt** uses two named targets in `profiles.yml` — `dev` (host: `localhost`, for local CLI runs) and `docker` (host: `postgres`, for Airflow-triggered runs via `--target docker --profiles-dir`). A third target, `ci`, was added for GitHub Actions, where the Postgres service container is reachable at `localhost` from the runner but credentials are injected via GitHub Secrets rather than hardcoded.

**Trade-off:** requires remembering to pass `--target` correctly and keeping the environment variable overrides in `docker-compose.yml` in sync with `.env` — a source of several debugging sessions during the Airflow DAG build (Week 4) before the pattern was made consistent across every component.

---

## Docker Compose over Kubernetes

The entire stack runs in Docker Compose rather than Kubernetes.

**Why:** this is a local development and portfolio project. Kubernetes adds significant operational overhead (cluster management, ingress, persistent volume claims, service accounts) that is unnecessary when running on a single machine. Docker Compose provides sufficient service isolation, networking, and volume management for this use case.

**Path to Kubernetes:** the Terraform configuration (optional stretch goal) targets AWS ECS Fargate, which provides container orchestration without the Kubernetes overhead. A full Kubernetes migration would be the next step for a production multi-tenant deployment.

---

## Python Version Pinning

The project pins Python 3.11 via a `.python-version` file in the repository root. This ensures all contributors use the same Python version regardless of their system Python.

**Why 3.11 over 3.12?** boto3 and several other dependencies had stability issues with 3.12 at the time of development. 3.11 is the current LTS-equivalent for the AWS SDK ecosystem.