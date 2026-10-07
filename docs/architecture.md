
---

## 📄 `docs/architecture.md` (المحدث)

```markdown
# Architecture — Midterm Data Pipeline

## 1. نظرة عامة

نظام خط بيانات هجين (Hybrid) يطبق نمط **ELT** (Extract, Load, Transform) على بيانات طلبات متجر إلكتروني. يستقبل ملف CSV ضخم، ويختار محرك المعالجة المناسب (Python Batch أو PySpark) حسب حجم الملف، ثم يمرر البيانات عبر مراحل: تحميل خام، تنظيف، تصنيف، وتحميل نهائي مع ضمان Idempotency.

---

## 2. المكونات الأساسية

### 2.1. File Router (موجه الملفات)
- **الموقع**: `src/file_router.py`
- **الوظيفة**: قراءة حجم الملف ومقارنته بالحد الفاصل (200 ميجابايت افتراضياً).
- **المخرجات**: `python_batch` أو `pyspark`.

### 2.2. Python Batch Loader (للملفات الصغيرة)
- **الموقع**: `src/batch_loader.py`
- **الوظيفة**: قراءة CSV باستخدام `csv.DictReader` بشكل متدفق (streaming) دون تحميل الملف كاملاً.
- **الدفعات**: تجميع السجلات في دفعات (`BATCH_SIZE`) ثم كتابتها إلى `orders_raw` باستخدام `insert_many`.

### 2.3. PySpark Loader (للملفات الكبيرة)
- **الموقع**: `src/spark_loader.py`
- **الوظيفة**: قراءة CSV باستخدام Spark DataFrame، وتقسيم البيانات إلى 300 Partition.
- **الكتابة**: كتابة `orders_raw` بالتوازي باستخدام `foreachPartition` + `pymongo`.
- **المسارات الثابتة**: تستخدم `JAVA_HOME` و `SPARK_HOME` المحددة في الكود (لجهاز المستخدم).

### 2.4. Quality Rules (قواعد الجودة)
- **الموقع**: `src/quality_rules.py`
- **الوظيفة**: تطبيق 10 قواعد تنظيف وتحقق على كل سجل.
- **المخرجات**: `(cleaned_record, corrections, error)`

#### قواعد التنظيف
| القاعدة | الدالة |
| :--- | :--- |
| الأرقام العربية | `arabic_numbers()` |
| توحيد العملة | `currency()` |
| إزالة فواصل الآلاف | `thousands()` |
| السعر بالكلمات | `price_words()` |
| تنظيف الهاتف | `phone()` |
| تنظيف الإيميل | `email()` |
| توحيد التاريخ | `date_iso()` |
| إزالة المسافات الزائدة | `whitespace()` |
| المرادفات | `synonym()` |
| إعادة حساب الإجمالي | `validate_and_clean()` |

#### التصنيف
- **`valid`**: السجل سليم دون أي تصحيح.
- **`corrected`**: السجل يحتوي على أخطاء قابلة للتصحيح، وتم حفظ أثر التصحيح.
- **`quarantine`**: السجل يحتوي على أخطاء جوهرية غير قابلة للتصحيح، مع `quarantine_reason`.

### 2.5. ELT Pipeline (خط الأنابيب)
- **الموقع**: `src/elt_pipeline.py`
- **الوظيفة**: قراءة السجلات من `orders_raw` (حسب `run_id`)، تطبيق `validate_and_clean`، وتوزيعها إلى `orders_validated` و `orders_quarantine`.
- **الكتابة**: استخدام `bulk_write` مع `UpdateOne` و `upsert=True` لضمان Idempotency.

### 2.6. MongoDB Setup
- **الموقع**: `src/mongo_setup.py`
- **الوظيفة**: إنشاء اتصال بقاعدة البيانات، وإنشاء الفهارس المطلوبة.
- **الفهارس**:
  - `orders_validated`: `Unique Index` على `order_id` (لمنع التكرار).
  - `orders_raw`: فهرس مركب على `(run_id, source_row_number)` للسرعة.
  - `orders_quarantine`: فهرس مركب على `(run_id, source_row_number)` للسرعة.

### 2.7. Metrics (المقاييس)
- **الموقع**: `src/metrics.py`
- **الوظيفة**: جمع الإحصائيات من قاعدة البيانات بعد التشغيل، وحفظها في `reports/results.json`.

---

## 3. تدفق البيانات (Data Flow)
