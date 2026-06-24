# Face Recognition API - Optimized Workflow Guide

เอกสารนี้คือโครงสร้าง API ที่ได้รับการปรับปรุงเพื่อลดกระบวนการทำงานให้สั้นและมีประสิทธิภาพสูงสุด สำหรับใช้งานร่วมกับเครื่องสแกนหน้าพกพา (ESP32-S3) โดยยุบรวมขั้นตอนจากระบบเดิม

---

## 🚀 สรุปการปรับปรุงจากระบบเดิม
* **ยุบรวม API ลงทะเบียน:** เปลี่ยนจากการเรียก API `POST /users` และ `POST /users/{id}/images` แยกกัน ให้เหลือเพียง `POST /register` แค่ครั้งเดียว
* **ตัด API `/train` ทิ้ง:** ระบบเดิมต้องรอเรียก API `/train` เพื่อฝึกสอนโมเดล ระบบใหม่จะทำการสกัด Face Embeddings อัตโนมัติทันทีที่อัปโหลดรูปลงทะเบียน
* **ลดจำนวนรูปภาพ:** ลดการใช้รูปภาพจาก 5-10 รูป เหลือเพียง 1-2 รูป (หน้าตรง แสงชัดเจน) ก็เพียงพอต่อการใช้งาน

---

## 📡 API Endpoints (Optimized Version)

### API 1: Health Check
**Purpose:** ตรวจสอบสถานะการทำงานของเซิร์ฟเวอร์
* **Method:** GET
* **URL:** `{{baseUrl}}/`
* **Success Response (200):**

{
  "status": "ok"
}
### API 2: Register & Train (สร้างผู้ใช้และบันทึกใบหน้า)

**Purpose:** ลงทะเบียนนักศึกษาใหม่ พร้อมสกัดเวกเตอร์ใบหน้าเข้าสู่ระบบอัตโนมัติ (1 Request จบ)

- **Method:** POST
    
- **URL:** `{{baseUrl}}/register`
    
- **Headers:** None
    
- **Body:** `form-data`
    
    - Key: `name` (type: **Text**) - ชื่อหรือรหัสนักศึกษา (เช่น "6600001")
        
    - Key: `file` (type: **File**) - รูปภาพหน้าตรง 10 รูป
        
- **Success Response (200):**
    

JSON

```
{
  "message": "User registered and face embedded successfully",
  "user_id": 1,
  "name": "6600001"
}
```

### API 3: Verify Face (สแกนใบหน้าเข้าใช้งาน)

**Purpose:** ยืนยันตัวบุคคลจากรูปภาพที่ส่งมาจากเครื่อง ESP32-S3 (อิงตามระบบเดิม)

- **Method:** POST
    
- **URL:** `{{baseUrl}}/verify`
    
- **Headers:** None
    
- **Body:** `form-data`
    
    - Key: `file` (type: **File**) - ไฟล์รูปภาพดิบที่สแกนได้
        
- **Success Response - Match Found (200):**
    

JSON

```
{
  "match": true,
  "user_id": 1,
  "name": "6600001",
  "similarity_score": 0.85,
  "timestamp": "2026-06-24T10:30:00"
}
```

### API 4: Get Attendance Logs

**Purpose:** ดึงข้อมูลประวัติการสแกนเข้าใช้งานทั้งหมด (อิงตามระบบเดิม)

- **Method:** GET
    
- **URL:** `{{baseUrl}}/logs`
    
- **Success Response (200):**
    

JSON

```
[
  {
    "id": 1,
    "user_id": 1,
    "name": "6600001",
    "similarity_score": 0.85,
    "device_id": "ESP32-S3-01",
    "timestamp": "2026-06-24T10:30:00"
  }
]
```

## 📊 ตารางเปรียบเทียบ Workflow สถาปัตยกรรมระบบ

| **ขั้นตอน**       | **ระบบเดิม (อิงจาก Postman Guide)**           | **ระบบที่ได้รับการปรับปรุง (Optimized)**               |
| ----------------- | --------------------------------------------- | ------------------------------------------------------ |
| **การลงทะเบียน**  | เรียก API `/users`<br><br>                    | เรียก API `/register` พร้อมแนบรูป (1 Request จบ)       |
| **การส่งรูปภาพ**  | เรียก API `/users/{id}/images` ซ้ำ 5-10 ครั้ง | (รวมอยู่ในขั้นตอน Registration แล้ว)                   |
| **การประมวลผล**   | เรียก API `/train` เพื่อแปลงรูปเป็นเวกเตอร์   | ระบบสกัดเวกเตอร์ให้อัตโนมัติทันทีที่รับรูป             |
| **การใช้งานจริง** | เรียก API `/verify`<br><br>                   | เรียก API `/verify` (ทำงานได้รวดเร็วและเป็น Real-time) |
