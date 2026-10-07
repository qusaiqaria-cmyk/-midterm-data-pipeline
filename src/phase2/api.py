from typing import Any, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from src.mongo_setup import connect
from src.main import main as run_ingest_pipeline
from src.phase2.queries import list_queries, run_parameterized_query, explain_query
from src.phase2.aggregations import list_aggregations, run_aggregation
from src.phase2.indexes import ensure_phase2_indexes, index_status
from src.phase2.materialized_views import refresh_all, list_materialized_views, get_view
from src.phase2.jobs import list_jobs, run_job, start_scheduler

app = FastAPI(title="Midterm Data Pipeline - Phase 2 API", version="2.0.0")

class IngestRequest(BaseModel):
    file_path: Optional[str] = None

class QueryRequest(BaseModel):
    parameters: dict[str, Any] = {}
    limit: int = 100

def _call(fn):
    client = None
    try:
        client, db = connect()
        return fn(db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if client is not None:
            client.close()

@app.get("/", tags=["system"])
def root():
    return {"project": "Midterm Data Pipeline", "phase": "Phase 2", "status": "running"}

@app.get("/health", tags=["system"])
def health():
    def check(db):
        db.command("ping")
        return {"status": "healthy", "database": db.name}
    return _call(check)

@app.post("/ingest", tags=["pipeline"])
def ingest(request: IngestRequest):
    try:
        run_ingest_pipeline(request.file_path)
        return {"status": "success", "message": "Midterm pipeline completed", "file_path": request.file_path}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/indexes", tags=["indexes"])
def create_indexes():
    return _call(ensure_phase2_indexes)

@app.get("/indexes/status", tags=["indexes"])
def indexes_status():
    return _call(index_status)

@app.get("/queries", tags=["queries"])
def queries():
    return list_queries()

@app.get("/queries/{name}", tags=["queries"])
def query(name: str, city: Optional[str] = None, status: Optional[str] = None, order_date: Optional[str] = None, customer_id: Optional[str] = None, limit: int = Query(100, ge=1, le=1000)):
    params = {k: v for k, v in {"city": city, "status": status, "order_date": order_date, "customer_id": customer_id}.items() if v is not None}
    return _call(lambda db: run_parameterized_query(db, name, params, limit))

@app.get("/queries/{name}/explain", tags=["queries"] )
def query_explain(name: str, city: Optional[str] = None, status: Optional[str] = None, order_date: Optional[str] = None, customer_id: Optional[str] = None):
    params = {k: v for k, v in {"city": city, "status": status, "order_date": order_date, "customer_id": customer_id}.items() if v is not None}
    return _call(lambda db: explain_query(db, name, params))

@app.get("/aggregations", tags=["aggregations"])
def aggregations():
    return list_aggregations()

@app.get("/aggregations/{name}", tags=["aggregations"])
def aggregation(name: str, limit: int = Query(10, ge=1, le=100)):
    return _call(lambda db: run_aggregation(db, name, limit))

@app.post("/refresh-mv", tags=["materialized-views"])
def refresh_mv():
    return _call(refresh_all)

@app.get("/materialized-views", tags=["materialized-views"])
def materialized_views():
    return list_materialized_views()

@app.get("/materialized-views/{name}", tags=["materialized-views"])
def materialized_view(name: str):
    return _call(lambda db: get_view(db, name))

@app.get("/jobs", tags=["jobs"])
def jobs():
    return list_jobs()

@app.post("/jobs/{name}/run", tags=["jobs"])
def run_named_job(name: str):
    try:
        return run_job(name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.on_event("startup")
def startup():
    if __import__("os").getenv("START_PHASE2_SCHEDULER", "false").lower() == "true":
        start_scheduler()
