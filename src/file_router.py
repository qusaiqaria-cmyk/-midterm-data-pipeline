from pathlib import Path
from config.settings import SMALL_FILE_THRESHOLD_MB

def route(file_path):
    p=Path(file_path)
    size_mb=p.stat().st_size/(1024*1024)
    engine="python_batch" if size_mb<=SMALL_FILE_THRESHOLD_MB else "pyspark"
    print(f"📁 حجم الملف: {size_mb:.2f} MB")
    print(f"📌 الحد الفاصل: {SMALL_FILE_THRESHOLD_MB} MB")
    print(f"⚡ المحرك المختار: {engine}")
    print("   السبب: الملف داخل/فوق الحد المحدد في الإعدادات.")
    return engine,size_mb
