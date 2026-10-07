from src.quality_rules import validate_and_clean
def good():
    return {"order_id":"طلب-1","customer_id":"عميل-1","order_date":"2025-02-24T21:29:00",
            "total_amount":"32000","delivery_cost":"2000","customer_phone":"771234567",
            "customer_email":"USER@@mail..COM","currency":"ريال يمني",
            "items_json":'[{"sku":"S1","qty":3,"unit_price":10000,"total":30000}]'}
def test_corrected():
    cleaned,corr,error=validate_and_clean(good())
    assert error is None
    assert cleaned["currency"]=="YER"
    assert any(x["rule_code"]=="EMAIL_REPEATED_SYMBOLS" for x in corr)
def test_missing_order_is_quarantine():
    r=good(); r["order_id"]=""
    _,_,error=validate_and_clean(r)
    assert error=="ID_ORDER_MISSING"
def test_bad_json_is_quarantine():
    r=good(); r["items_json"]="{bad"
    _,_,error=validate_and_clean(r)
    assert error=="JSON_ITEMS_CORRUPTED"
