/**
 * FLASHNOVA - UI Helpers, Toast Notifications, Modals & Network Client
 */

// Toast Notifications
function showToast(message, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  
  let icon = "fa-circle-info";
  if (type === "success") icon = "fa-circle-check text-emerald";
  else if (type === "error") icon = "fa-circle-exclamation text-coral";
  else if (type === "warning") icon = "fa-triangle-exclamation text-amber";

  toast.innerHTML = `
    <i class="fa-solid ${icon}"></i>
    <span>${message}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Modal Helpers
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("active");
    window.dispatchEvent(new CustomEvent("modalOpened", { detail: modalId }));
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("active");
    window.dispatchEvent(new CustomEvent("modalClosed", { detail: modalId }));
  }
}

// Global API Request Helper
async function apiRequest(endpoint, options = {}) {
  const url = window.FLASHNOVA_CONFIG.getApiUrl(endpoint);
  
  const headers = options.headers || {};
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  // Attach session token if stored
  const token = localStorage.getItem("flashnova_token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(url, {
      ...options,
      headers: headers,
      credentials: "include"
    });

    const data = await res.json().catch(() => ({ success: false, error: "Invalid JSON response from server" }));

    if (!res.ok) {
      const errMsg = data.error || `HTTP error ${res.status}`;
      return { success: false, error: errMsg, status: res.status };
    }

    return data;
  } catch (err) {
    console.warn("API Request failed. Falling back to Hackathon Demo Mode:", err);
    return handleOfflineMockResponse(endpoint, options);
  }
}

// Ensure default simulated demo data is seeded in localStorage
function initDemoData() {
  if (!localStorage.getItem("fn_demo_init")) {
    const defaultClassrooms = [
      {
        id: 101,
        name: "Room 401 - Innovation Lab",
        code: "CYB401",
        student_count: 36,
        allow_qr_auto_enroll: true,
        active_lecture: {
          id: 201,
          topic: "Advanced Calculus & Real-Time Limits",
          classroom_name: "Room 401 - Innovation Lab",
          subject_name: "Mathematics",
          subject_code: "MAT121",
          is_active: true
        }
      },
      {
        id: 102,
        name: "Room 203 - Cyber Hub",
        code: "ROB203",
        student_count: 28,
        allow_qr_auto_enroll: false,
        active_lecture: null
      }
    ];

    const defaultQuestions = [
      {
        id: 1,
        classroom_id: 101,
        topic: "Calculus",
        question_text: "What is the limit of (sin x) / x as x approaches 0?",
        difficulty: "Medium",
        is_compulsory: true,
        correct_answer: "A",
        reveal_answer: true,
        has_attempted: false,
        selected_option: null,
        is_correct: null,
        options: [
          { key: "A", text: "1" },
          { key: "B", text: "0" },
          { key: "C", text: "Infinity" },
          { key: "D", text: "Undefined" }
        ]
      },
      {
        id: 2,
        classroom_id: 101,
        topic: "Linear Algebra",
        question_text: "If det(A) = 0, which of the following is strictly true about square matrix A?",
        difficulty: "Easy",
        is_compulsory: false,
        correct_answer: "B",
        reveal_answer: false,
        has_attempted: false,
        selected_option: null,
        is_correct: null,
        options: [
          { key: "A", text: "A is invertible" },
          { key: "B", text: "A is singular (non-invertible)" },
          { key: "C", text: "A is an identity matrix" },
          { key: "D", text: "A has full rank" }
        ]
      }
    ];

    const defaultDoubts = [
      {
        id: 501,
        student_name: "Anirudha Student",
        student_enrollment_no: "2026101234",
        topic: "Calculus Limits",
        doubt_text: "Could you re-explain why L'Hopital's rule applies to 0/0 and infinity/infinity indeterminate forms?",
        status: "In Progress",
        created_at: new Date(Date.now() - 3600000).toISOString(),
        replies: [
          {
            teacher_name: "Prof. Alan Turing",
            reply_text: "Remember that L'Hopital takes the derivative of numerator and denominator separately until you obtain a defined value.",
            created_at: new Date(Date.now() - 1800000).toISOString()
          }
        ]
      }
    ];

    const defaultFiles = [
      {
        id: 1,
        title: "Lecture 08 - Neural Limits & Calculus Formulas",
        original_filename: "calculus_limits_cheatsheet.pdf",
        file_type: "PDF",
        file_size: 1420000,
        is_published: true
      },
      {
        id: 2,
        title: "Classroom Code & Workshop Starter Kit",
        original_filename: "flashnova_workshop_kit.zip",
        file_type: "ZIP",
        file_size: 3840000,
        is_published: true
      }
    ];

    const defaultAttendanceRecords = [
      { masked_enrollment: "2026****** (#1)", status: "Present", qr_scanned_at: new Date(Date.now() - 1200000).toISOString() },
      { masked_enrollment: "2026****** (#2)", status: "Present", qr_scanned_at: new Date(Date.now() - 1100000).toISOString() },
      { masked_enrollment: "1928******", status: "In Progress", qr_scanned_at: new Date(Date.now() - 900000).toISOString() },
      { masked_enrollment: "4532******", status: "Present", qr_scanned_at: new Date(Date.now() - 850000).toISOString() },
      { masked_enrollment: "8821******", status: "Pending Verification", qr_scanned_at: new Date(Date.now() - 600000).toISOString() }
    ];

    localStorage.setItem("fn_classrooms", JSON.stringify(defaultClassrooms));
    localStorage.setItem("fn_questions", JSON.stringify(defaultQuestions));
    localStorage.setItem("fn_doubts", JSON.stringify(defaultDoubts));
    localStorage.setItem("fn_files", JSON.stringify(defaultFiles));
    localStorage.setItem("fn_records", JSON.stringify(defaultAttendanceRecords));
    localStorage.setItem("fn_demo_init", "true");
  }
}

// Smart Offline / Mock Fallback when backend is unreachable
function handleOfflineMockResponse(endpoint, options) {
  initDemoData();

  let body = {};
  if (options.body && typeof options.body === "string") {
    try { body = JSON.parse(options.body); } catch(e) {}
  }

  // 1. Current Session (/api/auth/me)
  if (endpoint.includes("/api/auth/me")) {
    let user = localStorage.getItem("flashnova_user");
    if (user) {
      try { user = JSON.parse(user); } catch(e) {}
    }
    if (!user || typeof user !== "object") {
      user = {
        id: 999,
        name: "Anirudha Student",
        enrollment_no: "2026101234",
        role: "student",
        is_demo: true
      };
      localStorage.setItem("flashnova_user", JSON.stringify(user));
    }
    // Ensure teacher has authorized_subject if role is teacher
    if (user.role === "teacher" && !user.authorized_subject) {
      const storedSubj = localStorage.getItem("flashnova_subject");
      user.authorized_subject = storedSubj ? JSON.parse(storedSubj) : { name: "Mathematics", code: "MAT121" };
    }
    return { success: true, user: user };
  }

  // 2. Student Registration (/api/auth/student/register)
  if (endpoint.includes("/api/auth/student/register")) {
    const user = {
      id: 999,
      name: body.name || "Demo Student",
      enrollment_no: body.enrollment_no || "2026101234",
      role: "student",
      is_demo: true
    };
    localStorage.setItem("flashnova_token", "demo_token_student");
    localStorage.setItem("flashnova_user", JSON.stringify(user));
    showToast("Server offline: Activated Hackathon Demo Mode!", "info");
    return {
      success: true,
      message: "Student registered in Demo Mode",
      token: "demo_token_student",
      user: user
    };
  }

  // 3. Student Login (/api/auth/student/login)
  if (endpoint.includes("/api/auth/student/login")) {
    let user = localStorage.getItem("flashnova_user");
    if (user) {
      try { user = JSON.parse(user); } catch(e) {}
    }
    if (!user || user.role !== "student") {
      user = {
        id: 999,
        name: "Demo Student",
        enrollment_no: body.enrollment_no || "2026101234",
        role: "student",
        is_demo: true
      };
      localStorage.setItem("flashnova_user", JSON.stringify(user));
    }
    localStorage.setItem("flashnova_token", "demo_token_student");
    showToast("Server offline: Logged in via Demo Mode", "info");
    return { success: true, token: "demo_token_student", user: user };
  }

  // 4. Teacher Registration (/api/auth/teacher/register)
  if (endpoint.includes("/api/auth/teacher/register")) {
    const user = {
      id: 888,
      name: body.name || "Prof. Alan Turing",
      username: body.username || "prof_turing",
      department: body.department || "Engineering",
      role: "teacher",
      is_demo: true
    };
    localStorage.setItem("flashnova_user", JSON.stringify(user));
    return { success: true, message: "Teacher account registered in Demo Mode" };
  }

  // 5. Teacher Login (/api/auth/teacher/login)
  if (endpoint.includes("/api/auth/teacher/login")) {
    const user = {
      id: 888,
      name: "Prof. Alan Turing",
      username: body.username || "prof_turing",
      role: "teacher",
      is_demo: true,
      authorized_subject: { name: "Mathematics", code: "MAT121" }
    };
    localStorage.setItem("flashnova_token", "demo_token_teacher");
    localStorage.setItem("flashnova_user", JSON.stringify(user));
    return { success: true, token: "demo_token_teacher", user: user };
  }

  // 6. Teacher Subject Verification (/api/auth/teacher/verify-subject)
  if (endpoint.includes("/api/auth/teacher/verify-subject")) {
    const code = (body.subject_code || "MAT121").toUpperCase();
    const names = { MAT121: "Mathematics", CHM131: "Chemistry", WSP111: "Workshop" };
    const subject = { name: names[code] || "Engineering Sciences", code: code };
    
    localStorage.setItem("flashnova_subject", JSON.stringify(subject));
    let user = localStorage.getItem("flashnova_user");
    if (user) {
      try {
        user = JSON.parse(user);
        user.authorized_subject = subject;
        localStorage.setItem("flashnova_user", JSON.stringify(user));
      } catch(e) {}
    }
    return { success: true, message: "Access code verified!", subject: subject };
  }

  // 7. Logout (/api/auth/logout)
  if (endpoint.includes("/api/auth/logout")) {
    localStorage.removeItem("flashnova_token");
    localStorage.removeItem("flashnova_user");
    localStorage.removeItem("flashnova_subject");
    return { success: true, message: "Logged out" };
  }

  // 8. Teacher Classrooms (/api/teacher/classrooms)
  if (endpoint.includes("/api/teacher/classrooms")) {
    let classrooms = JSON.parse(localStorage.getItem("fn_classrooms") || "[]");

    // POST /api/teacher/classrooms
    if (options.method === "POST" && !endpoint.includes("toggle-auto-enroll")) {
      const newClassroom = {
        id: Date.now(),
        name: body.name || "New Classroom",
        code: "CLS" + Math.floor(100 + Math.random() * 900),
        student_count: 0,
        allow_qr_auto_enroll: Boolean(body.allow_qr_auto_enroll),
        active_lecture: null
      };
      classrooms.unshift(newClassroom);
      localStorage.setItem("fn_classrooms", JSON.stringify(classrooms));
      return { success: true, classroom: newClassroom };
    }

    // POST /api/teacher/classrooms/:id/toggle-auto-enroll
    if (endpoint.includes("toggle-auto-enroll")) {
      const parts = endpoint.split("/");
      const cid = parseInt(parts[parts.indexOf("classrooms") + 1]);
      const cls = classrooms.find(c => c.id === cid);
      if (cls) {
        cls.allow_qr_auto_enroll = !cls.allow_qr_auto_enroll;
        localStorage.setItem("fn_classrooms", JSON.stringify(classrooms));
        return { success: true, message: `Auto-enrollment ${cls.allow_qr_auto_enroll ? 'ENABLED' : 'DISABLED'}` };
      }
      return { success: true, message: "Auto-enrollment toggled" };
    }

    // GET /api/teacher/classrooms
    return { success: true, classrooms: classrooms };
  }

  // 9. Teacher Start / Stop Lecture (/api/teacher/lectures/start, /stop)
  if (endpoint.includes("/api/teacher/lectures/start")) {
    const classrooms = JSON.parse(localStorage.getItem("fn_classrooms") || "[]");
    const lec = {
      id: Date.now(),
      topic: body.topic || "Advanced Calculus & Real-Time Limits",
      classroom_name: "Room 401 - Innovation Lab",
      subject_name: "Mathematics",
      subject_code: "MAT121",
      is_active: true
    };
    if (classrooms.length > 0) {
      classrooms[0].active_lecture = lec;
      localStorage.setItem("fn_classrooms", JSON.stringify(classrooms));
    }
    return { success: true, lecture: lec };
  }

  if (endpoint.includes("/stop")) {
    const classrooms = JSON.parse(localStorage.getItem("fn_classrooms") || "[]");
    classrooms.forEach(c => { c.active_lecture = null; });
    localStorage.setItem("fn_classrooms", JSON.stringify(classrooms));
    return { success: true, message: "Lecture ended successfully." };
  }

  // 10. Dynamic Rotating QR Token (/api/teacher/lectures/:id/qr)
  if (endpoint.includes("/qr")) {
    const token = "FN-" + Math.random().toString(16).substring(2, 10).toUpperCase();
    localStorage.setItem("fn_current_qr_token", token);
    return { success: true, token: token, expires_in: 10 };
  }

  // 11. Teacher Analytics (/api/analytics/lecture/:id)
  if (endpoint.includes("/api/analytics/lecture")) {
    const records = JSON.parse(localStorage.getItem("fn_records") || "[]");
    return {
      success: true,
      confusion_stats: {
        understand: { count: 24, percentage: 67 },
        doubt: { count: 8, percentage: 22 },
        dont_understand: { count: 4, percentage: 11 },
        no_response: { count: 0, percentage: 0 }
      },
      attendance_summary: {
        total_eligible: 36,
        joined_count: 32,
        present_count: 27,
        in_progress_count: 4,
        pending_verif_count: 1,
        not_marked_count: 4,
        attendance_rate: 89,
        records: records
      },
      topic_confusion: {
        "Limits & Continuity": { understand: 24, doubt: 6, dont_understand: 2 },
        "Derivatives & Rates": { understand: 18, doubt: 9, dont_understand: 5 },
        "Integral Approximations": { understand: 14, doubt: 12, dont_understand: 6 }
      }
    };
  }

  // 12. Doubts (/api/teacher/doubts, /api/student/doubts)
  if (endpoint.includes("/doubts")) {
    let doubts = JSON.parse(localStorage.getItem("fn_doubts") || "[]");

    // Reply to doubt: POST /api/teacher/doubts/:id/reply
    if (endpoint.includes("/reply")) {
      const parts = endpoint.split("/");
      const did = parseInt(parts[parts.indexOf("doubts") + 1]);
      const target = doubts.find(d => d.id === did);
      if (target) {
        target.status = body.status || "Resolved";
        target.replies = target.replies || [];
        target.replies.push({
          teacher_name: "Prof. Alan Turing",
          reply_text: body.reply_text || "Thank you for asking. Concept explained.",
          created_at: new Date().toISOString()
        });
        localStorage.setItem("fn_doubts", JSON.stringify(doubts));
      }
      return { success: true, message: "Reply sent to student dashboard!" };
    }

    // Student volunteer doubt: POST /api/student/doubts/volunteer
    if (endpoint.includes("volunteer")) {
      const user = JSON.parse(localStorage.getItem("flashnova_user") || "{}");
      const newDoubt = {
        id: Date.now(),
        student_name: user.name || "Anirudha Student",
        student_enrollment_no: user.enrollment_no || "2026101234",
        topic: body.topic || "General Concept",
        doubt_text: body.doubt_text || "Could you please elaborate on this topic?",
        status: "Pending",
        created_at: new Date().toISOString(),
        replies: []
      };
      doubts.unshift(newDoubt);
      localStorage.setItem("fn_doubts", JSON.stringify(doubts));
      return { success: true, message: "Doubt submitted with identity consent!" };
    }

    return { success: true, doubts: doubts };
  }

  // 13. Questions (/api/teacher/questions, /api/student/questions)
  if (endpoint.includes("/questions")) {
    let questions = JSON.parse(localStorage.getItem("fn_questions") || "[]");

    // Submit student answer: POST /api/student/questions/:id/submit
    if (endpoint.includes("/submit")) {
      const parts = endpoint.split("/");
      const qid = parseInt(parts[parts.indexOf("questions") + 1]);
      const target = questions.find(q => q.id === qid);
      const isCorrect = target ? (body.selected_option === target.correct_answer) : true;
      if (target) {
        target.has_attempted = true;
        target.selected_option = body.selected_option;
        target.is_correct = isCorrect;
        localStorage.setItem("fn_questions", JSON.stringify(questions));
      }
      localStorage.setItem("demo_attendance_status", "Present");
      return { success: true, is_correct: isCorrect, attendance_status: "Present" };
    }

    // Toggle reveal: POST /api/teacher/questions/:id/toggle-reveal
    if (endpoint.includes("toggle-reveal")) {
      const parts = endpoint.split("/");
      const qid = parseInt(parts[parts.indexOf("questions") + 1]);
      const target = questions.find(q => q.id === qid);
      if (target) {
        target.reveal_answer = !target.reveal_answer;
        localStorage.setItem("fn_questions", JSON.stringify(questions));
      }
      return { success: true, message: "Answer reveal toggled" };
    }

    // Delete question: DELETE /api/teacher/questions/:id
    if (options.method === "DELETE") {
      const parts = endpoint.split("/");
      const qid = parseInt(parts[parts.length - 1]);
      questions = questions.filter(q => q.id !== qid);
      localStorage.setItem("fn_questions", JSON.stringify(questions));
      return { success: true, message: "Question deleted" };
    }

    // Create question: POST /api/teacher/questions
    if (options.method === "POST") {
      const opts = body.options || {};
      const newQ = {
        id: Date.now(),
        classroom_id: body.classroom_id || 101,
        topic: body.topic || "Calculus",
        question_text: body.question_text || "New Question",
        difficulty: body.difficulty || "Medium",
        is_compulsory: Boolean(body.is_compulsory),
        correct_answer: body.correct_answer || "A",
        reveal_answer: false,
        has_attempted: false,
        selected_option: null,
        is_correct: null,
        options: [
          { key: "A", text: opts.A || "Option A" },
          { key: "B", text: opts.B || "Option B" },
          { key: "C", text: opts.C || "Option C" },
          { key: "D", text: opts.D || "Option D" }
        ]
      };
      questions.unshift(newQ);
      localStorage.setItem("fn_questions", JSON.stringify(questions));
      return { success: true, question: newQ };
    }

    return { success: true, questions: questions };
  }

  // 14. Files (/api/teacher/files, /api/student/files)
  if (endpoint.includes("/files")) {
    let files = JSON.parse(localStorage.getItem("fn_files") || "[]");

    if (options.method === "POST") {
      const newFile = {
        id: Date.now(),
        title: "Lecture Slides - Real-Time Limits",
        original_filename: "lecture_slides.pdf",
        file_type: "PDF",
        file_size: 2100000,
        is_published: true
      };
      files.unshift(newFile);
      localStorage.setItem("fn_files", JSON.stringify(files));
      return { success: true, file: newFile };
    }

    return { success: true, files: files };
  }

  // 15. Student Dashboard (/api/student/dashboard)
  if (endpoint.includes("/api/student/dashboard")) {
    const classrooms = JSON.parse(localStorage.getItem("fn_classrooms") || "[]");
    let activeLec = classrooms.length && classrooms[0].active_lecture 
      ? classrooms[0].active_lecture 
      : {
          id: 201,
          topic: "Advanced Calculus & Real-Time Limits",
          classroom_name: "Room 401 - Innovation Lab",
          subject_name: "Mathematics",
          subject_code: "MAT121",
          is_active: true
        };
    activeLec.attendance_status = localStorage.getItem("demo_attendance_status") || "Present";
    return { success: true, active_lecture: activeLec };
  }

  // 16. Student Understanding Radar feedback (/api/student/understanding)
  if (endpoint.includes("/understanding")) {
    const st = body.status || "UNDERSTAND";
    localStorage.setItem("fn_last_feedback", st);
    return {
      success: true,
      message: `Anonymous feedback '${st.replace('_', ' ')}' recorded on classroom radar!`
    };
  }

  // 17. Student QR Scan (/api/student/scan-qr)
  if (endpoint.includes("/scan-qr")) {
    localStorage.setItem("demo_attendance_status", "Present");
    return {
      success: true,
      lecture: { topic: "Advanced Calculus & Real-Time Limits" },
      attendance_status: "Present"
    };
  }

  // 18. Student Attendance History (/api/student/attendance)
  if (endpoint.includes("/api/student/attendance")) {
    return {
      success: true,
      attendance: [
        { topic: "Advanced Calculus & Real-Time Limits", classroom_name: "Room 401 - Innovation Lab", status: "Present", qr_scanned_at: new Date(Date.now() - 1800000).toISOString() },
        { topic: "Matrix Inversion & Gaussian Elimination", classroom_name: "Room 401 - Innovation Lab", status: "Present", qr_scanned_at: new Date(Date.now() - 86400000).toISOString() },
        { topic: "Differential Equations intro", classroom_name: "Room 401 - Innovation Lab", status: "Present", qr_scanned_at: new Date(Date.now() - 172800000).toISOString() }
      ]
    };
  }

  return {
    success: true,
    message: "Operation completed in Hackathon Demo Mode."
  };
}

// Setup Backend Settings Modal for easy configuration on GitHub Pages
function setupBackendConfigModal() {
  const btn = document.getElementById("btn-backend-settings");
  if (btn) {
    btn.addEventListener("click", () => {
      const currentUrl = localStorage.getItem("FLASHNOVA_BACKEND_URL") || window.FLASHNOVA_CONFIG.API_BASE;
      const newUrl = prompt("Enter FLASHNOVA Backend API URL (e.g. https://flashnova-backend.onrender.com):", currentUrl);
      if (newUrl !== null) {
        window.FLASHNOVA_CONFIG.setBackendUrl(newUrl);
      }
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  setupBackendConfigModal();
  
  // Close modals on clicking overlay backdrop
  document.querySelectorAll(".cyber-modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.classList.remove("active");
      }
    });
  });
});
