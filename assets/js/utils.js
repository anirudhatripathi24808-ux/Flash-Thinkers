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
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("active");
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

// Smart Offline / Mock Fallback when backend is unreachable
function handleOfflineMockResponse(endpoint, options) {
  let body = {};
  if (options.body && typeof options.body === "string") {
    try { body = JSON.parse(options.body); } catch(e) {}
  }

  // 1. Student Registration
  if (endpoint.includes("/api/auth/student/register")) {
    const user = {
      id: 999,
      name: body.name || "Demo Student",
      enrollment_no: body.enrollment_no || "2026101234",
      role: "student",
      is_demo: true
    };
    localStorage.setItem("flashnova_token", "demo_token_offline");
    localStorage.setItem("flashnova_user", JSON.stringify(user));
    showToast("Server offline: Activated Hackathon Demo Mode!", "info");
    return {
      success: true,
      message: "Student registered in Demo Mode",
      token: "demo_token_offline",
      user: user
    };
  }

  // 2. Student Login
  if (endpoint.includes("/api/auth/student/login")) {
    let user = localStorage.getItem("flashnova_user");
    if (user) {
      try { user = JSON.parse(user); } catch(e) {}
    }
    if (!user || typeof user !== "object") {
      user = {
        id: 999,
        name: "Demo Student",
        enrollment_no: body.enrollment_no || "2026101234",
        role: "student",
        is_demo: true
      };
      localStorage.setItem("flashnova_user", JSON.stringify(user));
    }
    localStorage.setItem("flashnova_token", "demo_token_offline");
    showToast("Server offline: Logged in via Demo Mode", "info");
    return {
      success: true,
      token: "demo_token_offline",
      user: user
    };
  }

  // 3. Teacher Login / Register
  if (endpoint.includes("/api/auth/teacher/login") || endpoint.includes("/api/auth/teacher/register")) {
    const user = {
      id: 888,
      name: "Prof. Alan Turing",
      username: body.username || "prof_turing",
      role: "teacher",
      is_demo: true,
      verified_subjects: ["MAT121", "CHM131"]
    };
    localStorage.setItem("flashnova_token", "demo_teacher_token");
    localStorage.setItem("flashnova_user", JSON.stringify(user));
    showToast("Server offline: Logged in to Teacher Hub (Demo)", "info");
    return {
      success: true,
      token: "demo_teacher_token",
      user: user
    };
  }

  // 4. Current user session (/api/auth/me)
  if (endpoint.includes("/api/auth/me")) {
    const user = localStorage.getItem("flashnova_user");
    if (user) {
      try { return { success: true, user: JSON.parse(user) }; } catch(e) {}
    }
    return {
      success: true,
      user: {
        id: 999,
        name: "Demo Student",
        enrollment_no: "2026101234",
        role: "student",
        is_demo: true
      }
    };
  }

  // 5. Student Dashboard
  if (endpoint.includes("/api/student/dashboard")) {
    return {
      success: true,
      active_lecture: {
        id: 101,
        topic: "Advanced Calculus & Real-Time Limits",
        classroom_name: "Room 401 - Innovation Lab",
        subject_name: "Mathematics",
        subject_code: "MAT121",
        is_active: true,
        attendance_status: localStorage.getItem("demo_attendance_status") || "Present"
      }
    };
  }

  // 6. Student Understanding Radar feedback
  if (endpoint.includes("/api/student/feedback")) {
    return {
      success: true,
      message: "Anonymous feedback received and recorded in real time!"
    };
  }

  // 7. Student Volunteer Doubt Submission
  if (endpoint.includes("/api/student/volunteer-doubt")) {
    const doubts = JSON.parse(localStorage.getItem("demo_doubts") || "[]");
    doubts.unshift({
      id: Date.now(),
      topic: body.topic || "Calculus",
      question_text: body.question_text || body.doubt_text || "Concept clarification requested",
      status: "Pending",
      created_at: new Date().toLocaleTimeString(),
      teacher_reply: null
    });
    localStorage.setItem("demo_doubts", JSON.stringify(doubts));
    return {
      success: true,
      message: "Doubt successfully submitted to the teacher's radar!"
    };
  }

  // 8. Student Doubts list
  if (endpoint.includes("/api/student/doubts")) {
    const doubts = JSON.parse(localStorage.getItem("demo_doubts") || "[]");
    return {
      success: true,
      doubts: doubts
    };
  }

  // 9. QR Scan verification
  if (endpoint.includes("/api/student/scan-qr")) {
    localStorage.setItem("demo_attendance_status", "Present");
    return {
      success: true,
      message: "Dynamic cryptographic QR token accepted! Presence verified."
    };
  }

  // 10. Teacher Dashboard
  if (endpoint.includes("/api/teacher/dashboard")) {
    return {
      success: true,
      active_session: {
        id: 101,
        topic: "Advanced Calculus & Real-Time Limits",
        classroom_name: "Room 401 - Innovation Lab",
        subject_code: "MAT121",
        is_active: true
      },
      stats: {
        present_count: 28,
        in_progress_count: 4,
        total_enrolled: 32,
        confusion_index: 18.5
      }
    };
  }

  return {
    success: false,
    error: "Unable to reach server. Check network connection or backend URL in settings."
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
