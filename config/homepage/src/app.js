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

/* ── Canvas: stars + shooting stars ── */
var starCanvas = document.getElementById('star-canvas');
var sCtx = starCanvas.getContext('2d');
var stars = [];
var shootingStars = [];

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
      twinkleSpeed: Math.random() * 0.02 + 0.005,
      twinkleOffset: Math.random() * Math.PI * 2,
    });
  }
}

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

  if (Math.random() < 0.003) spawnShootingStar();
  requestAnimationFrame(drawStarfield);
}

initStarfield();
window.addEventListener('resize', initStarfield);
requestAnimationFrame(drawStarfield);
