// Starfield backdrop, matches other ishimura services.
(function() {
  const canvas = document.getElementById('star-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let w, h, stars;

  function resize() {
    w = canvas.width  = window.innerWidth;
    h = canvas.height = window.innerHeight;
    stars = Array.from({ length: 80 }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      z: Math.random() * 0.8 + 0.2,
    }));
  }
  window.addEventListener('resize', resize);
  resize();

  function tick() {
    ctx.clearRect(0, 0, w, h);
    for (const s of stars) {
      ctx.fillStyle = `rgba(183, 199, 209, ${0.15 + s.z * 0.35})`;
      ctx.fillRect(s.x, s.y, 1.2, 1.2);
      s.y += s.z * 0.15;
      if (s.y > h) { s.y = 0; s.x = Math.random() * w; }
    }
    requestAnimationFrame(tick);
  }
  tick();
})();

// Live log stream on server detail pages.
(function() {
  const panel = document.querySelector('.log-panel');
  if (!panel) return;
  const url    = panel.dataset.logUrl;
  const tail   = panel.querySelector('#log-tail');
  const pause  = panel.querySelector('#log-pause');
  const clear  = panel.querySelector('#log-clear');
  const follow = panel.querySelector('#log-follow');
  const status = panel.querySelector('#log-status');

  const MAX_LINES = 2000;
  let paused  = false;
  let es      = null;

  function setStatus(kind, text) {
    status.className = 'log-status log-status-' + kind;
    status.textContent = text;
  }

  function classify(line) {
    const l = line.toLowerCase();
    if (l.includes('error') || l.includes('failed') || l.includes('fatal')) return 'err';
    if (l.includes('warn')) return 'warn';
    if (line.startsWith('---') || line.startsWith('===')) return 'meta';
    return '';
  }

  function append(line) {
    const div = document.createElement('div');
    const cls = classify(line);
    if (cls) div.className = cls;
    div.textContent = line;
    tail.appendChild(div);
    while (tail.children.length > MAX_LINES) tail.removeChild(tail.firstChild);
    if (follow.checked) tail.scrollTop = tail.scrollHeight;
  }

  function connect() {
    setStatus('connecting', 'CONNECTING');
    es = new EventSource(url);
    es.onopen    = () => setStatus('live',  'LIVE');
    es.onerror   = () => {
      setStatus('lost', 'RECONNECTING');
      // EventSource auto-reconnects on error per its retry: field; no manual re-open needed.
    };
    es.onmessage = (e) => {
      if (paused) return;
      append(e.data);
    };
  }

  pause.addEventListener('click', () => {
    paused = !paused;
    pause.textContent = paused ? 'RESUME' : 'PAUSE';
    pause.classList.toggle('paused', paused);
    if (paused) setStatus('paused', 'PAUSED');
    else        setStatus('live',   'LIVE');
  });

  clear.addEventListener('click', () => { tail.innerHTML = ''; });

  // Scrolling up manually turns off follow; scrolling back to bottom re-enables.
  tail.addEventListener('scroll', () => {
    const atBottom = tail.scrollTop + tail.clientHeight >= tail.scrollHeight - 12;
    if (!atBottom && follow.checked) follow.checked = false;
    if (atBottom && !follow.checked) follow.checked = true;
  });

  connect();
})();

// Tab switching on server detail page.
(function() {
  const strip = document.querySelector('.tab-strip');
  if (!strip) return;
  strip.addEventListener('click', (e) => {
    const btn = e.target.closest('.tab-btn');
    if (!btn) return;
    const target = btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b =>
      b.classList.toggle('is-active', b === btn));
    document.querySelectorAll('.tab-pane').forEach(p =>
      p.classList.toggle('is-active', p.dataset.tabPane === target));
    // Refresh players when the tab is opened.
    if (target === 'players' && window.hangarPlayers) window.hangarPlayers.refresh();
  });
})();

// Cheatsheet - fetched once on load, click-to-insert into console input.
(function() {
  const page = document.querySelector('.server-page');
  if (!page || page.dataset.cheatsheetSupported !== 'true') return;
  const body  = document.getElementById('cheatsheet-body');
  const input = document.getElementById('console-input');
  const slug  = page.dataset.slug;

  function esc(s) {
    return String(s).replace(/[&<>"']/g, c => (
      { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]
    ));
  }

  fetch(`/server/${slug}/cheatsheet`, { headers: { 'Accept': 'application/json' } })
    .then(r => r.ok ? r.json() : null)
    .then(data => {
      if (!data || !data.categories) {
        body.textContent = 'unavailable';
        return;
      }
      body.innerHTML = data.categories.map(cat => `
        <div class="cheat-category">
          <div class="cheat-category-name">${esc(cat.category)}</div>
          ${cat.commands.map(c => `
            <div class="cheat-row" data-insert="${esc(c.cmd + (c.args ? ' ' + c.args : ''))}">
              <div class="cheat-name">${esc(c.cmd)}${c.args ? '<span class="args">' + esc(c.args) + '</span>' : ''}</div>
              <div class="cheat-desc">${esc(c.desc)}</div>
            </div>
          `).join('')}
        </div>
      `).join('');
    })
    .catch(() => { body.textContent = 'unavailable'; });

  body.addEventListener('click', (e) => {
    const row = e.target.closest('.cheat-row');
    if (!row || !input) return;
    input.value = row.dataset.insert;
    input.focus();
    // If there's a placeholder like <message>, select it so the user can type-over.
    const m = input.value.match(/<[^>]+>/);
    if (m) {
      const start = input.value.indexOf(m[0]);
      input.setSelectionRange(start, start + m[0].length);
    }
  });
})();

// Settings tab - load current + available options, POST /server/<slug>/change on apply.
(function() {
  const page = document.querySelector('.server-page');
  if (!page || page.dataset.changeSupported !== 'true') return;
  const slug     = page.dataset.slug;
  const status   = document.getElementById('settings-status');
  const form     = document.getElementById('settings-form');
  const selMap   = document.getElementById('setting-map');
  const selGT    = document.getElementById('setting-gametype');
  const selDiff  = document.getElementById('setting-difficulty');
  const selLen   = document.getElementById('setting-length');
  const restart  = document.getElementById('settings-restart');

  function fill(sel, options, currentValue) {
    sel.innerHTML = options.map(o =>
      `<option value="${o.value}"${o.value === currentValue ? ' selected' : ''}>${o.label}</option>`
    ).join('');
  }

  function setStatus(kind, text) {
    status.className = 'log-status log-status-' + kind;
    status.textContent = text;
  }

  async function load() {
    setStatus('connecting', 'LOADING');
    try {
      const r = await fetch(`/server/${slug}/change/options`, {
        headers: { 'Accept': 'application/json' },
      });
      if (!r.ok) throw new Error('bad status');
      const data = await r.json();
      fill(selMap,  data.maps      || [], data.current?.map      || '');
      fill(selGT,   data.gametypes || [], data.current?.gametype || '');
      fill(selDiff, data.difficulties || [], data.current?.difficulty || '0');
      fill(selLen,  data.lengths || [], data.current?.length || '0');
      setStatus('live', 'READY');
    } catch (e) {
      setStatus('lost', 'UNAVAILABLE');
    }
  }

  async function apply(restartOnly) {
    setStatus('connecting', restartOnly ? 'RESTARTING' : 'APPLYING');
    try {
      const body = restartOnly
        ? { restart: true }
        : {
            map:        selMap.value,
            gametype:   selGT.value,
            difficulty: selDiff.value,
            length:     selLen.value,
          };
      const r = await fetch(`/server/${slug}/change`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await r.json().catch(() => ({}));
      if (data.ok) setStatus('live', restartOnly ? 'RESTARTED' : 'APPLIED');
      else         setStatus('lost', 'FAILED');
    } catch (e) {
      setStatus('lost', 'ERROR');
    }
  }

  form.addEventListener('submit', (e) => { e.preventDefault(); apply(false); });
  restart.addEventListener('click', () => {
    if (confirm('Restart current map? Any active players will reconnect.')) apply(true);
  });

  // Load only when the tab is first shown so we don't hammer WebAdmin on page load.
  let loaded = false;
  document.querySelector('.tab-strip').addEventListener('click', (e) => {
    const btn = e.target.closest('.tab-btn');
    if (btn && btn.dataset.tab === 'settings' && !loaded) {
      loaded = true;
      load();
    }
  });
})();

// Console command form - POST to /server/<slug>/console, echo to history pane.
(function() {
  const form = document.getElementById('console-form');
  if (!form) return;
  const page = document.querySelector('.server-page');
  const slug = page.dataset.slug;
  const input = document.getElementById('console-input');
  const history = document.getElementById('console-history');

  function append(cls, text) {
    const div = document.createElement('div');
    div.className = cls;
    div.textContent = text;
    history.appendChild(div);
    history.scrollTop = history.scrollHeight;
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const cmd = input.value.trim();
    if (!cmd) return;
    append('cmd-echo', '> ' + cmd);
    input.value = '';
    input.disabled = true;
    try {
      const r = await fetch(`/server/${slug}/console`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ command: cmd }),
      });
      const data = await r.json().catch(() => ({}));
      if (data.ok) append('cmd-ok',  data.result || 'sent');
      else         append('cmd-err', data.error || 'send failed');
    } catch (err) {
      append('cmd-err', 'network error');
    } finally {
      input.disabled = false;
      input.focus();
    }
  });
})();

// Players table - polls /server/<slug>/players. Exposed as hangarPlayers so
// the tab click can trigger a refresh on demand.
(function() {
  const panel = document.querySelector('.players-panel');
  if (!panel) return;
  const page = document.querySelector('.server-page');
  const slug = page.dataset.slug;
  const kickOK = page.dataset.kickSupported === 'true';
  const banOK  = page.dataset.banSupported  === 'true';
  const body   = document.getElementById('players-body');
  const count  = document.getElementById('players-count');
  const refresh = document.getElementById('players-refresh');

  function esc(s) {
    return String(s).replace(/[&<>"']/g, c => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  function actionCell(p) {
    if (!kickOK && !banOK) return '<td class="actions-cell">---</td>';
    const buttons = [];
    if (kickOK) buttons.push(`<button type="button" class="btn-mini btn-kick" data-act="kick" data-pid="${esc(p.id)}">KICK</button>`);
    if (banOK)  buttons.push(`<button type="button" class="btn-mini btn-ban"  data-act="ban"  data-pid="${esc(p.id)}">BAN</button>`);
    return `<td class="actions-cell">${buttons.join(' ')}</td>`;
  }

  function render(players) {
    count.textContent = players.length + (players.length === 1 ? ' player' : ' players');
    count.className = 'log-status ' + (players.length ? 'log-status-live' : 'log-status-connecting');
    if (!players.length) {
      body.innerHTML = '<tr class="empty-row"><td colspan="4">no players</td></tr>';
      return;
    }
    body.innerHTML = players.map(p => `
      <tr>
        <td class="name-cell">${esc(p.name)}</td>
        <td>${esc(p.ping)}</td>
        <td>${esc(p.score)}</td>
        ${actionCell(p)}
      </tr>
    `).join('');
  }

  async function refreshOnce() {
    count.textContent = 'polling';
    count.className = 'log-status log-status-connecting';
    try {
      const r = await fetch(`/server/${slug}/players`, { headers: { 'Accept': 'application/json' } });
      const data = await r.json().catch(() => ({}));
      render(data.players || []);
    } catch (e) {
      count.textContent = 'error';
      count.className = 'log-status log-status-lost';
    }
  }

  body.addEventListener('click', async (e) => {
    const btn = e.target.closest('button[data-act]');
    if (!btn) return;
    const act = btn.dataset.act;
    const pid = btn.dataset.pid;
    if (act === 'ban' && !confirm(`Ban ${pid}? This session-bans them from the server.`)) return;
    btn.disabled = true;
    try {
      const r = await fetch(`/server/${slug}/players/${encodeURIComponent(pid)}/${act}`, {
        method: 'POST',
        headers: { 'Accept': 'application/json' },
      });
      const data = await r.json().catch(() => ({}));
      if (!data.ok) alert(`${act} failed`);
    } finally {
      setTimeout(refreshOnce, 500);
    }
  });

  refresh.addEventListener('click', refreshOnce);
  window.hangarPlayers = { refresh: refreshOnce };
  refreshOnce();
})();

// Auto-refresh status on server list every 10s.
(function() {
  if (!document.querySelector('.bay-grid')) return;
  function tick() {
    fetch('/api/servers', { headers: { 'Accept': 'application/json' } })
      .then(r => r.ok ? r.json() : null)
      .then(list => {
        if (!list) return;
        for (const s of list) {
          const el = document.querySelector(`.bay[href$="/server/${s.slug}"]`);
          if (!el) continue;
          const active = s.active === 'active';
          el.classList.toggle('bay-up',   active);
          el.classList.toggle('bay-down', !active);
          const dot = el.querySelector('.status-dot');
          if (dot) { dot.classList.toggle('dot-up', active); dot.classList.toggle('dot-down', !active); }
          const state = el.querySelector('.bay-state');
          if (state) state.textContent = (s.active || 'unknown').toUpperCase();
          const pcSlot = el.querySelector('.player-badge');
          if (pcSlot) {
            if (s.player_count === null || s.player_count === undefined) {
              pcSlot.remove();
            } else {
              pcSlot.textContent = s.player_count + ' PLAYER' + (s.player_count === 1 ? '' : 'S');
              pcSlot.classList.toggle('zero', s.player_count === 0);
            }
          } else if (typeof s.player_count === 'number') {
            const nb = document.createElement('span');
            nb.className = 'player-badge' + (s.player_count === 0 ? ' zero' : '');
            nb.textContent = s.player_count + ' PLAYER' + (s.player_count === 1 ? '' : 'S');
            const head = el.querySelector('.bay-head');
            if (head) head.appendChild(nb);
          }
        }
      })
      .catch(() => {});
  }
  setInterval(tick, 10000);
})();
