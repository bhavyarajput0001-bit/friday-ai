/* ══════════════════════════════════════════════════════════════════════════════
   FRIDAY AI — Panel Logic & Interactions (modular UI)
   View loaders, renderers, gauges, charts, modals
   ══════════════════════════════════════════════════════════════════════════════ */

const Panels = (() => {

    // ══════════════════════════════════════════════════════════════════════
    //  STATUS GAUGES (CPU / MEM / DISK)
    // ══════════════════════════════════════════════════════════════════════
    function drawGauge(canvasEl, value, label, color) {
        if (!canvasEl) return;
        const ctx = canvasEl.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const size = canvasEl.width || canvasEl.height || 140;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        const cx = size / 2, cy = size / 2, r = size / 2 - 12;
        const startAngle = Math.PI * 0.75;
        const endAngle = Math.PI * 2.25;
        const pct = Math.min(value / 100, 1);
        const valAngle = startAngle + (endAngle - startAngle) * pct;

        // Background arc
        ctx.beginPath();
        ctx.arc(cx, cy, r, startAngle, endAngle);
        ctx.strokeStyle = 'rgba(0,212,255,0.1)';
        ctx.lineWidth = 10;
        ctx.lineCap = 'round';
        ctx.stroke();

        // Value arc
        ctx.beginPath();
        ctx.arc(cx, cy, r, startAngle, valAngle);
        const grad = ctx.createLinearGradient(0, 0, size, size);
        if (value > 80) {
            grad.addColorStop(0, '#ff4757');
            grad.addColorStop(1, '#ffb300');
        } else {
            grad.addColorStop(0, color || '#00d4ff');
            grad.addColorStop(1, '#00ff88');
        }
        ctx.strokeStyle = grad;
        ctx.lineWidth = 10;
        ctx.lineCap = 'round';
        ctx.shadowColor = 'rgba(0,212,255,0.3)';
        ctx.shadowBlur = 12;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Center text
        ctx.fillStyle = '#c8e6ff';
        ctx.font = `700 ${size * 0.16}px 'Orbitron', sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(Math.round(value) + '%', cx, cy - 2);

        // Sub label
        ctx.fillStyle = 'rgba(200,230,255,0.4)';
        ctx.font = `500 ${size * 0.07}px 'Rajdhani', sans-serif`;
        ctx.fillText(label || '', cx, cy + size * 0.14);
    }

    function updateSystemStats(stats) {
        const cpuCanvas = document.querySelector('#gaugeCpu .gauge-canvas');
        if (cpuCanvas) drawGauge(cpuCanvas, stats.cpu, 'CPU');

        const memCanvas = document.querySelector('#gaugeMem .gauge-canvas');
        if (memCanvas) drawGauge(memCanvas, stats.mem_percent, `${stats.mem_used}G`);

        const diskCanvas = document.querySelector('#gaugeDisk .gauge-canvas');
        if (diskCanvas) drawGauge(diskCanvas, stats.disk_percent, `${stats.disk_used}G`);

        updateHealth(stats);
    }

    // ══════════════════════════════════════════════════════════════════════
    //  SYSTEM HEALTH
    // ══════════════════════════════════════════════════════════════════════
    function updateHealth(stats) {
        const health = stats.health != null ? stats.health : 98;
        drawHealthRing(health);

        const valEl = document.getElementById('sysHealthVal');
        if (valEl) valEl.textContent = Math.round(health) + '%';
        const pctEl = document.getElementById('macHealthPct');
        if (pctEl) pctEl.textContent = Math.round(health) + '%';
    }

    function drawHealthRing(health) {
        const canvas = document.getElementById('healthRingCanvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const size = canvas.width || canvas.height || 140;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        const cx = size / 2, cy = size / 2, r = size / 2 - 12;
        const pct = health / 100;

        // Background
        ctx.beginPath();
        ctx.arc(cx, cy, r, -Math.PI / 2, Math.PI * 1.5);
        ctx.strokeStyle = 'rgba(0,255,136,0.08)';
        ctx.lineWidth = 10;
        ctx.stroke();

        // Value
        ctx.beginPath();
        ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * pct);
        const color = health >= 80 ? '#00ff88' : health >= 60 ? '#ffb300' : '#ff4757';
        ctx.strokeStyle = color;
        ctx.lineWidth = 10;
        ctx.lineCap = 'round';
        ctx.shadowColor = color;
        ctx.shadowBlur = 14;
        ctx.stroke();
        ctx.shadowBlur = 0;

        ctx.fillStyle = '#c8e6ff';
        ctx.font = `700 ${size * 0.16}px 'Orbitron', sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(Math.round(health) + '%', cx, cy - 2);
    }

    // ══════════════════════════════════════════════════════════════════════
    //  CONVERSATION
    // ══════════════════════════════════════════════════════════════════════
    function addMessage(msg) {
        const container = document.getElementById('conversationMessages');
        if (!container) return;

        const div = document.createElement('div');
        div.className = `msg ${msg.sender === 'user' ? 'msg-user' : 'msg-friday'}`;
        const formatted = msg.sender !== 'user' ? _renderMarkdown(msg.text) : _escapeHtml(msg.text);
        div.innerHTML = formatted;
        if (msg.time) {
            div.innerHTML += `<span class="msg-meta">${_escapeHtml(msg.time)}</span>`;
        }
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    function _renderMarkdown(text) {
        let html = _escapeHtml(text);
        html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/^## (.+)$/gm, '<h4>$1</h4>');
        html = html.replace(/^### (.+)$/gm, '<h5>$1</h5>');
        html = html.replace(/^- (.+)$/gm, '• $1<br>');
        html = html.replace(/\n\n/g, '<br><br>');
        html = html.replace(/\n/g, '<br>');
        return html;
    }

    function loadConversationHistory(messages) {
        const container = document.getElementById('conversationMessages');
        if (!container) return;
        container.innerHTML = '';
        (messages || []).forEach(msg => addMessage(msg));
    }

    // ══════════════════════════════════════════════════════════════════════
    //  TASKS
    // ══════════════════════════════════════════════════════════════════════
    function renderTasks(tasks) {
        const container = document.getElementById('tasksList');
        if (!container) return;
        container.innerHTML = '';
        if (!tasks || tasks.length === 0) {
            container.innerHTML = '<div class="empty-tasks">No tasks</div>';
            return;
        }
        tasks.forEach((task, i) => {
            const div = document.createElement('div');
            div.className = 'task-item';
            div.style.animationDelay = `${i * 0.05}s`;
            const isDone = task.status === 'done';
            div.innerHTML = `
                <div class="task-prio ${task.priority || 'low'}"></div>
                <div class="task-info">
                    <div class="task-title" style="${isDone ? 'text-decoration:line-through;opacity:0.5' : ''}">${_escapeHtml(task.title)}</div>
                    <div class="task-meta">${_capitalize(task.status)}</div>
                </div>
                <div class="task-progress"><div class="task-progress-fill" style="width:${task.progress || 0}%"></div></div>
                <div class="task-progress-val" style="font-size:11px;font-family:var(--font-mono);color:var(--text-dim)">${task.progress || 0}%</div>
            `;
            div.addEventListener('click', () => {
                const newStatus = task.status === 'done' ? 'pending' : 'done';
                const newProgress = newStatus === 'done' ? 100 : task.progress;
                FridaySocket.emit('task:update', { id: task.id, status: newStatus, progress: newProgress });
            });
            container.appendChild(div);
        });
    }

    function renderTasksMini(tasks) {
        const container = document.getElementById('tasksMiniList');
        if (!container) return;
        container.innerHTML = '';
        if (!tasks || tasks.length === 0) {
            container.innerHTML = '<div class="empty-tasks">No tasks — enjoy the day</div>';
            return;
        }
        const countEl = document.getElementById('tasksCount');
        if (countEl) countEl.textContent = tasks.length;
        tasks.slice(0, 5).forEach(task => {
            const div = document.createElement('div');
            div.className = 'task-mini';
            div.innerHTML = `
                <span class="task-mini-dot ${task.priority || 'low'}"></span>
                <span class="task-mini-title">${_escapeHtml(task.title)}</span>
                <span class="task-mini-pct">${task.progress || 0}%</span>
            `;
            container.appendChild(div);
        });
    }

    function showAddTaskModal() {
        showModal('Add Task', [
            { label: 'Title', name: 'title', type: 'text', placeholder: 'Task title...' },
            { label: 'Priority', name: 'priority', type: 'select', options: ['high', 'medium', 'low'] },
            { label: 'Due', name: 'due', type: 'text', placeholder: 'e.g. Tomorrow 3PM' },
        ], (data) => {
            FridaySocket.emit('task:create', data);
        });
    }

    // ══════════════════════════════════════════════════════════════════════
    //  FILES & SCENES
    // ══════════════════════════════════════════════════════════════════════
    function renderScenes(scenes) {
        const container = document.getElementById('scenesGrid');
        if (!container) return;
        const list = Array.isArray(scenes) ? scenes : (scenes && scenes.scenes) || [];
        if (list.length === 0) {
            container.innerHTML = '<div class="scenes-loading">No scenes available</div>';
            return;
        }
        container.innerHTML = '';
        const icons = {
            coding: '💻', movie: '🎬', focus: '🎯', meeting: '📋',
            cleanup: '🧹', morning: '☀️',
        };
        list.forEach(scene => {
            const btn = document.createElement('button');
            btn.className = 'scene-btn';
            btn.dataset.scene = scene.id;
            btn.innerHTML = `
                <span class="scene-icon">${icons[scene.id] || '⚡'}</span>
                <span class="scene-name">${_escapeHtml(scene.name)}</span>
                <span class="scene-actions-count">${scene.actions} actions</span>
            `;
            btn.addEventListener('click', () => {
                FridayBridge.runScene(scene.id);
                btn.classList.add('running');
                setTimeout(() => btn.classList.remove('running'), 2000);
            });
            container.appendChild(btn);
        });
    }

    function updateSceneStatus(scene, status) {
        document.querySelectorAll('.scene-btn').forEach(btn => {
            if (btn.dataset.scene === scene) {
                btn.classList.toggle('running', status === 'running');
            }
        });
    }

    function renderFiles(data) {
        const container = document.getElementById('filesListView');
        if (!container) return;
        const obj = (data && data.files) ? data.files : data;
        container.innerHTML = '';
        if (!obj || Object.keys(obj).length === 0) {
            container.innerHTML = '<div class="files-loading">No folders found</div>';
            return;
        }
        Object.entries(obj).forEach(([key, folder]) => {
            const div = document.createElement('div');
            div.className = 'file-row';
            div.innerHTML = `
                <span class="file-icon">📁</span>
                <div style="flex:1">
                    <div style="font-weight:600">${_capitalize(key.replace(/_/g, ' '))}</div>
                    <div class="file-path">~/${folder.path || ''} · ${folder.total_files || 0} files</div>
                </div>
            `;
            div.addEventListener('click', () => {
                FridaySocket.emit('shortcut:run', { action: 'open_' + key.toLowerCase() });
            });
            container.appendChild(div);
        });
    }

    // ══════════════════════════════════════════════════════════════════════
    //  CALENDAR
    // ══════════════════════════════════════════════════════════════════════
    function renderCalendar(events) {
        const container = document.getElementById('calendarList');
        if (!container) return;
        const countEl = document.getElementById('calTodayCount');
        container.innerHTML = '';
        if (!events || events.length === 0) {
            container.innerHTML = '<div class="calendar-empty">No events</div>';
            if (countEl) countEl.textContent = '0 events today';
            return;
        }
        if (countEl) countEl.textContent = `${events.length} event${events.length !== 1 ? 's' : ''} today`;
        events.forEach(ev => {
            const div = document.createElement('div');
            div.className = 'cal-event';
            const time = ev.start_time ? ev.start_time.slice(11, 16) : '--:--';
            const srcLabel = ev.source === 'google' ? 'G' : ev.source === 'apple' ? '' : '•';
            div.innerHTML = `
                <span class="cal-event-time">${time}</span>
                <div class="cal-event-info">
                    <div class="cal-event-title">${_escapeHtml(ev.title)}</div>
                    ${ev.location ? `<div class="cal-event-location">📍 ${_escapeHtml(ev.location)}</div>` : ''}
                </div>
                <span class="cal-event-source">${srcLabel}</span>
            `;
            container.appendChild(div);
        });
    }

    function updateCalendarSyncStatus(apple, google) {
        const el = document.getElementById('calSyncStatus');
        if (!el) return;
        if (google) el.textContent = '☁️ Google';
        else if (apple) el.textContent = ' Apple';
        else el.textContent = '📁 Local';
    }

    // ══════════════════════════════════════════════════════════════════════
    //  MEDIA
    // ══════════════════════════════════════════════════════════════════════
    function updateMediaMusic(track) {
        const titleEl = document.getElementById('mediaMusicTitle');
        const artistEl = document.getElementById('mediaMusicArtist');
        const artEl = document.getElementById('mediaMusicArt');
        const playBtn = document.getElementById('mediaPlay');
        if (track && track.playing) {
            if (titleEl) titleEl.textContent = track.title || 'Unknown';
            if (artistEl) artistEl.textContent = track.artist || '';
            if (artEl) {
                artEl.innerHTML = track.album_art ? `<img src="${track.album_art}" alt="">` : '♪';
            }
            if (playBtn) playBtn.textContent = '⏸';
        } else {
            if (titleEl) titleEl.textContent = 'Nothing playing';
            if (artistEl) artistEl.textContent = '—';
            if (artEl) artEl.textContent = '♪';
            if (playBtn) playBtn.textContent = '▶';
        }
    }

    function showWebLoading() {
        const container = document.getElementById('webResults');
        if (container) container.innerHTML = '<div class="memory-empty">Searching...</div>';
    }

    function renderWebResults(results) {
        const container = document.getElementById('webResults');
        if (!container) return;
        if (!results || results.error) {
            container.innerHTML = `<div class="memory-empty">⚠️ ${_escapeHtml((results && results.error) || 'No results')}</div>`;
            return;
        }
        const list = (results.results || []).slice(0, 8);
        if (list.length === 0) {
            container.innerHTML = '<div class="memory-empty">No results found.</div>';
            return;
        }
        container.innerHTML = '';
        list.forEach(r => {
            const div = document.createElement('div');
            div.className = 'web-result';
            div.innerHTML = `
                <div class="web-result-title"><a href="${_escapeHtml(r.link || '#')}" target="_blank">${_escapeHtml(r.title)}</a></div>
                ${r.snippet ? `<div class="web-result-snippet">${_escapeHtml(r.snippet)}</div>` : ''}
            `;
            container.appendChild(div);
        });
    }

    // ══════════════════════════════════════════════════════════════════════
    //  CLIPBOARD
    // ══════════════════════════════════════════════════════════════════════
    function renderClipboard(entries) {
        const container = document.getElementById('clipboardList');
        if (!container) return;
        if (!entries || entries.length === 0) {
            container.innerHTML = '<div class="clipboard-empty">No clipboard history yet</div>';
            return;
        }
        container.innerHTML = '';
        entries.forEach(entry => {
            const div = document.createElement('div');
            div.className = 'clip-entry';
            div.innerHTML = `
                <span class="clip-entry-text">${_escapeHtml(entry.text || entry)}</span>
                <span class="clip-entry-time">${entry.time || ''}</span>
            `;
            div.addEventListener('click', () => {
                FridayBridge.copyClipboard(entry.full_text || entry.text || entry);
                div.style.borderColor = 'var(--accent)';
                setTimeout(() => div.style.borderColor = '', 800);
            });
            container.appendChild(div);
        });
    }

    function addClipboardEntry(entry) {
        const container = document.getElementById('clipboardList');
        if (!container) return;
        const empty = container.querySelector('.clipboard-empty');
        if (empty) container.innerHTML = '';
        const div = document.createElement('div');
        div.className = 'clip-entry';
        div.innerHTML = `
            <span class="clip-entry-text">${_escapeHtml(entry.text || '')}</span>
            <span class="clip-entry-time">${entry.time || ''}</span>
        `;
        div.addEventListener('click', () => {
            FridayBridge.copyClipboard(entry.full_text || entry.text || '');
        });
        container.insertBefore(div, container.firstChild);
        if (container.children.length > 12) container.lastChild.remove();
    }

    // ══════════════════════════════════════════════════════════════════════
    //  MEMORY VAULT
    // ══════════════════════════════════════════════════════════════════════
    function renderMemoryResults(results) {
        const container = document.getElementById('memoryResults');
        if (!container) return;
        container.innerHTML = '';
        if (!results || results.length === 0) {
            container.innerHTML = '<div class="memory-empty">No matching memories.</div>';
            return;
        }
        results.forEach(r => {
            const div = document.createElement('div');
            div.className = 'memory-item';
            div.innerHTML = `
                <div class="memory-title">📄 ${_escapeHtml(r.title || r.file || 'Memory')}</div>
                <div class="memory-content">${_escapeHtml((r.content || '').slice(0, 200))}</div>
                <div class="memory-file">${_escapeHtml(r.file || '')}</div>
            `;
            container.appendChild(div);
        });
    }

    function renderMemoryNotes(notes) {
        const container = document.getElementById('memoryNotesList');
        if (!container) return;
        container.innerHTML = '';
        if (!notes || notes.length === 0) {
            container.innerHTML = '<div class="memory-notes-loading">No vault notes yet.</div>';
            return;
        }
        notes.slice(0, 10).forEach(n => {
            const div = document.createElement('div');
            div.className = 'memory-note-item';
            div.innerHTML = `
                <span class="memory-note-name">📄 ${_escapeHtml(n.name || n.path || 'Note')}</span>
                <span class="memory-note-modified">${_escapeHtml((n.modified || '').slice(0, 10))}</span>
            `;
            container.appendChild(div);
        });
    }

    // ══════════════════════════════════════════════════════════════════════
    //  NOTES & EMAIL
    // ══════════════════════════════════════════════════════════════════════
    function renderNotes(data, source) {
        const container = document.getElementById('notesList');
        if (!container) return;
        container.innerHTML = '';
        let items = [];
        if (data && data.notes) {
            items = Array.isArray(data.notes) ? data.notes : (data.notes[source] || []);
        } else if (data) {
            items = data[source] || data.local || [];
        }
        if (items.length === 0) {
            container.innerHTML = `<div class="notes-loading">No ${source} notes.</div>`;
            return;
        }
        items.slice(0, 15).forEach(n => {
            const div = document.createElement('div');
            div.className = 'note-item';
            div.innerHTML = `
                <div class="note-title">📝 ${_escapeHtml(n.title || 'Untitled')}</div>
                ${n.body ? `<div class="note-body">${_escapeHtml((n.body || '').slice(0, 120))}</div>` : ''}
                ${n.folder ? `<div class="note-folder">📁 ${_escapeHtml(n.folder)}</div>` : ''}
            `;
            container.appendChild(div);
        });
    }

    function loadNotes(source = 'local') {
        if (source === 'apple' && FridayBridge.getAppleNotes) {
            FridayBridge.getAppleNotes().then(data => renderNotes(data, 'apple'));
        } else if (source === 'keep') {
            fetch('/api/notes/keep').then(r => r.json()).then(data => renderNotes(data, 'keep')).catch(() => {});
        } else if (FridayBridge.getNotes) {
            FridayBridge.getNotes().then(data => renderNotes(data, 'local'));
        }
    }

    function renderEmail(data, source) {
        const container = document.getElementById('emailList');
        if (!container) return;
        container.innerHTML = '';
        if (!data) {
            container.innerHTML = '<div class="email-loading">No mail available.</div>';
            return;
        }
        let items = (source === 'apple') ? (data.apple || []) : (data.gmail || []);
        if (items.length === 0) {
            container.innerHTML = `<div class="email-loading">No ${source} mail.</div>`;
            return;
        }
        items.slice(0, 10).forEach(m => {
            const div = document.createElement('div');
            div.className = 'email-item';
            div.innerHTML = `
                <div class="email-subject">📧 ${_escapeHtml(m.subject || 'No subject')}</div>
                <div class="email-from">${_escapeHtml(m.from || m.sender || '')}</div>
                ${m.snippet ? `<div class="email-snippet">${_escapeHtml(m.snippet.slice(0, 100))}</div>` : ''}
            `;
            container.appendChild(div);
        });
    }

    function loadEmail(source = 'apple') {
        if (FridayBridge.getEmail) {
            FridayBridge.getEmail().then(data => renderEmail(data, source));
        }
    }

    // ══════════════════════════════════════════════════════════════════════
    //  SCHEDULER
    // ══════════════════════════════════════════════════════════════════════
    function renderSchedulerTasks(tasks) {
        const container = document.getElementById('schedulerList');
        if (!container) return;
        container.innerHTML = '';
        if (!tasks || tasks.length === 0) {
            container.innerHTML = '<div class="scheduler-empty">No scheduled tasks. Add one to automate FRIDAY.</div>';
            return;
        }
        tasks.forEach(t => {
            const div = document.createElement('div');
            div.className = 'scheduler-item' + (t.enabled === false ? ' disabled' : '');
            div.innerHTML = `
                <div class="scheduler-item-header">
                    <span class="scheduler-status">${t.enabled === false ? '⏸' : '✅'}</span>
                    <span class="scheduler-name">${_escapeHtml(t.name)}</span>
                    <div class="scheduler-actions">
                        <button class="sched-toggle" data-id="${t.id}" title="Toggle">⏯</button>
                        <button class="sched-delete" data-id="${t.id}" title="Delete">🗑</button>
                    </div>
                </div>
                <div class="scheduler-meta">${_escapeHtml(t.trigger_type)}: ${_escapeHtml(t.trigger_value)} → ${_escapeHtml(t.action_type)}</div>
                ${t.next_run ? `<div class="scheduler-next">Next: ${_escapeHtml(t.next_run.slice(0, 16))}</div>` : ''}
            `;
            div.querySelector('.sched-toggle').addEventListener('click', () => {
                FridayBridge.schedulerToggle(t.id).then(() => loadScheduler());
            });
            div.querySelector('.sched-delete').addEventListener('click', () => {
                FridayBridge.schedulerDelete(t.id).then(() => loadScheduler());
            });
            container.appendChild(div);
        });
    }

    function loadScheduler() {
        if (FridayBridge.schedulerList) {
            FridayBridge.schedulerList().then(data => {
                renderSchedulerTasks((data && data.tasks) || []);
            });
        }
    }

    // ══════════════════════════════════════════════════════════════════════
    //  GIT AGENT
    // ══════════════════════════════════════════════════════════════════════
    function renderGitOutput(result) {
        const container = document.getElementById('gitOutput');
        if (!container) return;
        if (!result) {
            container.innerHTML = '<div class="git-empty">No output.</div>';
            return;
        }
        if (result.pending) {
            container.innerHTML = `<div class="git-pending">🔐 ${_escapeHtml(result.message || 'Pending permission')}<br><small>Click ✓ Confirm to execute.</small></div>`;
            return;
        }
        let html = '';
        if (result.error) html += `<div class="git-error">⚠️ ${_escapeHtml(result.error)}</div>`;
        if (result.output) html += `<pre class="git-output-block">${_escapeHtml(result.output)}</pre>`;
        if (!html) html = '<div class="git-empty">No output.</div>';
        container.innerHTML = html;
    }

    // ══════════════════════════════════════════════════════════════════════
    //  VIEW LOADERS (lazy-load data when view opens)
    // ══════════════════════════════════════════════════════════════════════
    function loadCalendarView() {
        FridayBridge.getTodayCalendar().then(d => {
            if (d && d.events) renderCalendar(d.events);
        });
        FridayBridge.getCalendarEvents(7).then(d => {
            if (d) updateCalendarSyncStatus(d.apple, d.google);
        });
        FridayBridge.getTasks().then(d => {
            if (d && d.tasks) renderTasks(d.tasks);
        });
    }

    function loadFilesView() {
        FridayBridge.getScenes().then(s => renderScenes(s));
        FridayBridge.searchFiles('').then(f => renderFiles(f));
    }

    function loadMediaView() {
        FridayBridge.getNowPlaying().then(t => updateMediaMusic(t));
    }

    function loadNotesView(source = 'local') {
        loadNotes(source);
    }

    function loadMemoryView() {
        if (FridayBridge.memoryNotes) {
            FridayBridge.memoryNotes().then(d => renderMemoryNotes((d && d.notes) || []));
        }
    }

    function loadGitView() {
        loadScheduler();
        FridayBridge.gitStatus().then(r => renderGitOutput(r));
    }

    function loadSettingsView() {
        if (FridayBridge.getClipboard) {
            FridayBridge.getClipboard().then(d => renderClipboard((d && d.entries) || []));
        }
        FridayBridge.getOmniRouteStatus().then(omni => {
            const aiStatus = document.getElementById('aiStatusVal');
            if (aiStatus) aiStatus.textContent = (omni && omni.available) ? 'Online ✓' : 'Offline';
        });
    }

    function loadSystemView() {
        FridayBridge.getSystemStats().then(stats => {
            if (stats && stats.cpu != null) updateSystemStats(stats);
        });
    }

    // ══════════════════════════════════════════════════════════════════════
    //  MODAL HELPER
    // ══════════════════════════════════════════════════════════════════════
    function showModal(title, fields, onSubmit) {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';

        let fieldsHTML = fields.map(f => {
            if (f.type === 'select') {
                const opts = f.options.map(o => `<option value="${o}">${_capitalize(o)}</option>`).join('');
                return `<div class="modal-field"><label>${f.label}</label><select name="${f.name}">${opts}</select></div>`;
            }
            return `<div class="modal-field"><label>${f.label}</label><input type="${f.type}" name="${f.name}" placeholder="${f.placeholder || ''}"></div>`;
        }).join('');

        overlay.innerHTML = `
            <div class="modal">
                <h3>${title}</h3>
                ${fieldsHTML}
                <div class="modal-actions">
                    <button class="btn-ghost" id="modalCancel">Cancel</button>
                    <button class="btn-primary" id="modalSubmit">Create</button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        overlay.querySelector('#modalCancel').addEventListener('click', () => overlay.remove());
        overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
        overlay.querySelector('#modalSubmit').addEventListener('click', () => {
            const data = {};
            fields.forEach(f => {
                const el = overlay.querySelector(`[name="${f.name}"]`);
                if (el) data[f.name] = el.value;
            });
            onSubmit(data);
            overlay.remove();
        });

        setTimeout(() => {
            const firstInput = overlay.querySelector('input, select');
            if (firstInput) firstInput.focus();
        }, 100);
    }

    // ══════════════════════════════════════════════════════════════════════
    //  UTILITIES
    // ══════════════════════════════════════════════════════════════════════
    function _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function _capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    return {
        drawGauge,
        updateSystemStats,
        updateHealth,
        drawHealthRing,
        addMessage,
        loadConversationHistory,
        renderTasks,
        renderTasksMini,
        showAddTaskModal,
        renderScenes,
        updateSceneStatus,
        renderFiles,
        renderCalendar,
        updateCalendarSyncStatus,
        updateMediaMusic,
        showWebLoading,
        renderWebResults,
        renderClipboard,
        addClipboardEntry,
        renderMemoryResults,
        renderMemoryNotes,
        loadMemoryNotes: loadMemoryView,
        searchMemory: (query) => {
            if (!query) return;
            if (FridayBridge.memorySearch) {
                FridayBridge.memorySearch(query).then(data => renderMemoryResults((data && data.results) || []));
            }
        },
        renderSchedulerTasks,
        loadScheduler,
        renderGitOutput,
        renderNotes,
        loadNotes,
        renderEmail,
        loadEmail,
        showModal,
        loadCalendarView,
        loadFilesView,
        loadMediaView,
        loadNotesView,
        loadMemoryView,
        loadGitView,
        loadSettingsView,
        loadSystemView,
    };
})();
