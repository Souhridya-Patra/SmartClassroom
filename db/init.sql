CREATE DATABASE IF NOT EXISTS smart_classroom;
USE smart_classroom;

CREATE TABLE IF NOT EXISTS students (
  id VARCHAR(64) PRIMARY KEY,
  enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_enrollment (enrollment_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS facial_embeddings (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  student_id VARCHAR(64) NOT NULL,
  embedding JSON NOT NULL,
  samples_count INT DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
  INDEX idx_student (student_id),
  INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_events (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  student_id VARCHAR(64),
  similarity FLOAT,
  confidence FLOAT,
  source VARCHAR(128),
  event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE SET NULL,
  INDEX idx_student (student_id),
  INDEX idx_event_time (event_time),
  INDEX idx_similarity (similarity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS faculty (
  faculty_id VARCHAR(64) PRIMARY KEY,
  full_name VARCHAR(255) NOT NULL,
  barcode_value VARCHAR(128) NOT NULL UNIQUE,
  face_identity_id VARCHAR(64) NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS classes (
  class_id VARCHAR(64) PRIMARY KEY,
  class_name VARCHAR(128) NOT NULL,
  section VARCHAR(32) NULL,
  semester VARCHAR(32) NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_class_name_section_semester (class_name, section, semester)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS student_class_enrollments (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  student_id VARCHAR(64) NOT NULL,
  class_id VARCHAR(64) NOT NULL,
  active TINYINT(1) NOT NULL DEFAULT 1,
  enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_student_class (student_id, class_id),
  CONSTRAINT fk_sce_student FOREIGN KEY (student_id)
    REFERENCES students(id) ON DELETE CASCADE,
  CONSTRAINT fk_sce_class FOREIGN KEY (class_id)
    REFERENCES classes(class_id) ON DELETE CASCADE,
  INDEX idx_sce_class (class_id),
  INDEX idx_sce_student (student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS class_sessions (
  session_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  class_id VARCHAR(64) NOT NULL,
  faculty_id VARCHAR(64) NOT NULL,
  period_id BIGINT NULL,
  timetable_schedule_id BIGINT NULL,
  start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  end_time TIMESTAMP NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  start_barcode_verified TINYINT(1) NOT NULL DEFAULT 0,
  start_face_verified TINYINT(1) NOT NULL DEFAULT 0,
  end_barcode_verified TINYINT(1) NOT NULL DEFAULT 0,
  end_face_verified TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_cs_class FOREIGN KEY (class_id)
    REFERENCES classes(class_id) ON DELETE RESTRICT,
  CONSTRAINT fk_cs_faculty FOREIGN KEY (faculty_id)
    REFERENCES faculty(faculty_id) ON DELETE RESTRICT,
  CONSTRAINT fk_cs_period FOREIGN KEY (period_id)
    REFERENCES subject_periods(period_id) ON DELETE SET NULL,
  CONSTRAINT fk_cs_timetable FOREIGN KEY (timetable_schedule_id)
    REFERENCES timetable(schedule_id) ON DELETE SET NULL,
  INDEX idx_cs_class (class_id),
  INDEX idx_cs_faculty (faculty_id),
  INDEX idx_cs_period (period_id),
  INDEX idx_cs_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS session_attendance (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  session_id BIGINT NOT NULL,
  class_id VARCHAR(64) NOT NULL,
  student_id VARCHAR(64) NOT NULL,
  status VARCHAR(16) NOT NULL,
  marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_session_student (session_id, student_id),
  CONSTRAINT fk_sa_session FOREIGN KEY (session_id)
    REFERENCES class_sessions(session_id) ON DELETE CASCADE,
  CONSTRAINT fk_sa_class FOREIGN KEY (class_id)
    REFERENCES classes(class_id) ON DELETE RESTRICT,
  CONSTRAINT fk_sa_student FOREIGN KEY (student_id)
    REFERENCES students(id) ON DELETE CASCADE,
  INDEX idx_sa_class (class_id),
  INDEX idx_sa_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS class_subjects (
  subject_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  class_id VARCHAR(64) NOT NULL,
  subject_name VARCHAR(128) NOT NULL,
  subject_code VARCHAR(32) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_class_subject (class_id, subject_code),
  CONSTRAINT fk_cs_subject_class FOREIGN KEY (class_id)
    REFERENCES classes(class_id) ON DELETE CASCADE,
  INDEX idx_cs_subject_class (class_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS class_timetable (
  period_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  class_id VARCHAR(64) NOT NULL,
  subject_id BIGINT NOT NULL,
  day_of_week VARCHAR(10) NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_class_period (class_id, day_of_week, start_time),
  CONSTRAINT fk_ct_class FOREIGN KEY (class_id)
    REFERENCES classes(class_id) ON DELETE CASCADE,
  CONSTRAINT fk_ct_subject FOREIGN KEY (subject_id)
    REFERENCES class_subjects(subject_id) ON DELETE RESTRICT,
  INDEX idx_ct_class (class_id),
  INDEX idx_ct_day (day_of_week)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS period_attendance (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  period_id BIGINT NOT NULL,
  student_id VARCHAR(64) NOT NULL,
  status VARCHAR(16) NOT NULL,
  marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_period_student (period_id, student_id),
  CONSTRAINT fk_pa_period FOREIGN KEY (period_id)
    REFERENCES class_timetable(period_id) ON DELETE CASCADE,
  CONSTRAINT fk_pa_student FOREIGN KEY (student_id)
    REFERENCES students(id) ON DELETE CASCADE,
  INDEX idx_pa_period (period_id),
  INDEX idx_pa_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
