# Report Formatting Update

## 🎯 **การอัพเดต Report Formatting ตามที่ร้องขอ**

### ✅ **สิ่งที่ได้ทำการปรับปรุง:**

#### **1. Threshold และ BER Format เป็น Scientific Notation**
- **Threshold**: แสดงเป็น `0.00E+00` แทน `0`
- **Instant BER After FEC**: แสดงเป็น scientific notation เช่น `8.71E-06`

#### **2. เน้นสีแดงคอลัมน์สำคัญ**
- **Fiber Performance**: คอลัมน์ "Max - Min (dB)" เน้นสีแดง
- **Line Performance**: คอลัมน์ "Instant BER After FEC" เน้นสีแดง

### 📊 **รายละเอียดการเปลี่ยนแปลง:**

#### **1. Scientific Notation Formatting**
```python
# Special formatting for Threshold and Instant BER After FEC
if "Threshold" in df_show.columns:
    df_show["Threshold"] = pd.to_numeric(df_show["Threshold"], errors="coerce")
    # Format Threshold เป็น scientific notation
    df_show["Threshold"] = df_show["Threshold"].apply(
        lambda x: f"{x:.2E}" if pd.notna(x) else ""
    )

if "Instant BER After FEC" in df_show.columns:
    df_show["Instant BER After FEC"] = pd.to_numeric(df_show["Instant BER After FEC"], errors="coerce")
    # Format BER เป็น scientific notation
    df_show["Instant BER After FEC"] = df_show["Instant BER After FEC"].apply(
        lambda x: f"{x:.2E}" if pd.notna(x) else ""
    )
```

#### **2. Column Highlighting**
```python
# Highlight Max - Min (dB) column for Fiber section
elif section_name == "Fiber" and "Max - Min (dB)" in cols_to_show:
    col_idx = cols_to_show.index("Max - Min (dB)")
    if col_idx < len(df_show.columns):
        style_cmds.append(("BACKGROUND", (col_idx, 1), (col_idx, -1), light_red))
        style_cmds.append(("TEXTCOLOR", (col_idx, 1), (col_idx, -1), text_black))

# Highlight Instant BER After FEC column for Line section
elif section_name == "Line" and "Instant BER After FEC" in cols_to_show:
    col_idx = cols_to_show.index("Instant BER After FEC")
    if col_idx < len(df_show.columns):
        style_cmds.append(("BACKGROUND", (col_idx, 1), (col_idx, -1), light_red))
        style_cmds.append(("TEXTCOLOR", (col_idx, 1), (col_idx, -1), text_black))
```

### 🎨 **Visual Improvements:**

#### **1. Scientific Notation Display**
- **Before**: `0` → **After**: `0.00E+00`
- **Before**: `0.00000870504774` → **After**: `8.71E-06`
- **Format**: `{value:.2E}` (2 decimal places in scientific notation)

#### **2. Column Highlighting**
- **Fiber Section**: "Max - Min (dB)" column highlighted in red
- **Line Section**: "Instant BER After FEC" column highlighted in red
- **Color**: Light red background with black text

### 📋 **Sections ที่ได้รับผลกระทบ:**

#### **1. Line Performance**
- **Threshold**: แสดงเป็น scientific notation
- **Instant BER After FEC**: แสดงเป็น scientific notation + เน้นสีแดง

#### **2. Fiber Performance**
- **Max - Min (dB)**: เน้นสีแดงทั้งคอลัมน์
- **Format**: ทศนิยม 2 ตำแหน่ง

#### **3. All Performance Sections**
- **Threshold columns**: แสดงเป็น scientific notation
- **BER columns**: แสดงเป็น scientific notation

### 🔧 **Technical Changes:**

#### **1. Scientific Notation Formatting**
```python
# Format Threshold และ BER เป็น scientific notation
df_show["Threshold"] = df_show["Threshold"].apply(
    lambda x: f"{x:.2E}" if pd.notna(x) else ""
)
df_show["Instant BER After FEC"] = df_show["Instant BER After FEC"].apply(
    lambda x: f"{x:.2E}" if pd.notna(x) else ""
)
```

#### **2. Column Highlighting Logic**
```python
# Highlight specific columns
if section_name == "Fiber" and "Max - Min (dB)" in cols_to_show:
    # Highlight Max - Min (dB) column
    
elif section_name == "Line" and "Instant BER After FEC" in cols_to_show:
    # Highlight Instant BER After FEC column
```

### 📈 **Benefits:**

#### **1. Better Data Representation**
- **Scientific notation**: แสดงค่าที่เล็กมากได้ชัดเจน
- **Consistent format**: ทุก threshold และ BER แสดงแบบเดียวกัน

#### **2. Visual Emphasis**
- **Red highlighting**: เน้นคอลัมน์สำคัญ
- **Easy identification**: หาข้อมูลสำคัญได้ง่ายขึ้น

#### **3. Professional Appearance**
- **Scientific notation**: ดูเป็นมืออาชีพมากขึ้น
- **Color coding**: แยกแยะข้อมูลได้ชัดเจน

### 🎯 **Result Examples:**

#### **Line Performance Table:**
```
| Site Name | ME | Call ID | Measure Object | Threshold | Instant BER After FEC |
|-----------|----|---------|----------------|-----------|----------------------|
| Jasmine   | BK | 13      | LB2Rx5[...]    | 0.00E+00  | 8.71E-06            |
```

#### **Fiber Performance Table:**
```
| Begin Time | End Time | Site Name | ME | Max - Min (dB) |
|------------|----------|-----------|----|----------------|
| 2024-01-01 | 2024-01-01| Jasmine   | BK | 2.50          |
```

### ✅ **Summary:**

✅ **Threshold**: แสดงเป็น `0.00E+00` แทน `0`  
✅ **BER**: แสดงเป็น scientific notation  
✅ **Max - Min (dB)**: เน้นสีแดงใน Fiber section  
✅ **Instant BER After FEC**: เน้นสีแดงใน Line section  
✅ **Format consistency**: ทุกคอลัมน์แสดงแบบเดียวกัน  

การอัพเดตนี้จะทำให้ report แสดงข้อมูลได้ชัดเจนและเป็นมืออาชีพมากขึ้นครับ! 🎉
