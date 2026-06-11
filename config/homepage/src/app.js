/* ── Audio ── */
var audioCtx = null;
var audioUnlocked = false;

function unlockAudio() {
  if (audioUnlocked) return;
  audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  if (audioCtx.state === 'suspended') audioCtx.resume();
  audioUnlocked = true;
}

function beep(freq, duration, vol) {
  if (!audioUnlocked) return;
  try {
    var osc  = audioCtx.createOscillator();
    var gain = audioCtx.createGain();
    osc.type = 'square';
    osc.frequency.value = freq;
    gain.gain.value = vol || 0.06;
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
    osc.stop(audioCtx.currentTime + duration);
  } catch(e) {}
}

function clickBeep() { beep(1200, 0.03, 0.02); }

document.addEventListener('click',   unlockAudio, { once: true });
document.addEventListener('keydown', unlockAudio, { once: true });

/* ── Quotes ── */
var QUOTES = [
  '"Make us whole!"',
  '"Convergence is at hand."',
  '"Fear not. It\'s just death."',
  '"Welcome back, Nicole Brennan."',
  '"Unity after death, unity forever."',
  '"The pilgrimage is at hand! Unity is at hand!"',
  '"The Moon IS Convergence!"',
  '"Worst bloody career move of my life."',
  '"Who could do that much damage to a Planet Cracker?"',
  '"Cut off their limbs."',
  '"Riskier than running out of air?"',
  '"We can be whole again."',
  '"Twinkle twinkle little star..."',
  '"Altman be praised!"',
  '"Marker be praised!"',
  '"The Black Marker is within reach!"',
];

var quoteIdx = Math.floor(Math.random() * QUOTES.length);
var quoteEl  = document.getElementById('quote');

quoteEl.textContent = QUOTES[quoteIdx];

function cycleQuote() {
  quoteEl.classList.add('fade');
  setTimeout(function () {
    quoteIdx = (quoteIdx + 1 + Math.floor(Math.random() * (QUOTES.length - 1))) % QUOTES.length;
    quoteEl.textContent = QUOTES[quoteIdx];
    quoteEl.classList.remove('fade');
  }, 800);
}

setInterval(cycleQuote, 12000 + Math.random() * 8000);

/* ── ASCII glitch ── */
var asciiEl = document.getElementById('ascii-art');
function triggerGlitch() {
  asciiEl.classList.add('glitch');
  setTimeout(function () {
    asciiEl.classList.remove('glitch');
  }, 150);
  scheduleGlitch();
}
function scheduleGlitch() {
  setTimeout(triggerGlitch, 6000 + Math.random() * 9000);
}
scheduleGlitch();

/* ── Services ── */
function renderServices(services) {
  var grid = document.getElementById('service-grid');
  grid.innerHTML = '';
  services.forEach(function (svc) {
    var dotId = 'dot-' + encodeURIComponent(svc.name);
    var a = document.createElement('a');
    a.href = svc.url;
    a.target = '_blank';
    a.rel = 'noopener';
    a.setAttribute('data-icon', svc.icon || '▣');
    a.innerHTML = svc.name + '<span class="svc-dot" id="' + dotId + '"></span>';
    a.addEventListener('mouseenter', clickBeep);
    grid.appendChild(a);
    checkStatus(svc, dotId);
  });
}

async function checkStatus(svc, dotId) {
  var dot = document.getElementById(dotId);
  if (!dot) return;
  /* use same-origin nginx proxy path when available, avoids CORS */
  var checkUrl = svc.statusPath || svc.url;
  try {
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 4000);
    var opts = svc.statusPath ? {} : { mode: 'no-cors' };
    var res = await fetch(checkUrl, Object.assign(opts, { signal: controller.signal }));
    clearTimeout(timer);
    dot.className = svc.statusPath ? (res.ok ? 'svc-dot online' : 'svc-dot') : 'svc-dot online';
  } catch (_) {
    dot.className = 'svc-dot';
  }
}

fetch('services.json')
  .then(function (r) { return r.json(); })
  .then(renderServices)
  .catch(function () {
    document.getElementById('service-grid').innerHTML =
      '<div style="color:var(--yellow);font-size:0.8rem;opacity:0.7">[SERVICE MANIFEST UNAVAILABLE]</div>';
  });

/* ── Canvas: stars + shooting stars + constellations ── */
var starCanvas = document.getElementById('star-canvas');
var sCtx = starCanvas.getContext('2d');
var stars = [];
var shootingStars = [];
var activeConstellation = null;

function initStarfield() {
  starCanvas.width  = window.innerWidth;
  starCanvas.height = window.innerHeight;
  stars = [];
  for (var i = 0; i < 200; i++) {
    stars.push({
      x:            Math.random() * starCanvas.width,
      y:            Math.random() * starCanvas.height,
      r:            Math.random() * 1.5 + 0.3,
      brightness:   Math.random() * 0.5 + 0.3,
      twinkleSpeed: Math.random() * 0.005 + 0.001,
      twinkleOffset: Math.random() * Math.PI * 2,
    });
  }
}

/* Constellation data: positions normalized 0–1, mag = star magnitude (lower = brighter). */
var CONSTELLATIONS = [
  {
    name: 'Orion',
    stars: [
      { x: 0.05, y: 0.10, mag: 0.5  },  /* Betelgeuse */
      { x: 0.55, y: 0.05, mag: 1.6  },  /* Bellatrix  */
      { x: 0.25, y: 0.40, mag: 1.7  },  /* Alnitak    */
      { x: 0.38, y: 0.42, mag: 1.7  },  /* Alnilam    */
      { x: 0.52, y: 0.45, mag: 2.2  },  /* Mintaka    */
      { x: 0.20, y: 0.95, mag: 0.1  },  /* Rigel      */
      { x: 0.65, y: 0.85, mag: 2.1  },  /* Saiph      */
    ],
    lines: [[0,1],[0,2],[1,4],[2,3],[3,4],[2,5],[4,6],[5,6]],
  },
  {
    name: 'Big Dipper',
    stars: [
      { x: 0.05, y: 0.10, mag: 1.8 },  /* Dubhe   */
      { x: 0.25, y: 0.30, mag: 2.4 },  /* Merak   */
      { x: 0.45, y: 0.35, mag: 2.4 },  /* Phecda  */
      { x: 0.35, y: 0.15, mag: 3.3 },  /* Megrez  */
      { x: 0.60, y: 0.25, mag: 1.8 },  /* Alioth  */
      { x: 0.80, y: 0.35, mag: 2.2 },  /* Mizar   */
      { x: 1.00, y: 0.50, mag: 1.9 },  /* Alkaid  */
    ],
    lines: [[0,1],[1,2],[2,3],[3,0],[3,4],[4,5],[5,6]],
  },
  {
    name: 'Cassiopeia',
    stars: [
      { x: 0.00, y: 0.50, mag: 2.2 },  /* Schedar  */
      { x: 0.25, y: 0.05, mag: 2.3 },  /* Caph     */
      { x: 0.50, y: 0.55, mag: 2.5 },  /* Gamma    */
      { x: 0.75, y: 0.10, mag: 2.7 },  /* Ruchbah  */
      { x: 1.00, y: 0.50, mag: 3.4 },  /* Segin    */
    ],
    lines: [[0,1],[1,2],[2,3],[3,4]],
  },
  {
    name: 'Crux',
    stars: [
      { x: 0.50, y: 1.00, mag: 0.8 },  /* Acrux   */
      { x: 0.95, y: 0.50, mag: 1.3 },  /* Mimosa  */
      { x: 0.50, y: 0.00, mag: 1.6 },  /* Gacrux  */
      { x: 0.10, y: 0.55, mag: 2.8 },  /* Imai    */
    ],
    lines: [[0,2],[1,3]],
  },
  {
    name: 'Lyra',
    stars: [
      { x: 0.50, y: 0.00, mag: 0.0 },  /* Vega     */
      { x: 0.30, y: 0.40, mag: 3.3 },  /* Zeta     */
      { x: 0.75, y: 0.40, mag: 4.4 },  /* Epsilon  */
      { x: 0.25, y: 0.85, mag: 3.5 },  /* Sheliak  */
      { x: 0.80, y: 0.90, mag: 3.3 },  /* Sulafat  */
    ],
    lines: [[0,1],[0,2],[1,3],[2,4],[3,4]],
  },
];

function spawnConstellation() {
  var data = CONSTELLATIONS[Math.floor(Math.random() * CONSTELLATIONS.length)];
  var size = 180 + Math.random() * 180;
  var pad  = 80;
  var x0   = pad + Math.random() * (starCanvas.width  - size - pad * 2);
  var y0   = pad + Math.random() * (starCanvas.height - size - pad * 2);

  activeConstellation = {
    data: data, x0: x0, y0: y0, size: size,
    phase: 'fadeIn', phaseStart: performance.now(),
  };
}

function drawConstellation(time) {
  if (!activeConstellation) return;
  var c = activeConstellation;
  var elapsed = time - c.phaseStart;

  var FADE_IN = 1800, DRAW_LINES = 3000, HOLD = 5000, FADE_OUT = 2500;
  var alpha = 1.0, linesProgress = 0;

  if (c.phase === 'fadeIn') {
    alpha = Math.min(1, elapsed / FADE_IN);
    if (elapsed >= FADE_IN) { c.phase = 'drawLines'; c.phaseStart = time; }
  } else if (c.phase === 'drawLines') {
    linesProgress = Math.min(1, elapsed / DRAW_LINES);
    if (elapsed >= DRAW_LINES) { c.phase = 'hold'; c.phaseStart = time; }
  } else if (c.phase === 'hold') {
    linesProgress = 1;
    if (elapsed >= HOLD) { c.phase = 'fadeOut'; c.phaseStart = time; }
  } else {
    linesProgress = 1;
    alpha = Math.max(0, 1 - elapsed / FADE_OUT);
    if (elapsed >= FADE_OUT) { activeConstellation = null; return; }
  }

  /* Stars (slightly warmer tone than background twinkle) */
  c.data.stars.forEach(function (s) {
    var sx = c.x0 + s.x * c.size;
    var sy = c.y0 + s.y * c.size;
    var r  = 1.4 + Math.max(0, 3 - s.mag) * 0.55;

    var grad = sCtx.createRadialGradient(sx, sy, 0, sx, sy, r * 4);
    grad.addColorStop(0, 'rgba(220, 232, 255, ' + (alpha * 0.45) + ')');
    grad.addColorStop(1, 'rgba(220, 232, 255, 0)');
    sCtx.fillStyle = grad;
    sCtx.beginPath();
    sCtx.arc(sx, sy, r * 4, 0, Math.PI * 2);
    sCtx.fill();

    sCtx.fillStyle = 'rgba(230, 240, 255, ' + alpha + ')';
    sCtx.beginPath();
    sCtx.arc(sx, sy, r, 0, Math.PI * 2);
    sCtx.fill();
  });

  /* Lines, drawn progressively */
  var total = c.data.lines.length;
  var full  = Math.floor(linesProgress * total);
  var partial = linesProgress * total - full;

  sCtx.strokeStyle = 'rgba(110, 200, 230, ' + (alpha * 0.55) + ')';
  sCtx.lineWidth = 0.8;
  sCtx.lineCap = 'round';

  function drawLine(idx, t) {
    var l = c.data.lines[idx];
    var s1 = c.data.stars[l[0]], s2 = c.data.stars[l[1]];
    var x1 = c.x0 + s1.x * c.size, y1 = c.y0 + s1.y * c.size;
    var x2 = c.x0 + s2.x * c.size, y2 = c.y0 + s2.y * c.size;
    sCtx.beginPath();
    sCtx.moveTo(x1, y1);
    sCtx.lineTo(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t);
    sCtx.stroke();
  }

  for (var i = 0; i < full; i++) drawLine(i, 1);
  if (full < total && partial > 0) drawLine(full, partial);
}

function scheduleConstellation() {
  setTimeout(function () {
    if (!activeConstellation) spawnConstellation();
    scheduleConstellation();
  }, 20000 + Math.random() * 40000);  /* 20–60s between */
}
scheduleConstellation();

function spawnShootingStar() {
  shootingStars.push({
    x:      Math.random() * starCanvas.width  * 0.8,
    y:      Math.random() * starCanvas.height * 0.4,
    vx:     4 + Math.random() * 6,
    vy:     2 + Math.random() * 3,
    life:   1.0,
    length: 40 + Math.random() * 60,
  });
}

function drawStarfield(time) {
  sCtx.clearRect(0, 0, starCanvas.width, starCanvas.height);

  for (var i = 0; i < stars.length; i++) {
    var s = stars[i];
    var twinkle = 0.5 + 0.5 * Math.sin(time * s.twinkleSpeed + s.twinkleOffset);
    sCtx.beginPath();
    sCtx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
    sCtx.fillStyle = 'rgba(170, 200, 240, ' + (s.brightness * twinkle) + ')';
    sCtx.fill();
  }

  for (var j = shootingStars.length - 1; j >= 0; j--) {
    var ss = shootingStars[j];
    ss.x += ss.vx;
    ss.y += ss.vy;
    ss.life -= 0.015;
    if (ss.life <= 0 || ss.x > starCanvas.width || ss.y > starCanvas.height) {
      shootingStars.splice(j, 1);
      continue;
    }
    var trail = ss.length / 6;
    var grad = sCtx.createLinearGradient(ss.x, ss.y, ss.x - ss.vx * trail, ss.y - ss.vy * trail);
    grad.addColorStop(0, 'rgba(160, 200, 255, ' + ss.life * 0.8 + ')');
    grad.addColorStop(1, 'rgba(160, 200, 255, 0)');
    sCtx.beginPath();
    sCtx.moveTo(ss.x, ss.y);
    sCtx.lineTo(ss.x - ss.vx * trail, ss.y - ss.vy * trail);
    sCtx.strokeStyle = grad;
    sCtx.lineWidth = 1.5;
    sCtx.stroke();
  }

  drawConstellation(time);

  if (Math.random() < 0.003) spawnShootingStar();
  requestAnimationFrame(drawStarfield);
}

initStarfield();
window.addEventListener('resize', initStarfield);
requestAnimationFrame(drawStarfield);
