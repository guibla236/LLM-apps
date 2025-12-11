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
    } else {
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
    document.getElementById('newsTitle').value = '';
    document.getElementById('newsContent').value = '';
    showLoading(false);
}
