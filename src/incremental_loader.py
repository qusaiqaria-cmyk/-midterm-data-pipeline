from datetime import datetime, timezone
from pymongo import UpdateOne
from src.quality_rules import validate_and_clean
from src.common import stable_hash
from config.settings import VALID_COLLECTION
from config.phase2.settings import INCREMENTAL_EVENTS_COLLECTION, VERSION_FIELD


def apply_delta(db, delta_rows, version_field=VERSION_FIELD):
    """Apply only new/changed records and record every effective operation."""
    coll = db[VALID_COLLECTION]
    events = db[INCREMENTAL_EVENTS_COLLECTION]
    inserted = updated = unchanged = 0
    now = datetime.now(timezone.utc)
    for raw in delta_rows:
        cleaned, corr, error = validate_and_clean(raw)
        if error:
            continue
        key = cleaned["order_id"]
        new_hash = stable_hash(cleaned)
        old = coll.find_one({"order_id": key}, {"record_hash": 1, version_field: 1, "city": 1, "status": 1})
        if old and old.get("record_hash") == new_hash:
            unchanged += 1
            continue
        doc = {**cleaned, "record_hash": new_hash,
               "quality_status": "corrected" if corr else "valid",
               "updated_at": now}
        if corr:
            doc["corrections"] = corr
        operation = "update" if old else "insert"
        if old:
            updated += 1
        else:
            inserted += 1
        coll.update_one(
            {"order_id": key},
            {"$set": doc, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        events.insert_one({
            "operation_id": f"{key}:{new_hash}",
            "order_id": key,
            "operation": operation,
            "updated_at": now,
            "record_hash": new_hash,
            "old_city": old.get("city") if old else None,
            "new_city": cleaned.get("city"),
            "old_status": old.get("status") if old else None,
            "new_status": cleaned.get("status"),
        })
    return {"count_inserted": inserted, "count_updated": updated, "count_unchanged": unchanged}
