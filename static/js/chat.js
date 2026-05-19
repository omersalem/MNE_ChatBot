(function() {
    const messagesEl = document.getElementById('messages');
    const form = document.getElementById('chat-form');
    const input = document.getElementById('message-input');
    const providerSelect = document.getElementById('provider-select');
    const questionsGrid = document.getElementById('questions-grid');
    const sendBtn = document.getElementById('send-btn');
    const sendText = document.getElementById('send-text');
    const sendSpinner = document.getElementById('send-spinner');

    let currentAiMessage = null;

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            form.dispatchEvent(new Event('submit'));
        }
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = input.value.trim();
        if (!message) return;

        input.value = '';
        input.style.height = 'auto';
        appendMessage('user', message);
        setLoading(true);

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN,
                },
                body: JSON.stringify({
                    message: message,
                    provider: providerSelect.value,
                }),
            });

            if (!response.ok) {
                const err = await response.json();
                appendMessage('ai', `Error: ${err.error || 'Request failed'}`);
                setLoading(false);
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullResponse = '';
            let buffer = '';

            const aiMsgEl = appendMessage('ai', '', true);

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6).trim();
                        if (data === '[DONE]') continue;
                        try {
                            const parsed = JSON.parse(data);
                            if (parsed.content) {
                                fullResponse += parsed.content;
                                aiMsgEl.querySelector('.message-content').innerHTML = renderMarkdown(fullResponse);
                                scrollToBottom();
                            }
                            if (parsed.sources) {
                                const sourcesDiv = aiMsgEl.querySelector('.sources');
                                if (sourcesDiv) {
                                    sourcesDiv.innerHTML = '<strong>Sources:</strong><br>' + parsed.sources.map(s => `${s.filename}`).join('<br>');
                                }
                            }
                        } catch (e) {
                        }
                    }
                }
            }

            setLoading(false);
            loadSuggestedQuestions();
        } catch (err) {
            appendMessage('ai', `Error: ${err.message}`);
            setLoading(false);
        }
    });

    function appendMessage(type, content, returnEl = false) {
        const div = document.createElement('div');
        div.className = `message ${type}`;
        div.innerHTML = `<div class="message-content">${renderMarkdown(content)}</div>`;
        
        if (type === 'ai') {
            div.innerHTML += '<div class="sources"></div>';
        }
        
        messagesEl.appendChild(div);
        scrollToBottom();
        return returnEl ? div : null;
    }

    function setLoading(loading) {
        sendBtn.disabled = loading;
        sendText.style.display = loading ? 'none' : 'inline';
        sendSpinner.style.display = loading ? 'inline-block' : 'none';
    }

    function scrollToBottom() {
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function renderMarkdown(text) {
        if (!text) return '';
        let html = text;
        html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
        html = html.replace(/\n/g, '<br>');
        return html;
    }

    async function loadSuggestedQuestions() {
        try {
            const res = await fetch('/api/suggested-questions');
            const data = await res.json();
            questionsGrid.innerHTML = '';
            if (data.questions && data.questions.length > 0) {
                data.questions.slice(0, 6).forEach(q => {
                    const card = document.createElement('div');
                    card.className = 'question-card';
                    card.textContent = q;
                    card.addEventListener('click', () => {
                        input.value = q;
                        form.dispatchEvent(new Event('submit'));
                    });
                    questionsGrid.appendChild(card);
                });
                document.getElementById('suggested-questions').style.display = 'block';
            } else {
                document.getElementById('suggested-questions').style.display = 'none';
            }
        } catch (err) {
            document.getElementById('suggested-questions').style.display = 'none';
        }
    }

    loadSuggestedQuestions();
})();
