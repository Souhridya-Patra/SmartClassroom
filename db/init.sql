CREATE DATABASE IF NOT EXISTS smart_classroom;
USE smart_classroom;

CREATE TABLE IF NOT EXISTS students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    department VARCHAR(50),
    qr_code VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS session (
    session_id INT AUTO_INCREMENT PRIMARY KEY,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT,
    student_id INT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
