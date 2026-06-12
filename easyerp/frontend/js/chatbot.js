/**
 * chatbot.js - Widget de chatbot IA para EasyERP
 * Soporta ChatGPT, Gemini y modo Auto con respaldo
 */

const Chatbot = (() => {
    let isOpen = false;
    let isLoading = false;
    let history = [];
    let provider = 'auto';

    const PROVIDER_LABELS = {
        auto: 'Auto (respaldo)',
        gemini: 'Gemini',
        openai: 'ChatGPT',
    };

    function init() {
        const container = document.getElementById('chatbot-widget');
        if (!container) return;

        provider = localStorage.getItem('erp_chat_provider') || 'auto';

        try {
            const saved = sessionStorage.getItem('erp_chat_history');
            if (saved) history = JSON.parse(saved);
        } catch (e) { /* ignore */ }

        if (history.length > 0) {
            history.forEach(msg => _appendBubble(msg.role, msg.content, false));
            _scrollToBottom();
        }

        _initProviderSelect();

        document.getElementById('chatbot-toggle')?.addEventListener('click', toggle);
        document.getElementById('chatbot-close')?.addEventListener('click', close);
        document.getElementById('chat-send')?.addEventListener('click', sendMessage);
        document.getElementById('chat-input')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        document.addEventListener('click', (e) => {
            const widget = document.getElementById('chatbot-widget');
            const toggle = document.getElementById('chatbot-toggle');
            if (isOpen && widget && !widget.contains(e.target) && !toggle.contains(e.target)) {
                close();
            }
        });
    }

    function _initProviderSelect() {
        const select = document.getElementById('chat-provider');
        if (!select) return;

        select.value = provider;
        _updateProviderLabel();

        select.addEventListener('change', () => {
            provider = select.value;
            localStorage.setItem('erp_chat_provider', provider);
            _updateProviderLabel();
            _appendBubble(
                'assistant',
                `🔄 API cambiada a **${PROVIDER_LABELS[provider]}**. ${
                    provider === 'auto'
                        ? 'Si una API se queda sin tokens, usaré la otra automáticamente.'
                        : `Usaré solo ${PROVIDER_LABELS[provider]} hasta que lo cambies.`
                }`,
                true
            );
        });
    }

    function _updateProviderLabel(text) {
        const label = document.getElementById('chat-provider-label');
        if (label) {
            label.textContent = text || PROVIDER_LABELS[provider] || 'Auto';
        }
    }

    function toggle() {
        isOpen ? close() : open();
    }

    function open() {
        isOpen = true;
        const panel = document.getElementById('chatbot-panel');
        const toggleBtn = document.getElementById('chatbot-toggle');
        panel?.classList.add('open');
        toggleBtn?.classList.add('active');

        setTimeout(() => {
            document.getElementById('chat-input')?.focus();
        }, 300);

        if (history.length === 0) {
            _appendBubble(
                'assistant',
                '¡Hola! 👋 Soy el asistente IA de EasyERP. Puedo ayudarte con inventario, ventas, finanzas, compras y RRHH. Puedes cambiar entre **Gemini** y **ChatGPT** con el selector de arriba.',
                true
            );
        }
    }

    function close() {
        isOpen = false;
        const panel = document.getElementById('chatbot-panel');
        const toggleBtn = document.getElementById('chatbot-toggle');
        panel?.classList.remove('open');
        toggleBtn?.classList.remove('active');
    }

    async function sendMessage() {
        if (isLoading) return;

        const input = document.getElementById('chat-input');
        const message = input?.value?.trim();
        if (!message) return;

        input.value = '';
        input.style.height = 'auto';

        _appendBubble('user', message, true);
        _showTyping();

        isLoading = true;
        _updateSendButton();

        try {
            const token = localStorage.getItem('erp_token');
            const response = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    message: message,
                    provider: provider,
                    history: history.slice(-10).map(m => ({
                        role: m.role === 'assistant' ? 'model' : 'user',
                        content: m.content
                    }))
                })
            });

            _hideTyping();

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                throw new Error(data.error || `Error ${response.status}`);
            }

            const result = data?.data || {};
            let aiResponse = result.response || 'No se pudo obtener respuesta.';

            if (result.fallback && result.provider_label) {
                aiResponse += `\n\n_↪ Respondido con ${result.provider_label} (respaldo automático)_`;
                _updateProviderLabel(`${result.provider_label} · respaldo`);
            } else if (result.provider_label) {
                _updateProviderLabel(result.provider_label);
            }

            _appendBubble('assistant', aiResponse, true);

        } catch (err) {
            _hideTyping();
            _appendBubble(
                'assistant',
                `⚠️ ${err.message || 'Error de conexión. Verifica que el servidor esté corriendo.'}`,
                true
            );
        } finally {
            isLoading = false;
            _updateSendButton();
        }
    }

    function _appendBubble(role, content, save) {
        const messagesEl = document.getElementById('chat-messages');
        if (!messagesEl) return;

        const wrapper = document.createElement('div');
        wrapper.className = `chat-bubble-wrap ${role}`;

        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${role}`;
        bubble.innerHTML = _parseMarkdown(content);

        const time = document.createElement('span');
        time.className = 'chat-time';
        time.textContent = new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });

        wrapper.appendChild(bubble);
        wrapper.appendChild(time);
        messagesEl.appendChild(wrapper);

        requestAnimationFrame(() => wrapper.classList.add('visible'));
        _scrollToBottom();

        if (save) {
            history.push({ role, content });
            try {
                sessionStorage.setItem('erp_chat_history', JSON.stringify(history.slice(-30)));
            } catch (e) { /* storage full */ }
        }
    }

    function _parseMarkdown(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/`(.+?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    function _showTyping() {
        const messagesEl = document.getElementById('chat-messages');
        if (!messagesEl) return;

        const typing = document.createElement('div');
        typing.className = 'chat-typing';
        typing.id = 'chat-typing-indicator';
        typing.innerHTML = `
            <div class="typing-dots">
                <span></span><span></span><span></span>
            </div>
            <span class="typing-text">ERP Assistant está pensando...</span>
        `;
        messagesEl.appendChild(typing);
        requestAnimationFrame(() => typing.classList.add('visible'));
        _scrollToBottom();
    }

    function _hideTyping() {
        document.getElementById('chat-typing-indicator')?.remove();
    }

    function _scrollToBottom() {
        const messagesEl = document.getElementById('chat-messages');
        if (messagesEl) {
            setTimeout(() => {
                messagesEl.scrollTop = messagesEl.scrollHeight;
            }, 50);
        }
    }

    function _updateSendButton() {
        const btn = document.getElementById('chat-send');
        if (btn) {
            btn.disabled = isLoading;
            btn.classList.toggle('loading', isLoading);
        }
    }

    function clearHistory() {
        history = [];
        sessionStorage.removeItem('erp_chat_history');
        const messagesEl = document.getElementById('chat-messages');
        if (messagesEl) messagesEl.innerHTML = '';
        _appendBubble('assistant', '💬 Historial limpiado. ¿En qué te puedo ayudar?', true);
    }

    return { init, toggle, open, close, sendMessage, clearHistory };
})();

document.addEventListener('DOMContentLoaded', () => {
    if (localStorage.getItem('erp_token')) {
        Chatbot.init();
    }
});
