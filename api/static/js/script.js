// Check authentication on load
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('access_token');
    const username = localStorage.getItem('username');
    if (!token && window.location.pathname !== '/auth') {
        window.location.href = '/auth';
        return;
    }

    const userDisplay = document.getElementById('user-display');
    const isAdmin = localStorage.getItem('is_admin') === 'true';
    const adminBtn = document.getElementById('admin-btn');

    if (userDisplay && username) {
        userDisplay.textContent = `👤 ${username}`;
    }
    if (adminBtn && isAdmin) {
        adminBtn.style.display = 'block';
    }
});

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('api_key');
    localStorage.removeItem('username');
    localStorage.removeItem('is_admin');
    window.location.href = '/auth';
}

function getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };
}

async function callSummarizeEndpoint() {
    showLoading(true);
    try {
        const title = document.getElementById('newsTitle').value.trim();
        const content = document.getElementById('newsContent').value.trim();

        if (!title || !content) {
            showResponse({ error: 'Por favor, completa el título y contenido de la noticia' }, true);
            return;
        }

        const response = await fetch('/api/summarize_news', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                title: title,
                content: content
            })
        });

        if (!response.ok) {
            if (response.status === 401) return logout();
            const errorData = await response.json();
            showResponse({ error: `Error ${response.status}: ${errorData.detail || 'Error desconocido'}` }, true);
            return;
        }

        const data = await response.json();
        showResponse(data, false);
    } catch (error) {
        showResponse({ error: error.message }, true);
    }
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById('summarizer-section').style.display = 'none';
    document.getElementById('ingestor-section').style.display = 'none';
    document.getElementById('bulk-section').style.display = 'none';
    document.getElementById('search-section').style.display = 'none';
    document.getElementById('augment-section').style.display = 'none';

    if (tabName === 'summarizer') {
        document.querySelector('.tab-btn:nth-child(1)').classList.add('active');
        document.getElementById('summarizer-section').style.display = 'block';
    } else if (tabName === 'ingestor') {
        document.querySelector('.tab-btn:nth-child(2)').classList.add('active');
        document.getElementById('ingestor-section').style.display = 'block';
    } else if (tabName === 'bulk') {
        document.querySelector('.tab-btn:nth-child(3)').classList.add('active');
        document.getElementById('bulk-section').style.display = 'block';
    } else if (tabName === 'search') {
        document.querySelector('.tab-btn:nth-child(4)').classList.add('active');
        document.getElementById('search-section').style.display = 'block';
    } else {
        document.querySelector('.tab-btn:nth-child(5)').classList.add('active');
        document.getElementById('augment-section').style.display = 'block';
    }
    clearResponse();
}

async function callIngestEndpoint() {
    showLoading(true);
    try {
        const jsonText = document.getElementById('ticketJson').value.trim();
        if (!jsonText) {
            showResponse({ error: 'Por favor, ingresa el JSON del ticket' }, true);
            return;
        }

        let ticketData = JSON.parse(jsonText);
        const response = await fetch('/api/ingest_json_ticket', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(ticketData)
        });

        if (!response.ok) {
            if (response.status === 401) return logout();
            const errorData = await response.json();
            showResponse({ error: `Error ${response.status}: ${errorData.detail || 'Error desconocido'}` }, true);
            return;
        }

        const data = await response.json();
        showResponse({ message: data }, false);
    } catch (error) {
        showResponse({ error: error.message }, true);
    }
}

async function callBulkIngestEndpoint() {
    showLoading(true);
    try {
        const fileInput = document.getElementById('jsonFile');
        const file = fileInput.files[0];

        if (!file) {
            showResponse({ error: 'Por favor, selecciona un archivo JSON' }, true);
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/ingest_json_file', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });

        if (!response.ok) {
            if (response.status === 401) return logout();
            const errorData = await response.json();
            showResponse({ error: `Error ${response.status}: ${errorData.detail || 'Error desconocido'}` }, true);
            return;
        }

        const data = await response.json();
        showResponse({ message: data.message }, false);
    } catch (error) {
        showResponse({ error: error.message }, true);
    }
}

async function callGetSimilarTicketsEndpoint() {
    showLoading(true);
    try {
        const jsonText = document.getElementById('ticketJsonSearch').value.trim();
        if (!jsonText) {
            showResponse({ error: 'Por favor, ingresa el JSON del ticket' }, true);
            return;
        }

        let ticketData = JSON.parse(jsonText);
        const response = await fetch('/api/get_similar_tickets', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(ticketData)
        });

        if (!response.ok) {
            if (response.status === 401) return logout();
            const errorData = await response.json();
            showResponse({ error: `Error ${response.status}: ${errorData.detail || 'Error desconocido'}` }, true);
            return;
        }

        const data = await response.json();
        showResponse(data, false);
    } catch (error) {
        showResponse({ error: error.message }, true);
    }
}

async function callAugmentEndpoint() {
    showLoading(true);
    try {
        const jsonText = document.getElementById('ticketJsonAugment').value.trim();
        if (!jsonText) {
            showResponse({ error: 'Por favor, ingresa el JSON del ticket' }, true);
            return;
        }

        let ticketData = JSON.parse(jsonText);
        const response = await fetch('/api/augment_ticket_information', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(ticketData)
        });

        if (!response.ok) {
            if (response.status === 401) return logout();
            const errorData = await response.json();
            showResponse({ error: `Error ${response.status}: ${errorData.detail || 'Error desconocido'}` }, true);
            return;
        }

        const data = await response.json();
        showResponse(data, false);
    } catch (error) {
        showResponse({ error: error.message }, true);
    }
}

function showResponse(data, isError = false) {
    showLoading(false);
    const box = document.getElementById('responseBox');
    const content = document.getElementById('responseContent');
    content.classList.remove('error', 'success');

    if (data.error || isError) {
        content.classList.add('error');
        content.textContent = `❌ Error: ${data.error}`;
    } else if (data.original_title) {
        content.classList.add('success');
        let formattedText = `📌 TÍTULO ORIGINAL:\n${data.original_title}\n\n`;
        formattedText += `📝 RESUMEN:\n${data.summary}\n\n`;
        if (Array.isArray(data.key_points) && data.key_points.length > 0) {
            formattedText += `🔑 PUNTOS CLAVE:\n`;
            data.key_points.forEach((point, index) => { formattedText += `   ${index + 1}. ${point}\n`; });
        }
        content.textContent = formattedText;
    } else if (data.resumen) {
        content.classList.add('success');
        let formattedText = `✨ CONSULTA AL ASISTENTE:\n\n`;
        formattedText += `📝 RESUMEN DE SOLUCIONES:\n${data.resumen}\n\n`;
        if (Array.isArray(data.contactos) && data.contactos.length > 0) {
            formattedText += `👥 CONTACTOS SUGERIDOS:\n`;
            data.contactos.forEach(contact => { formattedText += `   👤 ${contact}\n`; });
        }
        content.textContent = formattedText;
    } else if (data.message) {
        content.classList.add('success');
        content.textContent = `✅ Éxito: ${data.message}`;
    } else if (Array.isArray(data)) {
        content.classList.add('success');
        if (data.length === 0) {
            content.textContent = "🔍 No se encontraron tickets similares.";
        } else {
            let formattedText = `🔍 ENCONTRADOS ${data.length} TICKETS SIMILARES:\n\n`;
            data.forEach((ticket, index) => {
                formattedText += `--- TICKET #${index + 1} ---\n`;
                formattedText += `🆔 ID: ${ticket.ticketId}\n`;
                formattedText += `🚨 Prioridad: ${ticket.priority}\n`;
                formattedText += `📝 Descripción: ${ticket.description}\n\n`;
            });
            content.textContent = formattedText;
        }
    } else {
        content.classList.add('success');
        content.textContent = JSON.stringify(data, null, 2);
    }
    box.classList.add('active');
}

function showLoading(isLoading) {
    const loading = document.getElementById('loading');
    if (loading) isLoading ? loading.classList.add('active') : loading.classList.remove('active');
}

function clearResponse() {
    document.getElementById('responseBox').classList.remove('active');
    document.getElementById('responseContent').textContent = '';
    showLoading(false);
}
