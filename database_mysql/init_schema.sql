-- init_schema.sql
CREATE DATABASE IF NOT EXISTS face_attendance;
USE face_attendance;

-- 1. Create 'users' table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_student_id (student_id)
);

-- 2. Create 'registration_queue' table (stores pending registration photos)
CREATE TABLE IF NOT EXISTS registration_queue (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(50) NOT NULL,
    image_path VARCHAR(255) NULL,
    image_blob LONGBLOB NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME NULL,
    INDEX idx_registration_queue_student_id (student_id),
    INDEX idx_registration_queue_status (status)
);

-- 3. Create 'check_in_logs' table
CREATE TABLE IF NOT EXISTS check_in_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    student_id VARCHAR(50) NULL,
    similarity_score DOUBLE NULL,
    device_id VARCHAR(50) NULL,
    error_message VARCHAR(255) NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_check_in_logs_timestamp (timestamp DESC)
);
