กระบวนการทำงานแต่ละส่วนคร่าวๆ
folder ai_server:
มีหน้าที่ 2 ฝั่ง
1 ดึงข้อมูลรูปภาพจาก database เพื่อนำมาเรียนรู้ผ่านกระบวนการ
Face Alignment
Feature Extraction by InsightFace (ArcFace Model)
แล้วทำไฟล์ .pkl เพื่อเตรียมใช้จริง 
2 รับรูปภาพจาก esp32 เพื่อนำมาตรวจสอบระบุตัวตนแล้วส่งกลับไปผ่านกระบวนการ
Face Alignment
Feature Extraction by InsightFace (ArcFace Model)
แล้วนำไปประมวลผลกับไฟล์ .pkl เพื่อหาใบหน้าที่ตรงกันแล้วส่งข้อมูลชื่อใบหน้ากลับไปที่ esp32 แล้วเก็บข้อมูลการลงชื่อลง database

folder app_face_capture:
มีหน้าที่ถ่ายรูปที่เหมาะสมกับการนำไปเรียนรู้จดจำใบหน้าแล้วเก็บไว้ที่ database
จำนวน 10 รูปต่อคน

folder esp32_system:
รวมโค้ดบอร์ด ESP32-S3 CAM N16R8 WROOM ที่ใช้ร่วมกับเซนเซอหลายตัวได้แก่
OV5640 โมดูลกล้อง 5MP 100°
lan ethernet module W5500
ToF GY-VL53L0XV2
tft lcd 2.8 inch
LED WS2813 strip เลือกจำนวนตามที่ต้องการไม่เกิน 5 ดวง
