/* ── Quotes ── */
var QUOTES = [
  '"Make us whole." — The Marker',
  '"The signal changes you." — USG Ishimura Log',
  '"Altman be praised." — Unitologist Broadcast',
  '"Convergence is inevitable." — Marker Signal',
  '"There is no salvation. Only transformation." — Dr. Mercer',
  '"We will all be pure. We will all be together." — Unitologist Propaganda',
  '"In the void, every system is temporary." — CEC Engineering Manual',
  '"The Marker chose you, Isaac." — Nicole Brennan',
  '"This isn\'t happening..." — Isaac Clarke',
  '"We are all united in the Marker\'s embrace." — Unitologist Broadcast',
];

var quoteIdx = Math.floor(Math.random() * QUOTES.length);

function showQuote() {
  var el = document.getElementById('quote');
  el.classList.remove('visible');
  setTimeout(function () {
    el.textContent = QUOTES[quoteIdx % QUOTES.length];
    quoteIdx++;
    el.classList.add('visible');
  }, 700);
}

showQuote();
setInterval(showQuote, 9000);

/* ── Services ── */
function statusClass(state) {
  return state === 'online' ? 'online' : state === 'offline' ? 'offline' : 'checking';
}

function renderServices(services) {
  var grid = document.getElementById('service-grid');
  grid.innerHTML = '';
  services.forEach(function (svc) {
    var card = document.createElement('div');
    card.className = 'service-card';
    card.innerHTML =
      '<a href="' + svc.url + '" target="_blank" rel="noopener">' +
        '<div class="card-top">' +
          '<span class="service-icon">' + (svc.icon || '▣') + '</span>' +
          '<div class="status-dot checking" id="dot-' + encodeURIComponent(svc.name) + '"></div>' +
        '</div>' +
        '<div class="service-name">' + svc.name.toUpperCase() + '</div>' +
        '<div class="service-desc">' + (svc.description || '') + '</div>' +
      '</a>';
    grid.appendChild(card);
    checkStatus(svc);
  });
}

async function checkStatus(svc) {
  var dotId = 'dot-' + encodeURIComponent(svc.name);
  var dot = document.getElementById(dotId);
  if (!dot) return;
  try {
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 4000);
    await fetch(svc.url, { mode: 'no-cors', signal: controller.signal });
    clearTimeout(timer);
    dot.className = 'status-dot online';
  } catch (_) {
    dot.className = 'status-dot offline';
  }
}

fetch('services.json')
  .then(function (r) { return r.json(); })
  .then(renderServices)
  .catch(function () {
    document.getElementById('service-grid').innerHTML =
      '<div style="color:var(--yellow);font-size:0.8rem;opacity:0.7">[SERVICE MANIFEST UNAVAILABLE]</div>';
  });

/* ── Canvas: stars + shooting stars + ships ── */
var canvas = document.getElementById('star-canvas');
var ctx = canvas.getContext('2d');
var stars = [];
var shootingStars = [];
var ships = [];
var frame = 0;

function resize() {
  canvas.width  = window.innerWidth;
  canvas.height = window.innerHeight;
  initStars();
}

function initStars() {
  stars = [];
  for (var i = 0; i < 220; i++) {
    stars.push({
      x:            Math.random() * canvas.width,
      y:            Math.random() * canvas.height,
      r:            Math.random() * 1.4 + 0.2,
      brightness:   Math.random() * 0.55 + 0.25,
      speed:        Math.random() * 0.018 + 0.004,
      offset:       Math.random() * Math.PI * 2,
    });
  }
}

function initShips() {
  ships = [];
  for (var i = 0; i < 3; i++) {
    ships.push(makeShip(true));
  }
}

function makeShip(scatter) {
  var w = canvas.width;
  var h = canvas.height;
  return {
    x:     scatter ? Math.random() * w : -220,
    y:     (0.1 + Math.random() * 0.75) * h,
    vx:    0.06 + Math.random() * 0.1,
    scale: 0.6 + Math.random() * 1.0,
    alpha: 0.025 + Math.random() * 0.035,
  };
}

function drawShip(s) {
  ctx.save();
  ctx.translate(s.x, s.y);
  ctx.scale(s.scale, s.scale);
  ctx.strokeStyle = 'rgba(110, 200, 230, ' + s.alpha + ')';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(-110,  0);
  ctx.lineTo(  90, -9);
  ctx.lineTo( 115,  0);
  ctx.lineTo(  90,  9);
  ctx.closePath();
  ctx.moveTo( -30, -9);
  ctx.lineTo( -60, -22);
  ctx.lineTo( -90,  -9);
  ctx.moveTo( -30,  9);
  ctx.lineTo( -60,  22);
  ctx.lineTo( -90,   9);
  ctx.stroke();
  ctx.restore();

  s.x += s.vx;
  if (s.x > canvas.width + 220) {
    Object.assign(s, makeShip(false));
  }
}

function spawnShootingStar() {
  shootingStars.push({
    x:      Math.random() * canvas.width  * 0.75,
    y:      Math.random() * canvas.height * 0.45,
    vx:     4 + Math.random() * 7,
    vy:     1.5 + Math.random() * 3,
    life:   1.0,
    length: 45 + Math.random() * 65,
  });
}

function animate(time) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  /* stars */
  for (var i = 0; i < stars.length; i++) {
    var s = stars[i];
    var twinkle = 0.5 + 0.5 * Math.sin(time * 0.001 * s.speed * 50 + s.offset);
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(170, 200, 240, ' + (s.brightness * twinkle) + ')';
    ctx.fill();
  }

  /* ships */
  for (var j = 0; j < ships.length; j++) {
    drawShip(ships[j]);
  }

  /* shooting stars */
  for (var k = shootingStars.length - 1; k >= 0; k--) {
    var ss = shootingStars[k];
    ss.x += ss.vx;
    ss.y += ss.vy;
    ss.life -= 0.014;
    if (ss.life <= 0 || ss.x > canvas.width || ss.y > canvas.height) {
      shootingStars.splice(k, 1);
      continue;
    }
    var trail = ss.length / 6;
    var grad = ctx.createLinearGradient(ss.x, ss.y, ss.x - ss.vx * trail, ss.y - ss.vy * trail);
    grad.addColorStop(0, 'rgba(160, 200, 255, ' + (ss.life * 0.85) + ')');
    grad.addColorStop(1, 'rgba(160, 200, 255, 0)');
    ctx.beginPath();
    ctx.moveTo(ss.x, ss.y);
    ctx.lineTo(ss.x - ss.vx * trail, ss.y - ss.vy * trail);
    ctx.strokeStyle = grad;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }

  frame++;
  if (frame % 200 === 0 && Math.random() < 0.7) spawnShootingStar();

  requestAnimationFrame(animate);
}

resize();
initShips();
window.addEventListener('resize', resize);
requestAnimationFrame(animate);
