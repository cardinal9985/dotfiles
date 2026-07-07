// Skee-Ball client - two-phase (aim column + power row) + streak bonus

const GRID = [
  // row 0 = near (power 30-55%)
  [10, 20, 30, 20, 10],
  // row 1 = mid (power 55-80%)
  [20, 40, 50, 40, 20],
  // row 2 = far (power 80%+, corners are misses)
  [0,  10, 100, 10, 0],
];

let _phase = 'idle';   // idle | aiming | powering | resolving
let _aimPct = 0;
let _powerPct = 0;
let _aimDir = 1;
let _powerDir = 1;
let _tickId = null;
let _balls = 0;
let _score = 0;
let _streak = 0;
let _entered = false;
let _cfg;

function setBtnVis(newHidden, lockHidden, fireHidden) {
  document.getElementById('btn-new').style.display  = newHidden  ? 'none' : 'inline-block';
  document.getElementById('btn-lock').style.display = lockHidden ? 'none' : 'inline-block';
  document.getElementById('btn-fire').style.display = fireHidden ? 'none' : 'inline-block';
}

function updateHud() {
  document.getElementById('sb-balls').textContent = _balls + ' / ' + _cfg.balls_per_round;
  document.getElementById('sb-score').textContent = _score;
  document.getElementById('sb-streak').textContent = _streak + 'x';
}

function setResult(text, kind) {
  const el = document.getElementById('sb-result');
  el.className = 'sb-result ' + (kind || '');
  el.textContent = text;
}

function updateAimCol() {
  // Column indicator width 20%, so left ranges 0-80%
  const col = document.getElementById('sb-aim-col');
  col.style.left = (_aimPct * 0.8) + '%';
}

function updatePowerFill() {
  document.getElementById('sb-meter-fill').style.width = _powerPct + '%';
}

function resetHoleHighlights() {
  document.querySelectorAll('.sb-hole.landed').forEach(h => h.classList.remove('landed'));
}

// Map (aimPct 0-100, powerPct 0-100) -> (col 0-4, row 0-2 or -1 for miss)
function landing(aimPct, powerPct) {
  const col = Math.max(0, Math.min(4, Math.floor(aimPct / 20)));
  let row;
  if (powerPct < 30)       row = -1;   // rolled back / weak
  else if (powerPct < 55)  row = 0;    // near
  else if (powerPct < 80)  row = 1;    // mid
  else                     row = 2;    // far
  return { col, row };
}

async function newRound() {
  const balance = parseInt(document.getElementById('chip-balance').textContent, 10);
  if (balance < _cfg.entry_fee) { alert('Not enough tickets'); return; }
  _balls = 0;
  _score = 0;
  _streak = 0;
  _entered = true;
  updateHud();
  document.getElementById('sb-last').textContent = '-';
  setResult('AIM COLUMN :: click LOCK AIM', '');
  resetHoleHighlights();
  setBtnVis(true, false, true);
  startAim();
}

function startAim() {
  _phase = 'aiming';
  _aimPct = 0;
  _aimDir = 1;
  document.getElementById('sb-aim-col').classList.remove('locked');
  document.getElementById('sb-aim-col').classList.add('sweeping');
  document.getElementById('sb-meter-label').textContent = 'AIM (column selector)';
  document.getElementById('sb-power-zones').style.display = 'none';
  document.getElementById('sb-meter-hint').textContent = 'click LOCK AIM when the amber column is on the hole you want';
  document.getElementById('sb-meter-fill').style.width = '0%';
  if (_tickId) clearInterval(_tickId);
  _tickId = setInterval(() => {
    _aimPct += _aimDir * 1.4;
    if (_aimPct >= 100) { _aimPct = 100; _aimDir = -1; }
    else if (_aimPct <= 0) { _aimPct = 0; _aimDir = 1; }
    updateAimCol();
    document.getElementById('sb-meter-fill').style.width = _aimPct + '%';
  }, 15);
}

function lockAim() {
  if (_phase !== 'aiming') return;
  if (_tickId) { clearInterval(_tickId); _tickId = null; }
  document.getElementById('sb-aim-col').classList.remove('sweeping');
  document.getElementById('sb-aim-col').classList.add('locked');
  document.getElementById('sb-power-zones').style.display = 'grid';
  document.getElementById('sb-meter-label').textContent = 'POWER (row selector)';
  document.getElementById('sb-meter-hint').textContent = 'NEAR / MID / FAR - power decides which row you land in';
  setBtnVis(true, true, false);
  setResult('POWER :: click RELEASE', '');
  startPower();
}

function startPower() {
  _phase = 'powering';
  _powerPct = 0;
  _powerDir = 1;
  if (_tickId) clearInterval(_tickId);
  _tickId = setInterval(() => {
    _powerPct += _powerDir * 2.0;
    if (_powerPct >= 100) { _powerPct = 100; _powerDir = -1; }
    else if (_powerPct <= 0) { _powerPct = 0; _powerDir = 1; }
    updatePowerFill();
  }, 15);
}

async function release() {
  if (_phase !== 'powering') return;
  _phase = 'resolving';
  if (_tickId) { clearInterval(_tickId); _tickId = null; }
  const aim = _aimPct;
  const power = _powerPct;
  const { col, row } = landing(aim, power);
  const points = row < 0 ? 0 : GRID[row][col];
  const streakBonus = points === 100 ? (_streak >= 2 ? 2 : (_streak >= 1 ? 1.5 : 1)) : 1;
  const scored = Math.round(points * streakBonus);

  const ball = document.getElementById('sb-ball');
  const ramp = document.querySelector('.sb-ramp');
  resetHoleHighlights();
  if (row >= 0 && points > 0) {
    const holeEl = document.querySelector(`.sb-hole[data-row="${row}"][data-col="${col}"]`);
    if (holeEl) {
      const rampRect = ramp.getBoundingClientRect();
      const holeRect = holeEl.getBoundingClientRect();
      const dx = (holeRect.left + holeRect.width/2) - (rampRect.left + rampRect.width/2);
      const targetBottom = rampRect.height - ((holeRect.top + holeRect.height/2) - rampRect.top);
      ball.style.transition = 'bottom 0.7s cubic-bezier(0.3, 0, 0.5, 1), left 0.7s cubic-bezier(0.3, 0, 0.5, 1)';
      ball.style.left = `calc(50% + ${dx}px)`;
      ball.style.bottom = targetBottom + 'px';
      setTimeout(() => holeEl.classList.add('landed'), 400);
    }
  } else {
    ball.style.transition = 'bottom 0.5s ease-in, left 0.5s ease-in';
    ball.style.bottom = '-40px';
  }

  setTimeout(() => {
    _balls++;
    _score += scored;
    document.getElementById('sb-last').textContent = scored + (streakBonus > 1 ? ' (' + streakBonus + 'x)' : '');
    if (points === 100) {
      _streak++;
      setResult(streakBonus > 1
        ? `BULLSEYE STREAK ${_streak}! +${scored}`
        : `BULLSEYE! +${scored}`,
        'bullseye');
    } else if (points >= 40) {
      _streak = 0;
      setResult('GREAT! +' + scored, 'great');
    } else if (points >= 10) {
      _streak = 0;
      setResult('+' + scored, 'win');
    } else {
      _streak = 0;
      setResult('MISS :: 0', 'miss');
    }
    updateHud();

    setTimeout(() => {
      ball.style.transition = 'none';
      ball.style.left = '50%';
      ball.style.bottom = '-32px';
      void ball.offsetWidth;
      ball.style.transition = '';

      document.getElementById('sb-aim-col').classList.remove('locked');
      resetHoleHighlights();

      if (_balls >= _cfg.balls_per_round) {
        submitRound();
      } else {
        startAim();
        setBtnVis(true, false, true);
      }
    }, 900);
  }, 800);
}

async function submitRound() {
  _phase = 'idle';
  setBtnVis(true, true, true);
  setResult('SUBMITTING ROUND...', '');
  try {
    const res = await fetch('/skeeball/api/finish', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ score: _score }),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      setResult('ERROR: ' + (data.error || 'unknown'), 'miss');
      setBtnVis(false, true, true);
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
    setBtnVis(false, true, true);
    _entered = false;
  } catch (e) {
    setResult('NETWORK ERROR', 'miss');
    setBtnVis(false, true, true);
    _entered = false;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  _cfg = window.SB_CFG || { balls_per_round: 9, entry_fee: 20 };
  document.getElementById('btn-new').addEventListener('click', newRound);
  document.getElementById('btn-lock').addEventListener('click', lockAim);
  document.getElementById('btn-fire').addEventListener('click', release);
  updateHud();
});
