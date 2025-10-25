# 🔧 **Line Abnormal Count Fix**

## ❌ **ปัญหาที่พบ:**

### **1. การนับ Abnormal ไม่ตรงกัน**
- **Line Performance**: แสดง fail 11 rows
- **เมนูจุดแดง**: แสดงแค่ 3 rows
- **Root Cause**: Logic การนับ abnormal ใน `prepare()` ไม่ตรงกับ `_render_problem_call_ids()`

### **2. เงื่อนไข Abnormal ที่ไม่สอดคล้อง**
- **ตารางหลัก**: ใช้ `((ber_val > 0) | ber_val.isna()) & thr_val.notna()`
- **prepare()**: ใช้ `(ber_val > thr_val)` เท่านั้น
- **ผลลัพธ์**: นับไม่ตรงกัน

## ✅ **การแก้ไขที่ทำ:**

### **1. แก้ไข BER Abnormal Logic**
```python
# Before: ใช้เงื่อนไขแคบ
mask_ber = (pd.notna(ber_val) & pd.notna(thr_val) & (ber_val > thr_val))

# After: ใช้เงื่อนไขเดียวกับตารางหลัก
mask_ber = ((ber_val > 0) | ber_val.isna()) & thr_val.notna()
```

### **2. เพิ่ม Input/Output Abnormal Logic**
```python
# Input abnormal - ใช้เงื่อนไขเดียวกับตารางหลัก
vin = pd.to_numeric(df_result.get(self.col_in, pd.Series()), errors="coerce")
min_in = pd.to_numeric(df_result.get(self.col_min_in, pd.Series()), errors="coerce")
max_in = pd.to_numeric(df_result.get(self.col_max_in, pd.Series()), errors="coerce")
mask_input = (vin.notna() & min_in.notna() & max_in.notna() & ((vin < min_in) | (vin > max_in)))

# Output abnormal - ใช้เงื่อนไขเดียวกับตารางหลัก
vout = pd.to_numeric(df_result.get(self.col_out, pd.Series()), errors="coerce")
min_out = pd.to_numeric(df_result.get(self.col_min_out, pd.Series()), errors="coerce")
max_out = pd.to_numeric(df_result.get(self.col_max_out, pd.Series()), errors="coerce")
mask_output = (vout.notna() & min_out.notna() & max_out.notna() & ((vout < min_out) | (vout > max_out)))
```

### **3. รวมทุกเงื่อนไข Abnormal**
```python
# รวมทุกเงื่อนไข abnormal (BER + Input + Output)
mask_any_abnormal = mask_ber | mask_input | mask_output

# ใช้ข้อมูลจาก mask_any_abnormal เพื่อให้ตรงกับตารางหลัก
df_abnormal_all = df_result.loc[mask_any_abnormal, [
    "Site Name", "ME", "Call ID", "Measure Object", "Threshold", "Instant BER After FEC",
    self.col_max_out, self.col_min_out, self.col_out,
    self.col_max_in, self.col_min_in, self.col_in, "Route"
]].copy()
```

## 📊 **ผลลัพธ์:**

### **✅ การนับที่สอดคล้อง**
- **Line Performance**: แสดง fail 11 rows
- **เมนูจุดแดง**: แสดง 11 rows (ตรงกัน)
- **Logic**: ใช้เงื่อนไขเดียวกับตารางหลัก

### **✅ เงื่อนไข Abnormal ที่ถูกต้อง**
- **BER**: `((ber_val > 0) | ber_val.isna()) & thr_val.notna()`
- **Input**: `(vin < min_in) | (vin > max_in)`
- **Output**: `(vout < min_out) | (vout > max_out)`
- **รวม**: `mask_ber | mask_input | mask_output`

## 🎯 **สรุป:**

การแก้ไขนี้ทำให้:
1. **การนับสอดคล้อง**: Line Performance และเมนูจุดแดงแสดงจำนวนเดียวกัน
2. **Logic ถูกต้อง**: ใช้เงื่อนไขเดียวกับตารางหลัก
3. **ครอบคลุมทุกเงื่อนไข**: BER + Input + Output abnormal
