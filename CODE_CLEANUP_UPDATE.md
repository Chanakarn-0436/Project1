# 🔧 **Code Cleanup Update**

## ❌ **ปัญหาที่พบ:**

### **1. การแสดงซ้ำซ้อน**
- **Problem Call IDs**: แสดง 2 ครั้ง
  - ใน `_render_line_charts()` บรรทัดแรก
  - ใน `_render_abnormal_line_data()` อีกครั้ง
- **Result**: ข้อมูลซ้ำซ้อนและสับสน

### **2. ลำดับการแสดงไม่เป็นระเบียบ**
- **Before**: สับสนและไม่เป็นระเบียบ
- **After**: ควรเป็น 1. Line Performance → 2. Line Board Performance + Problem Call IDs → 3. Preset KPI

### **3. โค้ดซ้ำซ้อน**
- **Before**: Logic ซ้ำในหลายที่
- **After**: Clean และ maintainable

## ✅ **การแก้ไขที่ทำ:**

### **1. ลบการแสดงซ้ำซ้อน**
```python
def _render_line_charts(self, df_view: pd.DataFrame) -> None:
    """Plot Line Chart สำหรับ Board LB2R และ L4S (ใช้แถวจริงจากตารางหลัก)"""
    st.markdown("### Line Board Performance (LB2R & L4S)")
    
    # ลบการแสดง "Problem Call IDs" ที่เกินมา - ให้ _render_abnormal_line_data() แสดงเพียงครั้งเดียว
    
    # แสดงข้อมูล abnormal ที่มีปัญหา (สีแดง) จากตารางหลัก
    self._render_abnormal_line_data(df_view)
```

### **2. จัดระเบียบลำดับการแสดง**
- **Line Performance**: ตารางหลัก
- **Line Board Performance**: Header + Problem Call IDs + ตาราง abnormal
- **Preset KPI**: ข้อมูล Preset

### **3. เพิ่มระยะห่าง**
```python
st.markdown("<br><br>", unsafe_allow_html=True)  # เพิ่มระยะห่าง

# ---------- เนื้อหา LB2R & L4S Charts อยู่ด้านล่าง ----------
```

## 📊 **ผลลัพธ์:**

### **✅ ลำดับการแสดงที่ถูกต้อง**
1. **Line Performance**: ตารางหลัก
2. **Line Board Performance (LB2R & L4S)**: Header
3. **Problem Call IDs (BER/Input/Output abnormal)**: จำนวน abnormal
4. **ตารางข้อมูล abnormal**: ข้อมูลที่มีปัญหา
5. **LB2R & L4S Charts**: กราฟและข้อมูลเพิ่มเติม
6. **Preset KPI**: ข้อมูล Preset

### **✅ Code Quality**
- **No Duplication**: ไม่มีการแสดงซ้ำซ้อน
- **Clean Code**: โค้ดสะอาดและ maintainable
- **Clear Structure**: โครงสร้างชัดเจน

### **✅ User Experience**
- **Clear Information**: ข้อมูลชัดเจนและเป็นระเบียบ
- **Easy to Read**: อ่านง่ายและเข้าใจง่าย
- **Professional**: ดูเป็นระบบเดียวกัน

## 🎯 **สรุป:**

การแก้ไขนี้ทำให้:
1. **No Duplication**: ลบการแสดงซ้ำซ้อน
2. **Clear Structure**: โครงสร้างชัดเจนและเป็นระเบียบ
3. **Clean Code**: โค้ดสะอาดและ maintainable
4. **Better UX**: User experience ที่ดีขึ้น
