const statusCard = document.getElementById("status-card");
const statusLabel = document.getElementById("status-label");
const totalTasks = document.getElementById("total-tasks");
const completedTasks = document.getElementById("completed-tasks");
const activeTasks = document.getElementById("active-tasks");
const logsText = document.getElementById("logs");
const loginBtn = document.getElementById("login-btn");
const bulkDownloadBtn = document.getElementById("bulk-download-btn");
const dateInput = document.getElementById("date-input");

function formatToday() {
  const today = new Date();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  return `${today.getFullYear()}-${month}-${day}`;
}

dateInput.value = dateInput.value || formatToday();

function fetchStatus() {
  fetch("/api/logs")
    .then((response) => response.json())
    .then((data) => {
      statusCard.textContent = data.status_card;
      statusLabel.textContent = data.status_label;
      totalTasks.textContent = data.total_tasks;
      completedTasks.textContent = data.completed_tasks;
      activeTasks.textContent = data.active_downloads;
      logsText.value = data.logs.join("\n");
      logsText.scrollTop = logsText.scrollHeight;
    })
    .catch((error) => console.error("Status error:", error));
}

function postJson(path, body) {
  return fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((response) => response.json());
}

loginBtn.addEventListener("click", () => {
  loginBtn.disabled = true;
  postJson("/api/login", {}).then((data) => {
    statusCard.textContent = data.status_card;
    appendLog(data.message);
    loginBtn.disabled = false;
  }).catch(() => {
    appendLog("AWS login failed.");
    loginBtn.disabled = false;
  });
});

bulkDownloadBtn.addEventListener("click", () => {
  const selected = Array.from(document.querySelectorAll(".loc-checkbox:checked")).map(
    (checkbox) => checkbox.dataset.loc
  );
  if (!selected.length) {
    appendLog("⚠ No location selected");
    return;
  }
  submitDownload(selected);
});

function submitDownload(locations) {
  bulkDownloadBtn.disabled = true;
  postJson("/api/download", {
    locations,
    date: dateInput.value,
  }).then((data) => {
    appendLog(data.message);
    bulkDownloadBtn.disabled = false;
  }).catch((error) => {
    appendLog("Download request failed.");
    bulkDownloadBtn.disabled = false;
    console.error(error);
  });
}

function appendLog(message) {
  const now = new Date();
  const timestamp = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  logsText.value += `[${timestamp}] ${message}\n`;
  logsText.scrollTop = logsText.scrollHeight;
}

document.querySelectorAll(".save-path-btn").forEach((button) => {
  button.addEventListener("click", () => {
    const location = button.dataset.loc;
    const field = document.getElementById(`path-${location}`);
    const path = field.value.trim();

    if (!path) {
      appendLog("⚠ Path is required.");
      return;
    }

    button.disabled = true;
    postJson("/api/save-path", { location, path }).then((data) => {
      appendLog(data.message);
      button.disabled = false;
    }).catch((error) => {
      appendLog("Failed to save path.");
      button.disabled = false;
      console.error(error);
    });
  });
});

document.querySelectorAll(".download-btn").forEach((button) => {
  button.addEventListener("click", () => {
    const location = button.dataset.loc;
    submitDownload([location]);
  });
});

document.querySelectorAll(".group-checkbox").forEach((checkbox) => {
  checkbox.addEventListener("change", () => {
    const group = checkbox.dataset.group;
    document.querySelectorAll(`.location-row[data-group='${group}'] .loc-checkbox`).forEach((child) => {
      child.checked = checkbox.checked;
    });
  });
});

setInterval(fetchStatus, 1200);
fetchStatus();
