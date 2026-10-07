from pymongo import MongoClient, ASCENDING
from config.settings import MONGO_URI, DB_NAME, RAW_COLLECTION, VALID_COLLECTION, QUAR_COLLECTION

def connect():
    client=MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    client.admin.command("ping")
    return client, client[DB_NAME]

def setup(db):
    db[VALID_COLLECTION].create_index([("order_id",ASCENDING)],unique=True,name="uq_order_id")
    db[QUAR_COLLECTION].create_index([("id_run",ASCENDING),("number_row_source",ASCENDING)],unique=True,name="uq_run_row")
    # Raw deliberately has no unique business index: it is the historical trace layer.
    return True
