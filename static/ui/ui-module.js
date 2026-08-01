/* ══════════════════════════════════════════════════════════════════════════════
   FRIDAY UI MODULE — injected into EVERY interface.
   Floating menubar dock + interface gallery (thumbnails, preview, switch)
   + a slot to create / scaffold brand-new interfaces.
   Works on dark AND light themes. Loads itself; no dependencies.
   ══════════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';
  const CSS = '/ui/ui-module.css';
  const MODULE_ID = 'fridayUiModule';
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));

  const SELF = (function () {
    try { return document.currentScript && document.currentScript.src; } catch (e) { return null; }
  })();
  const IN_UI_PREVIEW = /\/ui\/[^/]+\//.test(location.pathname);
  const CURRENT_UI = (function () {
    if (location.pathname.startsWith('/dashboard')) return 'legacy';
    if (location.pathname.startsWith('/pwa/')) return 'pwa';
    const m = location.pathname.match(/\/ui\/([^/]+)\//);
    if (m) return m[1];
    return null; // served at / -> resolved from server's active_ui
  })();

  /* ── helpers ── */
  function esc(s) {
    return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  async function api(path, opts) {
    try {
      const r = await fetch(path, opts);
      return await r.json();
    } catch (e) { return { ok: false, error: 'unreachable' }; }
  }

  let REGISTRY = { uis: [], active: null };

  /* ═══ build the DOM ═══ */
  function build() {
    const wrap = document.createElement('div');
    wrap.id = MODULE_ID;
    wrap.innerHTML = `
      <div id="fridayUiDock" title="Switch interface">
        <span class="fud-ic">▦</span>
        <span class="fud-name">Interfaces</span>
        <span class="fud-chef" id="fudActive">—</span>
      </div>

      <div id="fridayUiOverlay">
        <div id="fridayUiGallery">
          <div id="fridayUiGalleryHead">
            <div>
              <div class="fuh-title">FRIDAY Interfaces</div>
              <div class="fuh-sub">Preview, switch, or build a new interface — available in every theme.</div>
            </div>
            <button id="fridayUiClose">✕</button>
          </div>
          <div id="fridayUiGrid"></div>
        </div>
      </div>

      <div id="fridayUiPreview">
        <div id="fridayUiPrevHead">
          <span id="fridayUiPrevTitle">Preview</span>
          <div class="fupb">
            <button class="fup-btn" id="fridayUiPrevBack">← Back</button>
            <button class="fup-btn switch" id="fridayUiPrevSwitch">◉ Switch to this</button>
          </div>
        </div>
        <iframe id="fridayUiPrevFrame"></iframe>
      </div>

      <div id="fridayUiCreate">
        <div id="fridayUiCreateBox">
          <h3>Design a new interface</h3>
          <div class="fuc-sub">Scaffold a fresh FRIDAY theme right here — it appears in the gallery for preview & switching instantly.</div>
          <div class="fuc-field"><label>NAME</label><input id="fucName" placeholder="e.g. FRIDAY Neon"></div>
          <div class="fuc-field"><label>ID (url-safe, unique)</label><input id="fucId" placeholder="e.g. neon"></div>
          <div class="fuc-field"><label>DESCRIPTION</label><textarea id="fucDesc" placeholder="A short line describing the design…"></textarea></div>
          <div class="fuc-field"><label>START FROM TEMPLATE</label>
            <select id="fucTemplate">
              <option value="glass">FRIDAY Glass (light, frosted)</option>
              <option value="mission">FRIDAY OS (dark, deep-navy)</option>
              <option value="blank">Blank canvas</option>
            </select>
          </div>
          <div class="fuc-acts">
            <button class="fuc-btn cancel" id="fucCancel">Cancel</button>
            <button class="fuc-btn create" id="fucCreate">Create interface</button>
          </div>
          <div id="fridayUiCreateMsg"></div>
        </div>
      </div>`;

    document.body.appendChild(wrap);

    const link = document.createElement('link');
    link.rel = 'stylesheet'; link.href = CSS;
    document.head.appendChild(link);

    bind();
  }

  /* ═══ gallery render ═══ */
  function renderGallery() {
    const grid = $('#fridayUiGrid');
    const uis = REGISTRY.uis || [];
    const activeId = REGISTRY.active || CURRENT_UI;

    const cards = uis.map(u => {
      const isActive = u.id === activeId;
      const kindTag = isActive ? 'active' : u.kind || 'current';
      return `
      <div class="fui-card${isActive ? ' active' : ''}" data-ui="${esc(u.id)}">
        <div class="fui-thumb" data-preview="${esc(u.id)}">
          ${isActive ? '<span class="fui-tag active">● active</span>' : `<span class="fui-tag ${esc(u.kind || 'current')}">${esc(u.kind || 'current')}</span>`}
          <img src="${esc(u.thumb || '')}" alt="${esc(u.name)}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
          <span class="fui-ph" style="display:none">◈</span>
          <div class="fui-hover"><button class="fui-eyebtn" data-preview="${esc(u.id)}">👁 Preview</button></div>
        </div>
        <div class="fui-body">
          <div class="fui-name"><b>${esc(u.name)}</b><em>v${esc(u.version)}</em></div>
          <div class="fui-desc">${esc(u.desc)}</div>
          <div class="fui-acts">
            <button class="fui-btn preview" data-preview="${esc(u.id)}">Preview</button>
            ${isActive
              ? '<button class="fui-btn active" disabled>● Active</button>'
              : `<button class="fui-btn switch" data-switch="${esc(u.id)}">◉ Switch</button>`}
          </div>
        </div>
      </div>`;
    }).join('');

    const addSlot = `
      <div class="fui-add" id="fuiAddNew">
        <div class="fa-plus">＋</div>
        <div class="fa-label">Design New Interface</div>
        <div class="fa-sub">Add a slot, scaffold a theme, start fresh</div>
      </div>`;

    grid.innerHTML = cards + addSlot;
    $('#fudActive').textContent = (activeId || '—').toUpperCase();

    $$('[data-preview]', grid).forEach(b => b.addEventListener('click', () => openPreview(b.dataset.preview)));
    $$('[data-switch]', grid).forEach(b => b.addEventListener('click', () => switchTo(b.dataset.switch)));
    $('#fuiAddNew').addEventListener('click', () => openCreate());
  }

  /* ═══ actions ═══ */
  async function loadRegistry() {
    const d = await api('/api/ui');
    if (d && d.uis) { REGISTRY = d; renderGallery(); }
    else $('#fudActive').textContent = 'OFFLINE';
  }

  async function switchTo(id) {
    const d = await api('/api/ui/activate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    });
    if (d.ok) {
      $('#fridayUiOverlay').classList.remove('open');
      setTimeout(() => { location.href = d.path; }, 350);
    } else {
      flash('switch failed: ' + (d.error || 'unknown'));
    }
  }

  function openPreview(id) {
    const u = (REGISTRY.uis || []).find(x => x.id === id);
    if (!u) return;
    $('#fridayUiPrevTitle').textContent = 'Previewing — ' + u.name + ' (v' + u.version + ')';
    $('#fridayUiPrevSwitch').dataset.switch = id;
    $('#fridayUiPrevSwitch').style.display = u.id === REGISTRY.active ? 'none' : '';
    $('#fridayUiPrevFrame').src = u.path;
    $('#fridayUiOverlay').classList.remove('open');
    $('#fridayUiPreview').classList.add('open');
  }

  function openCreate() {
    $('#fucName').value = ''; $('#fucId').value = '';
    $('#fucDesc').value = ''; $('#fucTemplate').value = 'glass';
    $('#fridayUiCreateMsg').textContent = ''; $('#fridayUiCreateMsg').className = '';
    $('#fridayUiCreate').classList.add('open');
  }

  async function createUI() {
    const name = $('#fucName').value.trim();
    const id = $('#fucId').value.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_');
    const desc = $('#fucDesc').value.trim();
    const template = $('#fucTemplate').value;
    const msg = $('#fridayUiCreateMsg');
    msg.className = '';
    if (!name) { msg.textContent = 'Give your interface a name.'; msg.classList.add('err'); return; }
    if (!id) { msg.textContent = 'Give it a url-safe id (e.g. neon).'; msg.classList.add('err'); return; }
    if (!/^[a-z0-9_]+$/.test(id)) { msg.textContent = 'id must be letters/numbers/underscore only.'; msg.classList.add('err'); return; }
    msg.textContent = 'Creating…';
    const d = await api('/api/ui/create', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, name, desc, template }),
    });
    if (d.ok) {
      msg.textContent = 'Created ✓ — opening your new interface.';
      await loadRegistry();
      $('#fridayUiCreate').classList.remove('open');
      setTimeout(() => { location.href = d.ui.path; }, 600);
    } else {
      msg.textContent = 'Failed: ' + (d.error || 'unknown');
      msg.classList.add('err');
    }
  }

  function flash(text) {
    $('#fudActive').textContent = text.toUpperCase();
    setTimeout(() => $('#fudActive').textContent = (REGISTRY.active || CURRENT_UI || '—').toUpperCase(), 1800);
  }

  function bind() {
    $('#fridayUiDock').addEventListener('click', () => {
      loadRegistry();
      $('#fridayUiOverlay').classList.add('open');
    });
    $('#fridayUiClose').addEventListener('click', () => $('#fridayUiOverlay').classList.remove('open'));
    $('#fridayUiOverlay').addEventListener('click', (e) => { if (e.target === $('#fridayUiOverlay')) $('#fridayUiOverlay').classList.remove('open'); });

    $('#fridayUiPrevBack').addEventListener('click', () => {
      $('#fridayUiPreview').classList.remove('open');
      $('#fridayUiPrevFrame').src = 'about:blank';
      $('#fridayUiOverlay').classList.add('open');
    });
    $('#fridayUiPrevSwitch').addEventListener('click', () => switchTo($('#fridayUiPrevSwitch').dataset.switch));

    $('#fucCancel').addEventListener('click', () => $('#fridayUiCreate').classList.remove('open'));
    $('#fucCreate').addEventListener('click', createUI);
    $('#fucName').addEventListener('input', () => {
      if (!$('#fucId').value.trim()) {
        $('#fucId').value = $('#fucName').value.toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '');
      }
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        $('#fridayUiOverlay').classList.remove('open');
        $('#fridayUiPreview').classList.remove('open');
        $('#fridayUiCreate').classList.remove('open');
      }
    });
  }

  /* ── keyboard: ⌘U opens the gallery ── */
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'u') {
      e.preventDefault();
      if ($('#fridayUiOverlay').classList.contains('open')) {
        $('#fridayUiOverlay').classList.remove('open');
      } else {
        loadRegistry();
        $('#fridayUiOverlay').classList.add('open');
      }
    }
  });

  function init() {
    build();
    loadRegistry();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
