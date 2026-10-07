import json
from pathlib import Path
from src.mongo_setup import connect
from src.phase2.indexes import ensure_phase2_indexes
from src.phase2.queries import explain_query
from config.settings import VALID_COLLECTION

QUERY_CASES = [
    ("orders_by_city", {"city": "صنعاء"}),
    ("orders_by_status", {"status": "confirmed"}),
    ("city_status_orders", {"city": "صنعاء", "status": "confirmed"}),
]
INDEX_NAMES = ["phase2_city", "phase2_status", "phase2_city_status"]

def _stats(explain):
    return {
        "executionTimeMillis": explain.get("executionStats", {}).get("executionTimeMillis"),
        "nReturned": explain.get("executionStats", {}).get("nReturned"),
        "totalKeysExamined": explain.get("executionStats", {}).get("totalKeysExamined"),
        "totalDocsExamined": explain.get("executionStats", {}).get("totalDocsExamined"),
        "winningPlan": explain.get("queryPlanner", {}).get("winningPlan", {}).get("stage"),
    }

def generate_explain_report(output="reports/phase2_explain.json"):
    client, db = connect()
    try:
        coll = db[VALID_COLLECTION]
        before = {}
        after = {}
        # Remove only Phase 2 indexes so the comparison is reproducible.
        for name in INDEX_NAMES:
            try:
                coll.drop_index(name)
            except Exception:
                pass
        for name, params in QUERY_CASES:
            before[name] = _stats(explain_query(db, name, params))
        ensure_phase2_indexes(db)
        for name, params in QUERY_CASES:
            after[name] = _stats(explain_query(db, name, params))
        report = {"queries": [x[0] for x in QUERY_CASES], "before_indexes": before, "after_indexes": after, "indexes_used": INDEX_NAMES}
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    finally:
        client.close()

if __name__ == "__main__":
    print(generate_explain_report())
