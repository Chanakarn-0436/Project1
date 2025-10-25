# 🔧 **Line Board Header Position Update**

## ❌ **ปัญหาที่พบ:**

### **1. Header แสดงในตำแหน่งผิด**
- **Line Board Performance**: แสดง "Problem Call IDs (BER/Input/Output abnormal) - Found 11 rows" หลังจากตาราง
- **User Request**: ต้องการให้แสดงข้างบนส่วน "Line Board Performance (LB2R & L4S)"

### **2. Layout ไม่เป็นระเบียบ**
- **Before**: Header อยู่หลังตาราง
- **After**: Header อยู่ก่อนตาราง
- **Result**: Layout ที่เป็นระเบียบมากขึ้น

## ✅ **การแก้ไขที่ทำ:**

### **1. ย้าย Header ไปข้างบน**
```python
def _render_line_charts(self, df_view: pd.DataFrame) -> None:
    """Plot Line Chart สำหรับ Board LB2R และ L4S (ใช้แถวจริงจากตารางหลัก)"""
    st.markdown("### Line Board Performance (LB2R & L4S)")
    
    # แสดงจำนวน abnormal rows ก่อน
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
    abnormal_count = mask_any_abnormal.sum()
    
    st.markdown(f"**Problem Call IDs (BER/Input/Output abnormal)** - Found {abnormal_count} rows")
    
    # แสดงข้อมูล abnormal ที่มีปัญหา (สีแดง) จากตารางหลัก
    self._render_abnormal_line_data(df_view)
```

### **2. Layout ที่เป็นระเบียบ**
- **Line Board Performance (LB2R & L4S)**: Header หลัก
- **Problem Call IDs (BER/Input/Output abnormal) - Found 11 rows**: จำนวน abnormal
- **ตารางข้อมูล**: ข้อมูล abnormal ที่มีปัญหา

## 📊 **ผลลัพธ์:**

### **✅ Layout ที่เป็นระเบียบ**
- **Header หลัก**: "Line Board Performance (LB2R & L4S)"
- **จำนวน Abnormal**: "Problem Call IDs (BER/Input/Output abnormal) - Found 11 rows"
- **ตารางข้อมูล**: ข้อมูล abnormal ที่มีปัญหา

### **✅ User Experience**
- **Clear Information**: ข้อมูลชัดเจนและเป็นระเบียบ
- **Easy to Read**: อ่านง่ายและเข้าใจง่าย
- **Professional**: ดูเป็นระบบเดียวกัน

### **✅ Data Consistency**
- **Same Logic**: ใช้ logic เดียวกัน
- **Same Count**: จำนวนที่แสดงถูกต้อง
- **Same Format**: ใช้ formatting เดียวกัน

## 🎯 **สรุป:**

การแก้ไขนี้ทำให้:
1. **Header ข้างบน**: แสดงจำนวน abnormal ก่อนตาราง
2. **Layout เป็นระเบียบ**: ข้อมูลเรียงลำดับถูกต้อง
3. **User Experience**: อ่านง่ายและเข้าใจง่าย
4. **Professional**: ดูเป็นระบบเดียวกัน
