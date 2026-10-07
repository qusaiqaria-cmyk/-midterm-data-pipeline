from typing import Any
from config.settings import VALID_COLLECTION


QUERIES = {
    "orders_by_city": {
        "description": "عدد الطلبات وإجمالي المبيعات حسب المدينة",
        "filter": {},
        "projection": {
            "_id": 0,
            "order_id": 1,
            "city": 1,
            "total_amount": 1,
            "status": 1,
        },
    },

    "orders_by_status": {
        "description": "الطلبات حسب الحالة",
        "filter": {},
        "projection": {
            "_id": 0,
            "order_id": 1,
            "status": 1,
            "city": 1,
            "total_amount": 1,
        },
    },

    "orders_by_date": {
        "description": "الطلبات حسب تاريخ الطلب",
        "filter": {},
        "projection": {
            "_id": 0,
            "order_id": 1,
            "order_date": 1,
            "total_amount": 1,
            "city": 1,
        },
    },

    "customer_orders": {
        "description": "طلبات عميل محدد",
        "filter": {},
        "projection": {
            "_id": 0,
            "order_id": 1,
            "customer_id": 1,
            "customer_name": 1,
            "total_amount": 1,
            "order_date": 1,
        },
    },

    "city_status_orders": {
        "description": "الطلبات حسب المدينة والحالة",
        "filter": {},
        "projection": {
            "_id": 0,
            "order_id": 1,
            "city": 1,
            "status": 1,
            "total_amount": 1,
            "order_date": 1,
        },
    },
}


def list_queries():
    """إرجاع قائمة الاستعلامات المتاحة."""
    return [
        {
            "name": name,
            "description": config["description"],
        }
        for name, config in QUERIES.items()
    ]


def run_query(db, name: str, limit: int = 100):
    """
    تشغيل أحد الاستعلامات المسجلة.

    ملاحظة:
    الفلاتر التي تعتمد على قيمة معينة يمكن تمريرها عبر parameters.
    """

    if name not in QUERIES:
        raise ValueError(f"Unknown query: {name}")

    collection = db[VALID_COLLECTION]
    query = QUERIES[name]

    cursor = (
        collection
        .find(
            query["filter"],
            query["projection"],
        )
        .limit(limit)
    )

    return list(cursor)


def run_parameterized_query(
    db,
    name: str,
    parameters: dict[str, Any] | None = None,
    limit: int = 100,
):
    """
    تشغيل الاستعلام مع Parameters.

    هذا يسمح للـAPI بتشغيل الاستعلامات على بيانات مختلفة
    بدون وضع نتائج ثابتة داخل الكود.
    """

    if name not in QUERIES:
        raise ValueError(f"Unknown query: {name}")

    parameters = parameters or {}
    collection = db[VALID_COLLECTION]

    if name == "orders_by_city":
        query = {}

        if parameters.get("city"):
            query["city"] = parameters["city"]

    elif name == "orders_by_status":
        query = {}

        if parameters.get("status"):
            query["status"] = parameters["status"]

    elif name == "orders_by_date":
        query = {}

        if parameters.get("order_date"):
            query["order_date"] = parameters["order_date"]

    elif name == "customer_orders":
        query = {}

        if parameters.get("customer_id"):
            query["customer_id"] = parameters["customer_id"]

    elif name == "city_status_orders":
        query = {}

        if parameters.get("city"):
            query["city"] = parameters["city"]

        if parameters.get("status"):
            query["status"] = parameters["status"]

    else:
        query = {}

    projection = QUERIES[name]["projection"]

    cursor = (
        collection
        .find(query, projection)
        .limit(limit)
    )

    return list(cursor)


def explain_query(db, name: str, parameters: dict[str, Any] | None = None):
    """
    تنفيذ explain باستخدام executionStats.

    يستخدم لإظهار تأثير الفهارس قبل وبعد إنشائها.
    """

    if name not in QUERIES:
        raise ValueError(f"Unknown query: {name}")

    parameters = parameters or {}
    collection = db[VALID_COLLECTION]

    if name == "orders_by_city":
        query = {"city": parameters.get("city", "صنعاء")}

    elif name == "orders_by_status":
        query = {"status": parameters.get("status", "confirmed")}

    elif name == "orders_by_date":
        query = {
            "order_date": parameters.get(
                "order_date",
                "2025-04-07",
            )
        }

    elif name == "customer_orders":
        query = {
            "customer_id": parameters.get(
                "customer_id",
                "عميل-7275",
            )
        }

    elif name == "city_status_orders":
        query = {
            "city": parameters.get("city", "صنعاء"),
            "status": parameters.get("status", "confirmed"),
        }

    else:
        query = {}

    return db.command(
    "explain",
    {
        "find": VALID_COLLECTION,
        "filter": query,
        "projection": QUERIES[name]["projection"],
    },
    verbosity="executionStats",
)
    
    
    
    
# ------------------------------------------------------------------
# API helper functions
# ------------------------------------------------------------------

def orders_by_city(db, city: str | None = None, limit: int = 100):
    parameters = {}
    if city:
        parameters["city"] = city

    return run_parameterized_query(
        db,
        "orders_by_city",
        parameters,
        limit,
    )


def orders_by_status(db, status: str | None = None, limit: int = 100):
    parameters = {}
    if status:
        parameters["status"] = status

    return run_parameterized_query(
        db,
        "orders_by_status",
        parameters,
        limit,
    )


def orders_by_date(
    db,
    order_date: str | None = None,
    limit: int = 100,
):
    parameters = {}
    if order_date:
        parameters["order_date"] = order_date

    return run_parameterized_query(
        db,
        "orders_by_date",
        parameters,
        limit,
    )


def customer_orders(
    db,
    customer_id: str,
    limit: int = 100,
):
    return run_parameterized_query(
        db,
        "customer_orders",
        {"customer_id": customer_id},
        limit,
    )


def city_status_orders(
    db,
    city: str | None = None,
    status: str | None = None,
    limit: int = 100,
):
    parameters = {}

    if city:
        parameters["city"] = city

    if status:
        parameters["status"] = status

    return run_parameterized_query(
        db,
        "city_status_orders",
        parameters,
        limit,
    )