from pymongo import ASCENDING, DESCENDING

from config.settings import VALID_COLLECTION


def ensure_phase2_indexes(db):
    """
    إنشاء الفهارس المطلوبة للمرحلة الثانية.
    لا يحذف أو يغير أي فهرس موجود من الجزء الأول.
    """

    collection = db[VALID_COLLECTION]

    indexes = [
        (
            [("order_id", ASCENDING)],
            {
                "name": "phase2_order_id",
                "unique": True,
            },
        ),
        (
            [("city", ASCENDING)],
            {
                "name": "phase2_city",
            },
        ),
        (
            [("status", ASCENDING)],
            {
                "name": "phase2_status",
            },
        ),
        (
            [("order_date", ASCENDING)],
            {
                "name": "phase2_order_date",
            },
        ),
        (
            [("customer_id", ASCENDING)],
            {
                "name": "phase2_customer_id",
            },
        ),
        (
            [("city", ASCENDING), ("status", ASCENDING)],
            {
                "name": "phase2_city_status",
            },
        ),
        (
            [("total_amount", DESCENDING)],
            {
                "name": "phase2_total_amount",
            },
        ),
    ]

    existing_indexes = list(collection.list_indexes())

    created = []

    for keys, options in indexes:
        requested_name = options["name"]

        # إذا كان الاسم نفسه موجودًا، نعتبره جاهزًا
        same_name = next(
            (
                index
                for index in existing_indexes
                if index["name"] == requested_name
            ),
            None,
        )

        if same_name:
            created.append(requested_name)
            continue

        # إذا كان نفس المفتاح موجودًا باسم مختلف،
        # نستخدم الفهرس الموجود ولا نلمس فهرس الجزء الأول.
        same_key = next(
            (
                index
                for index in existing_indexes
                if list(index["key"].items()) == keys
            ),
            None,
        )

        if same_key:
            created.append(same_key["name"])
            continue

        # إنشاء الفهرس الجديد
        name = collection.create_index(keys, **options)
        created.append(name)

    return {
        "collection": VALID_COLLECTION,
        "indexes": created,
        "count": len(created),
    }


def index_status(db):
    """
    فحص حالة فهارس المرحلة الثانية.
    """

    required = {
        "phase2_city",
        "phase2_status",
        "phase2_order_date",
        "phase2_customer_id",
        "phase2_city_status",
        "phase2_total_amount",
    }

    collection = db[VALID_COLLECTION]

    indexes = list(collection.list_indexes())

    existing_names = {
        index["name"]
        for index in indexes
    }

    # order_id مطلوب كـ unique index،
    # ويمكن أن يكون موجودًا من الجزء الأول باسم uq_order_id.
    order_id_ready = any(
        index["key"] == {"order_id": 1}
        and index.get("unique", False) is True
        for index in indexes
    )

    missing = sorted(required - existing_names)

    if not order_id_ready:
        missing.insert(0, "phase2_order_id")

    return {
        "required": [
            "phase2_order_id",
            "phase2_city",
            "phase2_status",
            "phase2_order_date",
            "phase2_customer_id",
            "phase2_city_status",
            "phase2_total_amount",
        ],
        "existing": sorted(existing_names),
        "missing": missing,
        "ready": len(missing) == 0,
    }