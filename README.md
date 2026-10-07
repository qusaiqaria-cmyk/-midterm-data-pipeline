midterm-data-pipeline — Hybrid ELT

مشروع منتصف مقرر البيانات الضخمة العملي، مطابق لمسار الطالب الفردي في وثيقة التكليف.



ملااااااحضة
<لقد قمت بتشغيل المشروع على البيانات كامل 
ايضا على النسخة التي تصل الى حجم 1 جيجا بايت
ايضا على النسخة الصغيره التي تصل الى 200 ميجا 
ايضا على الابيانات التي تصل حجمها الى 400 ميجا وهاذي البيانات هي اخر  بيانات تم تشغيلها  
لكي يسهل عمليات الاختبار  عليها  
  
   لذلك  قد تم  توضيح النتائج  الاخيرة  المذكورة في المشروع  حسب هذا النسخة الصغيرة  كونها هي اخر البيانات التي تم التشغيل عليها 

    ايضا لكي يشتغل المشروع عندك بدون اي مشاكل احرص على تسميه البيانات بنفس اسماء البينات في هذا المشروع 
    كما هي موضحة في ملف  ال  settings.py


    ايضا يوجد نقطة مهمه   انا حصلت مشاكل في تشغيل المشروع بسبب البيئه 
    لذلك قمت باضافت هاذه المسارات الثابته  كما يلي

    
# ============================================================
# 🔥 المسارات الثابتة لجهازك (Java 21 + Spark 4.2.0)
# ============================================================
JAVA_HOME = r"C:\Program Files\Java\jdk-21.0.12"
SPARK_HOME = r"C:\spark\spark-4.2.0-bin-hadoop3"

os.environ["JAVA_HOME"] = JAVA_HOME
os.environ["SPARK_HOME"] = SPARK_HOME
os.environ["HADOOP_HOME"] = SPARK_HOME

لقد اضفتها في ملف    spark_loader.py
>



المعمارية

CSV → File Router → Python Batch أو PySpark → "orders_raw" → Quality/Classification → "orders_validated" / "orders_quarantine" → Metrics.

- الحد الافتراضي: 200 MB.
- الملفات الصغيرة: "csv.DictReader" + batches بدون تحميل الملف كاملاً.
- الملفات الكبيرة: Spark DataFrame + fixed String schema + parallel MongoDB write.
- RAW لا يخضع لقواعد الجودة قبل التخزين.
- "orders_validated" تستخدم "order_id" كمفتاح أعمال ثابت + Unique Index + Upsert.
- "orders_raw" تاريخي، لذلك يمكن أن يحتوي أكثر من محاولة تشغيل.
- كل سجل من "id_run" ينتهي إلى Valid/Corrected أو Quarantine.
- النتائج: "reports/results.json".

---

البيئة والمتطلبات

المتطلبات

- Python 3.10+
- MongoDB
- Java / PySpark عند استخدام مسار الملفات الكبيرة
- Python packages الموجودة في "requirements.txt"

Installation

من داخل مجلد المشروع:

pip install -r requirements.txt

ثم انسخ:

example.env

إلى:

.env

وعدّل القيم عند الحاجة، خصوصًا مسارات البيانات وMongoDB وSpark.

«لا تعتمد على أي مسار خاص بجهازي . يجب استخدام مسار المشروع المحلي على الجهاز الذي سيتم تشغيل المشروع عليه.»

---

Phase 1 — التشغيل

تشغيل المشروع

PowerShell:

cd <project-folder>
.\venv_bd\Scripts\Activate.ps1
python main.py

إذا كانت سياسة PowerShell تمنع تشغيل البيئة:

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

ثم:

.\venv_bd\Scripts\Activate.ps1

ويجب أن تكون خدمة MongoDB تعمل قبل تشغيل الـpipeline.

إنشاء عينة

يمكن إنشاء عينة بدون Excel:

python src/create_small_sample.py --input data/orders_huge_mixed_quality.csv --output data/orders_sample.csv --rows 100000

ثم تشغيل العينة:

$env:DATA_FILE="data/orders_sample.csv"
python main.py

ولتشغيل الملف الكبير:

$env:DATA_FILE="data/orders_huge_mixed_quality.csv"
python main.py

«لا تعدّل ملف CSV الأصلي يدويًا. يتم إنشاء العينة باستخدام السكربت فقط.»

---

MongoDB

يجب أن تكون خدمة MongoDB تعمل قبل تشغيل المشروع.

يستخدم المشروع قاعدة البيانات:

bigdata_midterm

وينشئ/يستخدم المجموعات:

- "orders_raw"
- "orders_validated"
- "orders_quarantine"

---

Idempotency

إعادة تشغيل نفس المصدر لا تنشئ Business Records مكررة في "orders_validated" لأن "order_id" يستخدم كمفتاح أعمال ثابت مع Unique Index وUpsert.

أما "orders_raw" فهي تاريخية، لذلك يمكن أن تحتوي على أكثر من محاولة تشغيل وفق متطلبات ELT.

---

قواعد الجودة

يطبق المشروع قواعد الجودة التالية:

1. Arabic numbers
2. Currency normalization
3. Thousands separators
4. Known price words
5. Phone normalization
6. Email repeated-symbol repair
7. Date standardization
8. Whitespace normalization
9. Status/payment/delivery synonyms
10. Total recalculation from valid items + delivery

التصحيح لا يتم بالتخمين. الأخطاء الجوهرية تذهب إلى "quarantine" مع code واضح.

---

Phase 2 — Final Requirements

Run API

بعد تشغيل MongoDB وتثبيت المتطلبات:

uvicorn src.phase2.api:app --host 127.0.0.1 --port 8000

Swagger:

http://127.0.0.1:8000/docs

---

Required API

System

GET /health

Pipeline

POST /ingest

يستدعي الـoriginal midterm pipeline.

Indexes

POST /indexes
GET /indexes/status

Queries

GET /queries
GET /queries/{name}
GET /queries/{name}/explain

يوجد خمسة استعلامات مسجلة:

- "orders_by_city"
- "orders_by_status"
- "orders_by_date"
- "customer_orders"
- "city_status_orders"

وتدعم الاستعلامات Parameters مثل:

- "city"
- "status"
- "order_date"
- "customer_id"
- "limit"

---

Queries, Indexes and Explain

يوجد خمسة Queries في:

src/phase2/queries.py

وتوجد سبعة Indexes في:

src/phase2/indexes.py

ومن ضمنها Compound Index:

city + status

يمكن إنشاء تقرير Explain للمقارنة بين الأداء قبل وبعد الفهارس باستخدام:

python -m src.phase2.explain_report

ويتم إنشاء:

reports/phase2_explain.json

ويحتوي التقرير على "executionStats" قبل وبعد إنشاء Phase 2 indexes.

---

Aggregation Reports

يوفر المشروع تقارير Aggregation مستقلة:

- "sales_by_city"
- "sales_by_status"
- "sales_by_date"
- "top_customers"
- "top_cities"

يمكن الوصول إليها من خلال:

GET /aggregations
GET /aggregations/{name}

---

Materialized Views

يوفر المشروع أربع Materialized Views:

- "mv_sales_by_city"
- "mv_sales_by_status"
- "mv_sales_by_date"
- "mv_top_customers"

تستخدم:

- "mv_sales_by_city" — incremental refresh
- "mv_sales_by_status" — incremental refresh
- "mv_sales_by_date" — full-compatible refresh
- "mv_top_customers" — full-compatible refresh

يمكن عرض الـViews:

GET /materialized-views
GET /materialized-views/{name}

وتحديثها:

POST /refresh-mv

في حالة التحديث التدريجي تعتمد العملية على "updated_at" watermark، ويتم تسجيل عمليات الـdelta في:

incremental_events

---

Scheduled Jobs

يوفر المشروع Jobين:

refresh_materialized_views
periodic_aggregation_report

يمكن عرض الـJobs:

GET /jobs

وتشغيل Job يدويًا:

POST /jobs/{name}/run

كل Job يسجل:

- start time
- end time
- status
- result/error

في:

reports/phase2_jobs.jsonl

---

Background Scheduler

لتشغيل الـbackground scheduler مع الـAPI:

START_PHASE2_SCHEDULER=true

وتحدد الفترات بواسطة:

PHASE2_JOB_INTERVAL_SECONDS
PHASE2_REPORT_INTERVAL_SECONDS

القيمة الافتراضية:

3600

أي كل ساعة.

---

Phase 2 Verification

بعد تشغيل API يمكن استخدام Swagger:

http://127.0.0.1:8000/docs

لفحص جميع endpoints وتشغيلها.

ويجب التأكد من نجاح:

- Health
- Queries
- Index status
- Explain report
- Aggregations
- Materialized Views
- Jobs

---

Important Notes

- لا تعتمد على مسارات Windows الخاصة بجهازي.
- يجب ضبط ".env" بما يناسب الجهاز الذي سيتم تشغيل المشروع عليه.
- يجب تشغيل MongoDB قبل تشغيل الـpipeline أو API.
- لا تعدّل ملف CSV الأصلي يدويًا.
- ملفات "reports/" تحتوي على نتائج التشغيل والتقارير.
