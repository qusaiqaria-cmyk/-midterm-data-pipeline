import csv

input_file = "data/orders_1GB.csv"
output_file = "data/orders_400MB.csv"
rows_to_keep = 1000000  # 1 مليون سطر = ~400 ميجابايت

print(f"🚀 جاري قص الملف...")
print(f"📥 المصدر: {input_file}")
print(f"📤 الهدف: {output_file}")

with open(input_file, 'r', encoding='utf-8-sig', newline='') as infile, \
     open(output_file, 'w', encoding='utf-8', newline='') as outfile:
    
    reader = csv.reader(infile)
    writer = csv.writer(outfile)
    
    # الحصول على الرأس (أسماء الأعمدة)
    header = next(reader)
    writer.writerow(header)
    
    count = 0
    for i, row in enumerate(reader):
        if i >= rows_to_keep:
            break
        writer.writerow(row)
        count += 1
        
print(f"✅ تم الإنشاء بنجاح!")
print(f"📊 عدد الصفوف (بدون الرأس): {count:,}")
print(f"📁 الموقع: {output_file}")