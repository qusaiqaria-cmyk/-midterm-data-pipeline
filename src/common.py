import json, hashlib
from datetime import datetime, timezone

def now_utc():
    return datetime.now(timezone.utc)

def stable_hash(doc):
    clean = {k: v for k, v in doc.items() if k not in {"_id", "id_run", "at_ingested", "engine_used"}}
    return hashlib.sha256(
        json.dumps(clean, ensure_ascii=False, sort_keys=True, default=str).encode()
    ).hexdigest()

def normalize_keys(record):
    return {str(k).lstrip("\ufeff"): v for k, v in record.items()}

def parse_items(value):
    """
    تحليل حقل items_json القادم من CSV مع دعم التنسيقات التالية:
    - JSON عادي: [{"sku":"S1","qty":2}]
    - ملفوف بعلامات اقتباس CSV: "[{""sku"":""S1"",""qty"":2}]"
    - مقطوع (نضيف الأقواس المفقودة): "[{""sku"":""S1""] -> نضيف }]
    """
    if value is None or str(value).strip() == "":
        return None, "ITEMS_EMPTY"
    
    raw = str(value).strip()
    
    # ===== الخطوة 1: إزالة علامات الاقتباس الخارجية إن وجدت =====
    # إذا كانت القيمة تبدأ بـ "[{" وتنتهي بـ "]" (أو "]" مع علامة اقتباس)
    if raw.startswith('"[') and raw.endswith(']"'):
        raw = raw[1:-1]  # إزالة علامات الاقتباس الخارجية
    elif raw.startswith('"[{') and raw.endswith('"'):
        raw = raw[1:-1]  # إزالة علامة الاقتباس الخارجية فقط
    
    # ===== الخطوة 2: معالجة هروب علامات الاقتباس المزدوجة (CSV standard) =====
    # استبدال "" بـ " (هروب CSV)
    raw = raw.replace('""', '"')
    
    # ===== الخطوة 3: محاولة التحليل المباشر =====
    try:
        obj = json.loads(raw)
        # التحقق من الصحة
        if isinstance(obj, list) and obj:
            for item in obj:
                if not isinstance(item, dict):
                    return None, "JSON_ITEMS_CORRUPTED"
                if item.get("qty") is None:
                    return None, "JSON_ITEMS_CORRUPTED"
                try:
                    if float(item["qty"]) < 0:
                        return None, "VALUE_NEGATIVE_AMBIGUOUS"
                except Exception:
                    return None, "JSON_ITEMS_CORRUPTED"
            return obj, None
        elif obj == []:
            return None, "ITEMS_EMPTY"
        else:
            return None, "JSON_ITEMS_CORRUPTED"
            
    except json.JSONDecodeError:
        # ===== الخطوة 4: محاولة إصلاح الأقواس المفقودة =====
        # إذا كان يبدأ بـ [{ ولا ينتهي بـ }]، نضيف الأقواس المغلقة
        if raw.startswith('[{') and not raw.endswith('}]'):
            raw_corrected = raw + '}]'
            try:
                obj = json.loads(raw_corrected)
                if isinstance(obj, list) and obj:
                    for item in obj:
                        if not isinstance(item, dict):
                            return None, "JSON_ITEMS_CORRUPTED"
                        if item.get("qty") is None:
                            return None, "JSON_ITEMS_CORRUPTED"
                        try:
                            if float(item["qty"]) < 0:
                                return None, "VALUE_NEGATIVE_AMBIGUOUS"
                        except Exception:
                            return None, "JSON_ITEMS_CORRUPTED"
                    return obj, None
            except:
                pass
        
        # ===== الخطوة 5: إذا كل شيء فشل، نعزله =====
        return None, "JSON_ITEMS_CORRUPTED"