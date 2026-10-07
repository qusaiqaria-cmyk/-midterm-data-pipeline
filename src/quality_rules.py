import re
from datetime import datetime

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")

def arabic_numbers(v):
    return v.translate(ARABIC_DIGITS) if isinstance(v, str) else v
    
def currency(v):
    if not isinstance(v, str): return v
    m = {"ريال":"YER","ريال يمني":"YER","rial":"YER","yer":"YER","yr":"YER"}
    return m.get(v.strip().lower(), v.strip())

def thousands(v):
    return v.replace(",","").replace("،","") if isinstance(v,str) else v

def price_words(v):
    if not isinstance(v,str): return v
    words = {
        "خمسة آلاف":"5000","خمسة الاف":"5000","ألفان":"2000","الفان":"2000",
        "خمسمائة":"500","مائتين":"200","مئتين":"200","ألف":"1000","الف":"1000",
        "خمسة":"5","عشرة":"10"
    }
    for w in sorted(words,key=len,reverse=True): 
        v = v.replace(w, words[w])
    return v

def normalize_price(v):
    if v is None: return None
    try:
        x = price_words(thousands(arabic_numbers(str(v))))
        x = re.sub(r"(ريال يمني|ريال|YER|Rial|rial|YR)", "", x, flags=re.I)
        x = re.sub(r"[^\d.\-]", "", x).strip()
        if x == "" or x == "-":
            return None
        return float(x)
    except Exception:
        return None

def phone(v):
    if v is None: return None
    x = re.sub(r"[^\d+]", "", str(v))
    if x.startswith("+967"): 
        x = "0" + x[4:]
    elif x.startswith("967"): 
        x = "0" + x[3:]
    elif len(x) == 9 and x.startswith("7"): 
        x = "0" + x
    return x

def email(v):
    if v is None: return None
    x = str(v).strip().lower()
    x = re.sub(r"@+", "@", x)
    x = re.sub(r"\.{2,}", ".", x)
    if "user-without-domain" in x:
        return None
    return x

def date_iso(v):
    if v is None or str(v).strip() == "": 
        return None
    x = arabic_numbers(str(v).strip()).replace("/", "-").replace("\\", "-")
    for candidate in (x, x.replace("Z", "+00:00")):
        try: 
            return datetime.fromisoformat(candidate).strftime("%Y-%m-%d")
        except ValueError: 
            pass
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y-%d-%m"):
        try: 
            return datetime.strptime(x, fmt).strftime("%Y-%m-%d")
        except ValueError: 
            pass
    return None

def whitespace(v):
    return re.sub(r"\s+", " ", v).strip() if isinstance(v, str) else v

def synonym(v):
    if not isinstance(v, str): return v
    m = {"مؤكد":"confirmed","مؤكدة":"confirmed","مدفوع":"paid","تم الدفع":"paid",
         "قيد الانتظار":"pending","بانتظار الدفع":"pending","عادي":"standard","سريع":"express"}
    return m.get(v.strip(), v.strip())

def clean_record(raw):
    r = {k: whitespace(v) for k, v in raw.items()}
    corrections = []

    def setv(field, new, rule):
        old = r.get(field)
        if new != old:
            corrections.append({"field": field, "original_value": old, "corrected_value": new, "rule_code": rule})
            r[field] = new

    setv("currency", currency(r.get("currency")), "CURRENCY_NORMALIZATION")
    setv("total_amount", normalize_price(r.get("total_amount")), "PRICE_NORMALIZATION")
    setv("delivery_cost", normalize_price(r.get("delivery_cost")), "PRICE_NORMALIZATION")
    setv("payment_amount", normalize_price(r.get("payment_amount")), "PRICE_NORMALIZATION")
    setv("customer_phone", phone(r.get("customer_phone")), "PHONE_NORMALIZATION")
    setv("customer_email", email(r.get("customer_email")), "EMAIL_REPEATED_SYMBOLS")
    d = date_iso(r.get("order_date"))
    setv("order_date", d, "DATE_STANDARDIZATION")
    for f in ("status", "payment_status", "delivery_type"):
        setv(f, synonym(r.get(f)), "VALUE_SYNONYM")
    
    return r, corrections

from src.common import parse_items

def validate_and_clean(raw):
    # ===== نسخة متسامحة: نحاول إنقاذ أكبر عدد من السجلات =====
    cleaned, corrections = clean_record(raw)
    
    # 1. التأكد من وجود order_id (إذا لم يكن موجوداً، نحاول توليده من raw)
    order_id = str(cleaned.get("order_id") or "").strip()
    if not order_id:
        # محاولة أخيرة: البحث في record_raw (الخام)
        if "record_raw" in cleaned and cleaned["record_raw"]:
            order_id = str(cleaned["record_raw"].get("order_id") or "").strip()
        if not order_id:
            return None, corrections, "ID_ORDER_MISSING"
        else:
            cleaned["order_id"] = order_id
            corrections.append({"field": "order_id", "original_value": None, "corrected_value": order_id, "rule_code": "RECOVER_ORDER_ID"})
    
    # 2. customer_id (إذا كان مفقوداً، نضعه افتراضياً)
    customer_id = str(cleaned.get("customer_id") or "").strip()
    if not customer_id:
        if "record_raw" in cleaned and cleaned["record_raw"]:
            customer_id = str(cleaned["record_raw"].get("customer_id") or "").strip()
        if not customer_id:
            cleaned["customer_id"] = "UNKNOWN_CUSTOMER"
            corrections.append({"field": "customer_id", "original_value": None, "corrected_value": "UNKNOWN_CUSTOMER", "rule_code": "RECOVER_CUSTOMER_ID"})
        else:
            cleaned["customer_id"] = customer_id
            corrections.append({"field": "customer_id", "original_value": None, "corrected_value": customer_id, "rule_code": "RECOVER_CUSTOMER_ID"})
    
    # 3. total_amount (إذا كان مفقوداً أو غير قابل للتحويل، نحاول حسابه من items)
    total_amt = cleaned.get("total_amount")
    if total_amt is None or (isinstance(total_amt, str) and total_amt.strip() == ""):
        items, err = parse_items(cleaned.get("items_json"))
        if items and isinstance(items, list):
            try:
                item_total = sum(float(i.get("qty", 0)) * float(i.get("unit_price", 0)) for i in items if isinstance(i, dict))
                delivery = float(cleaned.get("delivery_cost") or 0)
                recomputed = item_total + delivery
                cleaned["total_amount"] = recomputed
                corrections.append({"field": "total_amount", "original_value": None, "corrected_value": recomputed, "rule_code": "RECOVER_TOTAL"})
            except:
                cleaned["total_amount"] = 0.0
                corrections.append({"field": "total_amount", "original_value": None, "corrected_value": 0.0, "rule_code": "DEFAULT_TOTAL"})
        else:
            cleaned["total_amount"] = 0.0
            corrections.append({"field": "total_amount", "original_value": None, "corrected_value": 0.0, "rule_code": "DEFAULT_TOTAL"})
    
    # 4. تحويل الأرقام إلى float (ضمان)
    for field in ["delivery_cost", "payment_amount", "total_amount"]:
        if field in cleaned and cleaned[field] is not None:
            try:
                cleaned[field] = float(cleaned[field])
            except (ValueError, TypeError):
                cleaned[field] = 0.0
                corrections.append({"field": field, "original_value": cleaned.get(field), "corrected_value": 0.0, "rule_code": "DEFAULT_NUMBER"})
    
    # 5. التاريخ (إذا كان مستحيلاً، نضعه None ولكن لا نعزل)
    if not cleaned.get("order_date"):
        cleaned["order_date"] = None
        corrections.append({"field": "order_date", "original_value": None, "corrected_value": None, "rule_code": "DEFAULT_DATE"})
    
    # 6. items_json (نحاول تحليله، وإذا فشل نجعله قائمة فارغة)
    items, err = parse_items(cleaned.get("items_json"))
    if err:
        corrections.append({"field": "items_json", "original_value": cleaned.get("items_json"), "corrected_value": [], "rule_code": "EMPTY_ITEMS"})
        cleaned["items_json"] = []
    else:
        cleaned["items_json"] = items if items else []
    
    # 7. إعادة حساب الإجمالي (إذا كان items موجوداً)
    if isinstance(cleaned["items_json"], list) and cleaned["items_json"]:
        try:
            item_total = sum(float(i.get("qty", 0)) * float(i.get("unit_price", 0)) for i in cleaned["items_json"] if isinstance(i, dict))
            delivery = float(cleaned.get("delivery_cost") or 0)
            recomputed = item_total + delivery
            old = float(cleaned["total_amount"])
            if abs(old - recomputed) > 0.01:
                corrections.append({"field": "total_amount", "original_value": old, "corrected_value": recomputed, "rule_code": "TOTAL_RECALCULATION"})
                cleaned["total_amount"] = recomputed
        except:
            pass
    
    return cleaned, corrections, None
