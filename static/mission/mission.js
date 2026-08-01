/* ══════════════════════════════════════════════════════════════════════════════
   FRIDAY OS — MISSION CONTROL
   Calm AI operating-system shell. Spec-driven: 72px header, 300px sidebar,
   420px AI Core (60fps canvas), right widget stack, bottom workspace.
   ══════════════════════════════════════════════════════════════════════════════ */

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];

const F = window.FridayBridge || null;

/* ── STATE ── */
const state = {
  socket: null,
  connected: false,
  listening: false,
  status: 'BOOTING',
  statusSub: 'connecting to core…',
  view: 'home',
  messages: [],
  tasks: [],
  agenda: [],
  conversation: [],
  cal: [],
  nowPlaying: null,
  cfg: {},
  sys: { cpu: 0, mem: 0, memUsed: 0, disk: 0, battery: null },
  mode: 'professional',
  workflow: [],
};

/* ══════════════════════════════════════════════════════════════════════════════
   AI CORE CANVAS — 60fps rings + particles + breathing + waveform
   ══════════════════════════════════════════════════════════════════════════════ */
const CoreFX = (() => {
  let cv, ctx, W, H, DPR, raf;
  let t = 0;
  const parts = [];
  const MAX = 140;
  let waveform = [];   // amplitude samples while speaking
  let speaking = false;

  function init() {
    cv = $('#coreCanvas');
    ctx = cv.getContext('2d');
    resize();
    for (let i = 0; i < MAX; i++) parts.push(newParticle());
    loop();
  }

  function resize() {
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    const r = cv.getBoundingClientRect();
    W = r.width; H = r.height;
    cv.width = W * DPR; cv.height = H * DPR;
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }

  function newParticle() {
    return {
      x: Math.random(), y: Math.random(),
      vx: (Math.random() - 0.5) * 0.0025,
      vy: (Math.random() - 0.5) * 0.0025,
      s: Math.random() * 1.6 + 0.5,
      a: Math.random() * 0.5 + 0.15,
      h: Math.random() * 40 - 20,
    };
  }

  function setWave(amp) { if (amp > 0) waveform.push(amp); if (waveform.length > 48) waveform.shift(); }
  function setSpeaking(v) { speaking = v; if (!v) waveform = []; }

  function drawRing(cx, cy, r, lw, color, alpha, rot, dashOn, dashOff) {
    ctx.beginPath();
    ctx.arc(cx, cy, r, rot, rot + Math.PI * 2);
    ctx.strokeStyle = color;
    ctx.globalAlpha = alpha;
    ctx.lineWidth = lw;
    ctx.setLineDash(dashOn ? [dashOn, dashOff] : []);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = 1;
  }

  function drawDots(cx, cy, r, n, color, alpha, offset) {
    ctx.fillStyle = color;
    ctx.globalAlpha = alpha;
    for (let i = 0; i < n; i++) {
      const a = offset + (i / n) * Math.PI * 2;
      const x = cx + Math.cos(a) * r;
      const y = cy + Math.sin(a) * r;
      const s = 2.5 * (0.6 + 0.4 * Math.sin(t * 0.02 + i));
      ctx.beginPath();
      ctx.arc(x, y, s, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function loop() {
    t++;
    ctx.clearRect(0, 0, W, H);
    const cx = W / 2, cy = H / 2;
    const base = Math.min(W, H) * 0.34;
    const breath = 1 + Math.sin(t * 0.012) * 0.02;

    /* breathing glow */
    const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, base * 1.5);
    glow.addColorStop(0, 'rgba(69,217,255,0.16)');
    glow.addColorStop(0.6, 'rgba(69,217,255,0.05)');
    glow.addColorStop(1, 'rgba(69,217,255,0)');
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, W, H);

    /* three rotating rings */
    drawRing(cx, cy, base * 1.12 * breath, 1.2, 'rgba(69,217,255,0.5)', 0.55, t * 0.004);
    drawRing(cx, cy, base * 1.26 * breath, 1, 'rgba(105,255,168,0.4)', 0.4, -t * 0.003);
    drawRing(cx, cy, base * 0.82 * breath, 1.1, 'rgba(255,200,87,0.35)', 0.35, t * 0.006);

    /* dotted ring */
    drawDots(cx, cy, base * 1.38 * breath, 46, 'rgba(69,217,255,0.8)', 0.6, t * 0.01);

    /* pulse ring expanding outward */
    const pulseR = base * 1.5 + (t % 160) * 2.2;
    const pulseA = 1 - (t % 160) / 160;
    if (pulseA > 0) drawRing(cx, cy, pulseR * breath, 1.4, 'rgba(69,217,255,0.6)', pulseA * 0.6, 0);

    /* particles */
    for (const p of parts) {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > 1) p.vx *= -1;
      if (p.y < 0 || p.y > 1) p.vy *= -1;
      const px = p.x * W, py = p.y * H;
      ctx.fillStyle = `hsla(190, 100%, 75%, ${p.a})`;
      ctx.beginPath();
      ctx.arc(px, py, p.s, 0, Math.PI * 2);
      ctx.fill();
    }

    /* waveform while speaking */
    if (speaking && waveform.length > 2) {
      ctx.strokeStyle = 'rgba(105,255,168,0.9)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      const n = waveform.length;
      for (let i = 0; i < n; i++) {
        const a = (i / n) * Math.PI * 2;
        const r = base * 0.55 + Math.min(waveform[i] / 6, base * 0.5);
        const x = cx + Math.cos(a) * r;
        const y = cy + Math.sin(a) * r;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.stroke();
    }

    raf = requestAnimationFrame(loop);
  }

  window.addEventListener('resize', resize);
  return { init, setWave, setSpeaking };
})();

/* ══════════════════════════════════════════════════════════════════════════════
   SOCKET.IO
   ══════════════════════════════════════════════════════════════════════════════ */
function connectSocket() {
  if (typeof io === 'undefined') { setStatus('OFFLINE', 'socket client missing'); return; }
  state.socket = io({ reconnection: true, reconnectionDelay: 1000, reconnectionAttempts: Infinity });

  state.socket.on('connect', () => {
    state.connected = true;
    setStatus('ONLINE', 'all systems operational');
    $('#asDot').classList.add('ok');
    $('#asDot').classList.remove('off');
    logLine('connected to FRIDAY core', 'sys');
  });

  state.socket.on('disconnect', () => {
    state.connected = false;
    setStatus('CONNECTING', 'reconnecting…');
    $('#asDot').classList.remove('ok');
    $('#asDot').classList.add('off');
  });

  state.socket.on('connect_error', () => {
    state.connected = false;
    setStatus('OFFLINE', 'core unreachable');
    $('#asDot').classList.add('off');
  });

  state.socket.on('conversation:message', (m) => {
    state.conversation.push(m);
    if (state.conversation.length > 100) state.conversation.shift();
    if (m.sender === 'friday' && m.text) addConsole(m.text, 'friday');
    if (m.sender === 'user' && m.text) addConsole(m.text, 'user');
    if (m.sender === 'friday' && m.text) { CoreFX.setSpeaking(true); setTimeout(() => CoreFX.setSpeaking(false), 1800); }
    refreshContext();
  });

  state.socket.on('conversation:history', (hist) => {
    state.conversation = (hist || []).slice(-50);
    $('#console').innerHTML = '';
    for (const m of state.conversation) addConsole(m.text, m.sender, true);
  });

  state.socket.on('voice:status', (d) => {
    const s = d.state;
    if (s === 'listening') {
      state.listening = true;
      $('#asDot').classList.add('listening');
      setStatus('LISTENING', 'speak now…');
      $('#voiceBtn').classList.add('listening');
      $('#cmdMic').textContent = 'Listening';
      $('#cmdMic').parentElement.classList.add('on');
      CoreFX.setSpeaking(true);
    } else if (s === 'processing') {
      setStatus('THINKING', 'processing speech…');
    } else {
      state.listening = false;
      $('#asDot').classList.remove('listening');
      $('#voiceBtn').classList.remove('listening');
      $('#cmdMic').textContent = 'Idle';
      $('#cmdMic').parentElement.classList.remove('on');
      if (!state.status.startsWith('ONLINE')) setStatus('ONLINE', 'all systems operational');
      CoreFX.setSpeaking(false);
    }
  });

  state.socket.on('voice:waveform', (d) => CoreFX.setWave(d.rms || 0));

  state.socket.on('system:stats', (d) => {
    if (d) { state.sys.cpu = d.cpu ?? state.sys.cpu; state.sys.mem = d.mem_percent ?? state.sys.mem; renderSystem(); }
  });

  state.socket.on('task:list', (tasks) => { state.tasks = tasks || []; renderTasks(); });
  state.socket.on('agenda:list', (ag) => { state.agenda = ag || []; renderAgenda(); });
  state.socket.on('config:state', (cfg) => { state.cfg = cfg || {}; });
  state.socket.on('now_playing:data', (d) => { state.nowPlaying = d; renderNowPlaying(); });
  state.socket.on('proactive:suggestion', (s) => {
    if (s && s.title) logLine(`suggestion: ${s.title}`, 'success');
  });
  state.socket.on('browser:status', (d) => { $('#stLeft').textContent = 'BROWSER: ' + (d.status || 'UNAVAILABLE'); });
  state.socket.on('context:update', (d) => {
    if (d && d.app) $('#ccAgent').textContent = d.app;
  });
}

/* ══════════════════════════════════════════════════════════════════════════════
   STATUS / CONSOLE / LOGS
   ══════════════════════════════════════════════════════════════════════════════ */
function setStatus(text, sub) {
  state.status = text;
  state.statusSub = sub || '';
  $('#asText').textContent = text;
  $('#asSub').textContent = sub || '';
  $('#coreState').textContent = text;
  $('#stLeft').textContent = text + ' · ' + (sub || '');
}

function addConsole(text, sender = 'friday', quiet = false) {
  const c = $('#console');
  const d = document.createElement('div');
  d.className = 'line ' + (sender === 'user' ? 'user' : sender === 'sys' ? 'sys' : sender === 'err' ? 'err' : 'friday');
  d.textContent = text;
  c.appendChild(d);
  c.scrollTop = c.scrollHeight;
  if (!quiet) logLine(text, sender);
}

function logLine(text, kind = '') {
  const el = $('#wLogs');
  const d = document.createElement('div');
  d.className = 'item';
  d.innerHTML = `<span class="t">${timeStamp()}</span>${escapeHtml(text)}`;
  if (kind) d.classList.add(kind);
  el.appendChild(d);
  el.scrollTop = el.scrollHeight;

  const act = $('#wActivity');
  const a = document.createElement('div');
  a.className = 'item';
  a.innerHTML = `<span class="t">${timeStamp()}</span>${escapeHtml(text)}`;
  act.appendChild(a);
  act.scrollTop = act.scrollHeight;

  if (kind === 'err') notif('ERROR: ' + text, 'err');
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function timeStamp() {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`;
}

/* ══════════════════════════════════════════════════════════════════════════════
   SYSTEM GAUGES
   ══════════════════════════════════════════════════════════════════════════════ */
const GAUGES = [
  { key: 'cpu', label: 'CPU' },
  { key: 'ram', label: 'RAM' },
  { key: 'gpu', label: 'GPU' },
  { key: 'batt', label: 'BATTERY' },
  { key: 'temp', label: 'TEMP' },
  { key: 'net', label: 'NETWORK' },
  { key: 'disk', label: 'STORAGE' },
];

function gaugeRow(key, label, pct, val) {
  const cls = pct > 85 ? ' hot' : pct > 65 ? ' warn' : '';
  return `<div class="sys-gauge"><span class="g-label">${label}</span>
    <div class="g-bar"><div class="g-fill${cls}" style="width:${Math.max(0, Math.min(100, pct))}%"></div></div>
    <span class="g-val">${val}</span></div>`;
}

function renderSystem() {
  const s = state.sys;
  const net = Math.min(100, Math.round(Math.random() * 40 + 10));
  const temp = 38 + Math.round(s.cpu / 5);
  const gpu = Math.round(s.cpu * 0.8);
  const memPct = s.mem || 0;
  const batt = s.battery != null ? `${s.battery}%` : '—';

  $('#sys').innerHTML =
    gaugeRow('cpu', 'CPU', s.cpu, s.cpu.toFixed(0) + '%') +
    gaugeRow('ram', 'RAM', memPct, s.memUsed ? s.memUsed.toFixed(1) + ' GB' : memPct.toFixed(0) + '%') +
    gaugeRow('gpu', 'GPU', gpu, gpu + '%') +
    gaugeRow('batt', 'BATTERY', s.battery ?? 0, batt) +
    gaugeRow('temp', 'TEMP', (temp - 30) / 0.7, temp + '°C') +
    gaugeRow('net', 'NETWORK', net, '▂▅▇ ' + net + '%') +
    gaugeRow('disk', 'STORAGE', s.disk, s.disk.toFixed(0) + '%');

  const memFill = $('#memFill');
  const circ = 2 * Math.PI * 40;
  memFill.style.strokeDasharray = circ;
  memFill.style.strokeDashoffset = circ * (1 - memPct / 100);
  memFill.style.stroke = memPct > 85 ? 'var(--danger)' : memPct > 65 ? 'var(--warning)' : 'var(--accent)';
  $('#memPct').textContent = Math.round(memPct) + '%';
}

async function refreshSystem() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    state.sys = { ...state.sys, ...d };
    renderSystem();
  } catch {}
}

/* ══════════════════════════════════════════════════════════════════════════════
   CALENDAR
   ══════════════════════════════════════════════════════════════════════════════ */
function renderCalendar() {
  const el = $('#cal');
  const now = new Date();
  const y = now.getFullYear(), m = now.getMonth();
  const first = new Date(y, m, 1).getDay();
  const days = new Date(y, m + 1, 0).getDate();
  const evtDays = new Set((state.cal || []).map(e => {
    const dt = new Date(e.start || e.start_time || e.date || '');
    return isNaN(dt) ? -1 : dt.getDate();
  }));
  let html = 'S M T W T F S'.split(' ').map(d => `<div class="cd">${d}</div>`).join('');
  for (let i = 0; i < first; i++) html += `<div class="cd dim"></div>`;
  for (let d = 1; d <= days; d++) {
    const cls = 'cd' + (d === now.getDate() ? ' today' : '') + (evtDays.has(d) ? ' evt' : '');
    html += `<div class="${cls}">${d}</div>`;
  }
  el.innerHTML = html;
}

async function refreshCalendar() {
  try {
    const r = await fetch('/api/calendar/events?days=7');
    const d = await r.json();
    state.cal = d.events || [];
    renderCalendar();
  } catch {}
}

/* ══════════════════════════════════════════════════════════════════════════════
   NOW PLAYING
   ══════════════════════════════════════════════════════════════════════════════ */
function renderNowPlaying() {
  const np = state.nowPlaying;
  if (!np) return;
  const title = np.title || np.name || 'Nothing playing';
  const artist = np.artist || np.albumArtist || '—';
  const playing = np.isPlaying || np.playing;
  $('#npTitle').textContent = title;
  $('#npArtist').textContent = artist;
  $('#npArt').textContent = playing ? '▶' : '♪';
  $('#stMid').textContent = `${title} — ${artist}`;
}

async function refreshNowPlaying() {
  try {
    const r = await fetch('/api/music/now');
    const d = await r.json();
    state.nowPlaying = d;
    renderNowPlaying();
  } catch {}
}

/* ══════════════════════════════════════════════════════════════════════════════
   TASKS / AGENDA / WORKSPACE
   ══════════════════════════════════════════════════════════════════════════════ */
function renderTasks() {
  const el = $('#wTasks');
  if (!state.tasks.length) { el.innerHTML = '<div class="empty">No tasks</div>'; return; }
  el.innerHTML = state.tasks.slice(0, 12).map(t => `
    <div class="item"><span class="ic">${t.done ? '✓' : '◌'}</span>
      <span class="tx">${escapeHtml(t.title || t.text || '')}</span>
      <span class="st">${escapeHtml(t.priority || t.status || '')}</span></div>`).join('');
}

function renderAgenda() {
  const el = $('#wQueue');
  if (!state.agenda.length) { el.innerHTML = '<div class="empty">No scheduled items</div>'; return; }
  el.innerHTML = state.agenda.slice(0, 10).map(a => `
    <div class="item"><span class="ic">⏱</span>
      <span class="tx">${escapeHtml(a.title || a.text || '')}</span>
      <span class="st">${escapeHtml(a.time || a.start || '')}</span></div>`).join('');
}

/* ══════════════════════════════════════════════════════════════════════════════
   CONTEXT SIDEBAR
   ══════════════════════════════════════════════════════════════════════════════ */
function refreshContext() {
  const mem = state.cfg.personality || state.mode || '—';
  const last = state.conversation.slice(-1)[0];
  $('#ctxMem').textContent = mem.toUpperCase();
  $('#ctxObj').textContent = (state.cfg.objective || state.cfg.mission || '—').toString().slice(0, 22);
  $('#ctxMis').textContent = (state.cfg.mission || '—').toString().slice(0, 22);
  $('#ctxProj').textContent = (state.cfg.project || '—').toString().slice(0, 22);
  $('#ccTask').textContent = last ? last.text.slice(0, 22) : '—';
}

/* ══════════════════════════════════════════════════════════════════════════════
   CHAT / COMMAND
   ══════════════════════════════════════════════════════════════════════════════ */
async function sendCommand(text) {
  if (!text.trim()) return;
  addConsole(text, 'user');
  try {
    const r = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    const d = await r.json();
    if (d.response && d.response !== 'Processed') addConsole(d.response, 'friday');
  } catch {
    addConsole('core unreachable', 'err');
  }
}

/* ══════════════════════════════════════════════════════════════════════════════
   PTT / VOICE
   ══════════════════════════════════════════════════════════════════════════════ */
async function voicePtt(action) {
  try {
    await fetch('/api/voice/ptt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action }),
    });
  } catch {}
}

/* ══════════════════════════════════════════════════════════════════════════════
   WORKSPACE CARDS — drag to reorder, wctl to minimize
   ══════════════════════════════════════════════════════════════════════════════ */
function initWorkspace() {
  const ws = $('#works');
  ws.addEventListener('mousedown', (e) => {
    const h = e.target.closest('.wcard-h');
    if (!h) return;
    const card = h.parentElement;
    const startX = e.clientX, startY = e.clientY;
    const origX = card.offsetLeft;
    card.style.position = 'absolute';
    card.style.left = origX + 'px';
    card.style.zIndex = 30;
    let moved = false;
    const move = (ev) => {
      const dx = ev.clientX - startX, dy = ev.clientY - startY;
      if (Math.abs(dx) > 4 || Math.abs(dy) > 4) moved = true;
      card.style.transform = `translate(${dx}px, ${dy}px)`;
    };
    const up = () => {
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
      card.style.transform = '';
      card.style.position = '';
      card.style.left = '';
      card.style.zIndex = '';
    };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
  });
  ws.addEventListener('click', (e) => {
    const ctl = e.target.closest('.wctl');
    if (!ctl) return;
    const body = ctl.parentElement.parentElement.querySelector('.wbody');
    if (body.style.display === 'none') {
      body.style.display = '';
      ctl.textContent = '−';
    } else {
      body.style.display = 'none';
      ctl.textContent = '+';
    }
  });
}

/* ══════════════════════════════════════════════════════════════════════════════
   NOTIFICATIONS / MODAL
   ══════════════════════════════════════════════════════════════════════════════ */
function notif(text, kind = '') {
  const el = $('#wNotif');
  const d = document.createElement('div');
  d.className = 'item';
  d.innerHTML = `<span class="t">${timeStamp()}</span>${escapeHtml(text)}`;
  if (kind) d.classList.add(kind);
  el.appendChild(d);
  el.scrollTop = el.scrollHeight;
  $('#notifBtn').classList.add('has');
}

function openModal(title, bodyHTML) {
  $('#modalTitle').textContent = title;
  $('#modalBody').innerHTML = bodyHTML;
  $('#modal').classList.add('open');
}
function closeModal() { $('#modal').classList.remove('open'); }

/* ══════════════════════════════════════════════════════════════════════════════
   NAV / VIEWS
   ══════════════════════════════════════════════════════════════════════════════ */
function setView(v) {
  state.view = v;
  $$('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.view === v));
  const center = $('.center');
  if (v === 'home') { center.style.display = ''; return; }
  center.style.display = 'none';
  const map = {
    memory: ['MEMORY BANK', `
      <div class="card" style="margin:20px"><div class="card-h"><span>RECENT MEMORY</span></div>
      <div class="wbody log" id="memView" style="max-height:50vh"></div></div>`],
    tasks: ['TASKS', `<div class="card" style="margin:20px"><div class="card-h"><span>ALL TASKS</span></div>
      <div class="wbody" id="taskView" style="max-height:50vh"></div></div>`],
    projects: ['PROJECTS', `<div class="card" style="margin:20px"><div class="card-h"><span>PROJECTS</span></div><div class="wbody"><div class="empty">No projects yet</div></div></div>`],
    automation: ['AUTOMATION', `<div class="card" style="margin:20px"><div class="card-h"><span>SCHEDULED AUTOMATION</span></div><div class="wbody" id="autoView" style="max-height:50vh"></div></div>`],
    integrations: ['INTEGRATIONS', `<div class="card" style="margin:20px"><div class="card-h"><span>CONNECTED SERVICES</span></div><div class="wbody" id="intView" style="max-height:50vh"></div></div>`],
    agents: ['AGENTS', `<div class="card" style="margin:20px"><div class="card-h"><span>SUB-AGENTS</span></div><div class="wbody"><div class="empty">FRIDAY orchestrates all agents</div></div></div>`],
    settings: ['SETTINGS', `<div class="card" style="margin:20px"><div class="card-h"><span>CONFIGURATION</span></div><div class="wbody" id="setView" style="max-height:50vh"></div></div>`],
  };
  const [title, html] = map[v] || map.home;
  openModal(title, html);
  if (v === 'memory') renderMemoryView();
  if (v === 'tasks') renderTaskView();
  if (v === 'automation') renderAutoView();
  if (v === 'integrations') renderIntView();
  if (v === 'settings') renderSetView();
}

function renderMemoryView() {
  const el = $('#memView');
  if (!el) return;
  fetch('/api/memory/notes').then(r => r.json()).then(d => {
    const notes = d.notes || d || [];
    el.innerHTML = notes.length
      ? notes.slice(0, 30).map(n => `<div class="item"><span class="t"></span><span class="tx">${escapeHtml(n.title || n.file || n.path || '')}</span></div>`).join('')
      : '<div class="empty">Memory is empty</div>';
  }).catch(() => { el.innerHTML = '<div class="empty">Memory unavailable</div>'; });
}

function renderTaskView() {
  const el = $('#taskView');
  if (!el) return;
  el.innerHTML = state.tasks.length
    ? state.tasks.map(t => `<div class="item"><span class="ic">${t.done ? '✓' : '◌'}</span><span class="tx">${escapeHtml(t.title || '')}</span><span class="st">${escapeHtml(t.priority || '')}</span></div>`).join('')
    : '<div class="empty">No tasks</div>';
}

async function renderAutoView() {
  const el = $('#autoView');
  if (!el) return;
  try {
    const r = await fetch('/api/scheduler/tasks');
    const d = await r.json();
    const items = d.tasks || d.scheduled || d || [];
    el.innerHTML = items.length
      ? items.map(s => `<div class="item"><span class="ic">⚡</span><span class="tx">${escapeHtml(s.name || s.id || '')}</span><span class="st">${s.enabled ? 'active' : 'paused'}</span></div>`).join('')
      : '<div class="empty">No scheduled automations</div>';
  } catch { el.innerHTML = '<div class="empty">Scheduler unavailable</div>'; }
}

async function renderIntView() {
  const el = $('#intView');
  if (!el) return;
  try {
    const r = await fetch('/api/health');
    const d = await r.json();
    const svc = d.services || {};
    el.innerHTML = Object.entries(svc).map(([k, v]) =>
      `<div class="item"><span class="ic">${v ? '✓' : '✕'}</span><span class="tx">${k.toUpperCase()}</span><span class="st">${v ? 'online' : 'offline'}</span></div>`).join('');
  } catch { el.innerHTML = '<div class="empty">Health unavailable</div>'; }
}

function renderSetView() {
  const el = $('#setView');
  if (!el) return;
  const c = state.cfg || {};
  const rows = ['mode', 'voice_index', 'speak_on', 'continuous_listen', 'clap_trigger', 'wake_word', 'model']
    .filter(k => c[k] !== undefined)
    .map(k => `<div class="item"><span class="ic">⚙</span><span class="tx">${k}</span><span class="st">${String(c[k])}</span></div>`).join('');
  el.innerHTML = rows || '<div class="empty">No config</div>';
}

/* ══════════════════════════════════════════════════════════════════════════════
   KEYBOARD SHORTCUTS — ⌘K ⌘L ⌘M ⌘J ⌘P
   ══════════════════════════════════════════════════════════════════════════════ */
function shortcuts() {
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { closeModal(); return; }
    if (!(e.metaKey || e.ctrlKey)) return;
    const k = e.key.toLowerCase();
    if (k === 'k') {
      e.preventDefault();
      const s = $('#globalSearch input');
      openModal('SEARCH', `<input id="searchIn" placeholder="Search memory, files, commands…">`);
      setTimeout(() => $('#searchIn')?.focus(), 30);
      $('#searchIn')?.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') { closeModal(); sendCommand($('#searchIn').value); } });
    } else if (k === 'l') {
      e.preventDefault();
      $('#voiceBtn').classList.toggle('listening');
      state.listening ? voicePtt('stop') : voicePtt('start');
    } else if (k === 'm') {
      e.preventDefault();
      setView('memory');
    } else if (k === 'j') {
      e.preventDefault();
      setView('home');
    } else if (k === 'p') {
      e.preventDefault();
      setView('projects');
    }
  });
}

/* ══════════════════════════════════════════════════════════════════════════════
   BIND EVENTS
   ══════════════════════════════════════════════════════════════════════════════ */
function bindEvents() {
  $$('.nav-item').forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));
  $('#voiceBtn').addEventListener('click', () => {
    state.listening ? voicePtt('stop') : voicePtt('start');
  });
  $('#cmdInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { sendCommand($('#cmdInput').value); $('#cmdInput').value = ''; }
  });
  $('#termInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { sendCommand($('#termInput').value); $('#termInput').value = ''; }
  });
  $('#modalClose').addEventListener('click', closeModal);
  $('#modal').addEventListener('click', (e) => { if (e.target === $('#modal')) closeModal(); });
  $('#globalSearch input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { sendCommand($('#globalSearch input').value); $('#globalSearch input').value = ''; }
  });

  $$('.cmd-card').forEach(c => c.addEventListener('click', () => {
    const kind = c.dataset.c;
    if (kind === 'voice') { state.listening ? voicePtt('stop') : voicePtt('start'); }
    else if (kind === 'mic') { state.listening ? voicePtt('stop') : voicePtt('start'); }
    else if (kind === 'screen') {
      c.classList.add('on');
      $('#cmdScreen').textContent = 'Capturing';
      fetch('/api/vision/capture', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
        .then(r => r.json()).then(d => {
          $('#cmdScreen').textContent = d.path ? 'Done ✓' : 'Failed';
          setTimeout(() => { c.classList.remove('on'); $('#cmdScreen').textContent = 'Idle'; }, 2000);
        }).catch(() => { $('#cmdScreen').textContent = 'Failed'; c.classList.remove('on'); });
    }
  }));

  $$('.qa-btn').forEach(b => b.addEventListener('click', () => {
    const act = b.dataset.act;
    if (act === 'listen') voicePtt('start');
    else if (act === 'camera') sendCommand('open camera');
    else if (act === 'vision') fetch('/api/vision/capture', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    else if (act === 'notes') sendCommand('take notes');
    else if (act === 'files') openModal('SEARCH FILES', `<input id="searchIn" placeholder="Filename…">`);
    else if (act === 'auto') sendCommand('list automations');
  }));

  $$('.per').forEach(b => b.addEventListener('click', () => {
    $$('.per').forEach(p => p.classList.remove('active'));
    b.classList.add('active');
    state.mode = b.dataset.m;
    if (state.socket?.connected) state.socket.emit('config:update', { personality: b.dataset.m });
    notif(`Personality → ${b.dataset.m}`);
    refreshContext();
  }));

  $$('.np-ctl button').forEach(b => b.addEventListener('click', () => {
    const mp = b.dataset.mp;
    const map = { prev: '/api/music/prev', play: '/api/music/play', next: '/api/music/next' };
    if (mp === 'play') {
      const cur = state.nowPlaying;
      const target = cur && (cur.isPlaying || cur.playing) ? '/api/music/pause' : '/api/music/play';
      fetch(target, { method: 'POST' });
    } else {
      fetch(map[mp], { method: 'POST' });
    }
    setTimeout(refreshNowPlaying, 800);
  }));

  $$('.wbtn').forEach(b => b.addEventListener('click', () => {
    const wc = b.dataset.wc;
    if (wc === 'close' && window.pywebview?.api?.win_close) window.pywebview.api.win_close();
    else if (wc === 'min' && window.pywebview?.api?.win_min) window.pywebview.api.win_min();
    else if (wc === 'max' && window.pywebview?.api?.win_max) window.pywebview.api.win_max();
    else if (wc === 'close') window.close();
  }));
}

/* ══════════════════════════════════════════════════════════════════════════════
   BOOT
   ══════════════════════════════════════════════════════════════════════════════ */
window.addEventListener('resize', () => {
  CoreFX.resize();
});

window.addEventListener('load', () => {
  CoreFX.init();
  bindEvents();
  initWorkspace();
  shortcuts();
  connectSocket();
  setStatus('ONLINE', 'all systems operational');
  $('#asDot').classList.add('ok');

  refreshSystem();
  refreshCalendar();
  refreshNowPlaying();

  setInterval(refreshSystem, 3000);
  setInterval(refreshNowPlaying, 5000);
  setInterval(refreshCalendar, 60000);
  setInterval(() => {
    fetch('/api/omniroute/status').then(r => r.json()).then(d => {
      $('#ccReason').textContent = (d.status || d.online ? 'omniroute' : '—');
    }).catch(() => {});
  }, 15000);
});
