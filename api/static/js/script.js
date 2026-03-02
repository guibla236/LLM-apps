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

    loadModels();
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
            showResponse({ error: 'Please fill the title and content of the news' }, true);
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
            showResponse({ error: `Error ${response.status}: ${errorData.detail || 'Unknown error'}` }, true);
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
    // document.getElementById('summarizer-section').style.display = 'none';
    document.getElementById('ingestor-section').style.display = 'none';
    document.getElementById('bulk-section').style.display = 'none';
    document.getElementById('kb-ingestor-section') && (document.getElementById('kb-ingestor-section').style.display = 'none');
    document.getElementById('kb-bulk-section') && (document.getElementById('kb-bulk-section').style.display = 'none');
    document.getElementById('search-section').style.display = 'none';
    document.getElementById('augment-section').style.display = 'none';

    // if (tabName === 'summarizer') {
    //     document.querySelector('.tab-btn:nth-child(1)').classList.add('active');
    //     document.getElementById('summarizer-section').style.display = 'block';
    // } else

    if (tabName === 'ingestor') {
        document.querySelector('.tab-btn:nth-child(1)').classList.add('active');
        document.getElementById('ingestor-section').style.display = 'block';
    } else if (tabName === 'bulk') {
        document.querySelector('.tab-btn:nth-child(2)').classList.add('active');
        document.getElementById('bulk-section').style.display = 'block';
    } else if (tabName === 'kb_ingestor') {
        document.querySelector('.tab-btn:nth-child(3)').classList.add('active');
        document.getElementById('kb-ingestor-section').style.display = 'block';
    } else if (tabName === 'kb_bulk') {
        document.querySelector('.tab-btn:nth-child(4)').classList.add('active');
        document.getElementById('kb-bulk-section').style.display = 'block';
    } else if (tabName === 'search') {
        document.querySelector('.tab-btn:nth-child(5)').classList.add('active');
        document.getElementById('search-section').style.display = 'block';
    } else {
        document.querySelector('.tab-btn:nth-child(6)').classList.add('active');
        document.getElementById('augment-section').style.display = 'block';
    }
    clearResponse();
}

async function callIngestEndpoint() {
    showLoading(true);
    try {
        const jsonText = document.getElementById('ticketJson').value.trim();
        if (!jsonText) {
            showResponse({ error: 'Please, enter the JSON of the ticket' }, true);
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
            showResponse({ error: `Error ${response.status}: ${errorData.detail || 'Unknown error'}` }, true);
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
            showResponse({ error: 'Please, select a JSON file' }, true);
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
            showResponse({ error: `Error ${response.status}: ${errorData.detail || 'Unknown error'}` }, true);
            return;
        }

        const data = await response.json();
        showResponse({ message: data.message }, false);
    } catch (error) {
        showResponse({ error: error.message }, true);
    }
}

async function callKBIngestEndpoint() {
    showLoading(true);
    try {
        const fileInput = document.getElementById('kbMdFile');
        const file = fileInput.files[0];

        if (!file) {
            showResponse({ error: 'Please, select a .md file' }, true);
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/ingest_kb_md', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });

        if (!response.ok) {
            if (response.status === 401) return logout();
            const errorData = await response.json();
            showResponse({ error: `Error ${response.status}: ${errorData.detail || 'Unknown error'}` }, true);
            return;
        }

        const data = await response.json();
        showResponse({ message: data.message || data }, false);
    } catch (error) {
        showResponse({ error: error.message }, true);
    }
}

async function callKBBulkIngestEndpoint() {
    showLoading(true);
    try {
        const fileInput = document.getElementById('kbZipFile');
        const file = fileInput.files[0];

        if (!file) {
            showResponse({ error: 'Please, select a ZIP file' }, true);
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/ingest_kb_zip', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });

        if (!response.ok) {
            if (response.status === 401) return logout();
            const errorData = await response.json();
            showResponse({ error: `Error ${response.status}: ${errorData.detail || 'Unknown error'}` }, true);
            return;
        }

        const data = await response.json();
        showResponse({ message: data.message || data }, false);
    } catch (error) {
        showResponse({ error: error.message }, true);
    }
}

async function callGetSimilarTicketsEndpoint() {
    showLoading(true);
    try {
        const jsonText = document.getElementById('ticketJsonSearch').value.trim();
        if (!jsonText) {
            showResponse({ error: 'Please, enter the JSON of the ticket' }, true);
            return;
        }

        let ticketData = JSON.parse(jsonText);
        const modelSel = document.getElementById('modelSelectSearch');
        if (modelSel) {
            ticketData.model_name = modelSel.value;
        }
        const response = await fetch('/api/get_similar_tickets', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(ticketData)
        });

        if (!response.ok) {
            if (response.status === 401) return logout();
            const errorData = await response.json();
            showResponse({ error: `Error ${response.status}: ${errorData.detail || 'Unknown error'}` }, true);
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
            showResponse({ error: 'Please, enter the JSON of the ticket' }, true);
            return;
        }

        let ticketData = JSON.parse(jsonText);
        const modelSel = document.getElementById('modelSelectAugment');
        if (modelSel) {
            ticketData.model_name = modelSel.value;
        }
        const response = await fetch('/api/augment_ticket_information', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(ticketData)
        });

        if (!response.ok) {
            if (response.status === 401) return logout();
            const errorData = await response.json();
            showResponse({ error: `Error ${response.status}: ${errorData.detail || 'Unknown error'}` }, true);
            return;
        }

        const data = await response.json();
        showResponse(data, false);
    } catch (error) {
        showResponse({ error: error.message }, true);
    }
}

async function loadModels() {
    try {
        const response = await fetch('/api/models', { headers: getAuthHeaders() });
        if (!response.ok) {
            if (response.status === 401) return logout();
            return;
        }
        const data = await response.json();
        // function to fill a given <select> element with options
        const populate = selectId => {
            const selectEl = document.getElementById(selectId);
            if (!selectEl) return;
            selectEl.innerHTML = '';

            let modelsArray = [];
            if (Array.isArray(data)) {
                modelsArray = data;
            } else if (data && Array.isArray(data.models)) {
                modelsArray = data.models;
            } else {
                console.warn('Unexpected /api/models response shape', data);
                return;
            }

            modelsArray.forEach(m => {
                const option = document.createElement('option');
                if (typeof m === 'string') {
                    option.value = m;
                    option.textContent = m;
                } else if (m && m.id) {
                    option.value = m.id;
                    option.textContent = m.name || m.id;
                } else {
                    option.value = String(m);
                    option.textContent = String(m);
                }
                selectEl.appendChild(option);
            });
        };

        // populate all selectors we care about
        populate('llmModelSelect');
        populate('modelSelectSearch');
        populate('modelSelectAugment');
    } catch (e) {
        console.warn('Could not load models:', e);
    }
}

async function callSupportAssistantEndpoint() {
    showLoading(true);
    try {
        const description = document.getElementById('consultDescription').value.trim();
        if (!description || description.length < 5) {
            showResponse({ error: 'Please enter a description of at least 5 characters.' }, true);
            return;
        }

        const searchType = document.getElementById('searchTypeSelect').value;
        const hybridSearch = document.getElementById('hybridSearchCheck').checked;
        const llmModel = document.getElementById('llmModelSelect')?.value;

        const payload = {
            description: description,
            search_type: searchType,
            hybrid_search: hybridSearch
        };
        if (llmModel) payload.model_name = llmModel;

        const response = await fetch('/api/augment_search_results', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            if (response.status === 401) return logout();
            const errorData = await response.json();
            showResponse({ error: `Error ${response.status}: ${errorData.detail || 'Unknown error'}` }, true);
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
        let formattedText = `📌 ORIGINAL TITLE:\n${data.original_title}\n\n`;
        formattedText += `📝 SUMMARY:\n${data.summary}\n\n`;
        if (Array.isArray(data.key_points) && data.key_points.length > 0) {
            formattedText += `🔑 KEY POINTS:\n`;
            data.key_points.forEach((point, index) => { formattedText += `   ${index + 1}. ${point}\n`; });
        }
        content.textContent = formattedText;
    } else if (data.answer) {
        content.classList.add('success');
        let formattedText = `✨ ASSISTANT QUERY:\n\n`;
        formattedText += `📝 SOLUTIONS SUMMARY:\n${data.answer}\n\n`;
        if (Array.isArray(data.contacts) && data.contacts.length > 0) {
            formattedText += `👥 SUGGESTED CONTACTS:\n`;
            data.contacts.forEach(contact => { formattedText += `   👤 ${contact}\n`; });
        }
        content.textContent = formattedText;
    } else if (data.message) {
        content.classList.add('success');
        content.textContent = `✅ Success: ${data.message}`;
    } else if (Array.isArray(data)) {
        content.classList.add('success');
        if (data.length === 0) {
            content.textContent = "🔍 No similar tickets found.";
        } else {
            let formattedText = `🔍 FOUND ${data.length} SIMILAR TICKETS:\n\n`;
            data.forEach((ticket, index) => {
                formattedText += `--- TICKET #${index + 1} ---\n`;
                formattedText += `🆔 ID: ${ticket.ticketId}\n`;
                formattedText += `🚨 Priority: ${ticket.priority}\n`;
                formattedText += `📝 Description: ${ticket.description}\n\n`;
            });
            content.textContent = formattedText;
        }
    } else if (data.summary) {
        content.classList.add('success');
        let formattedText = `🤖 SUPPORT ASSISTANT\n\n`;
        formattedText += `📝 SUMMARY:\n${data.summary}\n\n`;
        if (Array.isArray(data.suggested_actions) && data.suggested_actions.length > 0) {
            formattedText += `💡 SUGGESTED ACTIONS:\n`;
            data.suggested_actions.forEach((action, i) => { formattedText += `   ${i + 1}. ${action}\n`; });
            formattedText += '\n';
        }
        if (Array.isArray(data.contacts) && data.contacts.length > 0) {
            formattedText += `👥 CONTACTS:\n`;
            data.contacts.forEach(contact => { formattedText += `   👤 ${contact}\n`; });
            formattedText += '\n';
        }
        if (Array.isArray(data.ticket_references) && data.ticket_references.length > 0) {
            formattedText += `🎫 REFERENCED TICKETS: ${data.ticket_references.join(', ')}\n`;
        }
        if (Array.isArray(data.kb_references) && data.kb_references.length > 0) {
            formattedText += `📚 KB ARTICLES: ${data.kb_references.join(', ')}\n`;
        }
        content.textContent = formattedText;
    } else {
        content.classList.add('success');
        content.textContent = JSON.stringify(data, null, 2);
    }
    box.classList.add('active');
}

function showLoading(isLoading) {
    const loading = document.getElementById('loading');
    if (loading) isLoading ? loading.classList.add('active') : loading.classList.remove('active');

    // when a request starts we want to disable all form controls so the user
    // can't interact with the form until the response arrives. once loading
    // completes, controls are re‑enabled.
    toggleFormControls(isLoading);
}

// helper to enable/disable all inputs, selects, textareas and buttons in the
// UI. controls marked with the data-ignore-disable attribute will be skipped
// (logout button, admin panel, etc.).
function toggleFormControls(disabled) {
    document.querySelectorAll('input, textarea, select, button').forEach(el => {
        // skip elements that should remain active even while a request is pending
        if (el.dataset.ignoreDisable === 'true') {
            return;
        }
        el.disabled = disabled;
    });
}

function clearResponse() {
    document.getElementById('responseBox').classList.remove('active');
    document.getElementById('responseContent').textContent = '';
    showLoading(false);
}
