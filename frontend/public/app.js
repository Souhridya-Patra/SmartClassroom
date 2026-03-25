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
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
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
    recognizeOutput.textContent = pretty(result);
    await loadAttendance();
  } catch (error) {
    recognizeOutput.textContent = String(error.message || error);
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

(async function init() {
  await loadHealth();
  await loadAttendance();
})();
