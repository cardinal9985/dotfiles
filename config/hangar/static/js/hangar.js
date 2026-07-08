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
