# Midterm Data Pipeline — Hybrid ELT

A practical Big Data midterm project implementing a hybrid ELT pipeline for processing, validating, classifying, and reporting order data.

> **Project note:** This README documents the project as it was most recently executed and tested.

---

## ⚠️ Important Notes Before Running

The project has been tested with multiple dataset sizes:

- The complete dataset.
- A large version of approximately **1 GB**.
- A smaller version of approximately **200 MB**.
- A version of approximately **400 MB** — this is the **latest dataset used for execution and testing**.

For easier testing, the latest results described in the project are based on the **400 MB dataset**, because it was the most recently processed version.

### Dataset File Names

To run the project without unnecessary configuration problems, make sure the input data files use the **same file names expected by the project**.

These names and paths are defined in:

```text
settings.py
```

> **Important:** Do not assume that the original machine-specific paths will work on another computer. Update the project configuration to match the local environment.

---

## ⚙️ Environment-Specific Configuration

During development, some execution problems were caused by differences in the local environment. Therefore, the project currently contains fixed paths for Java and Spark in:

```text
spark_loader.py
```

The current configuration is:

```python
# ============================================================
# Fixed paths for the development machine (Java 21 + Spark 4.2.0)
# ============================================================

JAVA_HOME = r"C:\Program Files\Java\jdk-21.0.12"
SPARK_HOME = r"C:\spark\spark-4.2.0-bin-hadoop3"

os.environ["JAVA_HOME"] = JAVA_HOME
os.environ["SPARK_HOME"] = SPARK_HOME
os.environ["HADOOP_HOME"] = SPARK_HOME
```

> **Important:** These are machine-specific Windows paths. If you run the project on another computer, update these paths or configure the environment variables according to that machine.

---

# 🏗️ Architecture

The project uses the following hybrid processing architecture:

```text
CSV
  │
  ▼
File Router
  │
  ├── Small files ──► Python Batch
  │
  └── Large files ──► PySpark
              │
              ▼
          orders_raw
              │
              ▼
      Quality / Classification
              │
       ┌──────┴─────────┐
       ▼                ▼
orders_validated   orders_quarantine
       │
       └──────┬─────────┘
              ▼
           Metrics
```

### Processing Strategy

- Default routing threshold: **200 MB**.
- Small files use `csv.DictReader` with batch processing, avoiding loading the entire file into memory.
- Large files use a Spark DataFrame with a fixed string schema and parallel MongoDB writes.
- `orders_raw` is stored before quality rules are applied.
- `orders_validated` uses `order_id` as a stable business key together with a Unique Index and Upsert.
- `orders_raw` is historical and can therefore contain multiple processing attempts.
- Every record associated with an `id_run` ends in either the **Validated/Corrected** path or **Quarantine**.
- Main results are stored in:

```text
reports/results.json
```

---

# 🧰 Environment & Requirements

## Requirements

The project requires:

- **Python 3.10+**
- **MongoDB**
- **Java / PySpark** when processing large files
- Python packages listed in:

```text
requirements.txt
```

---

# 📦 Installation

From inside the project directory, install the required Python packages:

```powershell
pip install -r requirements.txt
```

Then copy:

```text
example.env
```

to:

```text
.env
```

Update the `.env` values when necessary, especially:

- Data file paths
- MongoDB configuration
- Spark configuration

> **Important:** The project should not depend on machine-specific paths. Use the local project path and environment configuration of the computer where the project is being executed.

---

# ▶️ Phase 1 — Running the Pipeline

## Run the Project

Open PowerShell and navigate to the project directory:

```powershell
cd <project-folder>
```

Activate the virtual environment:

```powershell
.\venv_bd\Scripts\Activate.ps1
```

Run the main pipeline:

```powershell
python main.py
```

### If PowerShell Blocks Virtual Environment Activation

If PowerShell prevents the environment from running, execute:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Then activate the environment again:

```powershell
.\venv_bd\Scripts\Activate.ps1
```

> **Important:** Make sure the MongoDB service is running before starting the pipeline.

---

# 🧪 Creating a Smaller Test Dataset

A smaller sample can be generated without using Excel:

```powershell
python src/create_small_sample.py --input data/orders_huge_mixed_quality.csv --output data/orders_sample.csv --rows 100000
```

Then run the pipeline using the generated sample:

```powershell
$env:DATA_FILE="data/orders_sample.csv"
python main.py
```

## Running the Large Dataset

To process the large input file:

```powershell
$env:DATA_FILE="data/orders_huge_mixed_quality.csv"
python main.py
```

> **Important:** Do not manually edit the original CSV file. Generate test samples only through the provided script.

---

# 🍃 MongoDB

The MongoDB service must be running before starting the project.

The project uses the following database:

```text
bigdata_midterm
```

The pipeline creates or uses these collections:

```text
orders_raw
orders_validated
orders_quarantine
```

---

# 🔁 Idempotency

Re-running the same source data does **not** create duplicate business records in:

```text
orders_validated
```

This is achieved because:

- `order_id` is used as the stable business key.
- A Unique Index is used.
- Upsert operations are used.

However, `orders_raw` is intentionally **historical**. Therefore, it may contain multiple processing attempts for the same source data, according to the ELT requirements.

---

# ✅ Data Quality Rules

The project applies the following data-quality rules:

1. Arabic number normalization
2. Currency normalization
3. Thousands-separator normalization
4. Recognition of known price words
5. Phone-number normalization
6. Repair of repeated symbols in email addresses
7. Date standardization
8. Whitespace normalization
9. Status, payment, and delivery synonym normalization
10. Total recalculation from valid items and delivery charges

### Quality Handling

The system does not make corrections based on arbitrary guesses.

Major or unresolvable errors are sent to:

```text
orders_quarantine
```

with a clear error code.

---

# 🚀 Phase 2 — Final Requirements

## Run the API

After MongoDB is running and all dependencies are installed, start the API with:

```powershell
uvicorn src.phase2.api:app --host 127.0.0.1 --port 8000
```

The Swagger documentation is available at:

```text
http://127.0.0.1:8000/docs
```

---

# 🔌 Required API Endpoints

## System

### Health Check

```http
GET /health
```

---

## Pipeline

### Ingest

```http
POST /ingest
```

This endpoint calls the original midterm pipeline.

---

## Indexes

```http
POST /indexes
GET /indexes/status
```

---

## Queries

```http
GET /queries
GET /queries/{name}
GET /queries/{name}/explain
```

The project contains five registered queries:

1. `orders_by_city`
2. `orders_by_status`
3. `orders_by_date`
4. `customer_orders`
5. `city_status_orders`

The queries support parameters such as:

- `city`
- `status`
- `order_date`
- `customer_id`
- `limit`

---

# 🔎 Queries, Indexes & Explain Reports

The five queries are defined in:

```text
src/phase2/queries.py
```

The project defines seven indexes in:

```text
src/phase2/indexes.py
```

One of the indexes is the following compound index:

```text
city + status
```

## Explain Performance Report

A report comparing query execution performance before and after the Phase 2 indexes can be generated with:

```powershell
python -m src.phase2.explain_report
```

This creates:

```text
reports/phase2_explain.json
```

The report contains `executionStats` from before and after the Phase 2 indexes are created.

---

# 📊 Aggregation Reports

The project provides independent aggregation reports for:

- `sales_by_city`
- `sales_by_status`
- `sales_by_date`
- `top_customers`
- `top_cities`

They can be accessed through:

```http
GET /aggregations
GET /aggregations/{name}
```

---

# 🧱 Materialized Views

The project provides four Materialized Views:

- `mv_sales_by_city`
- `mv_sales_by_status`
- `mv_sales_by_date`
- `mv_top_customers`

## Refresh Strategies

The views use the following refresh strategies:

| Materialized View | Refresh Strategy |
|---|---|
| `mv_sales_by_city` | Incremental refresh |
| `mv_sales_by_status` | Incremental refresh |
| `mv_sales_by_date` | Full-compatible refresh |
| `mv_top_customers` | Full-compatible refresh |

## View Endpoints

List all Materialized Views:

```http
GET /materialized-views
```

Get a specific Materialized View:

```http
GET /materialized-views/{name}
```

Refresh the views:

```http
POST /refresh-mv
```

### Incremental Refresh

For incremental refresh, the process uses the:

```text
updated_at
```

watermark.

Delta operations are recorded in:

```text
incremental_events
```

---

# ⏰ Scheduled Jobs

The project provides two scheduled jobs:

```text
refresh_materialized_views
periodic_aggregation_report
```

## List Jobs

```http
GET /jobs
```

## Run a Job Manually

```http
POST /jobs/{name}/run
```

Each job records:

- Start time
- End time
- Status
- Result or error

The job information is stored in:

```text
reports/phase2_jobs.jsonl
```

---

# 🔄 Background Scheduler

The background scheduler can be enabled together with the API using:

```text
START_PHASE2_SCHEDULER=true
```

The execution intervals are configured using:

```text
PHASE2_JOB_INTERVAL_SECONDS
PHASE2_REPORT_INTERVAL_SECONDS
```

The default interval is:

```text
3600
```

This means the jobs run approximately **once every hour** when the default configuration is used.

---

# 🧪 Phase 2 Verification

After starting the API, open Swagger:

```text
http://127.0.0.1:8000/docs
```

Use the Swagger interface to inspect and test the available endpoints.

The following areas should be verified:

- Health check
- Queries
- Index status
- Explain report
- Aggregations
- Materialized Views
- Scheduled jobs

---

# 📁 Output & Reports

The project stores generated reports and execution results under:

```text
reports/
```

Important output files include:

```text
reports/results.json
reports/phase2_explain.json
reports/phase2_jobs.jsonl
```

The `reports/` directory contains the results and reports generated during project execution.

---

# ⚠️ Final Important Notes

1. Do **not** rely on the original Windows paths from the development machine.
2. Configure `.env` according to the computer where the project will run.
3. Make sure MongoDB is running before starting the pipeline or API.
4. Do not manually modify the original CSV files.
5. Use the provided sample-generation script when a smaller dataset is required.
6. Make sure the input file names match the names expected by the project configuration.
7. The `reports/` directory contains the generated execution results and reports.
8. If Java or Spark is installed in a different location, update the configuration in `spark_loader.py`.

---

# 📌 Quick Start

For a standard Phase 1 execution:

```powershell
cd <project-folder>

.\venv_bd\Scripts\Activate.ps1

pip install -r requirements.txt

python main.py
```

For Phase 2:

```powershell
uvicorn src.phase2.api:app --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000/docs
```

---

## Project Summary

The project implements a hybrid ELT architecture that routes data according to file size, processes small files with Python and large files with PySpark, stores raw data before validation, separates validated and quarantined records, and provides MongoDB-based queries, indexes, aggregations, Materialized Views, Explain reports, and scheduled jobs.

