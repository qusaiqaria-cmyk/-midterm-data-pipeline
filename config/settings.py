import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DATA_FILE = os.getenv("DATA_FILE", "data/orders_400MB.csv")
SMALL_SAMPLE_FILE = os.getenv("SMALL_SAMPLE_FILE", "data/orders_sample.csv")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "bigdata_midterm")
RAW_COLLECTION = os.getenv("RAW_COLLECTION", "orders_raw")
VALID_COLLECTION = os.getenv("VALID_COLLECTION", "orders_validated")
QUAR_COLLECTION = os.getenv("QUAR_COLLECTION", "orders_quarantine")

SMALL_FILE_THRESHOLD_MB = int(os.getenv("SMALL_FILE_THRESHOLD_MB", "200"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))
SAMPLE_ROWS = int(os.getenv("SAMPLE_ROWS", "100000"))

SPARK_MASTER = os.getenv("SPARK_MASTER", "local[*]")
SPARK_DRIVER_MEMORY = os.getenv("SPARK_DRIVER_MEMORY", "4g")
SPARK_MAX_PARTITION_BYTES = os.getenv("SPARK_MAX_PARTITION_BYTES", "128m")
SPARK_LOCAL_DIRS = os.getenv("SPARK_LOCAL_DIRS", "D:/spark_tmp")
MONGO_CONNECTOR = os.getenv(
    "MONGO_CONNECTOR",
    "org.mongodb.spark:mongo-spark-connector_2.13:10.5.0"
)
CSV_ENCODING = "utf-8"
REQUIRED_COLUMNS = [
    "order_id","order_date","status","customer_id","customer_name",
    "customer_phone","customer_email","city","district","delivery_type",
    "delivery_cost","payment_method","payment_status","payment_amount",
    "currency","total_amount","items_json"
]
