import os
import time
import json
from collections import Counter

from pyspark.sql import SparkSession, functions as F
from pymongo import MongoClient, UpdateOne

from config.settings import *
from src.quality_rules import validate_and_clean

# ============================================================
# 🔥 المسارات الثابتة لجهازك (Java 21 + Spark 4.2.0)
# ============================================================
JAVA_HOME = r"C:\Program Files\Java\jdk-21.0.12"
SPARK_HOME = r"C:\spark\spark-4.2.0-bin-hadoop3"

os.environ["JAVA_HOME"] = JAVA_HOME
os.environ["SPARK_HOME"] = SPARK_HOME
os.environ["HADOOP_HOME"] = SPARK_HOME

# ============================================================
# دوال مساعدة
# ============================================================

def normalize_columns(df):
    clean_cols = [str(col).replace("\ufeff", "").strip() for col in df.columns]
    if clean_cols != df.columns:
        df = df.toDF(*clean_cols)
    return df

def fix_mongo_indexes():
    client = None
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        db = client[DB_NAME]
        try: db[VALID_COLLECTION].drop_index("order_id_1")
        except: pass
        try: db[VALID_COLLECTION].drop_index("uq_order_id")
        except: pass
        try: db[VALID_COLLECTION].drop_index("order_id")
        except: pass

        db[VALID_COLLECTION].create_index([("order_id", 1)], unique=True, name="uq_order_id", background=True)
        db[RAW_COLLECTION].create_index([("id_run", 1), ("number_row_source", 1)], background=True)
        db[QUAR_COLLECTION].create_index([("id_run", 1), ("number_row_source", 1)], background=True)
        print("✅ MongoDB indexes fixed successfully.")
    except Exception as e:
        print(f"⚠️ Mongo Indexing Notice: {e}")
    finally:
        if client: client.close()

def write_partition(rows, collection_name):
    if not rows: return 0
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=60000)
    db = client[DB_NAME]
    collection = db[collection_name]
    operations = []
    count = 0

    try:
        for row in rows:
            if not isinstance(row, dict): continue
            order_id = row.get("order_id")
            run_id = row.get("id_run")
            row_num = row.get("number_row_source")

            if collection_name == RAW_COLLECTION:
                filter_query = {"id_run": run_id, "number_row_source": row_num}
            elif collection_name == VALID_COLLECTION:
                if order_id:
                    filter_query = {"order_id": order_id}
                else:
                    continue
            else:
                filter_query = {"id_run": run_id, "number_row_source": row_num}

            operations.append(UpdateOne(filter_query, {"$set": row}, upsert=True))
            count += 1

            if len(operations) >= BATCH_SIZE:
                collection.bulk_write(operations, ordered=False)
                operations.clear()

        if operations:
            collection.bulk_write(operations, ordered=False)
            operations.clear()
    except Exception as e:
        # ✅ إصلاح الترميز: نطبع فقط رسالة مختصرة بدون رموز غير مدعومة
        print(f"Error writing to {collection_name}: {e.__class__.__name__}")
        # نطبع أول 100 حرف من الرسالة مع تجاهل الترميز
        safe_msg = str(e)[:100].encode('ascii', errors='ignore').decode()
        if safe_msg:
            print(f"   Details: {safe_msg}...")
    finally:
        client.close()
    return count

def clean_partition(iterator, run_id, file_path, target_valid, target_quarantine):
    valid_docs = []
    quarantine_docs = []
    valid = corrected = quarantine = 0
    errors = Counter()

    for item in iterator:
        if isinstance(item, tuple) and len(item) == 2:
            row_data, row_idx = item
        else:
            row_data, row_idx = item, None

        raw = row_data.asDict(recursive=True) if hasattr(row_data, "asDict") else dict(row_data)
        number_row_source = row_idx + 1 if row_idx is not None else raw.get("number_row_source", 0)

        # تطبيق قواعد الجودة (هنا يتم تحويل الأرقام إلى float)
        cleaned, corrections, error = validate_and_clean(raw)

        base = {
            "id_run": run_id,
            "number_row_source": number_row_source,
            "file_source": str(file_path),
            "engine_used": "pyspark",
            "record_raw": raw
        }

        if error:
            quarantine += 1
            errors[error] += 1
            quarantine_docs.append({
                **base,
                **raw,
                "codes_error": error,
                "details_error": error,
                "quarantine_reason": error,
                "quality_status": "quarantine"
            })
        else:
            # تأكد من وجود order_id بعد التنظيف
            if not cleaned.get("order_id"):
                quarantine += 1
                errors["MISSING_ORDER_ID"] += 1
                quarantine_docs.append({
                    **base,
                    **cleaned,
                    "codes_error": "MISSING_ORDER_ID",
                    "details_error": "order_id مفقود، لا يمكن إدراجه في VALID",
                    "quarantine_reason": "MISSING_ORDER_ID",
                    "quality_status": "quarantine"
                })
                continue

            # السجل صالح أو مصحح
            if corrections:
                corrected += 1
            else:
                valid += 1

            valid_docs.append({
                **base,
                **cleaned,
                "quality_status": "corrected" if corrections else "valid",
                "corrections": json.dumps(corrections, ensure_ascii=False) if corrections else None
            })

        # الكتابة على دفعات
        if len(valid_docs) >= BATCH_SIZE:
            write_partition(valid_docs, target_valid)
            valid_docs.clear()
        if len(quarantine_docs) >= BATCH_SIZE:
            write_partition(quarantine_docs, target_quarantine)
            quarantine_docs.clear()

    if valid_docs: write_partition(valid_docs, target_valid)
    if quarantine_docs: write_partition(quarantine_docs, target_quarantine)

    return {"valid": valid, "corrected": corrected, "quarantine": quarantine, "errors": dict(errors)}

def run(file_path, db, run_id):
    start = time.perf_counter()
    fix_mongo_indexes()

    spark = (
        SparkSession.builder
        .appName("MidtermDataPipeline")
        .master(SPARK_MASTER)
        .config("spark.driver.memory", SPARK_DRIVER_MEMORY)
        .config("spark.executor.memory", "4g")
        .config("spark.sql.shuffle.partitions", "300")
        .config("spark.sql.files.maxPartitionBytes", SPARK_MAX_PARTITION_BYTES)
        .config("spark.local.dir", SPARK_LOCAL_DIRS)
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")

    try:
        print(f"🚀 Spark Version: {spark.version}")
        df = spark.read.option("header", "true").option("encoding", CSV_ENCODING).csv(str(file_path))
        df = normalize_columns(df)
        df = df.repartition(300)
        partitions = df.rdd.getNumPartitions()
        rows = df.count()
        print(f"📊 Input Partitions: {partitions}, Rows: {rows}")

        # 1. تحميل الطبقة الخام (RAW)
        indexed_rdd = df.rdd.zipWithIndex()
        def process_raw_partition(partition):
            docs = []
            for row_data, idx in partition:
                raw_dict = row_data.asDict(recursive=True)
                doc = {
                    "id_run": run_id, 
                    "number_row_source": idx + 1,
                    "file_source": str(file_path), 
                    "engine_used": "pyspark",
                    "at_ingested": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "record_raw": raw_dict, 
                    **raw_dict
                }
                docs.append(doc)
                if len(docs) >= BATCH_SIZE:
                    write_partition(docs, RAW_COLLECTION)
                    docs.clear()
            if docs: 
                write_partition(docs, RAW_COLLECTION)
                
        indexed_rdd.foreachPartition(process_raw_partition)
        print("✅ RAW loaded")

        # 2. معالجة الجودة والتصنيف
        results = indexed_rdd.mapPartitions(
            lambda it: [clean_partition(it, run_id, file_path, VALID_COLLECTION, QUAR_COLLECTION)]
        ).collect()

        valid = sum(x["valid"] for x in results)
        corrected = sum(x["corrected"] for x in results)
        quarantine = sum(x["quarantine"] for x in results)
        errors = Counter()
        for result in results: 
            errors.update(result["errors"])

        elapsed = time.perf_counter() - start
        print(f"✅ Valid: {valid}, 🔧 Corrected: {corrected}, 🚧 Quarantine: {quarantine}")

        return {
            "read_rows": rows, 
            "loaded_raw": rows, 
            "partitions": partitions,
            "valid": valid, 
            "corrected": corrected, 
            "quarantine": quarantine,
            "error_case_counts": dict(errors), 
            "seconds": round(elapsed, 2)
        }
    except Exception as e:
        print("❌ Pipeline Error:", e)
        import traceback; traceback.print_exc()
        return None
    finally:
        try: spark.stop()
        except: pass
