-- ============================================================
--  TIMETABLE SCHEDULER — Full Database Schema
--  Database: timetable_db
-- ============================================================

CREATE DATABASE IF NOT EXISTS timetable_db;
USE timetable_db;

-- ────────────────────────────────────────────────────────────
-- 1. ADMIN
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admin (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(50)  NOT NULL UNIQUE,
    password    VARCHAR(255) NOT NULL,          -- stored as bcrypt hash
    full_name   VARCHAR(100),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Default admin (password: admin123 → will be hashed by app on first run)
INSERT INTO admin (username, password, full_name)
VALUES ('admin', 'HASH_PLACEHOLDER', 'Administrator');


-- ────────────────────────────────────────────────────────────
-- 2. DEPARTMENTS
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS departments (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    code        VARCHAR(20)  NOT NULL UNIQUE,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);


-- ────────────────────────────────────────────────────────────
-- 3. SEMESTERS
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS semesters (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    dept_id     INT NOT NULL,
    name        VARCHAR(50) NOT NULL,           -- e.g. "Semester 1", "Sem 3"
    sem_number  INT NOT NULL,                   -- 1, 2, 3 … 8
    teaching_weeks INT NOT NULL DEFAULT 16,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dept_id) REFERENCES departments(id) ON DELETE CASCADE,
    UNIQUE (dept_id, sem_number)
);


-- ────────────────────────────────────────────────────────────
-- 4. SECTIONS
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sections (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    sem_id      INT NOT NULL,
    name        VARCHAR(20) NOT NULL,           -- e.g. "A", "B", "C"
    strength    INT DEFAULT 60,                 -- student count
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sem_id) REFERENCES semesters(id) ON DELETE CASCADE,
    UNIQUE (sem_id, name)
);


-- ────────────────────────────────────────────────────────────
-- 5. ROOMS
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rooms (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(50)  NOT NULL UNIQUE,   -- e.g. "Room 101", "Lab A"
    room_type   ENUM('classroom','lab') NOT NULL DEFAULT 'classroom',
    capacity    INT DEFAULT 60,
    dept_id     INT,                            -- NULL = shared across depts
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dept_id) REFERENCES departments(id) ON DELETE SET NULL
);


-- ────────────────────────────────────────────────────────────
-- 6. TEACHERS
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teachers (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    full_name       VARCHAR(100) NOT NULL,
    email           VARCHAR(100) UNIQUE,
    dept_id         INT,
    max_hours_week  INT DEFAULT 20,             -- max teaching hrs/week
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dept_id) REFERENCES departments(id) ON DELETE SET NULL
);


-- ────────────────────────────────────────────────────────────
-- 7. TEACHER AVAILABILITY
--    One row per teacher per day — mark unavailable days
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teacher_availability (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    teacher_id  INT NOT NULL,
    day_of_week ENUM('Monday','Tuesday','Wednesday','Thursday','Friday') NOT NULL,
    is_available TINYINT(1) DEFAULT 1,          -- 1 = available, 0 = day off
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
    UNIQUE (teacher_id, day_of_week)
);


-- ────────────────────────────────────────────────────────────
-- 8. SUBJECTS
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subjects (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    code            VARCHAR(30)  NOT NULL UNIQUE,
    sem_id          INT NOT NULL,
    subject_type    ENUM('theory','practical','theory+practical','lab') NOT NULL DEFAULT 'theory',
    theory_hours    INT NULL,
    practical_hours INT NULL,
    lab_slots_per_session INT NOT NULL DEFAULT 2,
    -- legacy columns retained for backward compatibility with older tooling
    hours_per_week  INT NOT NULL DEFAULT 3,
    lab_slots       INT DEFAULT 2,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sem_id) REFERENCES semesters(id) ON DELETE CASCADE
);


-- ────────────────────────────────────────────────────────────
-- 9. SECTION–SUBJECT–TEACHER MAPPING
--    Which teacher handles which subject for which section
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS section_subject_teacher (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    section_id  INT NOT NULL,
    subject_id  INT NOT NULL,
    teacher_id  INT NOT NULL,
    theory_teacher_id INT NULL,
    practical_teacher_id INT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (section_id) REFERENCES sections(id)  ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id)  ON DELETE CASCADE,
    FOREIGN KEY (teacher_id) REFERENCES teachers(id)  ON DELETE CASCADE,
    UNIQUE (section_id, subject_id)             -- one teacher per subject per section
);


-- ────────────────────────────────────────────────────────────
-- 10. TIME SLOTS
--     Admin defines custom slots; breaks are flagged
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS time_slots (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    slot_number INT NOT NULL UNIQUE,            -- ordering: 1, 2, 3 …
    label       VARCHAR(50) NOT NULL,           -- e.g. "Period 1"
    start_time  TIME NOT NULL,                  -- e.g. 09:00:00
    end_time    TIME NOT NULL,                  -- e.g. 10:00:00
    is_break    TINYINT(1) DEFAULT 0            -- 1 = lunch/short break
);


-- ────────────────────────────────────────────────────────────
-- 11. TIMETABLE  (core output table)
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS timetable (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    section_id      INT NOT NULL,
    day_of_week     ENUM('Monday','Tuesday','Wednesday','Thursday','Friday') NOT NULL,
    slot_id         INT NOT NULL,
    subject_id      INT NOT NULL,
    teacher_id      INT NOT NULL,
    room_id         INT NOT NULL,
    session_type    ENUM('theory','lab') NOT NULL DEFAULT 'theory',
    lab_group       TINYINT DEFAULT NULL,       -- NULL for theory; 1/2 for split lab groups
    gen_id          INT,                        -- links to generation_log
    FOREIGN KEY (section_id)  REFERENCES sections(id)  ON DELETE CASCADE,
    FOREIGN KEY (slot_id)     REFERENCES time_slots(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id)  REFERENCES subjects(id)  ON DELETE CASCADE,
    FOREIGN KEY (teacher_id)  REFERENCES teachers(id)  ON DELETE CASCADE,
    FOREIGN KEY (room_id)     REFERENCES rooms(id)     ON DELETE CASCADE,
    UNIQUE (section_id, day_of_week, slot_id)   -- no double-booking a section slot
);


-- ────────────────────────────────────────────────────────────
-- 12. GENERATION LOG
--     Tracks every scheduler run
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS generation_log (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    generated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    status          ENUM('success','partial','failed') DEFAULT 'success',
    total_slots     INT DEFAULT 0,
    filled_slots    INT DEFAULT 0,
    conflict_count  INT DEFAULT 0,
    notes           TEXT
);


-- ────────────────────────────────────────────────────────────
-- 13. CONFLICT LOG
--     Records unresolved conflicts from each generation run
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conflict_log (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    gen_id          INT,
    section_id      INT,
    subject_id      INT,
    conflict_reason VARCHAR(255),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (gen_id)     REFERENCES generation_log(id) ON DELETE CASCADE,
    FOREIGN KEY (section_id) REFERENCES sections(id)       ON DELETE SET NULL,
    FOREIGN KEY (subject_id) REFERENCES subjects(id)       ON DELETE SET NULL
);


-- ────────────────────────────────────────────────────────────
-- 14. SMARTCLASSROOM CLASS → SECTION MAPPING
--     Explicit bridge to link SmartClassroom class_id values
--     with scheduler sections.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS smartclassroom_class_section_map (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    smart_class_id  VARCHAR(64) NOT NULL UNIQUE,
    section_id      INT NOT NULL,
    notes           VARCHAR(255) NULL,
    is_active       TINYINT(1) NOT NULL DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE,
    INDEX idx_scsm_section (section_id),
    INDEX idx_scsm_active (is_active)
);