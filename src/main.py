import time, uuid
from pathlib import Path
from src.file_router import route
from src.mongo_setup import connect, setup
from src.batch_loader import run as batch_run
from src.spark_loader import run as spark_run
from src.elt_pipeline import run as elt_run
from src.metrics import save_metrics
from config.settings import DATA_FILE

def main(file_path=None):
    file_path=Path(file_path or DATA_FILE)
    if not file_path.exists():
        raise FileNotFoundError(f"CSV not found: {file_path}")
    run_id=str(uuid.uuid4())
    started=time.perf_counter()
    print("🚀 بدء تشغيل Midterm Data Pipeline")
    print(f"🔑 Run ID: {run_id}")
    client,db=connect()
    try:
        setup(db)
        engine,size=route(file_path)

        if engine=="python_batch":
            load=batch_run(file_path,db,run_id)
            quality=elt_run(db,run_id)
        else:
            load=spark_run(file_path,db,run_id)
            if load is None:
                raise RuntimeError("spark pipline failed.  check the error sholw above")
            quality=load

        print(f"📦 Raw Loaded: {load['loaded_raw']}")
        print(f"✅ Valid: {quality['valid']}")
        print(f"🔧 Corrected: {quality['corrected']}")
        print(f"🚧 Quarantine: {quality['quarantine']}")

        assert load["loaded_raw"] == quality["valid"]+quality["corrected"]+quality["quarantine"], \
            "run_raw_count != run_valid_count + run_corrected_count + run_quarantine_count"

        elapsed=time.perf_counter()-started
        metrics={
            "id_run":run_id,
            "file_name":file_path.name,
            "file_size_mb":round(size,2),
            "used_engine":engine,
            "read_rows":load["read_rows"],
            "loaded_raw":load["loaded_raw"],
            "count_valid":quality["valid"],
            "count_corrected":quality["corrected"],
            "count_quarantine":quality["quarantine"],
            "seconds_elapsed":round(elapsed,2),
            "throughput":round(load["read_rows"]/elapsed,2) if elapsed else 0,
            "partitions":load.get("partitions"),
            "size_batch":load.get("size_batch"),
            "counts_case_error":quality["error_case_counts"],
            "count_inserted":None,
            "count_updated":None,
            "count_unchanged":None,
            "settings":{"small_file_threshold_mb":200}
        }
        save_metrics(metrics)
        print("📊 Metrics saved: reports/results.json")
    finally:
        client.close()
        print("🔌 MongoDB connection closed")

if __name__=="__main__":
    main()
