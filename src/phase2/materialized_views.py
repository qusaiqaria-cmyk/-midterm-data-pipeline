from datetime import datetime, timezone
from config.settings import VALID_COLLECTION
from config.phase2.settings import INCREMENTAL_RUNS_COLLECTION

CITY_SALES_VIEW = "mv_sales_by_city"
STATUS_SALES_VIEW = "mv_sales_by_status"
DATE_SALES_VIEW = "mv_sales_by_date"
CUSTOMER_SALES_VIEW = "mv_top_customers"


def _source(db):
    return db[VALID_COLLECTION]

def _watermark(db, name):
    return db[INCREMENTAL_RUNS_COLLECTION].find_one({"job": name})

def _set_watermark(db, name, value):
    db[INCREMENTAL_RUNS_COLLECTION].update_one(
        {"job": name}, {"$set": {"job": name, "watermark": value, "updated_at": datetime.now(timezone.utc)}}, upsert=True
    )

def _rebuild_groups(db, view, field, groups):
    if not groups:
        return 0
    count = 0
    for value in groups:
        if value is None:
            continue
        pipeline = [
            {"$match": {field: value, "total_amount": {"$type": "number"}}},
            {"$group": {"_id": f"${field}", "orders": {"$sum": 1}, "sales": {"$sum": "$total_amount"}, "average_order": {"$avg": "$total_amount"}}},
            {"$merge": {"into": view, "on": "_id", "whenMatched": "replace", "whenNotMatched": "insert"}},
        ]
        list(_source(db).aggregate(pipeline, allowDiskUse=True))
        count += 1
    return count

def _full_refresh(db, view, field):
    pipeline = [
        {"$match": {field: {"$exists": True, "$ne": None}, "total_amount": {"$type": "number"}}},
        {"$group": {"_id": f"${field}", "orders": {"$sum": 1}, "sales": {"$sum": "$total_amount"}, "average_order": {"$avg": "$total_amount"}}},
        {"$merge": {"into": view, "on": "_id", "whenMatched": "replace", "whenNotMatched": "insert"}},
    ]
    list(_source(db).aggregate(pipeline, allowDiskUse=True))
    return view

def refresh_incremental(db):
    """Incremental refresh for the two required materialized views.
    Initial run builds from source; later runs only recompute groups touched since watermark.
    """
    now = datetime.now(timezone.utc)
    wm = _watermark(db, "phase2_materialized_views")
    if not wm:
        _full_refresh(db, CITY_SALES_VIEW, "city")
        _full_refresh(db, STATUS_SALES_VIEW, "status")
        _set_watermark(db, "phase2_materialized_views", now)
        return {"mode": "initial", "updated_groups": "all"}

    last = wm["watermark"]
    events = list(db["incremental_events"].find({"updated_at": {"$gt": last}}))
    changed = list(_source(db).find({"updated_at": {"$gt": last}}, {"city": 1, "status": 1, "updated_at": 1}))
    cities = {r.get("city") for r in changed}
    statuses = {r.get("status") for r in changed}
    for event in events:
        cities.update([event.get("old_city"), event.get("new_city")])
        statuses.update([event.get("old_status"), event.get("new_status")])
    city_count = _rebuild_groups(db, CITY_SALES_VIEW, "city", cities)
    status_count = _rebuild_groups(db, STATUS_SALES_VIEW, "status", statuses)
    _set_watermark(db, "phase2_materialized_views", now)
    return {"mode": "incremental", "changed_records": len(changed), "event_count": len(events), "city_groups": city_count, "status_groups": status_count, "watermark": now.isoformat()}

def refresh_all(db):
    return refresh_incremental(db)

def list_materialized_views():
    return [
        {"name": CITY_SALES_VIEW, "description": "المبيعات وعدد الطلبات حسب المدينة", "refresh": "incremental"},
        {"name": STATUS_SALES_VIEW, "description": "المبيعات وعدد الطلبات حسب حالة الطلب", "refresh": "incremental"},
        {"name": DATE_SALES_VIEW, "description": "المبيعات وعدد الطلبات حسب التاريخ", "refresh": "full-compatible"},
        {"name": CUSTOMER_SALES_VIEW, "description": "أعلى العملاء من حيث إجمالي الإنفاق", "refresh": "full-compatible"},
    ]

def get_view(db, view_name):
    allowed = {CITY_SALES_VIEW, STATUS_SALES_VIEW, DATE_SALES_VIEW, CUSTOMER_SALES_VIEW}
    if view_name not in allowed:
        raise ValueError(f"Unknown materialized view: {view_name}")
    return list(db[view_name].find({}, {"_id": 0}))
