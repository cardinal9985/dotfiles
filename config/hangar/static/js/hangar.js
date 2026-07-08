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

// Auto-refresh status on server list every 10s.
(function() {
  if (!document.querySelector('.bay-grid')) return;
  setInterval(async () => {
    try {
      const r = await fetch('/api/servers', { headers: { 'Accept': 'application/json' } });
      if (!r.ok) return;
      const list = await r.json();
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
      }
    } catch (e) { /* ignore */ }
  }, 10000);
})();
