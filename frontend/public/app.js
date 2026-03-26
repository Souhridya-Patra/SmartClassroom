const backendStatus = document.getElementById("backendStatus");
const dbStatus = document.getElementById("dbStatus");
const aiStatus = document.getElementById("aiStatus");
const tuningStatus = document.getElementById("tuningStatus");

const backendPayload = document.getElementById("backendPayload");
const dbPayload = document.getElementById("dbPayload");
const aiPayload = document.getElementById("aiPayload");
const tuningPayload = document.getElementById("tuningPayload");

const cameraEnrollForm = document.getElementById("cameraEnrollForm");
const cameraEnrollOutput = document.getElementById("cameraEnrollOutput");
const recognizeOutput = document.getElementById("recognizeOutput");

const liveVideo = document.getElementById("liveVideo");
const overlayCanvas = document.getElementById("overlayCanvas");
const captureCanvas = document.getElementById("captureCanvas");
const startCameraButton = document.getElementById("startCamera");
const stopCameraButton = document.getElementById("stopCamera");
const startLiveRecognitionButton = document.getElementById("startLiveRecognition");
const stopLiveRecognitionButton = document.getElementById("stopLiveRecognition");
const runSingleFrameButton = document.getElementById("runSingleFrame");

const totalEvents = document.getElementById("totalEvents");
const uniqueStudents = document.getElementById("uniqueStudents");
const attendanceRows = document.getElementById("attendanceRows");

const refreshAllButton = document.getElementById("refreshAll");
const refreshAttendanceButton = document.getElementById("refreshAttendance");

let cameraStream = null;
let recognitionTimer = null;
let recognitionBusy = false;
let trackCounter = 1;
let tracks = [];
let hud = {
  fps: 0,
  latencyMs: 0,
  lastTimestamp: 0,
};

function setStatus(element, ok, label) {
  element.className = `status-pill ${ok ? "status-ok" : "status-bad"}`;
  element.textContent = label;
}

function pretty(data) {
  return JSON.stringify(data, null, 2);
}

async function getJson(url) {
  const res = await fetch(url);
  const text = await res.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    body = { raw: text };
  }
  if (!res.ok) {
    throw new Error(pretty(body));
  }
  return body;
}

async function loadHealth() {
  try {
    const backend = await getJson("/api/backend/");
    setStatus(backendStatus, true, "Online");
    backendPayload.textContent = pretty(backend);
  } catch (error) {
    setStatus(backendStatus, false, "Offline");
    backendPayload.textContent = String(error.message || error);
  }

  try {
    const db = await getJson("/api/backend/health/db");
    setStatus(dbStatus, true, "Connected");
    dbPayload.textContent = pretty(db);
  } catch (error) {
    setStatus(dbStatus, false, "Disconnected");
    dbPayload.textContent = String(error.message || error);
  }

  try {
    const ai = await getJson("/api/ai/health");
    setStatus(aiStatus, true, ai.model_ready ? "Model Ready" : "Service Ready");
    aiPayload.textContent = pretty(ai);
  } catch (error) {
    setStatus(aiStatus, false, "Offline");
    aiPayload.textContent = String(error.message || error);
  }

  try {
    const tuning = await getJson("/api/ai/tuning/thresholds");
    setStatus(tuningStatus, true, "Loaded");
    tuningPayload.textContent = pretty(tuning);
  } catch (error) {
    setStatus(tuningStatus, false, "Unavailable");
    tuningPayload.textContent = String(error.message || error);
  }
}

async function postMultipart(url, formData) {
  const res = await fetch(url, {
    method: "POST",
    body: formData,
  });

  const text = await res.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    body = { raw: text };
  }

  if (!res.ok) {
    throw new Error(pretty(body));
  }

  return body;
}

async function ensureCamera() {
  if (cameraStream) {
    return;
  }
  cameraStream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
    audio: false,
  });
  liveVideo.srcObject = cameraStream;
}

function stopCamera() {
  if (!cameraStream) {
    return;
  }
  cameraStream.getTracks().forEach((track) => track.stop());
  cameraStream = null;
  liveVideo.srcObject = null;
  clearOverlay();
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function syncOverlaySize() {
  if (!liveVideo.videoWidth || !liveVideo.videoHeight) {
    return;
  }

  if (
    overlayCanvas.width !== liveVideo.videoWidth ||
    overlayCanvas.height !== liveVideo.videoHeight
  ) {
    overlayCanvas.width = liveVideo.videoWidth;
    overlayCanvas.height = liveVideo.videoHeight;
  }
}

function clearOverlay() {
  syncOverlaySize();
  const context = overlayCanvas.getContext("2d");
  context.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
}

function assignTracking(matches) {
  const now = Date.now();
  tracks = tracks.filter((item) => now - item.updatedAt < 2500);

  const usedTrackIds = new Set();
  return matches.map((item) => {
    if (!item || !Array.isArray(item.bbox) || item.bbox.length !== 4) {
      return { ...item, track_id: null };
    }

    const [x1, y1, x2, y2] = item.bbox;
    const centerX = (x1 + x2) / 2;
    const centerY = (y1 + y2) / 2;

    let best = null;
    let bestDistance = Number.POSITIVE_INFINITY;

    tracks.forEach((track) => {
      if (usedTrackIds.has(track.id)) {
        return;
      }
      const distance = Math.hypot(track.cx - centerX, track.cy - centerY);
      if (distance < bestDistance) {
        bestDistance = distance;
        best = track;
      }
    });

    const maxDistance = 90;
    let trackId;
    if (best && bestDistance <= maxDistance) {
      trackId = best.id;
      best.cx = centerX;
      best.cy = centerY;
      best.updatedAt = now;
    } else {
      trackId = trackCounter;
      trackCounter += 1;
      tracks.push({ id: trackId, cx: centerX, cy: centerY, updatedAt: now });
    }

    usedTrackIds.add(trackId);
    return { ...item, track_id: trackId };
  });
}

function drawLandmarks(context, points) {
  if (!Array.isArray(points)) {
    return;
  }

  context.fillStyle = "#facc15";
  points.forEach((point) => {
    if (!Array.isArray(point) || point.length !== 2) {
      return;
    }
    context.beginPath();
    context.arc(point[0], point[1], 2.6, 0, Math.PI * 2);
    context.fill();
  });
}

function drawPoseArrow(context, bbox, poseHint, color) {
  if (!bbox || !poseHint || poseHint === "center") {
    return;
  }

  const [x1, y1, x2, y2] = bbox;
  const cx = (x1 + x2) / 2;
  const cy = (y1 + y2) / 2;
  const length = 32;
  let dx = 0;
  let dy = 0;

  if (poseHint === "look_left") dx = -length;
  if (poseHint === "look_right") dx = length;
  if (poseHint === "look_up") dy = -length;
  if (poseHint === "look_down") dy = length;

  const endX = cx + dx;
  const endY = cy + dy;

  context.strokeStyle = color;
  context.lineWidth = 2.5;
  context.beginPath();
  context.moveTo(cx, cy);
  context.lineTo(endX, endY);
  context.stroke();

  const angle = Math.atan2(dy, dx);
  const headSize = 8;
  context.beginPath();
  context.moveTo(endX, endY);
  context.lineTo(endX - headSize * Math.cos(angle - Math.PI / 6), endY - headSize * Math.sin(angle - Math.PI / 6));
  context.lineTo(endX - headSize * Math.cos(angle + Math.PI / 6), endY - headSize * Math.sin(angle + Math.PI / 6));
  context.closePath();
  context.fillStyle = color;
  context.fill();
}

function drawHud(context, faceCount) {
  const lines = [
    `FPS ${hud.fps.toFixed(1)}`,
    `Latency ${Math.round(hud.latencyMs)}ms`,
    `Faces ${faceCount}`,
  ];

  context.font = "14px 'IBM Plex Mono', monospace";
  context.textBaseline = "top";
  const padding = 8;
  const lineHeight = 18;
  const width = 150;
  const height = padding * 2 + lineHeight * lines.length;

  context.fillStyle = "rgba(10, 20, 35, 0.72)";
  context.fillRect(10, 10, width, height);
  context.fillStyle = "#ffffff";
  lines.forEach((line, index) => {
    context.fillText(line, 18, 18 + index * lineHeight);
  });
}

function drawMatchesOverlay(matches) {
  syncOverlaySize();
  clearOverlay();

  const context = overlayCanvas.getContext("2d");
  context.lineWidth = 3;
  context.font = "15px 'IBM Plex Mono', monospace";
  context.textBaseline = "middle";

  const trackedMatches = assignTracking(Array.isArray(matches) ? matches : []);
  drawHud(context, trackedMatches.length);

  if (trackedMatches.length === 0) {
    return;
  }

  trackedMatches.forEach((item) => {
    if (!item || !Array.isArray(item.bbox) || item.bbox.length !== 4) {
      return;
    }

    const [x1, y1, x2, y2] = item.bbox;
    const width = Math.max(0, x2 - x1);
    const height = Math.max(0, y2 - y1);
    const matched = Boolean(item.student_id);
    const color = matched ? "#10b981" : "#ef4444";
    const label = `#${item.track_id ?? "?"} ${item.student_id || "Unknown"} ${(Number(item.confidence || 0) * 100).toFixed(1)}%`;

    context.strokeStyle = color;
    context.strokeRect(x1, y1, width, height);

    const labelWidth = Math.ceil(context.measureText(label).width) + 14;
    const labelHeight = 22;
    const labelX = Math.max(0, x1);
    const labelY = Math.max(0, y1 - labelHeight - 4);

    context.fillStyle = color;
    context.fillRect(labelX, labelY, labelWidth, labelHeight);
    context.fillStyle = "#ffffff";
    context.fillText(label, labelX + 7, labelY + labelHeight / 2);

    drawLandmarks(context, item.landmarks || []);
    drawPoseArrow(context, item.bbox, item.pose_hint, color);
  });
}

async function captureFrameBlob() {
  if (!liveVideo.videoWidth || !liveVideo.videoHeight) {
    throw new Error("Camera not ready yet. Wait a second and retry.");
  }

  const context = captureCanvas.getContext("2d");
  captureCanvas.width = liveVideo.videoWidth;
  captureCanvas.height = liveVideo.videoHeight;
  context.drawImage(liveVideo, 0, 0, captureCanvas.width, captureCanvas.height);

  return new Promise((resolve, reject) => {
    captureCanvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error("Failed to capture frame."));
        return;
      }
      resolve(blob);
    }, "image/jpeg", 0.9);
  });
}

async function recognizeFromCurrentFrame() {
  if (recognitionBusy) {
    return;
  }
  recognitionBusy = true;
  try {
    const threshold = document.getElementById("thresholdInput").value;
    const frameBlob = await captureFrameBlob();
    const formData = new FormData();
    formData.append("image", frameBlob, `frame-${Date.now()}.jpg`);

    const result = await postMultipart(`/api/ai/recognize-and-forward?threshold=${encodeURIComponent(threshold)}`, formData);
    const now = performance.now();
    if (hud.lastTimestamp > 0) {
      const delta = now - hud.lastTimestamp;
      if (delta > 0) {
        hud.fps = 1000 / delta;
      }
    }
    hud.lastTimestamp = now;
    hud.latencyMs = Number(result.elapsed_ms || 0);

    recognizeOutput.textContent = pretty(result);
    drawMatchesOverlay(result.matches || []);
    await loadAttendance();
  } catch (error) {
    recognizeOutput.textContent = String(error.message || error);
    clearOverlay();
  } finally {
    recognitionBusy = false;
  }
}

cameraEnrollForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  cameraEnrollOutput.textContent = "Capturing frames from live camera...";

  try {
    await ensureCamera();

    const studentId = document.getElementById("cameraStudentId").value.trim();
    const shots = Number.parseInt(document.getElementById("enrollShots").value, 10);
    const formData = new FormData();

    for (let index = 0; index < shots; index += 1) {
      cameraEnrollOutput.textContent = `Capturing angle ${index + 1}/${shots}. Please slightly turn your head.`;
      const frameBlob = await captureFrameBlob();
      formData.append("images", frameBlob, `${studentId}-angle-${index + 1}.jpg`);
      await sleep(550);
    }

    const result = await postMultipart(`/api/ai/register-student-batch?student_id=${encodeURIComponent(studentId)}`, formData);
    cameraEnrollOutput.textContent = pretty(result);
    await loadHealth();
  } catch (error) {
    cameraEnrollOutput.textContent = String(error.message || error);
  }
});

async function loadAttendance() {
  try {
    const summary = await getJson("/api/backend/attendance/summary");
    const recent = await getJson("/api/backend/attendance/recent?limit=20");

    totalEvents.textContent = summary.total_events;
    uniqueStudents.textContent = summary.unique_students;

    attendanceRows.innerHTML = "";
    recent.events.forEach((event) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${event.student_id}</td>
        <td>${event.similarity}</td>
        <td>${event.confidence}</td>
        <td>${event.source}</td>
        <td>${event.event_time}</td>
      `;
      attendanceRows.appendChild(row);
    });
  } catch {
    totalEvents.textContent = "Error";
    uniqueStudents.textContent = "Error";
    attendanceRows.innerHTML = "<tr><td colspan='5'>Unable to load attendance data.</td></tr>";
  }
}

refreshAllButton.addEventListener("click", async () => {
  await loadHealth();
  await loadAttendance();
});

refreshAttendanceButton.addEventListener("click", loadAttendance);

startCameraButton.addEventListener("click", async () => {
  try {
    await ensureCamera();
    recognizeOutput.textContent = "Camera started.";
  } catch (error) {
    recognizeOutput.textContent = String(error.message || error);
  }
});

stopCameraButton.addEventListener("click", () => {
  stopCamera();
  recognizeOutput.textContent = "Camera stopped.";
});

runSingleFrameButton.addEventListener("click", async () => {
  try {
    await ensureCamera();
    await recognizeFromCurrentFrame();
  } catch (error) {
    recognizeOutput.textContent = String(error.message || error);
  }
});

startLiveRecognitionButton.addEventListener("click", async () => {
  try {
    await ensureCamera();
    const intervalMs = Number.parseInt(document.getElementById("loopInterval").value, 10);
    if (recognitionTimer) {
      clearInterval(recognitionTimer);
    }
    recognitionTimer = setInterval(() => {
      recognizeFromCurrentFrame();
    }, intervalMs);
    recognizeOutput.textContent = `Live recognition started at ${intervalMs}ms interval.`;
  } catch (error) {
    recognizeOutput.textContent = String(error.message || error);
  }
});

stopLiveRecognitionButton.addEventListener("click", () => {
  if (recognitionTimer) {
    clearInterval(recognitionTimer);
    recognitionTimer = null;
  }
  recognizeOutput.textContent = "Live recognition stopped.";
});

/* Faculty Management Handlers */

document.getElementById("facultyRegisterForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const output = document.getElementById("facultyRegisterOutput");
  try {
    const payload = {
      faculty_id: document.getElementById("facultyId").value.trim(),
      full_name: document.getElementById("facultyName").value.trim(),
      barcode_value: document.getElementById("facultyBarcode").value.trim(),
      face_identity_id: document.getElementById("facultyFaceId").value.trim(),
    };
    const res = await fetch("/api/backend/faculty/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await res.json();
    output.textContent = pretty(result);
    if (res.ok) {
      e.target.reset();
    }
  } catch (error) {
    output.textContent = `Error: ${error.message || error}`;
  }
});

let checkinVideoStream = null;

document.getElementById("startCheckinCamera").addEventListener("click", async () => {
  try {
    checkinVideoStream = await navigator.mediaDevices.getUserMedia({ video: true });
    document.getElementById("checkinVideo").srcObject = checkinVideoStream;
    document.getElementById("startCheckinCamera").disabled = true;
    document.getElementById("stopCheckinCamera").disabled = false;
  } catch (error) {
    document.getElementById("facultyCheckinOutput").textContent = `Camera error: ${error.message}`;
  }
});

document.getElementById("stopCheckinCamera").addEventListener("click", () => {
  if (checkinVideoStream) {
    checkinVideoStream.getTracks().forEach(track => track.stop());
    document.getElementById("checkinVideo").srcObject = null;
  }
  document.getElementById("startCheckinCamera").disabled = false;
  document.getElementById("stopCheckinCamera").disabled = true;
});

document.getElementById("facultyCheckinForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const output = document.getElementById("facultyCheckinOutput");
  try {
    const video = document.getElementById("checkinVideo");
    const canvas = document.getElementById("checkinCaptureCanvas");
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    canvas.toBlob(async (blob) => {
      const formData = new FormData();
      formData.append("faculty_id", document.getElementById("checkinFacultyId").value.trim());
      formData.append("barcode_value", document.getElementById("checkinBarcode").value.trim());
      formData.append("image", blob, "checkin.jpg");
      
      const res = await fetch("/api/backend/faculty/checkin-with-image", {
        method: "POST",
        body: formData,
      });
      const result = await res.json();
      output.textContent = pretty(result);
      if (res.ok) {
        e.target.reset();
      }
    }, "image/jpeg");
  } catch (error) {
    output.textContent = `Error: ${error.message || error}`;
  }
});

/* Class Management Handlers */

document.getElementById("classCreateForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const output = document.getElementById("classCreateOutput");
  try {
    const payload = {
      class_id: document.getElementById("classId").value.trim(),
      class_name: document.getElementById("className").value.trim(),
      section: document.getElementById("classSection").value.trim() || null,
      semester: document.getElementById("classSemester").value.trim() || null,
    };
    const res = await fetch("/api/backend/classes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await res.json();
    output.textContent = pretty(result);
    if (res.ok) {
      e.target.reset();
    }
  } catch (error) {
    output.textContent = `Error: ${error.message || error}`;
  }
});

document.getElementById("enrollStudentsForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const output = document.getElementById("enrollStudentsOutput");
  try {
    const studentIds = document.getElementById("studentIdsList").value
      .split("\n")
      .map(s => s.trim())
      .filter(s => s.length > 0);
    
    const classId = document.getElementById("enrollClassId").value.trim();
    const payload = { student_ids: studentIds };
    
    const res = await fetch(`/api/backend/classes/${classId}/students/enroll`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await res.json();
    output.textContent = pretty(result);
    if (res.ok) {
      e.target.reset();
    }
  } catch (error) {
    output.textContent = `Error: ${error.message || error}`;
  }
});

/* Session Management Handlers */

document.getElementById("sessionStartForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const output = document.getElementById("sessionStartOutput");
  try {
    const payload = {
      class_id: document.getElementById("sessionStartClassId").value.trim(),
      faculty_id: document.getElementById("sessionStartFacultyId").value.trim(),
      barcode_value: document.getElementById("sessionStartBarcode").value.trim(),
      recognized_face_id: document.getElementById("sessionStartFaceId").value.trim(),
    };
    const res = await fetch("/api/backend/sessions/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await res.json();
    output.textContent = pretty(result);
    if (res.ok) {
      e.target.reset();
    }
  } catch (error) {
    output.textContent = `Error: ${error.message || error}`;
  }
});

document.getElementById("sessionEndForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const output = document.getElementById("sessionEndOutput");
  try {
    const sessionId = Number.parseInt(document.getElementById("sessionEndId").value, 10);
    const payload = {
      faculty_id: document.getElementById("sessionEndFacultyId").value.trim(),
      barcode_value: document.getElementById("sessionEndBarcode").value.trim(),
      recognized_face_id: document.getElementById("sessionEndFaceId").value.trim(),
    };
    const res = await fetch(`/api/backend/sessions/${sessionId}/end`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await res.json();
    output.textContent = pretty(result);
    if (res.ok) {
      e.target.reset();
    }
  } catch (error) {
    output.textContent = `Error: ${error.message || error}`;
  }
});

/* Attendance Report Handler */

let currentSessionReport = null;

document.getElementById("reportForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const output = document.getElementById("reportOutput");
  const container = document.getElementById("reportContainer");
  const downloadBtn = document.getElementById("downloadReportBtn");
  
  try {
    const sessionId = Number.parseInt(document.getElementById("reportSessionId").value, 10);
    const res = await fetch(`/api/backend/sessions/${sessionId}/attendance`);
    const result = await res.json();
    
    currentSessionReport = result;
    output.textContent = pretty(result);
    
    if (res.ok && result.attendance) {
      const session = result.session || {};
      const attendance = result.attendance || [];
      
      let html = `<div style="margin:1rem 0; padding:1rem; background:#f0f5fa; border-radius:8px;">
        <h3 style="margin:0 0 1rem;">Session ${sessionId}</h3>
        <p style="margin:0.5rem 0;">Class: ${session.class_id || 'N/A'} | Faculty: ${session.faculty_id || 'N/A'}</p>
        <p style="margin:0.5rem 0;">Start: ${session.start_time || 'N/A'} | End: ${session.end_time || 'N/A'}</p>
        <p style="margin:0.5rem 0;"><strong>Present: ${result.present_count || 0} | Absent: ${result.absent_count || 0}</strong></p>
        <table style="width:100%; border-collapse:collapse; margin-top:1rem;">
          <thead>
            <tr style="background:#e0f2f1;">
              <th style="padding:0.5rem; border:1px solid #ccc;">Student ID</th>
              <th style="padding:0.5rem; border:1px solid #ccc;">Status</th>
              <th style="padding:0.5rem; border:1px solid #ccc;">Marked Time</th>
            </tr>
          </thead>
          <tbody>`;
      
      attendance.forEach(row => {
        const statusClass = row.status === 'present' ? 'style="color:green;"' : 'style="color:red;"';
        html += `<tr>
          <td style="padding:0.5rem; border:1px solid #ccc;">${row.student_id}</td>
          <td ${statusClass} style="padding:0.5rem; border:1px solid #ccc; text-transform:uppercase; font-weight:bold;">${row.status}</td>
          <td style="padding:0.5rem; border:1px solid #ccc;">${row.marked_at}</td>
        </tr>`;
      });
      
      html += `</tbody></table></div>`;
      container.innerHTML = html;
      downloadBtn.style.display = "block";
    }
  } catch (error) {
    output.textContent = `Error: ${error.message || error}`;
    container.innerHTML = "";
    downloadBtn.style.display = "none";
  }
});

document.getElementById("downloadReportBtn").addEventListener("click", () => {
  if (!currentSessionReport || !currentSessionReport.attendance) {
    alert("No report loaded");
    return;
  }
  
  const session = currentSessionReport.session || {};
  const attendance = currentSessionReport.attendance || [];
  
  let csv = "Student ID,Status,Marked Time\n";
  attendance.forEach(row => {
    csv += `"${row.student_id}","${row.status}","${row.marked_at}"\n`;
  });
  
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `session_${session.session_id}_attendance.csv`;
  link.click();
  URL.revokeObjectURL(url);
});

(async function init() {
  await loadHealth();
  await loadAttendance();
})();
