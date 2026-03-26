# Faculty Registration UI - Quick Reference

## New Registration Form Layout

```
┌───────────────────────────────────────────────────────────────────┐
│ Register Faculty (with Barcode & Face Capture)                    │
│ Register a new faculty: ID/name, scan barcode, capture face        │
├─────────────────────────────────────────┬─────────────────────────┤
│                                         │                         │
│  FACE CAPTURE (Live Camera)            │  FACULTY DETAILS        │
│  ┌─────────────────────────────────┐   │  ┌───────────────────┐  │
│  │                                 │   │  │ Faculty ID        │  │
│  │   📹 Video Stream               │   │  │ [____FID-001___]  │  │
│  │   (or captured face preview)    │   │  │                   │  │
│  │                                 │   │  │ Full Name         │  │
│  │                                 │   │  │ [__Dr. Smith____] │  │
│  └─────────────────────────────────┘   │  │                   │  │
│                                         │  │ Barcode *         │  │
│  [Start Camera] [Stop] [Capture Face]  │  │ [________987654] │  │
│                                         │  │ 🔴 Scanner focus │  │
│  ✅ Face: FACE-A1B2C3D4E5...           │  │                   │  │
│  Camera is active...                   │  │ ┌─────────────────┤  │
│                                         │  │ │Face Status:     │  │
│                                         │  │ │✅ Face ID:      │  │
│                                         │  │ │   FACE-A1B2...  │  │
│                                         │  │ └─────────────────┤  │
│                                         │  │                   │  │
│                                         │  │ [Register Faculty]  │  │
│                                         │  └───────────────────┘  │
└────────────────────────────────────────┴──────────────────────────┘
```

## Step-by-Step Usage

### 1️⃣ ENTER BASIC INFO
```
Input:
  Faculty ID: [____FID-002____]
  Full Name:  [__Dr. Sarah Chen_]
```

### 2️⃣ SCAN OR TYPE BARCODE
```
Barcode Field (auto-focused):
  [____________987654321_______]
  
  Option A: Scan with barcode device (recommended)
  Option B: Type manually if scanner unavailable
```

### 3️⃣ CAPTURE FACE
```
Step 3a: Start Camera
  [Start Camera] ← Click
  Status: 📹 Camera active...

Step 3b: Position Face  
  Live video shows in left panel
  Ensure good lighting, face visible

Step 3c: Capture Frame
  [Capture Face] ← Click
  Face preview appears with status

Step 3d: AI Enrollment
  Status updates: 📤 Sending to AI service...
  AI processes: MTCNN detect → FaceNet embed → Generate ID
  Status shows: ✅ Face ID: FACE-A1B2C3D4E5F6
```

### 4️⃣ REGISTER
```
When ready (after face enrollment):
  [Register Faculty] ← Click
  
Backend saves:
  ✓ faculty_id
  ✓ full_name  
  ✓ barcode_value
  ✓ face_identity_id (auto-enrolled)
  
Success: Form resets, camera stops, 
         status shows "Face registered successfully!"
```

---

## Status Messages & Meanings

### Camera Status
| Status | Meaning | Action |
|--------|---------|--------|
| "Waiting for capture..." | Camera not started | Click "Start Camera" |
| "📹 Camera active..." | Ready to capture | Position face, then click "Capture Face" |
| "Camera stopped" | Camera stopped | Click "Start Camera" to resume |

### Face Enrollment Status
| Status | Meaning | Action |
|--------|---------|--------|
| "No face captured yet" | Initial state | Capture a photo |
| "📤 Sending to AI..." | Processing | Wait, don't close form |
| "✅ Face ID: FACE-XXX" | Success! | Can now click Register |
| "❌ Enrollment failed" | Error occurred | Capture again or try new photo |

---

## Barcode Scanner Setup

### With Physical Scanner (USB/Wireless)
1. Connect barcode scanner to computer
2. Click in Barcode field (auto-focused)
3. Scan barcode with device
4. Value appears in field automatically
5. Field ready for next scan or manual entry

### Without Scanner (Manual Entry)
1. Click in Barcode field
2. Type barcode value manually
3. Press Tab or Enter
4. Field verified and ready

---

## Common Workflows

### Workflow A: Fast Registration (With Scanner)
```
1. Enter Faculty ID (Tab)
2. Enter Name (Tab)
3. Scan Barcode with device (Auto-focus)
4. Click "Start Camera"
5. Position face
6. Click "Capture Face"
7. Wait for Face ID ✅
8. Click "Register"
Total Time: ~2 minutes
```

### Workflow B: Manual Barcode (No Scanner)
```
1. Enter Faculty ID (Tab)
2. Enter Name (Tab)  
3. Type Barcode manually (Tab)
4. Click "Start Camera"
5. Position face
6. Click "Capture Face"
7. Wait for Face ID ✅
8. Click "Register"
Total Time: ~3 minutes
```

### Workflow C: Troubleshoot & Retry
```
1. Camera fails → Check browser permissions
2. Close camera, try again
3. Face not detected → Better lighting, closer to camera
4. AI error → Verify AI service running (docker logs ai_service)
5. Retry face capture → Click "Start Camera" again
```

---

## Keyboard Shortcuts

| Ctrl+Click | Action |
|------|--------|
| Tab | Next field |
| Shift+Tab | Previous field |
| Enter (in form) | Register (if all valid) |
| Esc (in camera) | Stop camera |

---

## Visual Indicators

### Form Validation
- ❌ Red border = Field missing/invalid
- ✅ Green checkmark = Field valid
- blue outline = Currently focused

### Processing Status
- 📹 Emoji = Camera is active
- 📤 Emoji = Uploading to AI
- ✅ Emoji = Success
- ❌ Emoji = Error

### Face Preview
- **Shown**: After capture (small image)
- **Hidden**: Initial state until capture
- **Updated**: With each new capture attempt

---

## Error Recovery

### "No face detected"
```
→ Try again:
  1. Click "Stop Camera"
  2. Improve lighting (try near window)
  3. Click "Start Camera"
  4. Get closer to camera
  5. Click "Capture Face" again
```

### "Camera error"
```
→ Fix browser permissions:
  1. Look for camera permission prompt
  2. Click "Allow" if prompted
  3. Check browser Settings → Privacy → Camera
  4. Ensure camera enabled for this site
  5. Try different browser if still fails
```

### "Registration failed"
```
→ Verify all fields:
  1. Faculty ID not empty? ✓
  2. Full Name not empty? ✓
  3. Barcode not empty? ✓
  4. Face ID shown? ✓
  5. Then click Register
```

---

## Before & After Comparison

### OLD WAY ❌
1. Open form
2. Type Faculty ID
3. Type Name
4. Type Barcode
5. STOP - Need face ID from separate AI tool
6. Run external face enrollment tool
7. Get face identity ID back
8. Copy and paste into form
9. Click Register
⏱️ Time: 10+ minutes, multiple tools

### NEW WAY ✅
1. Open form
2. Type Faculty ID
3. Type Name
4. Scan/Type Barcode
5. Click "Start Camera"
6. Capture face (automatic AI enrollment)
7. Click Register
⏱️ Time: 2-3 minutes, single tool

---

## Video/Screenshot Notes

### Desktop View
- Left side (40%): Camera preview + controls
- Right side (60%): Registration form
- Both visible simultaneously
- Responsive for tablets (stacks vertically)

### Mobile View
- Camera preview fullscreen with overlay form
- Can be used but suboptimal UX
- Barcode scanner works with mobile barcode laser scanners
- Recommended: Use desktop browser

---

## API Data Format

### What Gets Sent to Backend
```json
{
  "faculty_id": "FID-002",
  "full_name": "Dr. Sarah Chen",
  "barcode_value": "987654321",
  "face_identity_id": "FACE-A1B2C3D4E5F6"
}
```

### What Comes Back (Success)
```json
{
  "faculty_id": "FID-002",
  "full_name": "Dr. Sarah Chen",
  "barcode_value": "987654321",
  "face_identity_id": "FACE-A1B2C3D4E5F6",
  "created_at": "2026-03-26T10:30:00Z"
}
```

---

## Troubleshooting Checklist

- [ ] Font ID field has focus initially
- [ ] Barcode field auto-focuses after Name
- [ ] Camera permission popup appears when clicking "Start Camera"
- [ ] Video streams in the left camera preview area
- [ ] "Capture Face" button freezes current frame
- [ ] Face preview image shows captured photo
- [ ] Status text updates as face enrolls
- [ ] Face ID appears (e.g., "FACE-ABC123...")
- [ ] Register button enabled only after face captured
- [ ] Form resets after successful registration

---

*For detailed API and configuration information, see FACULTY_REGISTRATION_GUIDE.md*
