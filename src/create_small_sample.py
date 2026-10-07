import csv, argparse
from pathlib import Path
from config.settings import SAMPLE_ROWS

def create(input_file, output_file, rows=SAMPLE_ROWS):
    with open(input_file,"r",encoding="utf-8-sig",newline="") as src, open(output_file,"w",encoding="utf-8",newline="") as dst:
        reader=csv.reader(src); writer=csv.writer(dst)
        for i,row in enumerate(reader):
            if i==0: writer.writerow(row); continue
            if i>rows: break
            writer.writerow(row)
    print(f"✅ Sample created: {output_file} ({rows} data rows)")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True); ap.add_argument("--output",default="data/orders_samplee.csv")
    ap.add_argument("--rows",type=int,default=SAMPLE_ROWS)
    a=ap.parse_args(); create(a.input,a.output,a.rows)
