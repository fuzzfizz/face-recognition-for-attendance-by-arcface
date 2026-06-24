# Face Recognition API - Asynchronous Workflow Guide

เอกสารนี้คือโครงสร้าง API สำหรับระบบสแกนใบหน้าที่มีการปรับปรุงสถาปัตยกรรมเป็นแบบ **คิวประมวลผล (Asynchronous Processing)** เพื่อป้องกันปัญหาเซิร์ฟเวอร์โหลดหนัก (Overload) เมื่อมีนักศึกษาลงทะเบียนพร้อมกันจำนวนมาก

---

## 🚀 สรุปสถาปัตยกรรมระบบใหม่
* **รวดเร็ว ไม่บล็อกการทำงาน:** การส่งรูปลงทะเบียนจะบันทึกไฟล์ลงฮาร์ดดิสก์และเข้าคิว (Pending) ทันที โดยไม่รอให้ AI สกัดเวกเตอร์ ทำให้เครื่องสแกน (ESP32-S3) หรือแอปพลิเคชันไม่ต้องรอโหลดนาน
* **ประมวลผลอยู่เบื้องหลัง (Background Worker):** โมเดล AI จะทยอยนำรูปภาพในคิวมาสกัดใบหน้าตามรอบเวลา (Scheduler) หรือเมื่อถูกสั่งงาน (Manual Trigger)
* **เช็คสถานะได้:** แอดมินหรือระบบสามารถตรวจสอบได้ว่ารูปภาพถูกประมวลผลสำเร็จ หรือไม่พบใบหน้า

---

## 📡 API Endpoints

### API 1: Health Check
**Purpose:** ตรวจสอบสถานะการทำงานของเซิร์ฟเวอร์
* **Method:** GET
* **URL:** `{{baseUrl}}/`
* **Success Response (200):**

{
  "status": "ok"
}

### API 2: Register (อัปโหลดรูปลงทะเบียนเข้าคิว)

**Purpose:** ส่งไฟล์รูปภาพเข้าสู่ระบบเพื่อรอให้ AI ประมวลผลในภายหลัง (คืนค่าผลลัพธ์ทันที)

- **Method:** POST
    
- **URL:** `{{baseUrl}}/register`
    
- **Headers:** None
    
- **Body:** `form-data`
    
    - Key: `student_id` (type: **Text**) - รหัสนักศึกษา (เช่น "6600001")
        
    - Key: `files` (type: **File**) - รูปภาพหน้าตรง (10 รูป)
        
- **Success Response (200):**
    

JSON

```
{
  "message": "Images queued for processing successfully",
  "student_id": "6600001",
  "status": "pending"
}
```

### API 3: Check Registration Status (ตรวจสอบสถานะ AI)

**Purpose:** ตรวจสอบว่าระบบหลังบ้านทำการสกัดใบหน้าของนักศึกษาคนนี้เสร็จสมบูรณ์หรือยัง

- **Method:** GET
    
- **URL:** `{{baseUrl}}/register/status/6600001`
    
- **Success Response - กำลังรอ (200):**
    

JSON

```
{
  "student_id": "6600001",
  "status": "pending",
  "message": "Waiting for AI processing"
}
```

- **Success Response - สำเร็จ (200):**
    

JSON

```
{
  "student_id": "6600001",
  "status": "completed",
  "message": "Face extracted and saved successfully"
}
```

- **Success Response - ไม่ผ่าน (200):**
    

JSON

```
{
  "student_id": "6600001",
  "status": "failed",
  "message": "No face detected, please upload a new clear image"
}
```

### API 4: Trigger Training (สั่งประมวลผลคิวทันที)

**Purpose:** สั่งให้ Background Worker ดึงรูปภาพที่มีสถานะ `pending` ทั้งหมดมาประมวลผลเข้าโมเดล AI ทันที (Manual Trigger)

- **Method:** POST
    
- **URL:** `{{baseUrl}}/train-now`
    
- **Success Response (200):**
    

JSON

```
{
  "message": "Background training started",
  "pending_images_in_queue": 15
}
```

### API 5: Verify Face (สแกนใบหน้าเข้าห้องเรียน)

**Purpose:** ยืนยันตัวบุคคลแบบ Real-time จากภาพที่ถ่ายโดย ESP32-S3

- **Method:** POST
    
- **URL:** `{{baseUrl}}/verify`
    
- **Headers:** None
    
- **Body:** `form-data`
    
    - Key: `file` (type: **File**) - ไฟล์รูปภาพดิบ
        
- **Success Response - Match Found (200):**
    

JSON

```
{
  "match": true,
  "student_id": "6600001",
  "similarity_score": 0.85,
  "timestamp": "2026-06-24T12:30:00"
}
```

### API 6: Get Attendance Logs (ดูประวัติการเข้าใช้งาน)

**Purpose:** ดึงข้อมูลประวัติการสแกนเข้าใช้งานทั้งหมด

- **Method:** GET
    
- **URL:** `{{baseUrl}}/logs`
    
- **Success Response (200):**
    

JSON

```
[
  {
    "id": 1,
    "student_id": "6600001",
    "similarity_score": 0.85,
    "device_id": "ESP32-S3-01",
    "timestamp": "2026-06-24T12:30:00"
  }
]
```

## 🔄 ลำดับการทำงาน (Workflow)

| **ขั้นตอน**         | **ฝั่งผู้ใช้งาน / ESP32-S3**                           | **ฝั่งเซิร์ฟเวอร์ (API & AI)**                                        |
| ------------------- | ------------------------------------------------------ | --------------------------------------------------------------------- |
| **1. ลงทะเบียน**    | เรียก API `/register` ส่งรหัสนักศึกษาและรูปภาพ 1-3 รูป | รับรูปเซฟลงดิสก์ ตั้งสถานะใน DB เป็น `pending` คืนค่า 200 ทันที       |
| **2. สั่งประมวลผล** | (แอดมิน) กดปุ่มบนหน้าเว็บเพื่อเรียก API `/train-now`   | ระบบหลังบ้านทยอยรัน AI ดึงหน้าทีละรูปจนครบ แล้วอัปเดตเป็น `completed` |
| **3. เช็คสถานะ**    | แอปพลิเคชันเรียก API `/register/status/{id}`           | เซิร์ฟเวอร์ตอบกลับสถานะปัจจุบัน (Completed หรือ Failed)               |
| **4. ใช้งานจริง**   | เครื่องสแกนยิง API `/verify` ส่งรูปเพื่อเข้าห้อง       | นำรูปไปเทียบกับเวกเตอร์ในระบบ แล้วตอบกลับผลการสแกนทันที               |