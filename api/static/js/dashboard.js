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
        alert("No tienes permisos de administrador.");
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
        btn.textContent = 'Activado';
        btn.className = 'toggle-btn toggle-on';
    } else {
        btn.textContent = 'Desactivado';
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
            <td><button class="btn-save" onclick="updateQuota('${user.username}')">Guardar</button></td>
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
    if (response.ok) alert("Cuota actualizada");
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
                <button class="btn-view-more" onclick="showErrorDetail('${log.error_id}')">Ver Traza</button>
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
                <span style="color: var(--admin-success)">NUEVO</span>
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
            <td><button class="btn-view-more" onclick="showAgentDetail('${ex._id}')">Ver Solución</button></td>
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

    document.getElementById('modal-title').textContent = "Solución Propuesta por Agente";
    document.getElementById('modal-date').textContent = new Date(ex.timestamp).toLocaleString();
    document.getElementById('modal-user').textContent = ex.user;
    document.getElementById('modal-path').textContent = `Ticket ID: ${ex.ticket_id}`;
    document.getElementById('modal-trace').textContent = ex.solution || ex.error_message;

    document.getElementById('modal-overlay').style.display = 'block';
    document.getElementById('error-modal').style.display = 'block';
}

// Initialize
initDashboard();
