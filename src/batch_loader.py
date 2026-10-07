import csv,time
from datetime import datetime, timezone
from pymongo import UpdateOne
from src.common import normalize_keys
from config.settings import BATCH_SIZE, RAW_COLLECTION

def run(file_path,db,run_id,engine="python_batch"):
    coll=db[RAW_COLLECTION]; total=0; batches=0; started=time.perf_counter()
    with open(file_path,"r",encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        batch=[]
        for row_no,row in enumerate(reader,2):
            row=normalize_keys(row)
            doc={"id_run":run_id,"file_source":str(file_path),"number_row_source":row_no,
                 "at_ingested":datetime.now(timezone.utc),"engine_used":engine,"record_raw":row}
            batch.append(doc)
            if len(batch)>=BATCH_SIZE:
                t=time.perf_counter()
                coll.insert_many(batch,ordered=False)
                total+=len(batch); batches+=1
                print(f"📦 Batch {batches}: {len(batch)} rows | {time.perf_counter()-t:.2f}s | total={total}")
                batch=[]
        if batch:
            coll.insert_many(batch,ordered=False); total+=len(batch); batches+=1
    return {"read_rows":total,"loaded_raw":total,"size_batch":BATCH_SIZE,"partitions":None,
            "seconds":time.perf_counter()-started,"batches":batches}
