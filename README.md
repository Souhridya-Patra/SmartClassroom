# SmartClassroom

An AI-powered classroom attendance system that automates student tracking using facial recognition, with dual-factor faculty authentication (face + barcode) to control class sessions.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [How It Works](#how-it-works)
- [Privacy](#privacy)
- [Contributing](#contributing)

---

## Overview

SmartClassroom replaces manual roll calls with a real-time face recognition pipeline. A faculty member starts a session by verifying their identity (barcode scan + face recognition). The system then continuously scans the classroom via webcam, identifies students, and logs attendance events. When the session ends, it automatically marks every enrolled student as present or absent based on the events captured during the session.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Browser (Port 8080)                  │
│              SmartClassroom Control Deck                 │
│         Vanilla JS + Canvas Overlay + WebRTC             │
└────────────────────────┬────────────────────────────────┘
                         │ /api/backend/*   /api/ai/*
              ┌──────────┴──────────┐
              │                     │
   ┌──────────▼──────────┐  ┌──────▼──────────────┐
   │   Backend Service    │  │     AI Service       │
   │   FastAPI (8001)     │  │   FastAPI (8002)     │
   │   Business Logic     │  │  MTCNN + FaceNet     │
   │   Session Control    │  │  512D Embeddings     │
   └──────────┬──────────┘  └──────┬───────────────┘
              │                     │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │      MySQL DB        │
              │   smart_classroom    │
              │     (Port 3307)      │
              └─────────────────────┘

   ┌─────────────────────────┐
   │   Timetable Service      │
   │  Java/Spring Boot (8083) │
   └─────────────────────────┘
```

All services run as Docker containers orchestrated via Docker Compose.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla JS, HTML5 Canvas, WebRTC (getUserMedia) |
| Backend API | Python 3.11+, FastAPI, Pydantic |
| AI / ML | PyTorch, FaceNet (InceptionResnetV1 / VGGFace2), MTCNN |
| Database | MySQL 8 |
| Timetable | Java, Spring Boot |
| Infrastructure | Docker, Docker Compose, Nginx |

---

## Features

### Student Attendance
- Real-time face recognition from webcam stream
- Configurable recognition interval and similarity threshold
- Bounding box + landmark overlay on live video canvas
- Pose hint detection (look left/right/up/down) during enrollment
- Automatic present/absent marking when session ends

### Faculty Authentication
- Dual-factor verification: barcode scan + face recognition
- Live camera face capture during registration (no manual ID entry)
- Batch face enrollment with multiple angles for better accuracy
- Session start and end both require faculty re-verification

### Session Management
- Create classes and enroll students
- Start a session (requires faculty verification)
- Live attendance ingestion during session
- End session triggers automatic attendance reconciliation
- Per-session attendance report with CSV download

### Privacy
- Raw face images are never stored
- Only 512-dimensional embedding vectors are persisted
- Embeddings are averaged across samples (one vector per identity)

---

## Project Structure

```
SmartClassroom/
├── docker-compose.yml
├── .env
├── db/
│   ├── Dockerfile
│   └── init.sql                  # Schema: 7 tables
├── backend-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py               # All REST endpoints
│       ├── core/config.py
│       └── db/
│           ├── session.py        # DB connection with retry
│           └── init_db.py
├── ai-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py               # Recognition + enrollment endpoints
│       ├── core/settings.py
│       ├── schemas/contracts.py
│       └── services/
│           ├── face_engine.py    # MTCNN + FaceNet wrapper
│           ├── db_embedding_store.py
│           ├── embedding_store.py
│           └── image_io.py
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── public/
│       ├── index.html
│       ├── app.js
│       └── styles.css
└── Time-table-scheduler/         # Java Spring Boot service
```

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Git

### 1. Clone the repository

```bash
git clone https://github.com/Souhridya-Patra/SmartClassroom.git
cd SmartClassroom
```

### 2. Configure environment

Copy the example env file and adjust if needed:

```bash
cp .env.example .env
```

The defaults work out of the box for local development. See [Environment Variables](#environment-variables) for details.

### 3. Start all services

```bash
docker compose up -d --build
```

First run will take a few minutes — the AI service downloads the FaceNet model weights (~100MB).

### 4. Open the app

```
http://localhost:8080
```

### 5. Verify services are healthy

```bash
docker compose ps
```

All services should show `healthy` or `running`.

| Service | URL |
|---|---|
| Frontend | http://localhost:8080 |
| Backend API | http://localhost:8001 |
| AI Service | http://localhost:8002 |
| Timetable | http://localhost:8083 |
| MySQL | localhost:3307 |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MYSQL_ROOT_PASSWORD` | `root` | MySQL root password |
| `MYSQL_DATABASE` | `smart_classroom` | Database name |
| `DB_HOST` | `host.docker.internal` | DB host (use `db` inside Docker) |
| `DB_PORT` | `3306` | DB port |
| `DB_USER` | `root` | DB user |
| `DB_PASSWORD` | _(empty)_ | DB password |
| `DB_NAME` | `smart_classroom` | DB schema name |
| `AI_SERVICE_URL` | `http://ai-service:8000` | Internal AI service URL |
| `BACKEND_SERVICE_URL` | `http://backend-service:8000` | Internal backend URL |
| `MATCH_THRESHOLD` | `0.60` | Cosine similarity threshold for face match |
| `TORCH_DEVICE` | `cpu` | Set to `cuda` if GPU is available |

---

## API Reference

### Backend Service (Port 8001)

#### Students
| Method | Endpoint | Description |
|---|---|---|
| GET | `/students` | List all students |
| GET | `/students/{id}` | Get student + attendance stats |
| DELETE | `/students/{id}` | Delete student and all records |

#### Attendance
| Method | Endpoint | Description |
|---|---|---|
| POST | `/attendance/recognition` | Ingest recognition events |
| GET | `/attendance/recent` | Recent attendance events |
| GET | `/attendance/summary` | Total events + unique students |

#### Faculty
| Method | Endpoint | Description |
|---|---|---|
| POST | `/faculty/register` | Register faculty (ID + barcode + face ID) |
| POST | `/faculty/verify` | Verify faculty credentials |
| POST | `/faculty/checkin-with-image` | Orchestrated check-in with live image |

#### Classes
| Method | Endpoint | Description |
|---|---|---|
| POST | `/classes` | Create a class |
| POST | `/classes/{id}/students/enroll` | Enroll students in class |
| GET | `/classes/{id}/students` | List enrolled students |

#### Sessions
| Method | Endpoint | Description |
|---|---|---|
| POST | `/sessions/start` | Start session (pre-recognized face ID) |
| POST | `/sessions/start-with-image` | Start session with live image |
| POST | `/sessions/{id}/end` | End session (pre-recognized face ID) |
| POST | `/sessions/{id}/end-with-image` | End session with live image |
| GET | `/sessions/{id}/attendance` | Session attendance report |

### AI Service (Port 8002)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Service health + model status |
| POST | `/register-student` | Enroll student (single image) |
| POST | `/register-student-batch` | Enroll student (multiple angles) |
| POST | `/enroll-face` | Enroll faculty face, returns `FACE-XXXXX` ID |
| POST | `/enroll-face-batch` | Enroll faculty face (multiple angles) |
| POST | `/recognize` | Identify faces in image |
| POST | `/recognize-and-forward` | Recognize + forward to backend |
| GET | `/tuning/thresholds` | Recommended threshold values |

Full interactive docs available at:
- Backend: http://localhost:8001/docs
- AI Service: http://localhost:8002/docs

---

## How It Works

### Student Enrollment
1. Open the Control Deck → Camera Enrollment section
2. Enter student ID and number of angles (3–12 recommended)
3. Click "Capture Angles and Enroll" — the system captures frames with head-turn prompts
4. Each frame is sent to the AI service, which extracts a 512D embedding
5. Embeddings are averaged across samples and stored in the database

### Faculty Registration
1. Open Faculty section → Register Faculty
2. Enter Faculty ID and full name
3. Scan barcode (or type manually)
4. Start camera, click "Capture Face" — face is enrolled to AI service automatically
5. A unique `FACE-XXXXX` ID is generated and linked to the faculty record
6. Click Register to save everything

### Running a Class Session
1. Faculty opens Control Deck → Start Class Session
2. Enters class ID, faculty ID, barcode, and captures face via check-in camera
3. Backend verifies barcode + face — session starts only if both pass
4. Live Recognition runs in background, logging attendance events
5. Faculty ends session the same way (barcode + face re-verified)
6. System cross-references attendance events with enrolled students and marks present/absent

### Face Recognition Pipeline
```
Webcam frame
    → MTCNN face detection (bounding boxes + 5-point landmarks)
    → FaceNet embedding (512D L2-normalized vector)
    → Cosine similarity against all registered embeddings
    → Best match above threshold (default 0.60) → student identified
    → Attendance event logged to backend
```

---

## Privacy

- No raw face images are stored anywhere in the system
- Only 512-dimensional floating-point vectors (mathematical representations) are persisted
- Vectors cannot be reverse-engineered back into a face image
- Deleting a student removes all their embeddings and attendance records via cascade

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

---

## License

This project is for academic and educational use.
