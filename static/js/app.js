/* ══════════════════════════════════════════════════════════════════════════════
   FRIDAY AI — Main Application Controller
   Clean modular UI: sidebar navigation + home dashboard + module views
   ══════════════════════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', () => {
        initClock();
        initModules();
        initNav();
        initBridgeData();
        initSocketEvents();
        initUIEvents();
        hideLoading();
    });

    // ══════════════════════════════════════════════════════════════════════
    //  CLOCK
    // ══════════════════════════════════════════════════════════════════════
    function initClock() {
        function update() {
            const now = new Date();
            const h = now.getHours();
            const m = String(now.getMinutes()).padStart(2, '0');
            const s = String(now.getSeconds()).padStart(2, '0');
            const ampm = h >= 12 ? 'PM' : 'AM';
            const h12 = h % 12 || 12;

            const clockEl = document.getElementById('sidebarClock');
            if (clockEl) clockEl.textContent = `${h12}:${m}:${s} ${ampm}`;
            const homeTime = document.getElementById('homeTime');
            if (homeTime) homeTime.textContent = `${h12}:${m}`;
            const homeDate = document.getElementById('homeDate');
            if (homeDate) homeDate.textContent = now.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
        }
        update();
        setInterval(update, 1000);
    }

    // ══════════════════════════════════════════════════════════════════════
    //  MODULES
    // ══════════════════════════════════════════════════════════════════════
    function initModules() {
        FridaySocket.connect();
        HUD.init();
        initAppearance();
    }

    // ══════════════════════════════════════════════════════════════════════
    //  HOLOGRAM PRESETS + COLOR THEMES
    // ══════════════════════════════════════════════════════════════════════
    const THEMES = [
        { id: 'cyan',    label: 'Cyan',    color: '#00d4ff' },
        { id: 'emerald', label: 'Emerald', color: '#00ff88' },
        { id: 'violet',  label: 'Violet',  color: '#b48aff' },
        { id: 'amber',   label: 'Amber',   color: '#ffb300' },
        { id: 'rose',    label: 'Rose',    color: '#ff5f8a' },
        { id: 'ice',     label: 'Ice',     color: '#7fd4ff' },
        { id: 'matrix',  label: 'Matrix',  color: '#00ff41' },
    ];
    const PRESET_ICONS = {
        core: '◎', arc: '◠', radar: '⌖', nebula: '✦',
        matrix: '▤', pulse: '◉',
    };

    function initAppearance() {
        const savedTheme = localStorage.getItem('friday_theme') || 'cyan';
        const savedPreset = localStorage.getItem('friday_preset') || 'core';

        _applyTheme(savedTheme);
        HUD.setPreset(savedPreset);
        _buildAppearanceUI(savedTheme, savedPreset);
    }

    function _buildAppearanceUI(activeTheme, activePreset) {
        const presetBox = document.getElementById('holoPresets');
        if (presetBox) {
            presetBox.innerHTML = '';
            Object.entries(HUD.getPresets()).forEach(([id, p]) => {
                const btn = document.createElement('button');
                btn.className = 'preset-btn' + (id === activePreset ? ' active' : '');
                btn.dataset.preset = id;
                btn.innerHTML = `<span class="preset-icon">${PRESET_ICONS[id] || '◎'}</span><span>${p.name}</span>`;
                btn.addEventListener('click', () => {
                    HUD.setPreset(id);
                    localStorage.setItem('friday_preset', id);
                    presetBox.querySelectorAll('.preset-btn').forEach(b => b.classList.toggle('active', b.dataset.preset === id));
                    _pushAppearanceMessage(`Hologram switched to ${p.name}`);
                });
                presetBox.appendChild(btn);
            });
        }

        const themeBox = document.getElementById('themeSwatches');
        if (themeBox) {
            themeBox.innerHTML = '';
            THEMES.forEach(t => {
                const btn = document.createElement('button');
                btn.className = 'theme-swatch' + (t.id === activeTheme ? ' active' : '');
                btn.dataset.theme = t.id;
                btn.innerHTML = `<span class="theme-dot" style="background:${t.color};box-shadow:0 0 8px ${t.color}"></span><span>${t.label}</span>`;
                btn.addEventListener('click', () => {
                    _applyTheme(t.id);
                    localStorage.setItem('friday_theme', t.id);
                    themeBox.querySelectorAll('.theme-swatch').forEach(b => b.classList.toggle('active', b.dataset.theme === t.id));
                    _pushAppearanceMessage(`Theme switched to ${t.label}`);
                });
                themeBox.appendChild(btn);
            });
        }
    }

    function _applyTheme(theme) {
        document.body.setAttribute('data-theme', theme === 'cyan' ? '' : theme);
    }

    function _pushAppearanceMessage(text) {
        Panels.addMessage({ sender: 'friday', text, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) });
    }

    // ══════════════════════════════════════════════════════════════════════
    //  NAVIGATION
    // ══════════════════════════════════════════════════════════════════════
    function initNav() {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                const view = item.dataset.view;
                switchView(view);
            });
        });
    }

    function switchView(view) {
        document.querySelectorAll('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.view === view));
        document.querySelectorAll('.view').forEach(v => v.classList.toggle('active', v.id === 'view-' + view));

        // Load view data on first visit
        if (view === 'calendar') { Panels.loadCalendarView(); }
        if (view === 'files') { Panels.loadFilesView(); }
        if (view === 'media') { Panels.loadMediaView(); }
        if (view === 'notes') { Panels.loadNotesView(); }
        if (view === 'memory') { Panels.loadMemoryView(); }
        if (view === 'git') { Panels.loadGitView(); }
        if (view === 'settings') { Panels.loadSettingsView(); }
        if (view === 'system') { Panels.loadSystemView(); }
    }

    // ══════════════════════════════════════════════════════════════════════
    //  BRIDGE DATA (offline-first)
    // ══════════════════════════════════════════════════════════════════════
    async function initBridgeData() {
        const loadingText = document.getElementById('loadingText');

        // System stats
        const stats = await FridayBridge.getSystemStats();
        if (stats && stats.cpu != null) {
            updateHomeHealth(stats);
            Panels.updateSystemStats(stats);
        }

        // Scenes
        const scenes = await FridayBridge.getScenes();
        if (scenes) Panels.renderScenes(scenes);

        // Calendar
        const todayCal = await FridayBridge.getTodayCalendar();
        if (todayCal && todayCal.events) Panels.renderCalendar(todayCal.events);
        const calEvents = await FridayBridge.getCalendarEvents(7);
        if (calEvents && calEvents.events) Panels.updateCalendarSyncStatus(calEvents.apple, calEvents.google);

        // Tasks
        const tasks = await FridayBridge.getTasks();
        if (tasks && tasks.tasks) {
            Panels.renderTasks(tasks.tasks);
            Panels.renderTasksMini(tasks.tasks);
        }

        // Music
        const track = await FridayBridge.getNowPlaying();
        if (track) updateHomeMusic(track);

        // OmniRoute status
        const omni = await FridayBridge.getOmniRouteStatus();
        const aiStatus = document.getElementById('aiStatusVal');
        if (aiStatus) aiStatus.textContent = (omni && omni.available) ? 'Online ✓' : 'Offline';

        if (loadingText) {
            if (omni && omni.available) loadingText.textContent = 'FRIDAY online — AI ready';
            else loadingText.textContent = 'Running offline — local only';
        }
    }

    // ══════════════════════════════════════════════════════════════════════
    //  HOME WIDGET UPDATES
    // ══════════════════════════════════════════════════════════════════════
    function updateHomeHealth(stats) {
        const setBar = (id, val) => {
            const el = document.getElementById(id);
            if (el) {
                el.style.width = Math.min(val, 100) + '%';
                el.style.background = val > 80 ? 'linear-gradient(90deg, var(--danger), var(--warning))' : 'linear-gradient(90deg, var(--accent), var(--green))';
            }
        };
        setBar('hCpuBar', stats.cpu);
        setBar('hMemBar', stats.mem_percent);
        setBar('hDiskBar', stats.disk_percent);
        const setVal = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
        setVal('hCpuVal', stats.cpu != null ? Math.round(stats.cpu) + '%' : '--');
        setVal('hMemVal', stats.mem_percent != null ? Math.round(stats.mem_percent) + '%' : '--');
        setVal('hDiskVal', stats.disk_percent != null ? Math.round(stats.disk_percent) + '%' : '--');
        setVal('batteryVal', stats.battery != null ? Math.round(stats.battery) + '%' : '--');
        setVal('sbBattery', stats.battery != null ? Math.round(stats.battery) + '%' : '--');
        setVal('sbCpu', stats.cpu != null ? Math.round(stats.cpu) + '%' : '--');

        // Health percentage
        const health = Math.max(0, Math.min(100, 100 - (stats.cpu || 0) * 0.4 - (stats.mem_percent || 0) * 0.4 - (stats.disk_percent || 0) * 0.2));
        setVal('macHealthPct', Math.round(health) + '%');
    }

    function updateHomeBluetooth(devices) {
        const container = document.getElementById('healthDevices');
        if (!container || !devices) return;
        if (devices.length === 0) {
            container.innerHTML = '<div class="device-item" style="color:var(--text-mute);font-size:11px">No audio devices detected</div>';
            return;
        }
        container.innerHTML = '';
        devices.forEach(d => {
            const div = document.createElement('div');
            div.className = 'device-item';
            div.innerHTML = `
                <span class="device-icon">🎧</span>
                <span class="device-name">${d.name}</span>
                <span class="device-status ${d.connected ? 'on' : 'off'}">${d.connected ? '● Connected' : '○'}</span>
            `;
            container.appendChild(div);
        });
    }

    function updateHomeMusic(track) {
        const titleEl = document.getElementById('musicTitle');
        const artistEl = document.getElementById('musicArtist');
        const artEl = document.getElementById('musicArt');
        const srcEl = document.getElementById('musicSource');
        const playBtn = document.getElementById('mcPlay');

        if (track && track.playing) {
            if (titleEl) titleEl.textContent = track.title || 'Unknown';
            if (artistEl) artistEl.textContent = track.artist || '';
            if (artEl && track.album_art) artEl.innerHTML = `<img src="${track.album_art}" alt="">`;
            if (srcEl) srcEl.textContent = track.source || '';
            if (playBtn) playBtn.textContent = '⏸';
        } else {
            if (titleEl) titleEl.textContent = 'Nothing playing';
            if (artistEl) artistEl.textContent = '—';
            if (artEl) artEl.innerHTML = '♪';
            if (srcEl) srcEl.textContent = '—';
            if (playBtn) playBtn.textContent = '▶';
        }
    }

    // ══════════════════════════════════════════════════════════════════════
    //  SOCKET EVENTS
    // ══════════════════════════════════════════════════════════════════════
    function initSocketEvents() {
        FridaySocket.on('system:stats', (stats) => {
            if (!stats) return;
            updateHomeHealth(stats);
            updateHomeBluetooth(stats.bluetooth);
            Panels.updateSystemStats(stats);
            Panels.updateHealth(stats);

            const setVal = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
            setVal('sysNetwork', stats.network || '--');
            setVal('sysBattery', stats.battery != null ? Math.round(stats.battery) + '%' : '--');
            setVal('sysUptime', stats.uptime ? formatUptime(stats.uptime) : '--');
            setVal('sysBt', stats.bluetooth ? stats.bluetooth.filter(d => d.connected).length + ' connected' : '--');
            setVal('sysCpuVal', stats.cpu != null ? Math.round(stats.cpu) + '%' : '--');
            setVal('sysMemVal', stats.mem_percent != null ? Math.round(stats.mem_percent) + '%' : '--');
            setVal('sysDiskVal', stats.disk_percent != null ? Math.round(stats.disk_percent) + '%' : '--');
            setVal('sysHealthVal', stats.health != null ? Math.round(stats.health) + '%' : '--');

            // Status bar
            const sbNet = document.getElementById('sbNetwork');
            if (sbNet) sbNet.textContent = stats.network || '--';
            const sbVol = document.getElementById('sbVolume');
            if (sbVol) sbVol.textContent = stats.volume != null ? Math.round(stats.volume) + '%' : '--';
        });

        FridaySocket.on('conversation:message', (msg) => {
            Panels.addMessage(msg);
        });

        FridaySocket.on('music:now', (track) => {
            updateHomeMusic(track);
            Panels.updateMediaMusic(track);
        });

        FridaySocket.on('scene:status', (data) => {
            Panels.updateSceneStatus(data.scene, data.status);
        });

        FridaySocket.on('clipboard:new_entry', (entry) => {
            Panels.addClipboardEntry(entry);
        });

        FridaySocket.on('calendar:events', (data) => {
            if (data && data.events) Panels.renderCalendar(data.events);
        });

        FridaySocket.on('task:list', (tasks) => {
            if (Array.isArray(tasks)) {
                Panels.renderTasks(tasks);
                Panels.renderTasksMini(tasks);
            }
        });

        FridaySocket.on('conversation:history', (messages) => {
            if (Array.isArray(messages) && messages.length > 0) Panels.loadConversationHistory(messages);
        });

        FridaySocket.on('config:state', (cfg) => {
            if (!cfg) return;
            const voiceSelect = document.getElementById('voiceSelect');
            if (voiceSelect && cfg.voice_index) {
                if (voiceSelect.querySelector('option[value="' + cfg.voice_index + '"]')) {
                    voiceSelect.value = cfg.voice_index;
                }
            }
            const speakOn = document.getElementById('speakOn');
            if (speakOn && cfg.speak_on != null) speakOn.checked = !!cfg.speak_on;
            const wakeWord = document.getElementById('wakeWord');
            if (wakeWord && cfg.wake_word) wakeWord.value = cfg.wake_word;
        });
    }

    function formatUptime(secs) {
        const h = Math.floor(secs / 3600);
        const m = Math.floor((secs % 3600) / 60);
        return h > 0 ? `${h}h ${m}m` : `${m}m`;
    }

    // ══════════════════════════════════════════════════════════════════════
    //  UI EVENTS
    // ══════════════════════════════════════════════════════════════════════
    function initUIEvents() {
        // ── Send message ──
        function send() {
            const input = document.getElementById('commandInput');
            const text = input.value.trim();
            if (!text) return;
            Panels.addMessage({ sender: 'user', text, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) });
            input.value = '';
            FridaySocket.emit('command:send', { text });
        }
        _bindClick('sendBtn', send);
        const input = document.getElementById('commandInput');
        if (input) input.addEventListener('keydown', (e) => { if (e.key === 'Enter') send(); });

        // ── Quick actions ──
        document.querySelectorAll('.quick-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const cmd = btn.dataset.cmd;
                if (cmd) FridaySocket.emit('command:send', { text: cmd });
            });
        });

        // ── Modes ──
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const scene = btn.dataset.scene;
                if (scene) {
                    FridaySocket.emit('scene:run', { scene });
                    Panels.addMessage({ sender: 'friday', text: `Activating ${scene} mode...`, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) });
                }
            });
        });

        // ── Music controls (home) ──
        _bindClick('mcPrev', () => FridaySocket.emit('music:prev'));
        _bindClick('mcPlay', () => FridaySocket.emit('music:play'));
        _bindClick('mcNext', () => FridaySocket.emit('music:next'));
        // Music controls (media view)
        _bindClick('mediaPrev', () => FridaySocket.emit('music:prev'));
        _bindClick('mediaPlay', () => FridaySocket.emit('music:play'));
        _bindClick('mediaNext', () => FridaySocket.emit('music:next'));

        // ── Calendar ──
        _bindClick('syncCalendarBtn', () => {
            FridaySocket.emit('calendar:sync');
            setTimeout(() => FridaySocket.emit('calendar:events', { days: 7 }), 1500);
        });
        _bindClick('addCalendarEvent', () => {
            Panels.showModal('Add Event', [
                { label: 'Title', name: 'title', type: 'text', placeholder: 'Event title...' },
                { label: 'Time', name: 'start_time', type: 'text', placeholder: 'e.g. 2026-07-30T15:00:00' },
                { label: 'Duration (min)', name: 'duration', type: 'text', placeholder: '30' },
                { label: 'Location', name: 'location', type: 'text', placeholder: 'Optional' },
            ], (data) => {
                FridaySocket.emit('calendar:create', {
                    title: data.title,
                    start_time: data.start_time || new Date(Date.now() + 3600000).toISOString().slice(0, 19),
                    duration: parseInt(data.duration) || 30,
                    location: data.location || '',
                });
            });
        });
        _bindClick('taskAddBtn', () => Panels.showAddTaskModal());

        // ── Media view: web search ──
        _bindClick('webSearchBtn', () => {
            const input = document.getElementById('webSearchInput');
            if (!input || !input.value.trim()) return;
            const query = input.value.trim();
            Panels.showWebLoading();
            FridayBridge.webSearch(query).then(results => Panels.renderWebResults(results));
        });
        const webInput = document.getElementById('webSearchInput');
        if (webInput) webInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') document.getElementById('webSearchBtn').click(); });

        // ── Vision ──
        _bindClick('visionCaptureBtn', () => {
            FridayBridge.visionCapture().then(result => {
                Panels.addMessage({ sender: 'friday', text: result && result.path ? `📸 Screenshot captured (${(result.size/1024).toFixed(0)}KB)` : `⚠️ ${result?.error || 'Capture failed'}`, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) });
            });
        });
        _bindClick('visionAnalyzeBtn', () => {
            Panels.addMessage({ sender: 'friday', text: '📸 Capturing and analyzing screen...', time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) });
            FridayBridge.visionAnalyze('What do you see?').then(result => {
                if (result && result.analysis) {
                    Panels.addMessage({ sender: 'friday', text: `👁 **Analysis:**\n${result.analysis}`, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) });
                }
            });
        });

        // ── Notes ──
        _bindClick('notesAdd', () => {
            const form = document.getElementById('notesForm');
            if (form) form.style.display = form.style.display === 'none' ? 'flex' : 'none';
        });
        _bindClick('noteSaveBtn', () => {
            const title = document.getElementById('noteTitle');
            const body = document.getElementById('noteBody');
            if (!title || !title.value) return;
            FridayBridge.createNote(title.value, body ? body.value : '').then(() => {
                Panels.loadNotesView();
                if (title) title.value = '';
                if (body) body.value = '';
            });
        });
        document.querySelectorAll('.notes-tab[data-note-src]').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.notes-tab[data-note-src]').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                Panels.loadNotesView(tab.dataset.noteSrc);
            });
        });
        document.querySelectorAll('.email-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.email-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                Panels.loadEmail(tab.dataset.mailSrc);
            });
        });

        // ── Memory ──
        _bindClick('memorySearchBtn', () => {
            const input = document.getElementById('memorySearchInput');
            if (input) Panels.searchMemory(input.value.trim());
        });
        const memInput = document.getElementById('memorySearchInput');
        if (memInput) memInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') Panels.searchMemory(memInput.value.trim()); });

        // ── Git ──
        _bindClick('gitRunBtn', () => {
            const input = document.getElementById('gitCommandInput');
            if (!input || !input.value.trim()) return;
            FridayBridge.gitRun(input.value.trim()).then(result => Panels.renderGitOutput(result));
        });
        _bindClick('gitStatusBtn', async () => Panels.renderGitOutput(await FridayBridge.gitStatus()));
        _bindClick('gitLogBtn', async () => Panels.renderGitOutput(await FridayBridge.gitLog()));
        _bindClick('gitConfirmBtn', async () => Panels.renderGitOutput(await FridayBridge.gitConfirm()));
        const gitInput = document.getElementById('gitCommandInput');
        if (gitInput) gitInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') document.getElementById('gitRunBtn').click(); });

        // ── Scheduler ──
        _bindClick('schedulerRefresh', () => Panels.loadScheduler());
        _bindClick('schedulerAdd', () => {
            const form = document.getElementById('schedulerForm');
            if (form) form.style.display = form.style.display === 'none' ? 'flex' : 'none';
        });
        _bindClick('schedCreateBtn', () => {
            const name = document.getElementById('schedName');
            const tType = document.getElementById('schedTriggerType');
            const tVal = document.getElementById('schedTriggerValue');
            const aType = document.getElementById('schedActionType');
            const aCfg = document.getElementById('schedActionConfig');
            if (!name || !name.value) return;
            let config = {};
            const cfgVal = aCfg ? aCfg.value : '';
            if (aType.value === 'open_app') config = { app: cfgVal || 'Safari' };
            else if (aType.value === 'run_scene') config = { scene: cfgVal || 'focus' };
            else if (aType.value === 'send_message') config = { message: cfgVal };
            else if (aType.value === 'run_command') config = { command: cfgVal };
            FridayBridge.schedulerCreate(name.value, '', tType.value, tVal.value, aType.value, config).then(() => {
                Panels.loadScheduler();
                const form = document.getElementById('schedulerForm');
                if (form) form.style.display = 'none';
                if (name) name.value = '';
            });
        });

        // ── Settings / Voice ──
        _bindClick('voiceStartBtn', () => FridaySocket.emit('voice:start'));
        _bindClick('omniSaveBtn', () => {
            const keyInput = document.getElementById('omniKey');
            if (!keyInput || !keyInput.value.trim()) return;
            FridayBridge.setOmniKey(keyInput.value.trim()).then(result => {
                const aiStatus = document.getElementById('aiStatusVal');
                if (aiStatus) aiStatus.textContent = 'Online ✓';
                keyInput.value = '';
            });
        });
        _bindClick('clipboardSaveBtn', () => {
            const input = document.getElementById('clipboardInput');
            if (!input || !input.value.trim()) return;
            const text = input.value.trim();
            FridayBridge.copyClipboard(text);
            const name = text.split(' ')[0].toLowerCase().slice(0, 20);
            FridaySocket.emit('clipboard:save_snippet', { name, text });
            input.value = '';
        });

        // Voice config
        const voiceSelect = document.getElementById('voiceSelect');
        if (voiceSelect) voiceSelect.addEventListener('change', () => {
            FridaySocket.emit('config:update', { voice_index: voiceSelect.value });
        });
        const speakOn = document.getElementById('speakOn');
        if (speakOn) speakOn.addEventListener('change', () => {
            FridaySocket.emit('config:update', { speak_on: speakOn.checked });
        });
        const wakeWord = document.getElementById('wakeWord');
        if (wakeWord) wakeWord.addEventListener('change', () => {
            FridaySocket.emit('config:update', { wake_word: wakeWord.value || 'friday' });
        });

        // Push-to-Talk (Right Option + Space) — status + toggle
        const pttOn = document.getElementById('pttOn');
        const pttStatus = document.getElementById('pttStatus');
        function updatePttStatus(active) {
            if (pttOn) pttOn.checked = active;
            if (pttStatus) {
                pttStatus.textContent = active ? 'armed — hold ⌥ + Space to talk' : 'off';
                pttStatus.style.color = active ? 'var(--green)' : 'var(--dim)';
            }
        }
        if (pttOn) {
            pttOn.addEventListener('change', () => {
                const on = pttOn.checked;
                updatePttStatus(on);
                if (on) {
                    fetch('/api/voice/ptt', {
                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ action: 'ptt_hotkey', enable: true })
                    }).catch(() => {});
                }
            });
        }
        // Probe the PTT helper on load
        fetch('/api/voice/ptt', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'status' })
        }).then(r => r.json()).then(d => updatePttStatus(d && d.ok)).catch(() => updatePttStatus(false));

        // Refresh music every 5s
        setInterval(() => { FridaySocket.emit('music:get'); }, 5000);
    }

    function hideLoading() {
        const ls = document.getElementById('loadingScreen');
        if (ls) {
            ls.classList.add('hidden');
            setTimeout(() => ls.remove(), 700);
        }
    }

    function _bindClick(id, handler) {
        const el = document.getElementById(id);
        if (el) el.addEventListener('click', handler);
    }
})();
