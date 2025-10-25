# 🔧 **Summary Table & Report Data Synchronization**

## ❌ **ปัญหาที่พบ:**

### **1. ข้อมูลไม่สอดคล้องระหว่าง UI และ Summary/Report**
- **Line Board Performance**: แสดง "⚠️ Abnormal Line Board Data - Found 11 rows with issues"
- **Summary Table**: แสดงจำนวน abnormal ที่ไม่ตรงกัน
- **PDF Report**: ใช้ข้อมูลจาก `prepare()` ที่อาจไม่ตรงกับ UI

### **2. Logic การนับ Abnormal ไม่สอดคล้อง**
- **UI**: ใช้ `_render_abnormal_line_data()` 
- **Summary/Report**: ใช้ `prepare()` function
- **ผลลัพธ์**: จำนวน abnormal ไม่ตรงกัน

## ✅ **การแก้ไขที่ทำ:**

### **1. Synchronize Logic ระหว่าง UI และ Summary/Report**
```python
# ใช้เงื่อนไขเดียวกับ _render_abnormal_line_data() ใน prepare()
# 5.1 BER abnormal - ใช้เงื่อนไขเดียวกับตารางหลัก: v > 0 หรือ None
ber_val = pd.to_numeric(df_result["Instant BER After FEC"], errors="coerce")
thr_val = pd.to_numeric(df_result["Threshold"], errors="coerce")
mask_ber = ((ber_val > 0) | ber_val.isna()) & thr_val.notna()

# 5.2 Input abnormal - ใช้เงื่อนไขเดียวกับตารางหลัก
vin = pd.to_numeric(df_result.get(self.col_in, pd.Series()), errors="coerce")
min_in = pd.to_numeric(df_result.get(self.col_min_in, pd.Series()), errors="coerce")
max_in = pd.to_numeric(df_result.get(self.col_max_in, pd.Series()), errors="coerce")
mask_input = (vin.notna() & min_in.notna() & max_in.notna() & ((vin < min_in) | (vin > max_in)))

# 5.3 Output abnormal - ใช้เงื่อนไขเดียวกับตารางหลัก
vout = pd.to_numeric(df_result.get(self.col_out, pd.Series()), errors="coerce")
min_out = pd.to_numeric(df_result.get(self.col_min_out, pd.Series()), errors="coerce")
max_out = pd.to_numeric(df_result.get(self.col_max_out, pd.Series()), errors="coerce")
mask_output = (vout.notna() & min_out.notna() & max_out.notna() & ((vout < min_out) | (vout > max_out)))

# 5.4 รวมทุกเงื่อนไข abnormal (BER + Input + Output) - เหมือนกับ _render_abnormal_line_data()
mask_any_abnormal = mask_ber | mask_input | mask_output
```

### **2. ใช้ข้อมูลเดียวกันสำหรับ Summary และ Report**
```python
# 6) Save results to properties - ใช้ข้อมูลจาก mask_any_abnormal เหมือนกับ _render_abnormal_line_data()
df_abnormal_all = df_result.loc[mask_any_abnormal, [
    "Site Name", "ME", "Call ID", "Measure Object", "Threshold", "Instant BER After FEC",
    self.col_max_out, self.col_min_out, self.col_out,
    self.col_max_in, self.col_min_in, self.col_in, "Route"
]].copy()

self.df_abnormal = df_abnormal_all
```

### **3. ข้อมูลที่สอดคล้องกัน**
- **UI**: "⚠️ Abnormal Line Board Data - Found 11 rows with issues"
- **Summary Table**: แสดง 11 rows (ตรงกัน)
- **PDF Report**: ใช้ข้อมูล 11 rows เดียวกัน

## 📊 **ผลลัพธ์:**

### **✅ ข้อมูลสอดคล้องกัน**
- **Line Board Performance**: "Found 11 rows with issues"
- **Summary Table**: แสดง 11 abnormal rows
- **PDF Report**: ใช้ข้อมูล 11 rows เดียวกัน

### **✅ Logic ที่สอดคล้อง**
- **BER**: `((ber_val > 0) | ber_val.isna()) & thr_val.notna()`
- **Input**: `(vin < min_in) | (vin > max_in)`
- **Output**: `(vout < min_out) | (vout > max_out)`
- **รวม**: `mask_ber | mask_input | mask_output`

### **✅ Data Flow ที่ถูกต้อง**
1. **UI**: `_render_abnormal_line_data()` → แสดง 11 rows
2. **Summary**: `prepare()` → ใช้ logic เดียวกัน → 11 rows
3. **Report**: ใช้ข้อมูลจาก `prepare()` → 11 rows

## 🎯 **สรุป:**

การแก้ไขนี้ทำให้:
1. **ข้อมูลสอดคล้อง**: UI, Summary, Report แสดงจำนวนเดียวกัน
2. **Logic เดียวกัน**: ใช้เงื่อนไข abnormal เดียวกันทุกที่
3. **Data Consistency**: ข้อมูลที่แสดงในทุกส่วนตรงกัน
4. **User Experience**: ไม่มีความสับสนเรื่องจำนวน abnormal
