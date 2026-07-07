// Balloon Pop client

const COLORS = ['red', 'cyan', 'green', 'purple'];
let _playing = false;
let _pops = 0;
let _gold = 0;
let _timeLeft = 0;
let _timerId = null;
let _spawnId = null;
let _riseId = null;
let _cfg;

function updateHud() {
  document.getElementById('bp-pops').textContent = _pops;
  document.getElementById('bp-gold').textContent = _gold;
  document.getElementById('bp-timer').textContent = _timeLeft;
}

function spawnBalloon() {
  if (!_playing) return;
  const arena = document.getElementById('bp-arena');
  const isGold = Math.random() < 0.07;  // 7% chance
  const color = isGold ? 'gold' : COLORS[Math.floor(Math.random() * COLORS.length)];
  const el = document.createElement('div');
  el.className = 'balloon ' + color;
  el.dataset.gold = isGold ? '1' : '0';
  const x = 20 + Math.random() * (arena.clientWidth - 80);
  el.style.left = x + 'px';
  el.style.bottom = '-56px';
  el.dataset.speed = (isGold ? 0.9 : 1.3 + Math.random() * 0.8).toString();

  el.addEventListener('click', () => {
    if (el.classList.contains('popped')) return;
    el.classList.add('popped');
    _pops++;
    if (el.dataset.gold === '1') _gold++;
    updateHud();
    setTimeout(() => el.remove(), 250);
  });

  arena.appendChild(el);
}

function riseTick() {
  const arena = document.getElementById('bp-arena');
  const height = arena.clientHeight;
  arena.querySelectorAll('.balloon:not(.popped)').forEach(el => {
    const current = parseFloat(el.style.bottom || '-56');
    const speed = parseFloat(el.dataset.speed || '1.3');
    const next = current + speed;
    if (next > height) {
      el.remove();
    } else {
      el.style.bottom = next + 'px';
    }
  });
}

function scheduleSpawn() {
  if (!_playing) return;
  spawnBalloon();
  const delay = 350 + Math.random() * 400;
  _spawnId = setTimeout(scheduleSpawn, delay);
}

async function startRound() {
  const balance = parseInt(document.getElementById('chip-balance').textContent, 10);
  const entryFee = 15;
  if (balance < entryFee) { alert('Not enough tickets'); return; }

  _pops = 0; _gold = 0; _timeLeft = _cfg.round_secs; _playing = true;
  updateHud();
  document.getElementById('bp-status').textContent = 'GO!';
  document.getElementById('btn-start').disabled = true;
  document.getElementById('bp-arena').innerHTML = '';

  _timerId = setInterval(() => {
    _timeLeft--;
    updateHud();
    if (_timeLeft <= 0) finishRound();
  }, 1000);
  _riseId = setInterval(riseTick, 30);
  scheduleSpawn();
}

async function finishRound() {
  _playing = false;
  if (_timerId) { clearInterval(_timerId); _timerId = null; }
  if (_spawnId) { clearTimeout(_spawnId); _spawnId = null; }
  if (_riseId) { clearInterval(_riseId); _riseId = null; }
  document.getElementById('bp-status').textContent = 'SUBMITTING...';

  try {
    const res = await fetch('/balloonpop/api/finish', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ pops: _pops, gold_pops: _gold }),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      document.getElementById('bp-status').textContent = 'ERROR: ' + (data.error || 'unknown');
      document.getElementById('btn-start').disabled = false;
      return;
    }
    document.getElementById('chip-balance').textContent = data.new_balance;
    document.getElementById('bp-status').textContent =
      `ROUND OVER :: ${data.pops} POPS (${data.gold_pops} GOLD) :: ${data.net >= 0 ? '+' : ''}${data.net}`;
    if (window.showToast) {
      if (data.net > 0) showToast('+' + data.payout + ' TICKETS', data.pops + ' POPS', 'chip-win');
      else if (data.net < 0) showToast(data.net + ' TICKETS', data.pops + ' POPS', 'chip-loss');
    }
    document.getElementById('btn-start').disabled = false;
  } catch (e) {
    document.getElementById('bp-status').textContent = 'NETWORK ERROR';
    document.getElementById('btn-start').disabled = false;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  _cfg = window.BP_CFG || { points_per_pop: 2, gold_bonus: 20, round_secs: 30 };
  document.getElementById('btn-start').addEventListener('click', startRound);
  document.getElementById('bp-timer').textContent = _cfg.round_secs;
});
