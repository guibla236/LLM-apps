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
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                title: title,
                content: content
            })
        });

        if (!response.ok) {
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
    // Buttons
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));

    // Sections
    document.getElementById('summarizer-section').style.display = 'none';
    document.getElementById('ingestor-section').style.display = 'none';
    document.getElementById('bulk-section').style.display = 'none';
    document.getElementById('search-section').style.display = 'none';

    // Activate
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

    // Clear response box when switching
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

        let ticketData;
        try {
            ticketData = JSON.parse(jsonText);
        } catch (e) {
            showResponse({ error: 'Formato JSON inválido' }, true);
            return;
        }

        const response = await fetch('/api/ingest_json_ticket', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(ticketData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            showResponse({ error: `Error ${response.status}: ${errorData.detail || 'Error desconocido'}` }, true);
            return;
        }

        const data = await response.json();
        // The endpoint returns a string message, wrapping it in object for consistent display
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

        const response = await fetch('/api/ingest_json_file', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
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

        let ticketData;
        try {
            ticketData = JSON.parse(jsonText);
        } catch (e) {
            showResponse({ error: 'Formato JSON inválido' }, true);
            return;
        }

        const response = await fetch('/api/get_similar_tickets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(ticketData)
        });

        if (!response.ok) {
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

        let ticketData;
        try {
            ticketData = JSON.parse(jsonText);
        } catch (e) {
            showResponse({ error: 'Formato JSON inválido' }, true);
            return;
        }

        const response = await fetch('/api/augment_ticket_information', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(ticketData)
        });

        if (!response.ok) {
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

    // Limpiar clases anteriores
    content.classList.remove('error', 'success');

    if (data.error || isError) {
        content.classList.add('error');
        content.textContent = `❌ Error: ${data.error}`;
    } else if (data.original_title) {
        // News Summary response
        content.classList.add('success');
        let formattedText = `📌 TÍTULO ORIGINAL:\n${data.original_title}\n\n`;
        formattedText += `📝 RESUMEN:\n${data.summary}\n\n`;

        if (Array.isArray(data.key_points) && data.key_points.length > 0) {
            formattedText += `🔑 PUNTOS CLAVE:\n`;
            data.key_points.forEach((point, index) => {
                formattedText += `   ${index + 1}. ${point}\n`;
            });
        }

        formattedText += `\n\n📊 ESTADÍSTICAS:\n`;
        formattedText += `   • Caracteres en resumen: ${data.summary_length}\n\n`;

        content.textContent = formattedText;
    } else if (data.resumen) {
        // Assistant Response
        content.classList.add('success');
        let formattedText = `✨ CONSULTA AL ASISTENTE:\n\n`;
        formattedText += `📝 RESUMEN DE SOLUCIONES:\n${data.resumen}\n\n`;

        if (Array.isArray(data.contactos) && data.contactos.length > 0) {
            formattedText += `👥 CONTACTOS SUGERIDOS:\n`;
            data.contactos.forEach((contact, index) => {
                formattedText += `   👤 ${contact}\n`;
            });
        }

        content.textContent = formattedText;
    } else if (data.message) {
        // Ingestion success response (assuming strings come back as simple messages)
        content.classList.add('success');
        content.textContent = `✅ Éxito: ${data.message}`;
    } else if (Array.isArray(data)) {
        // List of tickets (Search result)
        content.classList.add('success');
        if (data.length === 0) {
            content.textContent = "🔍 No se encontraron tickets similares.";
        } else {
            let formattedText = `🔍 ENCONTRADOS ${data.length} TICKETS SIMILARES:\n\n`;
            data.forEach((ticket, index) => {
                formattedText += `--- TICKET #${index + 1} ---\n`;
                formattedText += `🆔 ID: ${ticket.ticketId}\n`;
                formattedText += `📌 Título: ${ticket.title}\n`;
                formattedText += `🚨 Prioridad: ${ticket.priority}\n`;
                formattedText += `📝 Descripción: ${ticket.description}\n`;
                formattedText += `\n`;
            });
            content.textContent = formattedText;
        }
    } else {
        // Fallback or generic JSON
        content.classList.add('success');
        content.textContent = JSON.stringify(data, null, 2);
    }

    box.classList.add('active');
}

function showLoading(isLoading) {
    const loading = document.getElementById('loading');
    if (isLoading) {
        loading.classList.add('active');
    } else {
        loading.classList.remove('active');
    }
}

function clearResponse() {
    document.getElementById('responseBox').classList.remove('active');
    document.getElementById('responseContent').textContent = '';
    document.getElementById('responseContent').classList.remove('error', 'success');

    // Clear inputs based on active section could be nice, but simple clear is fine
    const newsTitle = document.getElementById('newsTitle');
    const newsContent = document.getElementById('newsContent');
    const ticketJson = document.getElementById('ticketJson');

    if (newsTitle) newsTitle.value = '';
    if (newsContent) newsContent.value = '';
    if (ticketJson) ticketJson.value = '';

    const ticketJsonSearch = document.getElementById('ticketJsonSearch');
    if (ticketJsonSearch) ticketJsonSearch.value = '';

    const ticketJsonAugment = document.getElementById('ticketJsonAugment');
    if (ticketJsonAugment) ticketJsonAugment.value = '';

    const jsonFile = document.getElementById('jsonFile');
    if (jsonFile) jsonFile.value = '';

    showLoading(false);
}
