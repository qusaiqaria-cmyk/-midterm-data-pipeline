import json
from pathlib import Path
from config.settings import PROJECT_ROOT

def save_metrics(metrics):
    p=PROJECT_ROOT/"reports"/"results.json"
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(metrics,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    return p
