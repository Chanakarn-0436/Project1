# 🔧 **Abnormal Line Board Table Fix**

## ❌ **ปัญหาที่พบ:**

### **1. Abnormal Line Board Table ไม่แสดงข้อมูลที่ถูกต้อง**
- **Line Board Performance**: แสดง "⚠️ Abnormal Line Board Data - Found 11 rows with issues"
- **Abnormal Line Board Table**: แสดงข้อมูลไม่ตรงกันหรือไม่แสดง
- **User Request**: ต้องการให้ดึงข้อมูลจาก Line Board Performance มาแสดง

### **2. ข้อมูลไม่สอดคล้องกัน**
- **UI**: ใช้ `_render_abnormal_line_data()` ใน `Line_Analyzer.py`
- **Table**: ใช้ logic แยกต่างหากใน `table1.py`
- **ผลลัพธ์**: ข้อมูลไม่ตรงกัน

## ✅ **การแก้ไขที่ทำ:**

### **1. ใช้ข้อมูลจาก Line_Analyzer ที่เตรียมไว้แล้ว**
```python
# ใช้ข้อมูลจาก Line_Analyzer ที่เตรียมไว้แล้ว
line_analyzer = st.session_state.get("line_analyzer")
if line_analyzer and hasattr(line_analyzer, 'df_abnormal') and not line_analyzer.df_abnormal.empty:
    df_abn = line_analyzer.df_abnormal.copy()
```

### **2. ใช้เงื่อนไขเดียวกับ _render_abnormal_line_data()**
```python
# BER check - ใช้เงื่อนไขเดียวกับ _render_abnormal_line_data()
try:
    ber = float(row.get("Instant BER After FEC", 0))
    thr = float(row.get("Threshold", 0))
    if pd.notna(thr) and (pd.isna(ber) or ber > 0):
        styles[col_map["Instant BER After FEC"]] = "background-color:#ff4d4d; color:white"
except (ValueError, TypeError):
    try:
        thr = float(row.get("Threshold", 0))
        if pd.notna(thr):
            styles[col_map["Instant BER After FEC"]] = "background-color:#ff4d4d; color:white"
    except (ValueError, TypeError):
        pass
```

### **3. เพิ่ม Input/Output Abnormal Highlighting**
```python
# Input check
try:
    v = float(row.get("Input Optical Power(dBm)", 0))
    lo = float(row.get("Minimum threshold(in)", 0))
    hi = float(row.get("Maximum threshold(in)", 0))
    if pd.notna(v) and pd.notna(lo) and pd.notna(hi) and (v < lo or v > hi):
        styles[col_map["Input Optical Power(dBm)"]] = "background-color:#ff4d4d; color:white"
except (ValueError, TypeError):
    pass

# Output check
try:
    v = float(row.get("Output Optical Power (dBm)", 0))
    lo = float(row.get("Minimum threshold(out)", 0))
    hi = float(row.get("Maximum threshold(out)", 0))
    if pd.notna(v) and pd.notna(lo) and pd.notna(hi) and (v < lo or v > hi):
        styles[col_map["Output Optical Power (dBm)"]] = "background-color:#ff4d4d; color:white"
except (ValueError, TypeError):
    pass
```

### **4. ปรับปรุง Formatting**
```python
.format({
    "Threshold": "{:.2E}",
    "Instant BER After FEC": "{:.2E}",
    "Input Optical Power(dBm)": "{:.4f}",
    "Output Optical Power (dBm)": "{:.4f}",
    "Minimum threshold(in)": "{:.4f}",
    "Maximum threshold(in)": "{:.4f}",
    "Minimum threshold(out)": "{:.4f}",
    "Maximum threshold(out)": "{:.4f}"
}, na_rep="-")
```

## 📊 **ผลลัพธ์:**

### **✅ ข้อมูลสอดคล้องกัน**
- **Line Board Performance**: "⚠️ Abnormal Line Board Data - Found 11 rows with issues"
- **Abnormal Line Board Table**: แสดง 11 rows เดียวกัน
- **Data Source**: ใช้ข้อมูลจาก `line_analyzer.df_abnormal`

### **✅ Highlighting ที่ถูกต้อง**
- **BER**: สีแดงถ้า `(pd.isna(ber) or ber > 0) & pd.notna(thr)`
- **Input**: สีแดงถ้า `(v < lo or v > hi)`
- **Output**: สีแดงถ้า `(v < lo or v > hi)`
- **Color**: `#ff4d4d` (แดงเข้ม) พร้อม `color:white`

### **✅ Formatting ที่สอดคล้อง**
- **BER/Threshold**: Scientific notation `{:.2E}`
- **Power**: 4 decimal places `{:.4f}`
- **Consistent**: ใช้ formatting เดียวกับ Line Board Performance

## 🎯 **สรุป:**

การแก้ไขนี้ทำให้:
1. **ข้อมูลสอดคล้อง**: Abnormal Line Board Table แสดงข้อมูลเดียวกับ Line Board Performance
2. **Data Source**: ใช้ข้อมูลจาก `line_analyzer.df_abnormal` ที่เตรียมไว้แล้ว
3. **Logic เดียวกัน**: ใช้เงื่อนไขเดียวกับ `_render_abnormal_line_data()`
4. **User Experience**: แสดงข้อมูลที่ถูกต้องและสอดคล้องกัน
