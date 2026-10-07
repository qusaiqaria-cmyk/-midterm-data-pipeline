import os


# ============================================================
# Phase 2 - Incremental Loading Configuration
# ============================================================

# Delta input file
DELTA_FILE = os.getenv(
    "DELTA_FILE",
    "data/delta_orders.csv"
)

# Version field used to determine the newest record
VERSION_FIELD = os.getenv(
    "VERSION_FIELD",
    "version"
)

# Hash field used for idempotency/change detection
RECORD_HASH_FIELD = os.getenv(
    "RECORD_HASH_FIELD",
    "record_hash"
)

# MongoDB collection for incremental processing runs
INCREMENTAL_RUNS_COLLECTION = os.getenv(
    "INCREMENTAL_RUNS_COLLECTION",
    "incremental_runs"
)

# MongoDB collection for incremental operation history
INCREMENTAL_EVENTS_COLLECTION = os.getenv(
    "INCREMENTAL_EVENTS_COLLECTION",
    "incremental_events"
)

# Materialized report collections
MATERIALIZED_CITY_SALES = os.getenv(
    "MATERIALIZED_CITY_SALES",
    "report_city_sales"
)

MATERIALIZED_STATUS_SALES = os.getenv(
    "MATERIALIZED_STATUS_SALES",
    "report_status_sales"
)

# Stable business key
BUSINESS_KEY = "order_id"