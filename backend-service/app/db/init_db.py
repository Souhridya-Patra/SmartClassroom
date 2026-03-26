import os

import mysql.connector

from app.db.session import get_connection


def init():
    host = os.getenv("DB_HOST", "host.docker.internal")
    port = int(os.getenv("DB_PORT", "3306"))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "smart_classroom")

    admin_conn = mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
    )
    admin_cursor = admin_conn.cursor()
    admin_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
    admin_conn.commit()
    admin_cursor.close()
    admin_conn.close()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id VARCHAR(64) PRIMARY KEY,
            enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS facial_embeddings (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            student_id VARCHAR(64) NOT NULL,
            embedding JSON NOT NULL,
            samples_count INT NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_embeddings_student
                FOREIGN KEY (student_id)
                REFERENCES students(id)
                ON DELETE CASCADE,
            INDEX idx_facial_embeddings_student_id (student_id),
            INDEX idx_facial_embeddings_created_at (created_at)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance_events (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            student_id VARCHAR(64) NULL,
            similarity FLOAT NOT NULL,
            confidence FLOAT NOT NULL,
            source VARCHAR(32) NOT NULL DEFAULT 'ai-service',
            event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_attendance_student
                FOREIGN KEY (student_id)
                REFERENCES students(id)
                ON DELETE SET NULL,
            INDEX idx_attendance_student_id (student_id),
            INDEX idx_attendance_event_time (event_time),
            INDEX idx_attendance_similarity (similarity)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS faculty (
            faculty_id VARCHAR(64) PRIMARY KEY,
            full_name VARCHAR(255) NOT NULL,
            barcode_value VARCHAR(128) NOT NULL UNIQUE,
            face_identity_id VARCHAR(64) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS classes (
            class_id VARCHAR(64) PRIMARY KEY,
            class_name VARCHAR(128) NOT NULL,
            section VARCHAR(32) NULL,
            semester VARCHAR(32) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_class_name_section_semester (class_name, section, semester)
        )
        """
    )

    cursor.execute(
        """
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
        )
        """
    )

    cursor.execute(
        """
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
        )
        """
    )

    cursor.execute(
        """
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
        )
        """
    )

    cursor.execute(
        """
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
        )
        """
    )

    cursor.execute(
        """
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
        )
        """
    )

    cursor.execute(
        """
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
        )
        """
    )

    # Add period_id and timetable_schedule_id columns to class_sessions if they don't exist
    try:
        cursor.execute(
            """
            ALTER TABLE class_sessions 
            ADD COLUMN period_id BIGINT NULL
            """
        )
    except Exception:
        pass  # Column may already exist
    
    try:
        cursor.execute(
            """
            ALTER TABLE class_sessions 
            ADD COLUMN timetable_schedule_id BIGINT NULL
            """
        )
    except Exception:
        pass  # Column may already exist
    
    # Add foreign key constraints
    try:
        cursor.execute(
            """
            ALTER TABLE class_sessions 
            ADD CONSTRAINT fk_cs_period FOREIGN KEY (period_id)
            REFERENCES subject_periods(period_id) ON DELETE SET NULL
            """
        )
    except Exception:
        pass  # Constraint may already exist
    
    try:
        cursor.execute(
            """
            ALTER TABLE class_sessions 
            ADD CONSTRAINT fk_cs_timetable FOREIGN KEY (timetable_schedule_id)
            REFERENCES timetable(schedule_id) ON DELETE SET NULL
            """
        )
    except Exception:
        pass  # Constraint may already exist
    
    # Add indexes
    try:
        cursor.execute(
            """
            ALTER TABLE class_sessions 
            ADD INDEX idx_cs_period (period_id)
            """
        )
    except Exception:
        pass  # Index may already exist

    conn.commit()
    cursor.close()
    conn.close()

    print("DB initialized")