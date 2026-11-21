/**
 * FLASHNOVA - Futuristic Real-Time Chart.js Visualizations
 * Dark theme with neon cyan, electric purple, emerald, amber and coral accents
 */

let confusionChartInstance = null;
let attendanceChartInstance = null;
let topicChartInstance = null;

// Initialize or Update Confusion Doughnut Chart
function renderConfusionChart(canvasId, stats) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  if (confusionChartInstance) {
    confusionChartInstance.destroy();
  }

  const uCount = stats.understand ? stats.understand.count : 0;
  const dCount = stats.doubt ? stats.doubt.count : 0;
  const duCount = stats.dont_understand ? stats.dont_understand.count : 0;
  const nrCount = stats.no_response ? stats.no_response.count : 0;

  confusionChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Understand", "Have a Doubt", "Don't Understand", "No Feedback"],
      datasets: [{
        data: [uCount, dCount, duCount, nrCount],
        backgroundColor: [
          "#10b981", // Emerald
          "#f59e0b", // Amber
          "#ef4444", // Coral
          "#334155"  // Muted Slate
        ],
        borderColor: "#0a0f1d",
        borderWidth: 3,
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: "#94a3b8",
            font: { family: "'Space Grotesk', monospace", size: 12 },
            boxWidth: 14,
            padding: 15
          }
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              const val = context.raw || 0;
              const total = uCount + dCount + duCount + nrCount;
              const pct = total > 0 ? Math.round((val / total) * 100) : 0;
              return ` ${context.label}: ${val} (${pct}%)`;
            }
          }
        }
      },
      cutout: "68%"
    }
  });
}

// Initialize or Update Attendance Chart
function renderAttendanceChart(canvasId, summary) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  if (attendanceChartInstance) {
    attendanceChartInstance.destroy();
  }

  const present = summary.present_count || 0;
  const inProgress = summary.in_progress_count || 0;
  const pending = summary.pending_verif_count || 0;
  const notMarked = summary.not_marked_count || 0;

  attendanceChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Present", "In Progress", "Pending Verif", "Not Marked"],
      datasets: [{
        data: [present, inProgress, pending, notMarked],
        backgroundColor: [
          "#00f2fe", // Neon Cyan
          "#8b5cf6", // Electric Violet
          "#f59e0b", // Amber
          "#1e293b"  // Slate
        ],
        borderColor: "#0a0f1d",
        borderWidth: 3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: "#94a3b8",
            font: { family: "'Space Grotesk', monospace", size: 12 },
            boxWidth: 14,
            padding: 15
          }
        }
      },
      cutout: "68%"
    }
  });
}

// Initialize or Update Topic Confusion Horizontal Bar Chart
function renderTopicConfusionChart(canvasId, topicData) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  if (topicChartInstance) {
    topicChartInstance.destroy();
  }

  const topics = Object.keys(topicData || {});
  const understandData = [];
  const doubtData = [];
  const dontUnderstandData = [];

  topics.forEach(t => {
    const item = topicData[t];
    understandData.push(item.understand || 0);
    doubtData.push(item.doubt || 0);
    dontUnderstandData.push(item.dont_understand || 0);
  });

  topicChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: topics.length ? topics : ["No topic data"],
      datasets: [
        {
          label: "Understand",
          data: understandData.length ? understandData : [0],
          backgroundColor: "#10b981",
          borderRadius: 4
        },
        {
          label: "Doubt",
          data: doubtData.length ? doubtData : [0],
          backgroundColor: "#f59e0b",
          borderRadius: 4
        },
        {
          label: "Don't Understand",
          data: dontUnderstandData.length ? dontUnderstandData : [0],
          backgroundColor: "#ef4444",
          borderRadius: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          stacked: true,
          grid: { color: "rgba(56, 189, 248, 0.08)" },
          ticks: { color: "#94a3b8", font: { family: "'Space Grotesk', monospace" } }
        },
        y: {
          stacked: true,
          grid: { color: "rgba(56, 189, 248, 0.08)" },
          ticks: { color: "#94a3b8", font: { family: "'Space Grotesk', monospace" } }
        }
      },
      plugins: {
        legend: {
          position: "top",
          labels: { color: "#94a3b8", font: { family: "'Space Grotesk', monospace", size: 12 } }
        }
      }
    }
  });
}
