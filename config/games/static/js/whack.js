// Whack-a-Mole client

let _playing = false;
let _hits = 0;
let _misses = 0;
let _timeLeft = 0;
let _timerId = null;
let _moleTimeoutId = null;
let _activeHole = -1;
let _cfg = null;

function updateHud() {
  document.getElementById('w-hits').textContent = _hits;
  document.getElementById('w-misses').textContent = _misses;
  document.getElementById('w-timer').textContent = _timeLeft;
}

function popMole() {
  if (!_playing) return;
  // Pick a random hole, not the currently-active one
  let idx;
  do { idx = Math.floor(Math.random() * 9); } while (idx === _activeHole && _activeHole !== -1);
  _activeHole = idx;
  const hole = document.querySelector('.whack-hole[data-idx="' + idx + '"]');
  if (hole) hole.classList.add('active');
  // Mole stays visible 700-1100ms
  const visibleMs = 700 + Math.floor(Math.random() * 400);
  _moleTimeoutId = setTimeout(() => {
    if (hole) hole.classList.remove('active');
    _activeHole = -1;
    // Next mole after 200-600ms
    if (_playing) setTimeout(popMole, 200 + Math.floor(Math.random() * 400));
  }, visibleMs);
}

async function startRound() {
  const balance = parseInt(document.getElementById('chip-balance').textContent, 10);
  if (balance < _cfg.entry_fee) { alert('Not enough tickets'); return; }

  _hits = 0; _misses = 0;
  _timeLeft = _cfg.round_secs;
  _playing = true;
  updateHud();
  document.getElementById('btn-start').disabled = true;
  document.getElementById('w-status').textContent = 'GO!';

  _timerId = setInterval(() => {
    _timeLeft--;
    updateHud();
    if (_timeLeft <= 0) finishRound();
  }, 1000);

  setTimeout(popMole, 500);
}

async function finishRound() {
  _playing = false;
  if (_timerId) { clearInterval(_timerId); _timerId = null; }
  if (_moleTimeoutId) { clearTimeout(_moleTimeoutId); _moleTimeoutId = null; }
  document.querySelectorAll('.whack-hole.active').forEach(h => h.classList.remove('active'));
  _activeHole = -1;
  document.getElementById('w-status').textContent = 'SUBMITTING...';

  try {
    const res = await fetch('/whack/api/finish', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ hits: _hits, misses: _misses }),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      document.getElementById('w-status').textContent = 'ERROR: ' + (data.error || 'unknown');
      document.getElementById('btn-start').disabled = false;
      return;
    }
    document.getElementById('chip-balance').textContent = data.new_balance;
    document.getElementById('w-status').textContent =
      `ROUND OVER :: ${data.hits} HITS :: ${data.net >= 0 ? '+' : ''}${data.net} TICKETS`;
    if (window.showToast) {
      if (data.net > 0) showToast('+' + data.payout + ' TICKETS', data.hits + ' HITS', 'chip-win');
      else if (data.net < 0) showToast(data.net + ' TICKETS', data.hits + ' HITS', 'chip-loss');
    }
    document.getElementById('btn-start').disabled = false;
  } catch (e) {
    document.getElementById('w-status').textContent = 'NETWORK ERROR';
    document.getElementById('btn-start').disabled = false;
  }
}

function handleHoleClick(idx) {
  if (!_playing) return;
  const hole = document.querySelector('.whack-hole[data-idx="' + idx + '"]');
  if (!hole) return;
  if (hole.classList.contains('active')) {
    hole.classList.remove('active');
    hole.classList.add('hit');
    setTimeout(() => hole.classList.remove('hit'), 300);
    _hits++;
    _activeHole = -1;
    if (_moleTimeoutId) { clearTimeout(_moleTimeoutId); _moleTimeoutId = null; }
    setTimeout(popMole, 150 + Math.floor(Math.random() * 300));
  } else {
    hole.classList.add('miss');
    setTimeout(() => hole.classList.remove('miss'), 200);
    _misses++;
  }
  updateHud();
}

document.addEventListener('DOMContentLoaded', () => {
  _cfg = window.WHACK_CFG || { round_secs: 30, entry_fee: 20, payout_per_hit: 3 };
  document.getElementById('btn-start').addEventListener('click', startRound);
  document.querySelectorAll('.whack-hole').forEach(hole => {
    hole.addEventListener('click', () => handleHoleClick(parseInt(hole.dataset.idx, 10)));
  });
  document.getElementById('w-timer').textContent = _cfg.round_secs;
});
