import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from src.mongo_setup import connect
from src.phase2.indexes import ensure_phase2_indexes
from src.phase2.materialized_views import refresh_all
from src.phase2.aggregations import run_aggregation

LOG_FILE = Path("reports/phase2_jobs.jsonl")

def _log(result):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")

def _execute(name, fn):
    started = datetime.now(timezone.utc)
    try:
        client, db = connect()
        try:
            result = fn(db)
            status = "success"
        finally:
            client.close()
        finished = datetime.now(timezone.utc)
        record = {"name": name, "status": status, "started_at": started.isoformat(), "finished_at": finished.isoformat(), "result": result}
    except Exception as exc:
        finished = datetime.now(timezone.utc)
        record = {"name": name, "status": "failed", "started_at": started.isoformat(), "finished_at": finished.isoformat(), "error": str(exc)}
    _log(record)
    return record

def refresh_mv_job():
    return _execute("refresh_materialized_views", lambda db: refresh_all(db))

def aggregation_report_job():
    def run(db):
        return {"sales_by_city": len(run_aggregation(db, "sales_by_city")), "sales_by_status": len(run_aggregation(db, "sales_by_status"))}
    return _execute("periodic_aggregation_report", run)

def list_jobs():
    return [
        {"name": "refresh_materialized_views", "schedule_seconds": int(os.getenv("PHASE2_JOB_INTERVAL_SECONDS", "3600")), "description": "Incrementally refresh required materialized views"},
        {"name": "periodic_aggregation_report", "schedule_seconds": int(os.getenv("PHASE2_REPORT_INTERVAL_SECONDS", "3600")), "description": "Run periodic aggregation reports"},
    ]

def run_job(name):
    jobs = {"refresh_materialized_views": refresh_mv_job, "periodic_aggregation_report": aggregation_report_job}
    if name not in jobs:
        raise ValueError(f"Unknown job: {name}")
    return jobs[name]()

def start_scheduler():
    jobs = list_jobs()
    def loop(job):
        interval = max(10, int(job["schedule_seconds"]))
        while True:
            run_job(job["name"])
            time.sleep(interval)
    for job in jobs:
        threading.Thread(target=loop, args=(job,), daemon=True, name=job["name"]).start()

if __name__ == "__main__":
    print(run_job("refresh_materialized_views"))
