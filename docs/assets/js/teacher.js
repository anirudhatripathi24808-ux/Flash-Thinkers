/**
 * FLASHNOVA - Teacher Dashboard Control Center Logic
 * Dynamic 10s QR Rotation, Live Confusion Analytics, Privacy-Preserving Records, Doubts, Reports
 */

let activeLectureId = null;
let activeClassroomId = null;
let qrCountdownInterval = null;
let currentQrCountdown = 10;
let socket = null;

document.addEventListener("DOMContentLoaded", async () => {
  await verifyTeacherSession();
  await loadClassrooms();
  setupSocketConnection();

  // Bind Create Classroom Form
  const classroomForm = document.getElementById("form-create-classroom");
  if (classroomForm) {
    classroomForm.addEventListener("submit", handleCreateClassroom);
  }

  // Bind Start Lecture Form
  const startLecForm = document.getElementById("form-start-lecture");
  if (startLecForm) {
    startLecForm.addEventListener("submit", handleStartLecture);
  }

  // Bind Stop Lecture Button
  const btnStopLec = document.getElementById("btn-stop-lecture");
  if (btnStopLec) {
    btnStopLec.addEventListener("click", handleStopLecture);
  }

  // Bind Create Question Form
  const questionForm = document.getElementById("form-create-question");
  if (questionForm) {
    questionForm.addEventListener("submit", handleCreateQuestion);
  }

  // Bind File Upload Form
  const fileForm = document.getElementById("form-upload-file");
  if (fileForm) {
    fileForm.addEventListener("submit", handleFileUpload);
  }

  // Bind Doubt Reply Form
  const replyForm = document.getElementById("form-reply-doubt");
  if (replyForm) {
    replyForm.addEventListener("submit", handleDoubtReplySubmit);
  }

  // Bind Export Buttons
  const btnExportCsv = document.getElementById("btn-export-csv");
  if (btnExportCsv) {
    btnExportCsv.addEventListener("click", () => {
      if (activeLectureId) {
        window.location.href = window.FLASHNOVA_CONFIG.getApiUrl(`/api/analytics/lecture/${activeLectureId}/export/csv`);
      } else {
        showToast("Select or start an active lecture first.", "warning");
      }
    });
  }

  const btnExportPdf = document.getElementById("btn-export-pdf");
  if (btnExportPdf) {
    btnExportPdf.addEventListener("click", () => {
      if (activeLectureId) {
        window.location.href = window.FLASHNOVA_CONFIG.getApiUrl(`/api/analytics/lecture/${activeLectureId}/export/pdf`);
      } else {
        showToast("Select or start an active lecture first.", "warning");
      }
    });
  }

  // Auto-refresh analytics and doubts every 6 seconds
  setInterval(() => {
    if (activeLectureId) {
      loadLectureAnalytics(activeLectureId);
      loadTeacherDoubts();
    }
  }, 6000);
});

// Verify Teacher Session
async function verifyTeacherSession() {
  const res = await apiRequest("/api/auth/me");
  if (!res.success || !res.user || res.user.role !== "teacher") {
    showToast("Please log in as a teacher.", "warning");
    setTimeout(() => { window.location.href = "index.html"; }, 800);
    return;
  }

  document.getElementById("teacher-name-display").innerText = res.user.name;
  if (res.user.authorized_subject) {
    document.getElementById("teacher-subject-badge").innerText = 
      `${res.user.authorized_subject.name} (${res.user.authorized_subject.code})`;
  } else {
    document.getElementById("teacher-subject-badge").innerText = "Subject: Not Selected";
  }
}

// Load Classrooms
async function loadClassrooms() {
  const res = await apiRequest("/api/teacher/classrooms");
  if (res.success && res.classrooms) {
    const select = document.getElementById("select-active-classroom");
    const listContainer = document.getElementById("classrooms-list-container");
    
    if (select) {
      select.innerHTML = '<option value="">-- Choose Classroom --</option>';
      res.classrooms.forEach(c => {
        select.innerHTML += `<option value="${c.id}">${c.name} (${c.code})</option>`;
      });
      
      select.onchange = () => {
        activeClassroomId = select.value ? parseInt(select.value) : null;
        const selectedObj = res.classrooms.find(c => c.id === activeClassroomId);
        if (selectedObj && selectedObj.active_lecture) {
          onActiveLectureFound(selectedObj.active_lecture);
        } else {
          onNoActiveLecture();
        }
        loadTeacherFiles();
        loadTeacherQuestions();
      };
    }

    if (listContainer) {
      listContainer.innerHTML = "";
      res.classrooms.forEach(c => {
        const item = document.createElement("div");
        item.className = "glass-card mb-2 p-3 d-flex justify-content-between align-items-center";
        item.innerHTML = `
          <div>
            <div class="font-weight-bold text-white">${c.name}</div>
            <div class="text-muted" style="font-size: 0.8rem;">Code: <span class="text-cyan">${c.code}</span> &bull; ${c.student_count} Enrolled</div>
          </div>
          <div>
            <button class="btn-cyber btn-cyber-outline btn-cyber-sm btn-toggle-enroll" data-id="${c.id}">
              Auto-Enroll: ${c.allow_qr_auto_enroll ? 'ON' : 'OFF'}
            </button>
          </div>
        `;
        listContainer.appendChild(item);
      });

      // Bind toggle auto-enroll buttons
      listContainer.querySelectorAll(".btn-toggle-enroll").forEach(b => {
        b.onclick = async () => {
          const cid = b.getAttribute("data-id");
          const toggleRes = await apiRequest(`/api/teacher/classrooms/${cid}/toggle-auto-enroll`, { method: "POST" });
          if (toggleRes.success) {
            showToast(toggleRes.message, "success");
            await loadClassrooms();
          }
        };
      });
    }

    // Auto-select first active lecture if any
    const firstActive = res.classrooms.find(c => c.active_lecture);
    if (firstActive) {
      if (select) select.value = firstActive.id;
      activeClassroomId = firstActive.id;
      onActiveLectureFound(firstActive.active_lecture);
      loadTeacherFiles();
      loadTeacherQuestions();
    }
  }
}

// When Active Lecture is active
function onActiveLectureFound(lec) {
  activeLectureId = lec.id;
  document.getElementById("control-lecture-topic").innerText = lec.topic;
  document.getElementById("section-active-lecture").style.display = "block";
  document.getElementById("section-start-lecture").style.display = "none";
  
  startDynamicQrCycle();
  loadLectureAnalytics(activeLectureId);
  loadTeacherDoubts();

  if (socket) {
    socket.emit("join_lecture", { lecture_id: activeLectureId });
  }
}

function onNoActiveLecture() {
  activeLectureId = null;
  stopDynamicQrCycle();
  document.getElementById("section-active-lecture").style.display = "none";
  document.getElementById("section-start-lecture").style.display = "block";
}

// Start Dynamic 10s QR Cycle
function startDynamicQrCycle() {
  stopDynamicQrCycle();
  fetchAndRenderQr();
  
  currentQrCountdown = 10;
  updateCountdownDisplay(10);
  
  qrCountdownInterval = setInterval(() => {
    currentQrCountdown--;
    updateCountdownDisplay(currentQrCountdown);
    
    if (currentQrCountdown <= 0) {
      currentQrCountdown = 10;
      fetchAndRenderQr();
    }
  }, 1000);
}

function stopDynamicQrCycle() {
  if (qrCountdownInterval) {
    clearInterval(qrCountdownInterval);
    qrCountdownInterval = null;
  }
}

function updateCountdownDisplay(sec) {
  const el = document.getElementById("qr-countdown-text");
  const circle = document.getElementById("qr-countdown-circle");
  if (el) el.innerText = `${sec}s`;
  if (circle) {
    const pct = (sec / 10) * 100;
    circle.style.setProperty("--progress", pct);
  }
}

// Fetch and Render Dynamic QR
async function fetchAndRenderQr() {
  if (!activeLectureId) return;
  const res = await apiRequest(`/api/teacher/lectures/${activeLectureId}/qr`);
  if (res.success && res.token) {
    renderQrCode(res.token);
    document.getElementById("display-qr-token-text").innerText = res.token;
  }
}

function renderQrCode(token) {
  const container = document.getElementById("qr-canvas-container");
  if (!container) return;
  container.innerHTML = "";

  if (typeof QRCode !== "undefined") {
    new QRCode(container, {
      text: token,
      width: 180,
      height: 180,
      colorDark: "#060913",
      colorLight: "#ffffff",
      correctLevel: QRCode.CorrectLevel.M
    });
  } else {
    // Fallback: render SVG QR via API or placeholder
    container.innerHTML = `
      <img src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(token)}" 
           alt="FLASHNOVA Dynamic QR" style="max-width: 180px; border-radius: 8px;" />
    `;
  }
}

// Start Lecture
async function handleStartLecture(e) {
  e.preventDefault();
  const select = document.getElementById("select-active-classroom");
  const topic = document.getElementById("input-lecture-topic").value.trim();

  if (!select || !select.value) {
    showToast("Please choose a classroom to start the lecture.", "error");
    return;
  }
  if (!topic) {
    showToast("Please enter a lecture topic name.", "error");
    return;
  }

  const res = await apiRequest("/api/teacher/lectures/start", {
    method: "POST",
    body: JSON.stringify({
      classroom_id: parseInt(select.value),
      topic: topic
    })
  });

  if (res.success) {
    showToast(`Lecture '${res.lecture.topic}' started! Dynamic 10s QR is active.`, "success");
    document.getElementById("input-lecture-topic").value = "";
    onActiveLectureFound(res.lecture);
    await loadClassrooms();
  } else {
    showToast(res.error || "Failed to start lecture.", "error");
  }
}

// Stop Lecture
async function handleStopLecture() {
  if (!activeLectureId) return;
  if (!confirm("Are you sure you want to stop this lecture? QR codes will expire and post-class reports will be compiled.")) return;

  const res = await apiRequest(`/api/teacher/lectures/${activeLectureId}/stop`, { method: "POST" });
  if (res.success) {
    showToast("Lecture ended successfully. Reports generated.", "info");
    onNoActiveLecture();
    await loadClassrooms();
  } else {
    showToast(res.error || "Failed to stop lecture.", "error");
  }
}

// Load Lecture Analytics
async function loadLectureAnalytics(lecId) {
  const res = await apiRequest(`/api/analytics/lecture/${lecId}`);
  if (res.success) {
    // 1. Stat Badges
    document.getElementById("stat-eligible-students").innerText = res.attendance_summary.total_eligible;
    document.getElementById("stat-joined-students").innerText = res.attendance_summary.joined_count;
    document.getElementById("stat-attendance-rate").innerText = `${res.attendance_summary.attendance_rate}%`;
    document.getElementById("stat-doubt-rate").innerText = `${res.confusion_stats.doubt.percentage}%`;

    // 2. Render Charts
    renderConfusionChart("chart-confusion", res.confusion_stats);
    renderAttendanceChart("chart-attendance", res.attendance_summary);
    renderTopicConfusionChart("chart-topic-confusion", res.topic_confusion);

    // 3. Render Attendance Records (Strictly Masked: 1234******)
    const attTbody = document.getElementById("tbody-attendance-records");
    if (attTbody) {
      attTbody.innerHTML = "";
      if (res.attendance_summary.records.length === 0) {
        attTbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">No students joined yet.</td></tr>`;
      } else {
        res.attendance_summary.records.forEach(rec => {
          let statusBadge = `<span class="badge-cyber badge-cyan">${rec.status}</span>`;
          if (rec.status === "Present") statusBadge = `<span class="badge-cyber badge-emerald"><i class="fa-solid fa-circle-check"></i> Present</span>`;
          else if (rec.status === "In Progress") statusBadge = `<span class="badge-cyber badge-amber"><i class="fa-solid fa-clock"></i> In Progress</span>`;
          else if (rec.status === "Pending Verification") statusBadge = `<span class="badge-cyber badge-purple">Pending Verif</span>`;

          attTbody.innerHTML += `
            <tr>
              <td><span class="masked-enrollment-tag">${rec.masked_enrollment}</span></td>
              <td>${statusBadge}</td>
              <td class="text-muted" style="font-size: 0.8rem;">${rec.qr_scanned_at ? new Date(rec.qr_scanned_at).toLocaleTimeString() : 'N/A'}</td>
            </tr>
          `;
        });
      }
    }
  }
}

// Load Voluntary Doubt Inbox
async function loadTeacherDoubts() {
  const container = document.getElementById("teacher-doubts-container");
  if (!container) return;

  const res = await apiRequest(`/api/teacher/doubts${activeLectureId ? `?lecture_id=${activeLectureId}` : ''}`);
  if (res.success && res.doubts) {
    if (res.doubts.length === 0) {
      container.innerHTML = `<p class="text-muted text-center py-4">No voluntary doubts submitted yet.</p>`;
      return;
    }

    container.innerHTML = "";
    res.doubts.forEach(d => {
      const card = document.createElement("div");
      card.className = "glass-card mb-3 p-3";
      
      let statusBadge = `<span class="badge-cyber badge-amber">${d.status}</span>`;
      if (d.status === "Resolved") {
        statusBadge = `<span class="badge-cyber badge-emerald"><i class="fa-solid fa-check-double"></i> Resolved</span>`;
      }

      card.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-2">
          <div class="d-flex align-items-center gap-2">
            <span class="font-weight-bold text-white"><i class="fa-solid fa-user-graduate text-purple"></i> ${d.student_name}</span>
            <span class="badge-cyber badge-cyan">${d.student_enrollment_no}</span>
          </div>
          ${statusBadge}
        </div>
        <div class="text-muted mb-2" style="font-size: 0.8rem;">Topic: <span class="text-white">${d.topic}</span> &bull; ${new Date(d.created_at).toLocaleString()}</div>
        <div class="p-2 rounded mb-3" style="background: rgba(10, 15, 29, 0.8); border: 1px solid rgba(56, 189, 248, 0.1);">
          ${d.doubt_text}
        </div>
        <div class="d-flex justify-content-between align-items-center">
          <button class="btn-cyber btn-cyber-primary btn-cyber-sm btn-open-reply" data-id="${d.id}" data-name="${d.student_name}">
            <i class="fa-solid fa-reply"></i> Reply to Student
          </button>
          <span class="text-muted" style="font-size: 0.75rem;"><i class="fa-solid fa-shield-halved text-emerald"></i> Consented Disclosure</span>
        </div>
      `;
      container.appendChild(card);
    });

    // Bind open reply buttons
    container.querySelectorAll(".btn-open-reply").forEach(btn => {
      btn.onclick = () => {
        const doubtId = btn.getAttribute("data-id");
        const studentName = btn.getAttribute("data-name");
        document.getElementById("reply-doubt-id").value = doubtId;
        document.getElementById("reply-modal-title").innerText = `Reply to ${studentName}`;
        openModal("modal-reply-doubt");
      };
    });
  }
}

// Submit Doubt Reply
async function handleDoubtReplySubmit(e) {
  e.preventDefault();
  const doubtId = document.getElementById("reply-doubt-id").value;
  const replyText = document.getElementById("input-reply-text").value.trim();
  const status = document.getElementById("select-reply-status").value;

  if (!replyText) {
    showToast("Please write a reply.", "error");
    return;
  }

  const res = await apiRequest(`/api/teacher/doubts/${doubtId}/reply`, {
    method: "POST",
    body: JSON.stringify({ reply_text: replyText, status: status })
  });

  if (res.success) {
    showToast("Reply sent to student dashboard!", "success");
    document.getElementById("form-reply-doubt").reset();
    closeModal("modal-reply-doubt");
    await loadTeacherDoubts();
  } else {
    showToast(res.error || "Failed to send reply.", "error");
  }
}

// Create Classroom
async function handleCreateClassroom(e) {
  e.preventDefault();
  const name = document.getElementById("input-classroom-name").value.trim();
  const autoEnroll = document.getElementById("check-classroom-auto-enroll").checked;

  if (!name) {
    showToast("Classroom name is required.", "error");
    return;
  }

  const res = await apiRequest("/api/teacher/classrooms", {
    method: "POST",
    body: JSON.stringify({ name: name, allow_qr_auto_enroll: autoEnroll })
  });

  if (res.success) {
    showToast(`Classroom '${res.classroom.name}' created! Code: ${res.classroom.code}`, "success");
    document.getElementById("form-create-classroom").reset();
    closeModal("modal-create-classroom");
    await loadClassrooms();
  } else {
    showToast(res.error || "Failed to create classroom.", "error");
  }
}

// Create Question
async function handleCreateQuestion(e) {
  e.preventDefault();
  const select = document.getElementById("select-active-classroom");
  const cid = select ? select.value : activeClassroomId;
  if (!cid) {
    showToast("Please choose a classroom first.", "error");
    return;
  }

  const qText = document.getElementById("q-text").value.trim();
  const optA = document.getElementById("q-opt-a").value.trim();
  const optB = document.getElementById("q-opt-b").value.trim();
  const optC = document.getElementById("q-opt-c").value.trim();
  const optD = document.getElementById("q-opt-d").value.trim();
  const correct = document.getElementById("q-correct").value;
  const topic = document.getElementById("q-topic").value.trim() || "General";
  const difficulty = document.getElementById("q-difficulty").value;
  const isCompulsory = document.getElementById("q-compulsory").checked;

  const res = await apiRequest("/api/teacher/questions", {
    method: "POST",
    body: JSON.stringify({
      classroom_id: parseInt(cid),
      lecture_id: activeLectureId,
      question_text: qText,
      topic: topic,
      difficulty: difficulty,
      is_compulsory: isCompulsory,
      correct_answer: correct,
      options: { A: optA, B: optB, C: optC, D: optD }
    })
  });

  if (res.success) {
    showToast("Question published to eligible student dashboards!", "success");
    document.getElementById("form-create-question").reset();
    closeModal("modal-create-question");
    await loadTeacherQuestions();
  } else {
    showToast(res.error || "Question creation failed.", "error");
  }
}

// Load Questions
async function loadTeacherQuestions() {
  const container = document.getElementById("teacher-questions-container");
  if (!container) return;

  const cid = activeClassroomId;
  const res = await apiRequest(`/api/teacher/questions${cid ? `?classroom_id=${cid}` : ''}`);
  if (res.success && res.questions) {
    if (res.questions.length === 0) {
      container.innerHTML = `<p class="text-muted text-center py-3">No questions created yet for this classroom.</p>`;
      return;
    }

    container.innerHTML = "";
    res.questions.forEach((q, idx) => {
      const card = document.createElement("div");
      card.className = "mcq-card p-3 mb-2";
      
      const compBadge = q.is_compulsory 
        ? '<span class="badge-cyber badge-amber">Compulsory</span>' 
        : '<span class="badge-cyber badge-cyan">Optional</span>';

      card.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-2">
          <div class="d-flex align-items-center gap-2">
            <span class="badge-cyber badge-cyan">Q${idx + 1}</span>
            ${compBadge}
            <span class="text-muted" style="font-size: 0.8rem;">Topic: ${q.topic} &bull; Correct: <b class="text-emerald">${q.correct_answer}</b></span>
          </div>
          <div>
            <button class="btn-cyber btn-cyber-outline btn-cyber-sm btn-toggle-reveal" data-id="${q.id}">
              ${q.reveal_answer ? '<i class="fa-solid fa-eye-slash"></i> Hide Answer' : '<i class="fa-solid fa-eye"></i> Reveal Answer'}
            </button>
            <button class="btn-cyber btn-cyber-danger btn-cyber-sm btn-delete-question" data-id="${q.id}">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </div>
        <div class="text-white mb-2 font-weight-bold">${q.question_text}</div>
      `;
      container.appendChild(card);
    });

    // Bind reveal and delete buttons
    container.querySelectorAll(".btn-toggle-reveal").forEach(b => {
      b.onclick = async () => {
        const qid = b.getAttribute("data-id");
        const revRes = await apiRequest(`/api/teacher/questions/${qid}/toggle-reveal`, { method: "POST" });
        if (revRes.success) {
          showToast(revRes.message, "info");
          await loadTeacherQuestions();
        }
      };
    });

    container.querySelectorAll(".btn-delete-question").forEach(b => {
      b.onclick = async () => {
        if (!confirm("Delete this question?")) return;
        const qid = b.getAttribute("data-id");
        const delRes = await apiRequest(`/api/teacher/questions/${qid}`, { method: "DELETE" });
        if (delRes.success) {
          showToast("Question deleted.", "info");
          await loadTeacherQuestions();
        }
      };
    });
  }
}

// Upload File
async function handleFileUpload(e) {
  e.preventDefault();
  const cid = activeClassroomId;
  if (!cid) {
    showToast("Please choose a classroom first.", "error");
    return;
  }

  const fileInput = document.getElementById("file-input");
  const title = document.getElementById("file-title").value.trim();
  const desc = document.getElementById("file-desc").value.trim();

  if (!fileInput.files.length) {
    showToast("Please select a file to upload.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("classroom_id", cid);
  if (activeLectureId) formData.append("lecture_id", activeLectureId);
  formData.append("title", title);
  formData.append("description", desc);

  const res = await apiRequest("/api/teacher/files", {
    method: "POST",
    body: formData
  });

  if (res.success) {
    showToast(`File '${res.file.title}' uploaded and published to students!`, "success");
    document.getElementById("form-upload-file").reset();
    closeModal("modal-upload-file");
    await loadTeacherFiles();
  } else {
    showToast(res.error || "File upload failed.", "error");
  }
}

// Load Teacher Files
async function loadTeacherFiles() {
  const container = document.getElementById("teacher-files-container");
  if (!container) return;

  const cid = activeClassroomId;
  const res = await apiRequest(`/api/teacher/files${cid ? `?classroom_id=${cid}` : ''}`);
  if (res.success && res.files) {
    if (res.files.length === 0) {
      container.innerHTML = `<p class="text-muted text-center py-3">No study materials uploaded for this classroom.</p>`;
      return;
    }

    container.innerHTML = "";
    res.files.forEach(f => {
      const item = document.createElement("div");
      item.className = "d-flex justify-content-between align-items-center p-2 mb-2 rounded";
      item.style.background = "rgba(10, 15, 29, 0.7)";
      item.style.border = "1px solid rgba(56, 189, 248, 0.15)";
      
      item.innerHTML = `
        <div class="d-flex align-items-center gap-2">
          <span class="badge-cyber badge-purple">${f.file_type}</span>
          <span class="text-white font-weight-bold" style="font-size: 0.9rem;">${f.title}</span>
          <span class="text-muted" style="font-size: 0.75rem;">(${f.original_filename})</span>
        </div>
        <div>
          <button class="btn-cyber btn-cyber-outline btn-cyber-sm btn-toggle-publish" data-id="${f.id}">
            ${f.is_published ? 'Published' : 'Unpublished'}
          </button>
          <button class="btn-cyber btn-cyber-danger btn-cyber-sm btn-delete-file" data-id="${f.id}">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
      `;
      container.appendChild(item);
    });

    container.querySelectorAll(".btn-toggle-publish").forEach(b => {
      b.onclick = async () => {
        const fid = b.getAttribute("data-id");
        const pubRes = await apiRequest(`/api/teacher/files/${fid}/toggle-publish`, { method: "POST" });
        if (pubRes.success) {
          showToast(pubRes.message, "info");
          await loadTeacherFiles();
        }
      };
    });

    container.querySelectorAll(".btn-delete-file").forEach(b => {
      b.onclick = async () => {
        if (!confirm("Delete this file?")) return;
        const fid = b.getAttribute("data-id");
        const delRes = await apiRequest(`/api/teacher/files/${fid}`, { method: "DELETE" });
        if (delRes.success) {
          showToast("File deleted.", "info");
          await loadTeacherFiles();
        }
      };
    });
  }
}

// SocketIO Setup
function setupSocketConnection() {
  if (typeof io === "undefined") return;
  const socketUrl = window.FLASHNOVA_CONFIG.API_BASE || window.location.origin;
  socket = io(socketUrl, { transports: ["websocket", "polling"] });

  socket.on("connect", () => {
    if (activeLectureId) {
      socket.emit("join_lecture", { lecture_id: activeLectureId });
    }
  });

  socket.on("confusion_tally", (data) => {
    if (activeLectureId && data.lecture_id === activeLectureId) {
      loadLectureAnalytics(activeLectureId);
    }
  });

  socket.on("new_voluntary_doubt", (data) => {
    showToast(`New voluntary doubt from ${data.student_name}!`, "warning");
    loadTeacherDoubts();
  });
}
