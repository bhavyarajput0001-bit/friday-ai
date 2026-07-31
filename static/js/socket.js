/* ══════════════════════════════════════════════════════════════════════════════
   FRIDAY AI — WebSocket Client (Socket.IO)
   ══════════════════════════════════════════════════════════════════════════════ */

const FridaySocket = (() => {
    let socket = null;
    const handlers = {};

    function connect() {
        socket = io({
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: Infinity,
        });

        socket.on('connect', () => {
            console.log('[WS] Connected to Friday server');
            _updateConnectionUI(true);
            _fire('connected');
        });

        socket.on('disconnect', (reason) => {
            console.log('[WS] Disconnected:', reason);
            _updateConnectionUI(false);
            _fire('disconnected', reason);
        });

        socket.on('connect_error', (err) => {
            console.warn('[WS] Connection error:', err.message);
            _updateConnectionUI(false);
        });

        // Register all server event listeners
        const events = [
            'system:stats',
            'conversation:message',
            'conversation:history',
            'voice:waveform',
            'voice:status',
            'browser:status',
            'config:state',
            'task:list',
            'agenda:list',
            'knowledge:data',
            'automation:list',
            'productivity:data',
            'now_playing:data',
            'files:data',
            'scene:status',
            'scenes:data',
            'clipboard:data',
            'clipboard:new_entry',
            'clipboard:snippet_saved',
            'clipboard:snippet',
            'clipboard:snippets_list',
            'clipboard:snippet_deleted',
            'proactive:data',
            'proactive:suggestion',
            'system:state',
            'calendar:events',
            'calendar:created',
            'calendar:deleted',
            'calendar:synced',
            'calendar:today',
            'music:now',
            'music:status',
            'music:volume',
            'web:results',
            'web:page',
            'vision:captured',
            'vision:analysis',
        ];

        events.forEach(evt => {
            socket.on(evt, (data) => _fire(evt, data));
        });
    }

    function emit(event, data) {
        if (socket && socket.connected) {
            socket.emit(event, data);
        } else {
            console.warn('[WS] Not connected, cannot emit:', event);
        }
    }

    function on(event, callback) {
        if (!handlers[event]) handlers[event] = [];
        handlers[event].push(callback);
    }

    function off(event, callback) {
        if (!handlers[event]) return;
        handlers[event] = handlers[event].filter(cb => cb !== callback);
    }

    function _fire(event, data) {
        (handlers[event] || []).forEach(cb => {
            try { cb(data); } catch (e) { console.error(`[WS] Handler error for ${event}:`, e); }
        });
    }

    function _updateConnectionUI(connected) {
        const dot = document.querySelector('.status-dot');
        const text = document.getElementById('sidebarStatusText');
        const sbNet = document.getElementById('sbNetwork');
        if (dot) {
            dot.style.background = connected ? 'var(--green)' : 'var(--danger)';
            dot.style.boxShadow = connected ? '0 0 8px var(--green)' : '0 0 8px var(--danger)';
        }
        if (text) {
            text.textContent = connected ? 'Online' : 'Offline';
            text.style.color = connected ? '' : 'var(--danger)';
        }
        if (sbNet) sbNet.textContent = connected ? 'Online' : 'Offline';
    }

    return { connect, emit, on, off };
})();
