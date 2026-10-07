from src.quality_rules import *
def test_arabic_digits(): assert arabic_numbers("٥٠٠٠٫٥")=="5000.5"
def test_currency(): assert currency("ريال يمني")=="YER"
def test_price_words(): assert normalize_price("خمسة آلاف ريال")==5000.0
def test_phone(): assert phone("+967 771234567")=="0771234567"
def test_email(): assert email("USER@@mail..COM")=="user@mail.com"
def test_date_iso_datetime(): assert date_iso("2025-02-24T21:29:00")=="2025-02-24"
def test_whitespace(): assert whitespace("  a   b ")=="a b"
