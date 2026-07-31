/* ══════════════════════════════════════════════════════════════════════════════
   FRIDAY AI — pywebview JS↔Python Bridge
   Direct local operations without needing Flask/SocketIO.
   Falls through to REST API if bridge unavailable.
   ══════════════════════════════════════════════════════════════════════════════ */

const FridayBridge = (() => {
    const IS_BRIDGE = typeof window.pywebview !== 'undefined';
    const IS_FILE = window.location.protocol === 'file:';

    function _api(method, ...args) {
        if (IS_BRIDGE && window.pywebview.api && window.pywebview.api[method]) {
            try {
                const result = window.pywebview.api[method](...args);
                if (typeof result === 'string') {
                    try { return JSON.parse(result); } catch { return result; }
                }
                return result;
            } catch (e) {
                console.warn(`[Bridge] ${method} failed:`, e);
                return null;
            }
        }
        return null;
    }

    async function _rest(method, endpoint, body) {
        try {
            const opts = { method, headers: { 'Content-Type': 'application/json' } };
            if (body) opts.body = JSON.stringify(body);
            const r = await fetch(endpoint, opts);
            return await r.json();
        } catch { return null; }
    }

    async function _bridgeOrRest(bridgeMethod, restEndpoint, restBody) {
        const bResult = _api(bridgeMethod, ...(restBody ? [restBody] : []));
        if (bResult !== null) return bResult;
        return await _rest('POST', restEndpoint, restBody);
    }

    return {
        get isBridge() { return IS_BRIDGE; },
        get isFile() { return IS_FILE; },

        async getSystemStats() {
            return _bridgeOrRest('get_system_stats', '/api/status');
        },

        async runScene(name) {
            return _bridgeOrRest('run_scene', '/api/scenes/run', { scene: name });
        },

        async getScenes() {
            return _bridgeOrRest('get_scenes', '/api/scenes');
        },

        async getClipboard() {
            return _bridgeOrRest('get_clipboard', '/api/clipboard');
        },

        async copyClipboard(text) {
            return _bridgeOrRest('copy_clipboard', '/api/clipboard/copy', { text });
        },

        async openApp(name) {
            return _bridgeOrRest('open_app', '/api/chat', { text: `open ${name}` });
        },

        async setVolume(level) {
            return _bridgeOrRest('set_volume', '/api/chat', { text: `volume ${level}` });
        },

        async setBrightness(level) {
            return _bridgeOrRest('set_brightness', '/api/chat', { text: `brightness ${level}` });
        },

        async lockScreen() {
            return _bridgeOrRest('lock_screen', '/api/chat', { text: 'lock screen' });
        },

        async tileWindow(direction) {
            return _bridgeOrRest('tile_window', '/api/chat', { text: `tile ${direction}` });
        },

        async searchFiles(query) {
            return _bridgeOrRest('search_files', '/api/files');
        },

        async getOmniRouteStatus() {
            return _bridgeOrRest('get_omniroute_status', '/api/omniroute/status');
        },

        async getProactiveSuggestions() {
            return _bridgeOrRest('get_proactive_suggestions', '/api/proactive/data');
        },

        async getTasks() {
            return _bridgeOrRest('get_tasks', '/api/tasks');
        },

        async setOmniKey(key) {
            return _bridgeOrRest('set_omniroute_key', '/api/omniroute/key', { key });
        },

        async isOnline() {
            return _bridgeOrRest('is_online', '/api/health');
        },

        get frontmostApp() {
            return _api('get_frontmost_app') || 'Friday';
        },

        // ── Calendar ──
        async getCalendarEvents(days = 7) {
            return _bridgeOrRest('get_calendar_events', '/api/calendar/events?days=' + days);
        },

        async createCalendarEvent(title, startTime, duration = 30, location = '', notes = '') {
            const bResult = _api('create_calendar_event', title, startTime, String(duration), location, notes);
            if (bResult !== null) return bResult;
            return await _rest('POST', '/api/calendar/create', { title, start_time: startTime, duration, location, notes });
        },

        async deleteCalendarEvent(id) {
            return _bridgeOrRest('delete_calendar_event', '/api/calendar/delete', { id });
        },

        async syncCalendar() {
            return _bridgeOrRest('sync_calendar', '/api/calendar/sync', {});
        },

        async getTodayCalendar() {
            return _bridgeOrRest('get_today_calendar', '/api/calendar/today');
        },

        async parseCalendarNatural(text) {
            return _bridgeOrRest('parse_calendar_natural', '/api/chat', { text: 'add event ' + text });
        },

        // ── Music ──
        async getNowPlaying() {
            return _bridgeOrRest('get_now_playing', '/api/music/now');
        },

        async musicPlay() {
            return _bridgeOrRest('music_play', '/api/music/play', {});
        },

        async musicPause() {
            return _bridgeOrRest('music_pause', '/api/music/pause', {});
        },

        async musicNext() {
            return _bridgeOrRest('music_next', '/api/music/next', {});
        },

        async musicPrev() {
            return _bridgeOrRest('music_prev', '/api/music/prev', {});
        },

        async musicVolume(level) {
            return _bridgeOrRest('music_volume', '/api/music/volume', { level });
        },

        // ── Web Agent ──
        async webSearch(query) {
            const bResult = _api('web_search', query);
            if (bResult !== null) return bResult;
            return await _rest('POST', '/api/web/search', { query });
        },

        async webReadPage(url) {
            return _bridgeOrRest('web_read_page', '/api/web/read', { url });
        },

        // ── Vision ──
        async visionCapture() {
            return _bridgeOrRest('vision_capture', '/api/vision/capture', {});
        },

        async visionAnalyze(prompt) {
            const bResult = _api('vision_analyze', prompt || 'What do you see?');
            if (bResult !== null) return bResult;
            return await _rest('POST', '/api/vision/analyze', { prompt: prompt || 'What do you see?' });
        },

        async visionCaptureSelection() {
            return _bridgeOrRest('vision_capture_selection', '/api/vision/capture_selection', {});
        },

        // ── Notes ──
        async getNotes() {
            return _bridgeOrRest('get_notes_list', '/api/notes');
        },

        async createNote(title, body, folder = '') {
            const bResult = _api('create_note', title, body, folder);
            if (bResult !== null) return bResult;
            return await _rest('POST', '/api/notes/create', { title, body, folder });
        },

        async getAppleNotes() {
            return _bridgeOrRest('get_apple_notes', '/api/notes/apple');
        },

        // ── Email ──
        async getEmail() {
            return _bridgeOrRest('get_email', '/api/email');
        },

        // ── Git ──
        async gitStatus() {
            return _bridgeOrRest('git_status', '/api/git/status');
        },

        async gitLog() {
            return _bridgeOrRest('git_log', '/api/git/log');
        },

        async gitRun(command) {
            const bResult = _api('git_run', command);
            if (bResult !== null) return bResult;
            return await _rest('POST', '/api/git/run', { command });
        },

        async gitConfirm() {
            return _bridgeOrRest('git_confirm', '/api/git/confirm', {});
        },

        // ── Memory ──
        async memorySearch(query) {
            const bResult = _api('memory_search', query);
            if (bResult !== null) return bResult;
            return await _rest('GET', '/api/memory/search?q=' + encodeURIComponent(query));
        },

        async memoryNotes() {
            return _bridgeOrRest('memory_notes', '/api/memory/notes');
        },

        async memoryRead(path) {
            const bResult = _api('memory_read', path);
            if (bResult !== null) return bResult;
            return await _rest('GET', '/api/memory/read?file=' + encodeURIComponent(path));
        },

        async memoryWrite(filename, content) {
            const bResult = _api('memory_write', filename, content);
            if (bResult !== null) return bResult;
            return await _rest('POST', '/api/memory/write', { filename, content });
        },

        // ── Scheduler ──
        async schedulerList() {
            return _bridgeOrRest('scheduler_list', '/api/scheduler/tasks');
        },

        async schedulerCreate(name, description, triggerType, triggerValue, actionType, actionConfig) {
            const bResult = _api('scheduler_create', name, description, triggerType, triggerValue, actionType, JSON.stringify(actionConfig || {}));
            if (bResult !== null) return bResult;
            return await _rest('POST', '/api/scheduler/create', { name, description, trigger_type: triggerType, trigger_value: triggerValue, action_type: actionType, action_config: actionConfig });
        },

        async schedulerDelete(id) {
            const bResult = _api('scheduler_delete', id);
            if (bResult !== null) return bResult;
            return await _rest('POST', '/api/scheduler/delete', { id });
        },

        async schedulerToggle(id) {
            return _bridgeOrRest('scheduler_toggle', '/api/scheduler/toggle', { id });
        },
    };
})();
