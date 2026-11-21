/**
 * FLASHNOVA - Client Configuration & API Resolution
 * Handles dynamic API routing between Localhost and GitHub Pages / Render deployment.
 */

(function () {
  const isLocal = window.location.hostname === "localhost" || 
                  window.location.hostname === "127.0.0.1" || 
                  window.location.protocol === "file:";

  // Default live backend URL
  const DEFAULT_RENDER_URL = "https://294133b52004c8.app.lhr.life";

  // Check saved override from localStorage or fallback
  let configuredUrl = localStorage.getItem("FLASHNOVA_BACKEND_URL");

  let apiBase = "";
  if (isLocal && window.location.port === "5000") {
    // Served directly by Flask local server
    apiBase = "";
  } else if (configuredUrl) {
    apiBase = configuredUrl.replace(/\/+$/, "");
  } else {
    // If on GitHub Pages, use default Render URL or relative if hosted together
    apiBase = isLocal ? "http://localhost:5000" : DEFAULT_RENDER_URL;
  }

  window.FLASHNOVA_CONFIG = {
    API_BASE: apiBase,
    IS_LOCAL: isLocal,
    getApiUrl: function (endpoint) {
      if (!endpoint.startsWith("/")) {
        endpoint = "/" + endpoint;
      }
      return (window.FLASHNOVA_CONFIG.API_BASE || "") + endpoint;
    },
    setBackendUrl: function (newUrl) {
      if (newUrl) {
        localStorage.setItem("FLASHNOVA_BACKEND_URL", newUrl.trim());
      } else {
        localStorage.removeItem("FLASHNOVA_BACKEND_URL");
      }
      window.location.reload();
    }
  };

  console.log("%c FLASHNOVA %c Connected to API: " + (apiBase || "Same-Origin"), 
    "background: #00f2fe; color: #060913; font-weight: bold; padding: 2px 6px; border-radius: 4px;", 
    "color: #38bdf8;");
})();
