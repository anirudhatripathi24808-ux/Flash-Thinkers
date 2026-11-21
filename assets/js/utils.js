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
    console.error("API Request failed:", err);
    return {
      success: false,
      error: "Unable to reach server. Check network connection or backend URL in settings."
    };
  }
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
