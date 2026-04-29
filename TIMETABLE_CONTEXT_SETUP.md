# Timetable Context Resolution Guide

## Problem

When a faculty member selects a room to start a class session, the system should automatically fetch and populate:
- **Resolved Class ID** - Which class is supposed to be in this room now?
- **Resolved Faculty** - Which teacher should be teaching?
- **Resolved Subject** - What subject is scheduled?

Currently these fields remain empty because the **class-to-section mapping is missing**.

## How It Works

The system has **two separate databases**:

1. **smart_classroom** - Stores students, classes, faculty, sessions, attendance
2. **timetable_db** - Stores the generated timetable with sections, time slots, teachers, subjects, rooms

### The Flow

```
User selects room "CSE-102"
         ↓
Frontend calls: GET /api/backend/timetable/context?room_name=CSE-102
         ↓
Backend queries timetable_db:
  - Find current day/time in room "CSE-102"
  - Match to a timetable entry (subject, teacher, section)
  - LEFT JOIN with smartclassroom_class_section_map
       ↓
Does the mapping exist?
  YES → Returns smart_class_id (e.g., "CS101-A")
  NO  → Returns NULL, frontend shows empty fields ❌
```

## Solution: Create Class-to-Section Mappings

### Step 1: Create the Mapping Table

Run this SQL in your **timetable_db database** (NOT smart_classroom):

```sql
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### Step 2: List Available Sections

Call the backend endpoint to see all sections in your timetable:

```bash
curl http://localhost:8080/api/backend/timetable/sections
```

Response example:
```json
[
  {"id": 1, "name": "CS Section A", "sem_number": 3, "dept_name": "Computer Science"},
  {"id": 2, "name": "CS Section B", "sem_number": 3, "dept_name": "Computer Science"},
  {"id": 3, "name": "EC Section A", "sem_number": 4, "dept_name": "Electronics"}
]
```

### Step 3: Map Your Classes to Sections

#### Option A: Automatic Mapping (Recommended)

Run this SQL to auto-map based on section names appearing in class IDs:

```sql
INSERT INTO timetable_db.smartclassroom_class_section_map (smart_class_id, section_id, is_active)
SELECT 
  c.class_id,
  s.id,
  1
FROM smart_classroom.classes c
CROSS JOIN timetable_db.sections s
WHERE 
  -- Match 1: Section name appears in class_name
  LOWER(c.class_name) LIKE CONCAT('%', LOWER(s.name), '%')
  OR 
  -- Match 2: Section name appears in class_id
  LOWER(c.class_id) LIKE CONCAT('%', LOWER(SUBSTRING_INDEX(s.name, ' ', -1)), '%')
ON DUPLICATE KEY UPDATE is_active = 1;
```

#### Option B: Manual Mapping via API

Create a mapping for a specific class:

```bash
curl -X POST http://localhost:8080/api/backend/timetable/class-section-mappings \
  -H "Content-Type: application/json" \
  -d '{
    "smart_class_id": "CS101-A",
    "section_id": 1
  }'
```

Response:
```json
{
  "status": "created",
  "smart_class_id": "CS101-A",
  "section_id": 1
}
```

#### Option C: Manual SQL Insert

```sql
INSERT INTO timetable_db.smartclassroom_class_section_map 
  (smart_class_id, section_id, is_active) 
VALUES 
  ('CS101-A', 1, 1),
  ('CS101-B', 2, 1),
  ('EC102-A', 3, 1);
```

### Step 4: Verify the Mappings

Call the API to list all mappings:

```bash
curl http://localhost:8080/api/backend/timetable/class-section-mappings
```

Or run this query:

```sql
SELECT 
  m.smart_class_id,
  s.name as section_name,
  COUNT(DISTINCT tt.id) as timetable_entries
FROM timetable_db.smartclassroom_class_section_map m
JOIN timetable_db.sections s ON m.section_id = s.id
LEFT JOIN timetable_db.timetable tt ON tt.section_id = s.id
WHERE m.is_active = 1
GROUP BY m.smart_class_id, s.name
ORDER BY m.smart_class_id;
```

### Step 5: Test the Room Selection

Now when you select a room in the UI:

```
1. Select room: "CSE-102"
2. Class loads: "CS101-A" ✓
3. Faculty loads: "Dr. Smith" ✓
4. Subject loads: "Data Structures" ✓
```

## Debugging

If fields still don't populate, check:

### 1. Are there any rooms in the timetable for the current time?
```sql
SELECT r.name, ts.label, sb.name, t.full_name, s.name
FROM timetable_db.timetable tt
JOIN timetable_db.time_slots ts ON tt.slot_id = ts.id
JOIN timetable_db.rooms r ON tt.room_id = r.id
JOIN timetable_db.subjects sb ON tt.subject_id = sb.id
JOIN timetable_db.teachers t ON tt.teacher_id = t.id
JOIN timetable_db.sections s ON tt.section_id = s.id
WHERE tt.day_of_week = DAYNAME(NOW())
  AND NOW() BETWEEN CONCAT(CURDATE(), ' ', ts.start_time) 
                AND CONCAT(CURDATE(), ' ', ts.end_time);
```

### 2. Does the mapping exist?
```sql
SELECT * FROM timetable_db.smartclassroom_class_section_map WHERE is_active = 1;
```

### 3. Test the full lookup query:
```sql
SELECT 
  m.smart_class_id,
  s.name,
  tt.day_of_week,
  ts.label,
  sb.name as subject_name,
  t.full_name as teacher_name,
  r.name as room_name
FROM timetable_db.timetable tt
JOIN timetable_db.time_slots ts ON tt.slot_id = ts.id
JOIN timetable_db.rooms r ON tt.room_id = r.id
JOIN timetable_db.sections s ON tt.section_id = s.id
LEFT JOIN timetable_db.smartclassroom_class_section_map m ON m.section_id = s.id
WHERE r.name = 'CSE-102'
  AND tt.day_of_week = DAYNAME(NOW())
  AND NOW() >= CONCAT(CURDATE(), ' ', ts.start_time)
  AND NOW() <= CONCAT(CURDATE(), ' ', ts.end_time);
```

### 4. Check backend logs
```bash
docker compose logs backend-service | tail -20
```

## Backend API Reference

### List All Sections
```
GET /api/backend/timetable/sections
```
Returns array of `{id, name, sem_number, dept_name}`

### List All Mappings
```
GET /api/backend/timetable/class-section-mappings
```
Returns array of `{smart_class_id, section_id}`

### Create/Update Mapping
```
POST /api/backend/timetable/class-section-mappings
Content-Type: application/json

{
  "smart_class_id": "CS101-A",
  "section_id": 1
}
```
Returns `{status, smart_class_id, section_id}`

### Get Context for Room
```
GET /api/backend/timetable/context?room_name=CSE-102
```
Returns:
- If match found: `{has_active_timetable: true, class_id, subject_name, teacher_name, ...}`
- If no match: `{has_active_timetable: false, message: "No active timetable entry..."}`

## Related Files

- [db/init.sql](../db/init.sql) - Main smart_classroom schema
- [db/timetable_mapping.sql](../db/timetable_mapping.sql) - Mapping table creation script
- [backend-service/app/services/timetable_lookup.py](../backend-service/app/services/timetable_lookup.py) - Query logic
- [backend-service/app/main.py](../backend-service/app/main.py) - API endpoints
- [frontend/public/app.js](../frontend/public/app.js) - Frontend room selection logic
