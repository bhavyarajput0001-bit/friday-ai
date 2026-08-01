/* ═══════════════════════════════════════════════════════════════
   FRIDAY — Mission Control UI controller
   All data flows through the FRIDAY server REST API.
   ═══════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    const $ = (id) => document.getElementById(id);

    // ═══════════════ REST helpers ═══════════════
    async function get(path) {
        try {
            const r = await fetch(path, { cache: 'no-store' });
            return await r.json();
        } catch (e) { return null; }
    }
    async function post(path, body) {
        try {
            const r = await fetch(path, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body || {}),
            });
            return await r.json();
        } catch (e) { return null; }
    }

    // ═══════════════ AI CORE CANVAS ═══════════════
    const cv = $('mcCoreCanvas');
    const ctx = cv.getContext('2d');
    let W = 0, H = 0, coreState = 'STANDBY', rmsBoost = 0;
    const particles = [];

    function resizeCore() {
        const box = $('mcCore').getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        W = box.width; H = box.height;
        cv.width = W * dpr; cv.height = H * dpr;
        cv.style.width = W + 'px'; cv.style.height = H + 'px';
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function seedParticles() {
        particles.length = 0;
        const cx = W / 2, cy = H / 2, R = Math.min(W, H) * 0.30;
        for (let i = 0; i < 60; i++) {
            particles.push({
                ang: Math.random() * Math.PI * 2,
                rad: R * (0.7 + Math.random() * 0.5),
                speed: (0.2 + Math.random() * 0.8) * (Math.random() < 0.5 ? -1 : 1),
                size: 0.8 + Math.random() * 1.6,
                hue: Math.random() < 0.85 ? '55,216,255' : '105,255,175',
            });
        }
    }

    function drawCore(t) {
        const cx = W / 2, cy = H / 2;
        const R = Math.min(W, H) * 0.30;
        const breathe = 1 + Math.sin(t * 0.0012) * 0.02;

        ctx.clearRect(0, 0, W, H);

        // outer orbit rings
        for (let i = 0; i < 3; i++) {
            const rr = R * (0.62 + i * 0.18) * breathe;
            ctx.beginPath();
            ctx.arc(cx, cy, rr, 0, Math.PI * 2);
            ctx.strokeStyle = `rgba(55,216,255,${0.10 + i * 0.06})`;
            ctx.lineWidth = 1;
            ctx.stroke();
        }

        // rotating dotted ring
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(t * 0.0004);
        ctx.beginPath();
        ctx.setLineDash([2, 9]);
        ctx.arc(0, 0, R * 0.92 * breathe, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(55,216,255,0.35)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.restore();

        // orbit particles
        for (const p of particles) {
            p.ang += p.speed * 0.01;
            const x = cx + Math.cos(p.ang) * p.rad * breathe;
            const y = cy + Math.sin(p.ang) * p.rad * breathe * 0.6;
            ctx.beginPath();
            ctx.arc(x, y, p.size, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${p.hue},${0.5 + 0.4 * Math.sin(p.ang * 3)})`;
            ctx.fill();
        }

        // core glow
        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 0.28);
        g.addColorStop(0, 'rgba(55,216,255,0.28)');
        g.addColorStop(1, 'transparent');
        ctx.beginPath();
        ctx.arc(cx, cy, R * 0.28, 0, Math.PI * 2);
        ctx.fillStyle = g;
        ctx.fill();

        // core body
        const cg = ctx.createRadialGradient(cx - R * 0.1, cy - R * 0.1, 0, cx, cy, R * 0.2);
        cg.addColorStop(0, 'rgba(255,255,255,0.9)');
        cg.addColorStop(0.35, 'rgba(55,216,255,0.85)');
        cg.addColorStop(1, 'rgba(26,139,181,0.9)');
        ctx.beginPath();
        ctx.arc(cx, cy, R * 0.20 * breathe, 0, Math.PI * 2);
        ctx.fillStyle = cg;
        ctx.shadowColor = 'rgba(55,216,255,0.7)';
        ctx.shadowBlur = 30 + rmsBoost * 8;
        ctx.fill();
        ctx.shadowBlur = 0;

        requestAnimationFrame(drawCore);
    }

    function startCore() {
        resizeCore();
        seedParticles();
        requestAnimationFrame(drawCore);
        window.addEventListener('resize', () => { resizeCore(); seedParticles(); });
    }

    // ═══════════════ system polling ═══════════════
    async function pollStatus() {
        const st = await get('/api/status');
        if (st) {
            setBar($('mcBarMem'), st.mem_percent);
            setBar($('mcBarCpu'), st.cpu);
            setBar($('mcBarNet'), st.network || Math.min(100, 40 + (st.cpu || 0) * 0.3));
            setGauge($('mcGaugeCpu'), $('mcGaugeCpuV'), st.cpu);
            setGauge($('mcGaugeMem'), $('mcGaugeMemV'), st.mem_percent);
            setGauge($('mcGaugeBat'), $('mcGaugeBatV'), st.battery);
            const memUsed = Math.min(100, (st.mem_percent || 0) + 12);
            const circ = $('mcMemFill');
            const circV = $('mcMemV');
            circ.style.strokeDashoffset = 239 - (239 * memUsed / 100);
            if (circV) circV.textContent = Math.round(memUsed) + '%';
        }
    }

    async function pollOnline() {
        const om = await get('/api/omniroute/status');
        const online = om && om.available;
        const el = $('mcOnline');
        const txt = $('mcOnlineText');
        el.classList.toggle('mc-pill-online', !!online);
        if (txt) txt.textContent = online ? 'ONLINE' : 'OFFLINE';
        setCoreState(online ? 'READY' : 'LOCAL');
    }

    function setBar(el, val) { if (el) el.style.width = Math.min(100, Math.max(0, val || 0)) + '%'; }

    function setGauge(arc, valEl, val) {
        const v = Math.min(100, Math.max(0, val || 0));
        const R = 28, C = Math.PI * R; // semicircle length = pi*R
        const arcLen = C * v / 100;
        if (arc) arc.style.strokeDasharray = `${arcLen} ${C}`;
        if (valEl) valEl.textContent = Math.round(v) + '%';
    }

    function setCoreState(state) {
        coreState = state;
        const el = $('mcCoreState');
        if (el) el.textContent = state;
    }

    // ═══════════════ data loads ═══════════════
    async function loadTasks() {
        const d = await get('/api/tasks');
        const box = $('mcTasks');
        if (!box) return;
        const tasks = (d && d.tasks) || [];
        if (!tasks.length) { box.innerHTML = '<span class="mc-log-empty">No tasks</span>'; return; }
        box.innerHTML = tasks.slice(0, 6).map(t =>
            `<div style="padding:5px 0;border-bottom:1px solid var(--border-soft)">
               <span style="color:var(--text)">${esc(t.title || t.name || 'Task')}</span>
               <span style="float:right;color:var(--muted)">${t.status || t.trigger_type || ''}</span>
             </div>`).join('');
    }

    async function loadNotes() {
        const d = await get('/api/notes');
        const box = $('mcNotes');
        if (!box) return;
        const notes = (d && (d.notes || d.local || d)) || [];
        const arr = Array.isArray(notes) ? notes : [];
        if (!arr.length) { box.innerHTML = '<span class="mc-log-empty">No notes</span>'; return; }
        box.innerHTML = arr.slice(0, 6).map(n =>
            `<div style="padding:4px 0">${esc(n.title || n.body || '').slice(0, 60)}</div>`).join('');
    }

    function logLine(text, cls) {
        const box = $('mcActivity');
        if (!box) return;
        const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const div = document.createElement('div');
        div.innerHTML = `<span class="mc-log-time">${t}</span><span class="${cls || ''}">${esc(text)}</span>`;
        box.prepend(div);
        while (box.children.length > 40) box.lastChild.remove();
    }

    // ═══════════════ chat ═══════════════
    async function sendCommand(text) {
        if (!text.trim()) return;
        const log = $('mcCoreLog');
        const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        if (log) {
            log.innerHTML = '';
            const u = document.createElement('div');
            u.innerHTML = `<span class="mc-log-time">${t}</span><span class="mc-log-user">❯ ${esc(text)}</span>`;
            log.appendChild(u);
        }
        logLine(text, 'mc-log-user');
        setCoreState('THINKING');
        const rmsTimer = setInterval(() => { rmsBoost = Math.min(6, rmsBoost + 0.6); }, 60);
        const d = await post('/api/chat', { text });
        clearInterval(rmsTimer);
        rmsBoost = 0;
        const reply = (d && d.response) || (d && d.interim && d.interim[d.interim.length - 1]) || '[no response]';
        if (log) {
            const a = document.createElement('div');
            a.innerHTML = `<span class="mc-log-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span><span class="mc-log-ai">${esc(reply)}</span>`;
            log.appendChild(a);
        }
        const th = $('mcThoughts');
        if (th) th.innerHTML = `<div style="color:var(--text)">${esc(reply)}</div>`;
        logLine(reply, 'mc-log-ai');
        setCoreState('READY');
    }

    // ═══════════════ controls ═══════════════
    function wireControls() {
        $('mcCmdSend').addEventListener('click', () => {
            const inp = $('mcCmdInput');
            sendCommand(inp.value);
            inp.value = '';
        });
        $('mcCmdInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') { e.preventDefault(); $('mcCmdSend').click(); }
        });

        $('mcListen').addEventListener('click', async (e) => {
            const btn = e.currentTarget;
            const on = btn.classList.toggle('active');
            const r = await post('/api/voice/ptt', { action: on ? 'start' : 'stop' });
            setCoreState(on ? 'LISTENING' : 'READY');
            if (on) logLine('Listening… speak now');
            else if (r && r.text) sendCommand(r.text);
        });

        $('mcCamera').addEventListener('click', async () => {
            const r = await post('/api/vision/capture', {});
            const img = r && r.path;
            logLine('Camera: ' + (img ? 'captured' : 'failed'));
            if (img) {
                const fname = (img.split('/').pop());
                openModal('Camera', `<img src="/screenshots/${fname}" style="width:100%;border-radius:8px">`);
            }
        });

        $('mcScreen').addEventListener('click', async () => {
            const r = await post('/api/vision/capture_selection', {});
            logLine('Screen: ' + (r && (r.path || r.message) ? 'captured' : 'requested'));
        });

        // personality
        document.querySelectorAll('#mcPersonality .mc-pill-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('#mcPersonality .mc-pill-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                logLine('Personality → ' + btn.dataset.mode);
            });
        });

        // nav
        document.querySelectorAll('.mc-nav-item').forEach(item => {
            item.addEventListener('click', () => {
                document.querySelectorAll('.mc-nav-item').forEach(n => n.classList.remove('active'));
                item.classList.add('active');
                const view = item.dataset.view;
                logLine('View → ' + view);
                if (view === 'memory') loadMemoryView();
                if (view === 'settings') openModal('Settings',
                    'Voice engine, push-to-talk, and memory settings live in the Settings panel of the main dashboard.');
            });
        });

        $('mcWorkspace').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) $('mcApplyWs').click();
        });
        $('mcApplyWs').addEventListener('click', async () => {
            const ws = $('mcWorkspace').value.trim();
            if (ws) { await sendCommand('remember as workspace: ' + ws.slice(0, 200)); }
            else { await sendCommand('forget workspace instructions'); }
        });

        $('mcModalClose').addEventListener('click', closeModal);
        $('mcModal').addEventListener('click', (e) => { if (e.target === $('mcModal')) closeModal(); });

        // switches
        $('mcAutoVoice').addEventListener('change', (e) => {
            post('/api/chat', { text: 'turn ' + (e.target.checked ? 'on' : 'off') + ' the voice' });
        });
        $('mcPtt').addEventListener('change', (e) => {
            post('/api/voice/ptt', { action: 'ptt_hotkey', enable: e.target.checked });
        });
    }

    async function loadMemoryView() {
        const d = await get('/api/memory/notes');
        const notes = (d && d.notes) || [];
        const body = $('mcModalBody');
        $('mcModalTitle').textContent = 'MEMORY';
        body.innerHTML = notes.length
            ? notes.map(n => `<div style="padding:8px 0;border-bottom:1px solid var(--border-soft)">${esc(n.content || n).slice(0, 120)}</div>`).join('')
            : '<span class="mc-log-empty">Memory vault empty</span>';
        $('mcModal').classList.add('show');
    }

    function openModal(title, html) {
        $('mcModalTitle').textContent = title;
        $('mcModalBody').innerHTML = html;
        $('mcModal').classList.add('show');
    }
    function closeModal() { $('mcModal').classList.remove('show'); }

    function esc(s) {
        const d = document.createElement('div');
        d.textContent = s == null ? '' : String(s);
        return d.innerHTML;
    }

    // ═══════════════ clock ═══════════════
    function clock() {
        const el = $('mcFootClock');
        if (el) el.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        setTimeout(clock, 1000);
    }

    // ═══════════════ init ═══════════════
    function init() {
        startCore();
        wireControls();
        clock();
        pollOnline();
        pollStatus();
        loadTasks();
        loadNotes();
        setInterval(pollStatus, 3000);
        setInterval(pollOnline, 5000);
        setInterval(loadTasks, 10000);
        setInterval(loadNotes, 15000);
    }

    document.addEventListener('DOMContentLoaded', init);
})();
