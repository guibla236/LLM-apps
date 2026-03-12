const API_BASE = '/api';
const adminToken = localStorage.getItem('access_token');
const adminName = localStorage.getItem('username');

if (!adminToken) {
    window.location.href = '/auth';
}

document.getElementById('admin-name').textContent = adminName;

// Fetch initial data
async function initDashboard() {
    await loadFeatureFlags();
    await loadUsers();
    await loadLogs();
    await loadIPUsage();
    await loadRegistrations();
    await loadAgentExecutions();
}

async function fetchAdmin(url, options = {}) {
    const headers = {
        'Authorization': `Bearer ${adminToken}`,
        'Content-Type': 'application/json',
        ...options.headers
    };
    const response = await fetch(url, { ...options, headers });
    if (response.status === 403) {
        alert("Access Denied (admins only section).");
        window.location.href = '/';
        return;
    }
    return response;
}

// --- Feature Flags ---
async function loadFeatureFlags() {
    const response = await fetchAdmin(`${API_BASE}/admin/flags`);
    const flags = await response.json();
    const ingestionFlag = flags.find(f => f.name === 'block_ticket_ingestion');

    const btn = document.getElementById('toggle-ingestion');
    if (ingestionFlag && ingestionFlag.enabled) {
        btn.textContent = 'Enabled';
        btn.className = 'toggle-btn toggle-on';
    } else {
        btn.textContent = 'Disabled';
        btn.className = 'toggle-btn toggle-off';
    }
}

document.getElementById('toggle-ingestion').addEventListener('click', async () => {
    const isCurrentlyOn = document.getElementById('toggle-ingestion').classList.contains('toggle-on');
    const response = await fetchAdmin(`${API_BASE}/admin/flags/block_ticket_ingestion`, {
        method: 'POST',
        body: JSON.stringify({ enabled: !isCurrentlyOn })
    });
    if (response.ok) await loadFeatureFlags();
});

// --- Users ---
async function loadUsers() {
    const response = await fetchAdmin(`${API_BASE}/admin/users`);
    const users = await response.json();
    const tbody = document.querySelector('#users-table tbody');
    tbody.innerHTML = '';

    users.forEach(user => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${user.username}</td>
            <td>${user.daily_usage}</td>
            <td><input type="number" class="form-input" value="${user.quota_limit}" id="quota-${user.username}"></td>
            <td><button class="btn-save" onclick="updateQuota('${user.username}')">Save</button></td>
        `;
        tbody.appendChild(tr);
    });
}

async function updateQuota(username) {
    const newLimit = document.getElementById(`quota-${username}`).value;
    const response = await fetchAdmin(`${API_BASE}/admin/users/${username}/quota`, {
        method: 'POST',
        body: JSON.stringify({ quota_limit: parseInt(newLimit) })
    });
    if (response.ok) alert("Quota updated successfully.");
}

// --- Logs ---
async function loadLogs() {
    const response = await fetchAdmin(`${API_BASE}/admin/logs`);
    const logs = await response.json();
    const container = document.getElementById('logs-container');
    container.innerHTML = '';

    logs.forEach(log => {
        const div = document.createElement('div');
        div.className = 'log-item';
        div.innerHTML = `
            <div class="log-header">
                <span>${new Date(log.timestamp).toLocaleString()}</span>
                <span class="log-error-id">ID: ${log.error_id}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span><strong>${log.user}</strong>: ${log.error_message.substring(0, 50)}...</span>
                <button class="btn-view-more" onclick="showErrorDetail('${log.error_id}')">View Trace</button>
            </div>
        `;
        container.appendChild(div);
    });
}

let logsCache = []; // To store full logs for detail view
async function showErrorDetail(errorId) {
    const response = await fetchAdmin(`${API_BASE}/admin/logs/${errorId}`);
    const log = await response.json();

    document.getElementById('modal-date').textContent = new Date(log.timestamp).toLocaleString();
    document.getElementById('modal-user').textContent = log.user;
    document.getElementById('modal-path').textContent = `${log.method} ${log.path}`;
    document.getElementById('modal-trace').textContent = log.traceback;

    document.getElementById('modal-overlay').style.display = 'block';
    document.getElementById('error-modal').style.display = 'block';
}

function closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
    document.getElementById('error-modal').style.display = 'none';
}

// --- IP Usage ---
async function loadIPUsage() {
    const response = await fetchAdmin(`${API_BASE}/admin/ips`);
    const ips = await response.json();
    const tbody = document.querySelector('#ips-table tbody');
    tbody.innerHTML = '';

    ips.forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${item.last_ip}</td>
            <td>${item.count}</td>
        `;
        tbody.appendChild(tr);
    });
}

// --- Registrations ---
async function loadRegistrations() {
    const response = await fetchAdmin(`${API_BASE}/admin/registrations`);
    const regs = await response.json();
    const container = document.getElementById('registrations-container');
    container.innerHTML = '';

    regs.forEach(reg => {
        const div = document.createElement('div');
        div.className = 'log-item';
        div.innerHTML = `
            <div class="log-header">
                <span>${new Date(reg.timestamp).toLocaleString()}</span>
                <span style="color: var(--admin-success)">NEW</span>
            </div>
            <div>
                <strong>${reg.username}</strong> desde <small>${reg.ip}</small>
            </div>
        `;
        container.appendChild(div);
    });
}

// --- Agent Executions ---
async function loadAgentExecutions() {
    const response = await fetchAdmin(`${API_BASE}/admin/agent_executions`);
    const executions = await response.json();
    const tbody = document.querySelector('#agent-table tbody');
    tbody.innerHTML = '';

    executions.forEach(ex => {
        const tr = document.createElement('tr');
        const statusClass = ex.status === 'success' ? 'color: var(--admin-success)' : 'color: var(--admin-danger)';
        tr.innerHTML = `
            <td>${new Date(ex.timestamp).toLocaleString()}</td>
            <td>${ex.user}</td>
            <td>${ex.ticket_id}</td>
            <td style="${statusClass}">${ex.status.toUpperCase()}</td>
            <td>${ex.execution_time ? ex.execution_time + 's' : '-'}</td>
            <td><button class="btn-view-more" onclick="showAgentDetail('${ex._id}')">View Details</button></td>
        `;
        tbody.appendChild(tr);
        // Cache execution for detail view
        agentCache[ex._id] = ex;
    });
}

const agentCache = {};
function showAgentDetail(id) {
    const ex = agentCache[id];
    if (!ex) return;

    const durationText = ex.execution_time ? ` | Duration: ${ex.execution_time}s` : "";
    document.getElementById('modal-title').textContent = "Agent Proposed Solution";
    document.getElementById('modal-date').textContent = new Date(ex.timestamp).toLocaleString() + durationText;
    document.getElementById('modal-user').textContent = ex.user;
    document.getElementById('modal-path').textContent = `Ticket ID: ${ex.ticket_id}`;
    document.getElementById('modal-trace').textContent = ex.solution || ex.error_message;

    document.getElementById('modal-overlay').style.display = 'block';
    document.getElementById('error-modal').style.display = 'block';
}

// --- Evaluation Async System ---
let currentEvalTaskId = null;
let evalInterval = null;

async function startEvaluation() {
    const type = document.getElementById('eval-type').value;
    const goldenFile = document.getElementById('golden-file').files[0];
    const resultsFile = document.getElementById('results-file').files[0];

    if (!goldenFile || !resultsFile) {
        alert("Please upload both Golden Dataset and Results JSON files.");
        return;
    }

    const formData = new FormData();
    formData.append("system_type", type);
    formData.append("golden_file", goldenFile);
    formData.append("results_file", resultsFile);

    document.getElementById('eval-status-container').style.display = 'block';
    document.getElementById('eval-status-text').textContent = "Starting...";
    document.getElementById('eval-download-btn').style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/admin/evaluate/start?system_type=${type}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${adminToken}` },
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Upload failed");
        }

        const data = await response.json();
        currentEvalTaskId = data.task_id;
        
        // Empezar Polling cada 5 segundos
        if (evalInterval) clearInterval(evalInterval);
        evalInterval = setInterval(pollEvaluationStatus, 5000);
        
        document.getElementById('eval-status-text').textContent = "In Progress";
        document.getElementById('eval-status-text').style.color = "#fbbf24"; // Amarillo
        
    } catch (e) {
        alert("Evaluation Start Error: " + e.message);
        document.getElementById('eval-status-container').style.display = 'none';
    }
}

async function pollEvaluationStatus() {
    if (!currentEvalTaskId) return;

    try {
        const response = await fetchAdmin(`${API_BASE}/admin/evaluate/status/${currentEvalTaskId}`);
        if (!response.ok) return;
        
        const task = await response.json();
        
        document.getElementById('eval-progress').textContent = `(Question ${task.progress})`;

        if (task.status === "completed") {
            clearInterval(evalInterval);
            document.getElementById('eval-status-text').textContent = "Analysis Complete ✅";
            document.getElementById('eval-status-text').style.color = "var(--admin-success)";
            const dlBtn = document.getElementById('eval-download-btn');
            dlBtn.style.display = 'inline-block';
            dlBtn.onclick = () => {
                window.location.href = `${API_BASE}/admin/evaluate/download/${currentEvalTaskId}?token=${adminToken}`;
            }
        } else if (task.status === "failed") {
            clearInterval(evalInterval);
            document.getElementById('eval-status-text').textContent = "Failed ❌";
            document.getElementById('eval-status-text').style.color = "var(--admin-danger)";
            document.getElementById('eval-progress').textContent = `(${task.error})`;
        }

    } catch (e) {
        console.error("Polling error:", e);
    }
}


// Initialize
initDashboard();
