from config.settings import VALID_COLLECTION


def _collection(db):
    return db[VALID_COLLECTION]


def sales_by_city(db):
    """
    تقرير المبيعات وعدد الطلبات حسب المدينة.
    """
    pipeline = [
        {
            "$match": {
                "total_amount": {"$type": "number"},
                "city": {"$exists": True, "$ne": None},
            }
        },
        {
            "$group": {
                "_id": "$city",
                "orders": {"$sum": 1},
                "sales": {"$sum": "$total_amount"},
                "average_order": {"$avg": "$total_amount"},
            }
        },
        {
            "$sort": {
                "sales": -1,
            }
        },
    ]

    return list(
        _collection(db).aggregate(
            pipeline,
            allowDiskUse=True,
        )
    )


def sales_by_status(db):
    """
    تقرير عدد الطلبات والمبيعات حسب حالة الطلب.
    """
    pipeline = [
        {
            "$match": {
                "status": {"$exists": True, "$ne": None},
                "total_amount": {"$type": "number"},
            }
        },
        {
            "$group": {
                "_id": "$status",
                "orders": {"$sum": 1},
                "sales": {"$sum": "$total_amount"},
            }
        },
        {
            "$sort": {
                "sales": -1,
            }
        },
    ]

    return list(
        _collection(db).aggregate(
            pipeline,
            allowDiskUse=True,
        )
    )


def sales_by_date(db):
    """
    تقرير المبيعات وعدد الطلبات حسب التاريخ.
    """
    pipeline = [
        {
            "$match": {
                "order_date": {"$exists": True, "$ne": None},
                "total_amount": {"$type": "number"},
            }
        },
        {
            "$group": {
                "_id": "$order_date",
                "orders": {"$sum": 1},
                "sales": {"$sum": "$total_amount"},
            }
        },
        {
            "$sort": {
                "_id": 1,
            }
        },
    ]

    return list(
        _collection(db).aggregate(
            pipeline,
            allowDiskUse=True,
        )
    )


def top_customers(db, limit=10):
    """
    أعلى العملاء من حيث إجمالي قيمة الطلبات.
    """
    pipeline = [
        {
            "$match": {
                "customer_id": {"$exists": True, "$ne": None},
                "total_amount": {"$type": "number"},
            }
        },
        {
            "$group": {
                "_id": "$customer_id",
                "orders": {"$sum": 1},
                "total_spending": {"$sum": "$total_amount"},
                "average_order": {"$avg": "$total_amount"},
            }
        },
        {
            "$sort": {
                "total_spending": -1,
            }
        },
        {
            "$limit": int(limit),
        },
    ]

    return list(
        _collection(db).aggregate(
            pipeline,
            allowDiskUse=True,
        )
    )


def top_cities(db, limit=10):
    """
    أعلى المدن من حيث المبيعات.
    """
    pipeline = [
        {
            "$match": {
                "city": {"$exists": True, "$ne": None},
                "total_amount": {"$type": "number"},
            }
        },
        {
            "$group": {
                "_id": "$city",
                "orders": {"$sum": 1},
                "sales": {"$sum": "$total_amount"},
            }
        },
        {
            "$sort": {
                "sales": -1,
            }
        },
        {
            "$limit": int(limit),
        },
    ]

    return list(
        _collection(db).aggregate(
            pipeline,
            allowDiskUse=True,
        )
    )


def list_aggregations():
    """
    إرجاع التقارير المتاحة في Phase 2.
    """
    return [
        {
            "name": "sales_by_city",
            "description": "المبيعات وعدد الطلبات حسب المدينة",
        },
        {
            "name": "sales_by_status",
            "description": "المبيعات وعدد الطلبات حسب حالة الطلب",
        },
        {
            "name": "sales_by_date",
            "description": "المبيعات وعدد الطلبات حسب التاريخ",
        },
        {
            "name": "top_customers",
            "description": "أعلى العملاء من حيث إجمالي الإنفاق",
        },
        {
            "name": "top_cities",
            "description": "أعلى المدن من حيث إجمالي المبيعات",
        },
    ]


def run_aggregation(db, name, limit=10):
    """
    تشغيل تقرير محدد بالاسم.
    """

    reports = {
        "sales_by_city": sales_by_city,
        "sales_by_status": sales_by_status,
        "sales_by_date": sales_by_date,
        "top_customers": lambda database: top_customers(
            database,
            limit,
        ),
        "top_cities": lambda database: top_cities(
            database,
            limit,
        ),
    }

    if name not in reports:
        raise ValueError(
            f"Unknown aggregation: {name}. "
            f"Available: {list(reports.keys())}"
        )

    return reports[name](db)
