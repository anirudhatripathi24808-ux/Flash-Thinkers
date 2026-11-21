/**
 * FLASHNOVA - Student Dashboard Logic
 * QR Scanner, 3 Understanding Buttons, Voluntary Doubt Submission, MCQ Questions, Files
 */

let currentActiveLecture = null;
let currentActiveTopic = "General";
let socket = null;

document.addEventListener("DOMContentLoaded", async () => {
  await verifyStudentSession();
  await loadStudentDashboard();
  setupSocketConnection();

  // Bind QR manual submission
  const btnSubmitQr = document.getElementById("btn-submit-qr-token");
  if (btnSubmitQr) {
    btnSubmitQr.addEventListener("click", handleQrSubmission);
  }

  // Bind Understanding Buttons
  document.querySelectorAll(".btn-feedback").forEach(btn => {
    btn.addEventListener("click", () => {
      const status = btn.getAttribute("data-status");
      handleFeedbackSubmit(status);
    });
  });

  // Bind Voluntary Doubt Form
  const doubtForm = document.getElementById("form-volunteer-doubt");
  if (doubtForm) {
    doubtForm.addEventListener("submit", handleVolunteerDoubtSubmit);
  }

  // Refresh interval for live questions and doubts
  setInterval(loadMyDoubts, 15000);
});

// Verify Student Session
async function verifyStudentSession() {
  const res = await apiRequest("/api/auth/me");
  if (!res.success || !res.user || res.user.role !== "student") {
    showToast("Please log in as a student to access this portal.", "warning");
    setTimeout(() => {
      window.location.href = "index.html";
    }, 800);
    return;
  }

  // Update UI with student's own private information
  document.getElementById("student-name-display").innerText = res.user.name;
  document.getElementById("student-enrollment-display").innerText = res.user.enrollment_no || "N/A";
  if (res.user.is_demo) {
    const demoBadge = document.getElementById("student-demo-badge");
    if (demoBadge) demoBadge.style.display = "inline-flex";
  }
}

// Load Dashboard Data
async function loadStudentDashboard() {
  const res = await apiRequest("/api/student/dashboard");
  if (res.success) {
    currentActiveLecture = res.active_lecture;
    
    // Update Active Lecture Card
    const cardActiveLec = document.getElementById("card-active-lecture");
    const noActiveLec = document.getElementById("no-active-lecture-msg");
    
    if (currentActiveLecture && currentActiveLecture.is_active) {
      if (cardActiveLec) cardActiveLec.style.display = "block";
      if (noActiveLec) noActiveLec.style.display = "none";
      
      document.getElementById("active-lec-topic").innerText = currentActiveLecture.topic;
      document.getElementById("active-lec-classroom").innerText = currentActiveLecture.classroom_name || "Classroom";
      document.getElementById("active-lec-subject").innerText = `${currentActiveLecture.subject_name || ''} (${currentActiveLecture.subject_code || ''})`;
      
      currentActiveTopic = currentActiveLecture.topic;
      updateAttendanceBadge(currentActiveLecture.attendance_status || "Not Marked");

      // Join Socket Room for this lecture
      if (socket) {
        socket.emit("join_lecture", { lecture_id: currentActiveLecture.id });
      }
    } else {
      if (cardActiveLec) cardActiveLec.style.display = "none";
      if (noActiveLec) noActiveLec.style.display = "block";
    }

    // Load components
    await loadQuestions();
    await loadStudyFiles();
    await loadMyDoubts();
    await loadAttendanceHistory();
  }
}

// Update Attendance Status Badge
function updateAttendanceBadge(status) {
  const badge = document.getElementById("student-attendance-status");
  if (!badge) return;

  badge.className = "badge-cyber";
  if (status === "Present") {
    badge.classList.add("badge-emerald");
    badge.innerHTML = '<i class="fa-solid fa-circle-check"></i> Present';
  } else if (status === "In Progress") {
    badge.classList.add("badge-amber");
    badge.innerHTML = '<i class="fa-solid fa-clock"></i> In Progress (Attempt Compulsory Questions)';
  } else if (status === "Pending Verification") {
    badge.classList.add("badge-purple");
    badge.innerHTML = '<i class="fa-solid fa-user-clock"></i> Pending Verification';
  } else {
    badge.classList.add("badge-coral");
    badge.innerHTML = '<i class="fa-solid fa-circle-xmark"></i> Not Marked (Scan QR to Enter)';
  }
}

// Handle QR Token Entry (via manual code or camera scan)
async function handleQrSubmission() {
  const tokenInput = document.getElementById("input-qr-token");
  const token = tokenInput ? tokenInput.value.trim() : "";

  if (!token) {
    showToast("Please enter or scan the active QR token.", "error");
    return;
  }

  // Attempt to get device geolocation with user permission
  let lat = null;
  let lon = null;
  if ("geolocation" in navigator) {
    try {
      const pos = await new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 3000 });
      }).catch(() => null);
      if (pos && pos.coords) {
        lat = pos.coords.latitude;
        lon = pos.coords.longitude;
      }
    } catch (_) {}
  }

  const res = await apiRequest("/api/student/scan-qr", {
    method: "POST",
    body: JSON.stringify({
      token: token,
      latitude: lat,
      longitude: lon,
      device_info: navigator.userAgent
    })
  });

  if (res.success) {
    showToast(`Access granted to ${res.lecture.topic}! Attendance: ${res.attendance_status}`, "success");
    if (tokenInput) tokenInput.value = "";
    closeModal("modal-qr-scanner");
    await loadStudentDashboard();
  } else {
    showToast(res.error || "QR validation failed. Check if code expired.", "error");
  }
}

// 3 Understanding Buttons Feedback
async function handleFeedbackSubmit(status) {
  if (!currentActiveLecture || !currentActiveLecture.id) {
    showToast("No active lecture in session for feedback.", "warning");
    return;
  }

  const res = await apiRequest("/api/student/understanding", {
    method: "POST",
    body: JSON.stringify({
      lecture_id: currentActiveLecture.id,
      status: status,
      topic: currentActiveTopic
    })
  });

  if (res.success) {
    showToast(`Anonymous feedback recorded: ${status.replace('_', ' ')}`, "success");
    // Visually toggle active button
    document.querySelectorAll(".btn-feedback").forEach(b => b.classList.remove("active"));
    const activeBtn = document.querySelector(`.btn-feedback[data-status="${status}"]`);
    if (activeBtn) activeBtn.classList.add("active");
  } else {
    showToast(res.error || "Feedback submission failed.", "error");
  }
}

// Handle Volunteer To Ask A Doubt
async function handleVolunteerDoubtSubmit(e) {
  e.preventDefault();
  if (!currentActiveLecture || !currentActiveLecture.id) {
    showToast("Active lecture required to volunteer a doubt.", "warning");
    return;
  }

  const topic = document.getElementById("doubt-topic").value.trim() || currentActiveTopic;
  const doubtText = document.getElementById("doubt-text").value.trim();
  const consentBox = document.getElementById("doubt-consent-checkbox");

  if (!consentBox || !consentBox.checked) {
    showToast("You must explicitly check the identity disclosure confirmation.", "error");
    return;
  }

  if (!doubtText) {
    showToast("Please describe your doubt clearly.", "error");
    return;
  }

  const res = await apiRequest("/api/student/doubts/volunteer", {
    method: "POST",
    body: JSON.stringify({
      lecture_id: currentActiveLecture.id,
      topic: topic,
      doubt_text: doubtText,
      is_consented: true
    })
  });

  if (res.success) {
    showToast("Doubt submitted to teacher inbox with voluntary identity consent!", "success");
    document.getElementById("form-volunteer-doubt").reset();
    closeModal("modal-volunteer-doubt");
    await loadMyDoubts();
  } else {
    showToast(res.error || "Doubt submission failed.", "error");
  }
}

// Load Questions (Can be answered later too!)
async function loadQuestions() {
  const container = document.getElementById("student-questions-container");
  if (!container) return;

  const res = await apiRequest("/api/student/questions");
  if (res.success && res.questions) {
    if (res.questions.length === 0) {
      container.innerHTML = `
        <div class="glass-card text-center py-4">
          <i class="fa-solid fa-clipboard-question text-muted" style="font-size: 2.5rem; margin-bottom: 0.75rem;"></i>
          <p class="text-muted">No questions published yet. Questions appear here when released by your teacher.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = "";
    res.questions.forEach((q, idx) => {
      const qCard = document.createElement("div");
      qCard.className = "mcq-card";
      
      const compulsoryBadge = q.is_compulsory 
        ? '<span class="badge-cyber badge-amber"><i class="fa-solid fa-asterisk"></i> Compulsory</span>' 
        : '<span class="badge-cyber badge-cyan">Optional</span>';
        
      const statusBadge = q.has_attempted 
        ? '<span class="badge-cyber badge-emerald"><i class="fa-solid fa-check"></i> Attempted</span>' 
        : '<span class="badge-cyber badge-purple">Pending</span>';

      let optionsHtml = "";
      q.options.forEach(opt => {
        const isSelected = q.has_attempted && q.selected_option === opt.key;
        optionsHtml += `
          <div class="option-item ${isSelected ? 'selected' : ''}" data-qid="${q.id}" data-key="${opt.key}">
            <div class="option-badge">${opt.key}</div>
            <div class="option-text">${opt.text}</div>
          </div>
        `;
      });

      let revealHtml = "";
      if (q.has_attempted && q.is_correct !== null) {
        revealHtml = `
          <div class="mt-3 p-2 rounded" style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3);">
            <span class="text-emerald font-weight-bold">
              ${q.is_correct ? '<i class="fa-solid fa-circle-check"></i> Correct!' : '<i class="fa-solid fa-circle-xmark text-coral"></i> Incorrect'}
            </span>
            <span class="text-muted ml-2">Correct Answer: <b>${q.correct_answer}</b></span>
          </div>
        `;
      }

      const submitBtnHtml = q.has_attempted 
        ? `<button class="btn-cyber btn-cyber-outline btn-cyber-sm mt-3" disabled>Already Submitted (Option ${q.selected_option})</button>`
        : `<button class="btn-cyber btn-cyber-primary btn-cyber-sm mt-3 btn-submit-answer" data-qid="${q.id}">Submit Answer</button>`;

      qCard.innerHTML = `
        <div class="mcq-header">
          <div>
            <div class="d-flex align-items-center gap-2 mb-2">
              <span class="badge-cyber badge-cyan">Q${idx + 1}</span>
              ${compulsoryBadge}
              ${statusBadge}
              <span class="text-muted" style="font-size: 0.8rem;">Topic: ${q.topic}</span>
            </div>
            <div class="mcq-question-text">${q.question_text}</div>
          </div>
        </div>
        <div class="options-grid">
          ${optionsHtml}
        </div>
        ${revealHtml}
        <div class="d-flex justify-content-between align-items-center">
          ${submitBtnHtml}
          ${q.has_attempted ? `<span class="text-muted" style="font-size: 0.75rem;">Submitted</span>` : ''}
        </div>
      `;

      container.appendChild(qCard);
    });

    // Bind option selection
    container.querySelectorAll(".option-item").forEach(optItem => {
      optItem.addEventListener("click", () => {
        const qid = optItem.getAttribute("data-qid");
        const parentGrid = optItem.parentElement;
        // Don't allow changing if already submitted
        const submitBtn = parentGrid.parentElement.querySelector(`.btn-submit-answer[data-qid="${qid}"]`);
        if (!submitBtn) return;

        parentGrid.querySelectorAll(".option-item").forEach(it => it.classList.remove("selected"));
        optItem.classList.add("selected");
      });
    });

    // Bind submit answer buttons
    container.querySelectorAll(".btn-submit-answer").forEach(btn => {
      btn.addEventListener("click", async () => {
        const qid = btn.getAttribute("data-qid");
        const parentCard = btn.closest(".mcq-card");
        const selectedOpt = parentCard.querySelector(".option-item.selected");

        if (!selectedOpt) {
          showToast("Please choose an answer option before submitting.", "error");
          return;
        }

        const chosenKey = selectedOpt.getAttribute("data-key");
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Submitting...';

        const res = await apiRequest(`/api/student/questions/${qid}/submit`, {
          method: "POST",
          body: JSON.stringify({ selected_option: chosenKey })
        });

        if (res.success) {
          showToast("Answer submitted successfully!", "success");
          if (res.attendance_status) {
            updateAttendanceBadge(res.attendance_status);
          }
          await loadQuestions();
        } else {
          showToast(res.error || "Submission error.", "error");
          btn.disabled = false;
          btn.innerText = "Submit Answer";
        }
      });
    });
  }
}

// Load Study Materials
async function loadStudyFiles() {
  const container = document.getElementById("student-files-container");
  if (!container) return;

  const res = await apiRequest("/api/student/files");
  if (res.success && res.files) {
    if (res.files.length === 0) {
      container.innerHTML = `<p class="text-muted text-center py-3">No study materials published yet.</p>`;
      return;
    }

    container.innerHTML = "";
    res.files.forEach(f => {
      const item = document.createElement("div");
      item.className = "d-flex justify-content-between align-items-center p-3 mb-2 rounded";
      item.style.background = "rgba(10, 15, 29, 0.7)";
      item.style.border = "1px solid rgba(56, 189, 248, 0.15)";
      
      const sizeMb = (f.file_size / (1024 * 1024)).toFixed(2);
      item.innerHTML = `
        <div class="d-flex align-items-center gap-3">
          <div class="option-badge" style="background: rgba(139, 92, 246, 0.15); color: #c084fc;">
            ${f.file_type}
          </div>
          <div>
            <div class="font-weight-bold text-white">${f.title}</div>
            <div class="text-muted" style="font-size: 0.75rem;">${f.original_filename} &bull; ${sizeMb} MB</div>
          </div>
        </div>
        <a href="${window.FLASHNOVA_CONFIG.getApiUrl(`/api/student/files/${f.id}/download`)}" 
           class="btn-cyber btn-cyber-outline btn-cyber-sm" download>
          <i class="fa-solid fa-download"></i> Download
        </a>
      `;
      container.appendChild(item);
    });
  }
}

// Load My Doubts & Teacher Replies
async function loadMyDoubts() {
  const container = document.getElementById("student-doubts-container");
  if (!container) return;

  const res = await apiRequest("/api/student/doubts");
  if (res.success && res.doubts) {
    if (res.doubts.length === 0) {
      container.innerHTML = `<p class="text-muted text-center py-3">You haven't submitted any voluntary doubts yet.</p>`;
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

      let repliesHtml = "";
      if (d.replies && d.replies.length > 0) {
        d.replies.forEach(r => {
          repliesHtml += `
            <div class="p-2 mt-2 rounded" style="background: rgba(56, 189, 248, 0.1); border-left: 3px solid var(--neon-cyan);">
              <div class="text-cyan font-weight-bold" style="font-size: 0.8rem;"><i class="fa-solid fa-chalkboard-user"></i> ${r.teacher_name} Reply:</div>
              <div class="text-white" style="font-size: 0.9rem;">${r.reply_text}</div>
            </div>
          `;
        });
      } else {
        repliesHtml = `<div class="text-muted mt-2" style="font-size: 0.8rem;"><i class="fa-solid fa-clock"></i> Awaiting teacher response...</div>`;
      }

      card.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-2">
          <span class="badge-cyber badge-cyan">Topic: ${d.topic}</span>
          ${statusBadge}
        </div>
        <div class="text-white mb-2" style="font-size: 0.95rem;">${d.doubt_text}</div>
        ${repliesHtml}
      `;
      container.appendChild(card);
    });
  }
}

// Load Attendance History
async function loadAttendanceHistory() {
  const container = document.getElementById("student-attendance-history");
  if (!container) return;

  const res = await apiRequest("/api/student/attendance");
  if (res.success && res.attendance) {
    if (res.attendance.length === 0) {
      container.innerHTML = `<tr><td colspan="4" class="text-center text-muted">No attendance logs yet.</td></tr>`;
      return;
    }

    container.innerHTML = "";
    res.attendance.forEach(att => {
      const tr = document.createElement("tr");
      let statusClass = "text-muted";
      if (att.status === "Present") statusClass = "text-emerald";
      else if (att.status === "In Progress") statusClass = "text-amber";
      
      tr.innerHTML = `
        <td>${att.topic}</td>
        <td>${att.classroom_name}</td>
        <td><span class="${statusClass} font-weight-bold">${att.status}</span></td>
        <td>${att.qr_scanned_at ? new Date(att.qr_scanned_at).toLocaleString() : 'N/A'}</td>
      `;
      container.appendChild(tr);
    });
  }
}

// SocketIO Real-Time Listener
function setupSocketConnection() {
  if (typeof io === "undefined") return;
  const socketUrl = window.FLASHNOVA_CONFIG.API_BASE || window.location.origin;
  socket = io(socketUrl, { transports: ["websocket", "polling"] });

  socket.on("connect", () => {
    if (currentActiveLecture && currentActiveLecture.id) {
      socket.emit("join_lecture", { lecture_id: currentActiveLecture.id });
    }
  });

  socket.on("attendance_change", (data) => {
    // If attendance updated for this student
    loadStudentDashboard();
  });
}
