# Enhanced Faculty Registration with Barcode Scanner & Face Capture

## Overview
Faculty registration now includes **live barcode scanning** and **automatic face enrollment** during registration, eliminating the need to manually provide face identity IDs.

## What's New

### 1. **Barcode Scanner Integration**
- **Automatic Detection**: Barcode scanners can input directly into the barcode field
- **Manual Fallback**: Users can type barcode manually if scanner unavailable
- **Auto-focus**: Barcode field gets focus by default for seamless scanning workflow

### 2. **Live Face Capture**
- Start camera and capture faculty's face during registration
- Face image automatically sent to AI service for embedding generation
- Unique face identity ID (`FACE-XXXXXXXXXXXXX`) generated and stored automatically
- Real-time preview of captured face with status feedback

### 3. **Unified Registration Process**
No more manual face enrollment - everything happens in one workflow:
1. Enter Faculty ID
2. Enter Full Name
3. Scan barcode (or enter manually)
4. Start camera and capture face photo
5. Click Register - face is automatically enrolled and faculty record created

---

## How to Use

### Step 1: Open Faculty Registration
1. Navigate to SmartClassroom Control Deck (http://localhost:8080)
2. Scroll to **"Register Faculty (with Barcode & Face Capture)"** section
3. You'll see a split view with:
   - **Left**: Live camera preview for face capture
   - **Right**: Registration form

### Step 2: Enter Faculty Details
- **Faculty ID**: Enter unique faculty identifier (e.g., `FID-001`)
- **Full Name**: Enter faculty's full name (e.g., `Dr. John Smith`)
- **Barcode**: 
  - Place cursor in barcode field (it auto-focuses)
  - Scan barcode with device (barcode scanner will input automatically)
  - OR manually type barcode value

### Step 3: Capture Face
1. Click **"Start Camera"** button to activate webcam
2. Position face in camera view (ensure good lighting)
3. Click **"Capture Face"** to capture current frame
4. System will:
   - Send face to AI service
   - Generate face embeddings
   - Create unique face identity ID
   - Display preview and status (e.g., `✅ Face ID: FACE-ABC123456789`)
5. Status updates:
   - 📹 "Camera active..." → Camera is running
   - 📤 "Sending to AI service..." → Processing face
   - ✅ "Face ID: FACE-XXX..." → Successfully enrolled

### Step 4: Submit Registration
- Click **"Register Faculty"** to save all information to database
- On success:
  - Form resets
  - Face preview clears
  - Camera stops
  - Confirmation shown in output panel

---

## Technical Details

### Frontend Components

#### HTML Elements
- `facultyRegisterVideo`: Live camera video stream
- `facultyRegisterCaptureCanvas`: Hidden canvas for frame capture
- Camera controls: Start, Stop, Capture buttons
- Face preview image with status indicator
- Registration form with barcode, ID, name fields

#### JavaScript Handlers
1. **Camera Management**
   - `startFacultyCamera()`: Requests camera access via `getUserMedia` API
   - `stopFacultyCamera()`: Stops video stream and releases camera
   - `captureFacultyFace()`: Captures current frame to canvas, converts to blob

2. **Face Enrollment**
   - Sends captured image blob to `/api/ai/enroll-face` endpoint
   - Stores returned `face_identity_id` in `window.enrolledFaceIdentityId`
   - Updates UI status with enrollment result

3. **Registration Submission**
   - Validates face was captured before allowing submission
   - Bundles all data (ID, name, barcode, face_identity_id)
   - Sends to `/api/backend/faculty/register` endpoint
   - Resets form on success

### Backend API Endpoints

#### 1. **New AI Service Endpoint: `/enroll-face`**
```
POST /enroll-face
Content-Type: multipart/form-data

Request:
- image (file): JPEG image file containing face

Response:
{
  "face_identity_id": "FACE-ABC123456789",
  "samples": 1,
  "message": "Face enrolled successfully",
  "status": "success"
}
```

**Process**:
1. Receives image file
2. Detects faces in image using MTCNN
3. Extracts face embeddings using FaceNet
4. Generates unique ID: `FACE-{UUID hex}`
5. Stores embeddings in database with ID
6. Returns face_identity_id for use in faculty registration

#### 2. **Existing Backend Endpoint: `/faculty/register`**
```
POST /faculty/register
Content-Type: application/json

Request:
{
  "faculty_id": "FID-001",
  "full_name": "Dr. John Smith",
  "barcode_value": "123456789",
  "face_identity_id": "FACE-ABC123456789"
}

Response:
{
  "faculty_id": "FID-001",
  "full_name": "Dr. John Smith",
  "barcode_value": "123456789",
  "face_identity_id": "FACE-ABC123456789",
  "created_at": "2026-03-26T10:30:00Z"
}
```

---

## Data Flow

### Registration Workflow
```
User Input (ID, Name, Barcode)
    ↓
Start Camera & Capture Face (JPEG)
    ↓
Send to /enroll-face (AI Service)
    ↓
AI Service:
  - Detect face with MTCNN
  - Extract embedding with FaceNet
  - Generate ID: FACE-XXXXX
  - Store in DB
    ↓
Get face_identity_id from AI response
    ↓
Display face_identity_id to user
    ↓
User clicks Register
    ↓
Send all data to /faculty/register (Backend)
    ↓
Backend:
  - Validate data
  - Store faculty record in DB
  - Link barcode + face_identity_id
    ↓
Success response + Clear form
```

### Check-In Workflow (Unchanged)
```
Faculty starts check-in:
  - Provide Faculty ID
  - Scan barcode
  - Capture face photo
    ↓
Backend /faculty/checkin-with-image:
  - Verify barcode matches stored value
  - Send face image to AI /recognize
  - AI returns matching face_identity_id
  - Compare with stored face_identity_id
  - If match: verification successful
    ↓
Session starts / Faculty verified
```

---

## Error Handling

### Common Issues & Solutions

#### "No face detected in image"
- **Cause**: Camera captured frame without visible face
- **Solution**: Ensure good lighting, face is clearly visible, try capturing again

#### "Camera error: NotAllowedError"
- **Cause**: Browser permission denied for camera access
- **Solution**: 
  - Allow camera access when browser prompts
  - Check browser security settings
  - Try different browser tab/window

#### "AI error: Connection refused"
- **Cause**: AI service not running or unreachable
- **Solution**: 
  - Check `docker compose ps` - ai-service should be healthy
  - Verify port 8002 is accessible
  - Check Docker logs: `docker logs ai_service`

#### "Registration failed: Face ID not found"
- **Cause**: Face enrollment didn't complete before clicking Register
- **Solution**: Click "Capture Face" again and wait for status to show face ID before submitting

---

## Integration with Check-In

After faculty is registered with captured face:

1. **Check-In Process** (unchanged):
   - Faculty provides Faculty ID
   - Scans barcode
   - Takes photo at check-in time

2. **Verification** (enhanced):
   - Backend calls AI service /recognize on check-in photo
   - AI returns matching face_identity_id
   - Backend compares with stored face_identity_id
   - Barcode + face both verified for session start

3. **Session Attendance**:
   - If registered period is detected, session auto-tags with period_id
   - Attendance records linked to both class AND period/subject
   - Enhanced reporting by subject

---

## Configuration

### Environment Variables (No Changes Required)
- `BACKEND_SERVICE_URL`: Backend API location (default: http://backend-service:8000)
- `AI_SERVICE_URL`: AI service location (proxied via `/api/ai/`)
- `DB_HOST`, `DB_USER`, `DB_PASSWORD`: Database credentials (unchanged)

### Frontend Proxy Routes
- `/api/backend/*` → Proxied to backend service (8001)
- `/api/ai/*` → Proxied to AI service (8002)

---

## Testing Checklist

- [ ] Faculty registration form displays split view (camera + form)
- [ ] Barcode field auto-focuses when page loads
- [ ] Camera starts/stops successfully
- [ ] Face capture creates 640x480 preview image
- [ ] Face enrollment returns unique FACE-XXXXX ID
- [ ] Face status displays ID after successful enrollment
- [ ] Register button requires face to be captured first
- [ ] Registration succeeds with all data saved to database
- [ ] Barcode scanner works with existing readers
- [ ] Form resets after successful registration
- [ ] Event logging (console) shows API calls and responses

---

## API Testing

### Manual Test: Enroll Face
```bash
# With actual image file
curl -X POST http://localhost:8002/enroll-face \
  -F "image=@/path/to/faculty_photo.jpg"

# Response:
{
  "face_identity_id": "FACE-A1B2C3D4E5F6",
  "samples": 1,
  "message": "Face enrolled successfully",
  "status": "success"
}
```

### Manual Test: Register Faculty
```bash
curl -X POST http://localhost:8001/faculty/register \
  -H "Content-Type: application/json" \
  -d '{
    "faculty_id": "FID-001",
    "full_name": "Dr. John Smith",
    "barcode_value": "123456789",
    "face_identity_id": "FACE-A1B2C3D4E5F6"
  }'

# Response:
{
  "faculty_id": "FID-001",
  "full_name": "Dr. John Smith",
  "barcode_value": "123456789",
  "face_identity_id": "FACE-A1B2C3D4E5F6",
  "created_at": "2026-03-26T10:30:00Z"
}
```

---

## Files Modified

### Frontend
- `frontend/public/index.html`: Added faculty registration form with camera preview
- `frontend/public/app.js`: Added handlers for camera, face capture, and enrollment

### Backend
- No changes required (existing `/faculty/register` endpoint used)

### AI Service
- `ai-service/app/main.py`: Added `/enroll-face` endpoint for face enrollment
- Uses existing MTCNN + FaceNet models
- Generates unique `FACE-XXXXX` IDs

### Database
- No schema changes (existing faculty table + embeddings storage compatible)

---

## Troubleshooting

### Check Logs
```bash
# Frontend logs (browser console)
F12 → Console tab → Look for API errors

# Backend logs
docker logs backend | grep -i error

# AI Service logs  
docker logs ai_service | grep -i error

# Verify services healthy
docker compose ps
```

### Restart Services if Needed
```bash
docker compose restart frontend
docker compose restart ai-service
docker compose restart backend
```

### Rebuild if Code Changed
```bash
docker compose up -d --build
```
