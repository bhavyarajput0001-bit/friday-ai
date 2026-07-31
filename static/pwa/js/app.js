(function() {
  const $ = id => document.getElementById(id);
  const convo = $('conversation'), input = $('cmdInput'), sendBtn = $('sendBtn');
  const statusDot = $('statusDot'), statusText = $('statusText');
  let socket = null;

  function connect() {
    socket = io({ reconnection: true, reconnectionDelay: 1000 });
    socket.on('connect', () => { setStatus(true); fetchScenes(); fetchStatus(); });
    socket.on('disconnect', () => setStatus(false));
    socket.on('conversation:message', addMessage);
    socket.on('system:stats', updateSysPanel);
    socket.on('scenes:data', renderScenes);
  }

  function setStatus(connected) {
    statusDot.style.background = connected ? 'var(--green)' : '#ff4757';
    statusText.textContent = connected ? 'ACTIVE' : 'OFFLINE';
    statusText.style.color = connected ? '' : '#ff4757';
  }

  function addMessage(msg) {
    const div = document.createElement('div');
    div.className = `msg ${msg.sender === 'user' ? 'user' : 'friday'}`;
    const text = msg.sender !== 'user' ? renderMarkdown(msg.text) : escapeHtml(msg.text);
    div.innerHTML = `
      <div class="avatar">${msg.sender === 'user' ? '👤' : '🤖'}</div>
      <div>
        <div class="bubble">${text}</div>
        <div class="time">${msg.time || ''}</div>
      </div>`;
    const typing = convo.querySelector('.typing');
    if (typing) typing.remove();
    convo.appendChild(div);
    convo.scrollTop = convo.scrollHeight;
  }

  function showTyping() {
    const existing = convo.querySelector('.typing');
    if (existing) return;
    const div = document.createElement('div');
    div.className = 'msg friday typing';
    div.innerHTML = '<div class="avatar">🤖</div><div class="bubble typing"><span></span><span></span><span></span></div>';
    convo.appendChild(div);
    convo.scrollTop = convo.scrollHeight;
  }

  function renderMarkdown(text) {
    let h = escapeHtml(text);
    h = h.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    h = h.replace(/`([^`]+)`/g, '<code>$1</code>');
    h = h.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    h = h.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    h = h.replace(/^- (.+)$/gm, '• $1<br>');
    h = h.replace(/\n/g, '<br>');
    return h;
  }

  function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
  }

  function sendCommand(text) {
    if (!text) return;
    socket.emit('command:send', { text });
    addMessage({ sender: 'user', text, time: new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) });
    showTyping();
    input.value = '';
  }

  function fetchScenes() {
    socket.emit('scenes:list');
  }

  function renderScenes(scenes) {
    const grid = document.getElementById('sceneGrid');
    if (!grid || !scenes) return;
    grid.innerHTML = '';
    const icons = { coding:'💻', movie:'🎬', focus:'🎯', meeting:'📋', cleanup:'🧹', morning:'☀️' };
    scenes.forEach(s => {
      const btn = document.createElement('button');
      btn.className = 'c-btn';
      btn.innerHTML = `${icons[s.id]||'⚡'} ${s.name}`;
      btn.addEventListener('click', () => {
        socket.emit('scene:run', { scene: s.id });
        sendCommandViaRest(`${s.name} mode`);
      });
      grid.appendChild(btn);
    });
  }

  async function fetchStatus() {
    try {
      const r = await fetch('/api/status');
      const d = await r.json();
      updateSysPanel(d);
    } catch(e) {}
    try {
      const r = await fetch('/api/omniroute/status');
      const d = await r.json();
      const el = document.getElementById('sOmni');
      if (el) el.textContent = d.available ? '✅' : '❌';
    } catch(e) {}
  }

  function updateSysPanel(stats) {
    $('sCpu').textContent = stats.cpu + '%';
    $('sRam').textContent = stats.mem_percent + '%';
    $('sSsd').textContent = stats.disk_percent + '%';
    $('sBat').textContent = stats.battery != null ? stats.battery + '%' : 'N/A';
  }

  async function sendCommandViaRest(text) {
    try {
      await fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ text })
      });
    } catch(e) {}
  }

  input.addEventListener('keydown', e => { if (e.key === 'Enter') sendCommand(input.value.trim()); });
  sendBtn.addEventListener('click', () => sendCommand(input.value.trim()));

  document.querySelectorAll('[data-cmd]').forEach(btn => {
    btn.addEventListener('click', () => {
      const cmd = btn.dataset.cmd;
      if (cmd === 'system status') {
        document.getElementById('sysPanel').classList.toggle('open');
        fetchStatus();
      } else {
        sendCommand(cmd);
      }
    });
  });

  setInterval(fetchStatus, 15000);
  connect();

  const sysPanel = document.getElementById('sysPanel');
  sysPanel.addEventListener('click', () => sysPanel.classList.remove('open'));

  fetchStatus();
})();
