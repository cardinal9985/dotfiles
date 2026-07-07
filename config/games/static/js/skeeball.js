// Skee-Ball client

let _state = 'idle';
let _power = 0;
let _direction = 1;
let _tickId = null;
let _balls = 0;
let _score = 0;
let _entered = false;
let _cfg;

function updateFill() {
  document.getElementById('sb-charge-fill').style.width = _power + '%';
}

function updateHud() {
  document.getElementById('sb-balls').textContent = _balls + ' / ' + _cfg.balls_per_round;
  document.getElementById('sb-score').textContent = _score;
}

function scoreForPower(power) {
  // Sweet spot 70-80% = 100 (bullseye)
  if (power >= 70 && power <= 80) return 100;
  if (power >= 60 && power < 70)  return 50;
  if (power >  80 && power <= 88) return 50;
  if (power >= 45 && power < 60)  return 30;
  if (power >  88 && power <= 94) return 30;
  if (power >= 25 && power < 45)  return 20;
  if (power >  94)                return 20;
  return 10;
}

function setResult(text, kind) {
  const el = document.getElementById('sb-result');
  el.className = 'sb-result ' + (kind || '');
  el.textContent = text;
}

async function newRound() {
  const balance = parseInt(document.getElementById('chip-balance').textContent, 10);
  if (balance < _cfg.entry_fee) { alert('Not enough tickets'); return; }
  // Take the entry fee immediately in the client display; server also deducts on finish
  _balls = 0;
  _score = 0;
  _entered = true;
  updateHud();
  document.getElementById('sb-last').textContent = '-';
  setResult('CHARGE POWER, RELEASE FOR BULLSEYE', '');
  document.getElementById('btn-new').style.display = 'none';
  document.getElementById('btn-roll').style.display = 'inline-block';
  document.getElementById('btn-roll').disabled = false;
  startCharge();
}

function startCharge() {
  if (_state !== 'idle') return;
  _state = 'charging';
  _power = 0;
  _direction = 1;
  const btn = document.getElementById('btn-roll');
  btn.textContent = 'RELEASE!';
  _tickId = setInterval(() => {
    _power += _direction * 2.5;
    if (_power >= 100) { _power = 100; _direction = -1; }
    else if (_power <= 0) { _power = 0; _direction = 1; }
    updateFill();
  }, 20);
}

function resetHoleHighlights() {
  document.querySelectorAll('.sb-hole.landed').forEach(h => h.classList.remove('landed'));
}

async function release() {
  if (_state !== 'charging') return;
  _state = 'resolving';
  if (_tickId) { clearInterval(_tickId); _tickId = null; }
  const finalPower = _power;
  const points = scoreForPower(finalPower);
  const btn = document.getElementById('btn-roll');
  btn.disabled = true;

  // Animate ball to the hole
  const ball = document.getElementById('sb-ball');
  resetHoleHighlights();
  const holeClass = 'sb-hole-' + points;
  const holeEl = document.querySelector('.' + holeClass);
  if (holeEl && ball) {
    const ballRect = ball.getBoundingClientRect();
    const holeRect = holeEl.getBoundingClientRect();
    const ramp = document.querySelector('.sb-ramp').getBoundingClientRect();
    const dx = (holeRect.left + holeRect.width/2) - (ballRect.left + ballRect.width/2);
    const dy = (holeRect.top + holeRect.height/2) - (ballRect.top + ballRect.height/2);
    ball.style.left = 'calc(50% + ' + dx + 'px)';
    ball.style.bottom = (20 - dy) + 'px';
    setTimeout(() => holeEl.classList.add('landed'), 300);
  }

  setTimeout(() => {
    _balls++;
    _score += points;
    document.getElementById('sb-last').textContent = points;
    updateHud();
    if (points === 100)      setResult('BULLSEYE! +100', 'bullseye');
    else if (points >= 50)   setResult('GREAT! +' + points, 'win');
    else                     setResult('+' + points, '');

    // Reset ball position
    setTimeout(() => {
      if (ball) {
        ball.style.left = '50%';
        ball.style.bottom = '20px';
      }
      _state = 'idle';
      if (_balls >= _cfg.balls_per_round) {
        submitRound();
      } else {
        btn.disabled = false;
        btn.textContent = 'ROLL (BALL ' + (_balls + 1) + ')';
        startCharge();
      }
    }, 500);
  }, 700);
}

async function submitRound() {
  document.getElementById('btn-roll').style.display = 'none';
  setResult('SUBMITTING ROUND...', '');
  try {
    const res = await fetch('/skeeball/api/finish', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ score: _score }),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      setResult('ERROR: ' + (data.error || 'unknown'), '');
      document.getElementById('btn-new').style.display = 'inline-block';
      _entered = false;
      return;
    }
    document.getElementById('chip-balance').textContent = data.new_balance;
    setResult(`ROUND OVER :: ${data.score} pts :: ${data.net >= 0 ? '+' : ''}${data.net} tickets`,
              data.net > 0 ? 'win' : '');
    if (window.showToast) {
      if (data.net > 0) showToast('+' + data.payout + ' TICKETS', 'SCORE ' + data.score, 'chip-win');
      else if (data.net < 0) showToast(data.net + ' TICKETS', 'SCORE ' + data.score, 'chip-loss');
    }
    document.getElementById('btn-new').style.display = 'inline-block';
    _entered = false;
    resetHoleHighlights();
  } catch (e) {
    setResult('NETWORK ERROR', '');
    document.getElementById('btn-new').style.display = 'inline-block';
    _entered = false;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  _cfg = window.SB_CFG || { balls_per_round: 9, entry_fee: 20 };
  document.getElementById('btn-new').addEventListener('click', newRound);
  document.getElementById('btn-roll').addEventListener('click', () => {
    if (_state === 'charging') release();
  });
  updateHud();
});
