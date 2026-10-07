import time
from datetime import datetime, timezone
from collections import Counter
from pymongo import UpdateOne
from src.quality_rules import validate_and_clean
from src.common import stable_hash
from config.settings import RAW_COLLECTION, VALID_COLLECTION, QUAR_COLLECTION

def process_raw(db,run_id):
    raw=db[RAW_COLLECTION]; valid=db[VALID_COLLECTION]; quar=db[QUAR_COLLECTION]
    counts=Counter(); ops=[]; qops=[]; valid_count=corrected=quarantine=0
    cursor=raw.find({"id_run":run_id},{"_id":0,"id_run":1,"file_source":1,"number_row_source":1,"at_ingested":1,"engine_used":1,"record_raw":1},batch_size=1000)
    started=time.perf_counter()
    for d in cursor:
        cleaned,corr,error=validate_and_clean(d["record_raw"])
        base={"id_run":run_id,"file_source":d["file_source"],"number_row_source":d["number_row_source"],
              "at_ingested":d["at_ingested"],"engine_used":d["engine_used"],"record_raw":d["record_raw"]}
        if error:
            counts[error]+=1; quarantine+=1
            qdoc={**base,"codes_error":error,"details_error":error,"quarantine_reason":error}
            qops.append(UpdateOne({"id_run":run_id,"number_row_source":d["number_row_source"]},{"$set":qdoc},upsert=True))
        else:
            status="corrected" if corr else "valid"
            doc={**cleaned,**base,"quality_status":status,"record_hash":stable_hash(cleaned)}
            if corr: doc["corrections"]=corr; corrected+=1
            else: valid_count+=1
            ops.append(UpdateOne({"order_id":doc["order_id"]},{"$set":doc},upsert=True))
        if len(ops)>=1000:
            valid.bulk_write(ops,ordered=False); ops=[]
        if len(qops)>=1000:
            quar.bulk_write(qops,ordered=False); qops=[]
    if ops: valid.bulk_write(ops,ordered=False)
    if qops: quar.bulk_write(qops,ordered=False)
    return {"valid":valid_count,"corrected":corrected,"quarantine":quarantine,
            "error_case_counts":dict(counts),"seconds":time.perf_counter()-started}

def run(db,run_id):
    return process_raw(db,run_id)
