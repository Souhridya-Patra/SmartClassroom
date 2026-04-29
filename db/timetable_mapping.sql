-- Create the mapping table in the timetable_db to link smart_classroom classes with timetable sections
-- This table is queried by lookup_current_assignment_by_room() in timetable_lookup.py

USE timetable_db;

CREATE TABLE IF NOT EXISTS smartclassroom_class_section_map (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  smart_class_id VARCHAR(64) NOT NULL COMMENT 'FK to smart_classroom.classes.class_id',
  section_id BIGINT NOT NULL COMMENT 'FK to sections.id in timetable_db',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_smart_class_section (smart_class_id, section_id),
  INDEX idx_smart_class (smart_class_id),
  INDEX idx_section (section_id),
  INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Maps smart_classroom class IDs to timetable section IDs for autonomous room-based session start';

-- IMPORTANT: You must manually populate this table after creating it!
-- 
-- Example INSERT:
--   INSERT INTO smartclassroom_class_section_map (smart_class_id, section_id, is_active)
--   SELECT c.class_id, s.id, 1
--   FROM smart_classroom.classes c
--   CROSS JOIN sections s
--   WHERE c.class_name LIKE CONCAT('%', s.name, '%')
--     OR FIND_IN_SET(s.name, c.class_id) > 0;
--
-- This links each class to its matching section in the timetable based on:
--   1. Section name appearing in class_name or class_id
--   2. Manual mapping if needed

-- To verify the mappings are working, run:
-- SELECT 
--   m.smart_class_id,
--   s.name as section_name,
--   tt.day_of_week,
--   ts.label as slot_label,
--   sb.name as subject_name,
--   t.full_name as teacher_name,
--   r.name as room_name
-- FROM smartclassroom_class_section_map m
-- JOIN sections s ON m.section_id = s.id
-- LEFT JOIN timetable tt ON tt.section_id = s.id
-- LEFT JOIN time_slots ts ON tt.slot_id = ts.id
-- LEFT JOIN subjects sb ON tt.subject_id = sb.id
-- LEFT JOIN teachers t ON tt.teacher_id = t.id
-- LEFT JOIN rooms r ON tt.room_id = r.id
-- WHERE m.is_active = 1
-- ORDER BY m.smart_class_id, tt.day_of_week, ts.slot_number;
