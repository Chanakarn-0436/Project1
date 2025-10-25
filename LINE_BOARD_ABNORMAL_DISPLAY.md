# 🔧 **Line Board Abnormal Display Fix**

## ❌ **ปัญหาที่พบ:**

### **1. Line Board Performance ไม่แสดงข้อมูล Abnormal**
- **Before**: แสดงแค่ข้อความ "📊 Line Board Performance data is displayed in the main table above."
- **Issue**: ไม่แสดงข้อมูล abnormal ที่มีปัญหา (สีแดง)
- **User Request**: ต้องการเห็นข้อมูล abnormal ที่มีปัญหาใน Line Board Performance

## ✅ **การแก้ไขที่ทำ:**

### **1. เพิ่ม Function `_render_abnormal_line_data()`**
```python
def _render_abnormal_line_data(self, df_view: pd.DataFrame) -> None:
    """แสดงข้อมูล abnormal ที่มีปัญหา (สีแดง) สำหรับ Line Board Performance"""
    # ใช้เงื่อนไขเดียวกับตารางหลัก: BER + Input + Output abnormal
    ber_val = pd.to_numeric(df_view.get("Instant BER After FEC", pd.Series()), errors="coerce")
    thr_val = pd.to_numeric(df_view.get("Threshold", pd.Series()), errors="coerce")
    mask_ber = ((ber_val > 0) | ber_val.isna()) & thr_val.notna()
    
    # Input abnormal
    vin = pd.to_numeric(df_view.get(self.col_in, pd.Series()), errors="coerce")
    min_in = pd.to_numeric(df_view.get(self.col_min_in, pd.Series()), errors="coerce")
    max_in = pd.to_numeric(df_view.get(self.col_max_in, pd.Series()), errors="coerce")
    mask_input = (vin.notna() & min_in.notna() & max_in.notna() & ((vin < min_in) | (vin > max_in)))
    
    # Output abnormal
    vout = pd.to_numeric(df_view.get(self.col_out, pd.Series()), errors="coerce")
    min_out = pd.to_numeric(df_view.get(self.col_min_out, pd.Series()), errors="coerce")
    max_out = pd.to_numeric(df_view.get(self.col_max_out, pd.Series()), errors="coerce")
    mask_output = (vout.notna() & min_out.notna() & max_out.notna() & ((vout < min_out) | (vout > max_out)))
    
    # รวมทุกเงื่อนไข abnormal
    mask_any_abnormal = mask_ber | mask_input | mask_output
```

### **2. แก้ไข `_render_line_charts()` Function**
```python
# Before: แสดงแค่ข้อความ
st.info("📊 Line Board Performance data is displayed in the main table above.")

# After: แสดงข้อมูล abnormal ที่มีปัญหา
self._render_abnormal_line_data(df_view)
```

### **3. เพิ่ม Highlighting และ Formatting**
```python
def highlight_abnormal_row(row):
    styles = [""] * len(row)
    col_map = {c: i for i, c in enumerate(fail_rows.columns)}
    
    # BER check - สีแดงถ้า abnormal
    # Input check - สีแดงถ้า abnormal  
    # Output check - สีแดงถ้า abnormal
    
    return styles
```

## 📊 **ผลลัพธ์:**

### **✅ Line Board Performance แสดงข้อมูล Abnormal**
- **Header**: "⚠️ Abnormal Line Board Data - Found X rows with issues"
- **Data**: แสดงเฉพาะแถวที่มีปัญหา (สีแดง)
- **Highlighting**: BER, Input, Output abnormal แสดงสีแดง
- **Formatting**: Scientific notation สำหรับ BER, 4 decimal places สำหรับ Power

### **✅ เงื่อนไข Abnormal ที่ถูกต้อง**
- **BER**: `((ber_val > 0) | ber_val.isna()) & thr_val.notna()`
- **Input**: `(vin < min_in) | (vin > max_in)`
- **Output**: `(vout < min_out) | (vout > max_out)`
- **รวม**: `mask_ber | mask_input | mask_output`

### **✅ User Experience**
- **มีข้อมูล**: แสดงตาราง abnormal พร้อม highlighting
- **ไม่มีข้อมูล**: แสดง "✅ All Line Board data is within normal parameters."
- **Consistent**: ใช้เงื่อนไขเดียวกับตารางหลัก

## 🎯 **สรุป:**

การแก้ไขนี้ทำให้:
1. **แสดงข้อมูล Abnormal**: Line Board Performance แสดงข้อมูลที่มีปัญหา
2. **Highlighting สีแดง**: แสดงสีแดงสำหรับ BER, Input, Output abnormal
3. **User Friendly**: แสดงจำนวน abnormal และข้อความที่เหมาะสม
4. **Consistent Logic**: ใช้เงื่อนไขเดียวกับตารางหลัก
