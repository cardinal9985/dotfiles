// High Striker client - hold to charge, release to swing

let _charging = false;
let _power = 0;
let _direction = 1;
let _tickId = null;
let _resolved = false;

function setResult(text, kind) {
  const el = document.getElementById('hs-result');
  el.className = 'hs-result ' + (kind || '');
  el.textContent = text;
}

function updateFill() {
  document.getElementById('hs-charge-fill').style.width = _power + '%';
}

function startCharge() {
  if (_charging || _tickId) return;
  _charging = true;
  _resolved = false;
  _power = 0;
  _direction = 1;
  setResult('CHARGING... RELEASE AT PEAK', '');
  const btn = document.getElementById('btn-swing');
  btn.textContent = 'RELEASE!';
  document.getElementById('hs-puck').style.bottom = '8px';
  document.getElementById('hs-bell').classList.remove('ring');
  // Bar oscillates: fills toward 100, back to 0, etc.
  _tickId = setInterval(() => {
    _power += _direction * 3;
    if (_power >= 100) { _power = 100; _direction = -1; }
    else if (_power <= 0) { _power = 0; _direction = 1; }
    updateFill();
  }, 25);
}

async function releaseSwing() {
  if (!_charging || _resolved) return;
  _resolved = true;
  _charging = false;
  if (_tickId) { clearInterval(_tickId); _tickId = null; }
  const finalPower = _power;
  updateFill();

  // Animate puck up scale before showing outcome
  const puck = document.getElementById('hs-puck');
  const towerHeight = 400 - 60 - 8;   // pixels
  const targetOffset = 8 + (finalPower / 100) * towerHeight;
  puck.style.transition = 'bottom 0.6s cubic-bezier(0.2, 0.8, 0.2, 1)';
  puck.style.bottom = targetOffset + 'px';

  const btn = document.getElementById('btn-swing');
  btn.disabled = true;

  try {
    const res = await fetch('/highstriker/api/swing', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ power: finalPower }),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      setResult('ERROR: ' + (data.error || 'unknown'), 'weak');
      btn.disabled = false;
      btn.textContent = 'SWING';
      return;
    }
    document.getElementById('chip-balance').textContent = data.new_balance;
    let msg;
    if (data.rang_bell) {
      msg = `🔔 BELL RUNG! +${data.payout} TICKETS`;
      setResult(msg, 'bell');
      document.getElementById('hs-bell').classList.add('ring');
    } else if (data.payout > 0) {
      msg = `POWER ${finalPower} :: +${data.payout} TICKETS`;
      setResult(msg, data.net > 0 ? 'strong' : '');
    } else {
      msg = `POWER ${finalPower} :: NO PAYOUT`;
      setResult(msg, 'weak');
    }
    if (window.showToast) {
      if (data.rang_bell) showToast('BELL!', '+' + data.payout + ' TICKETS', 'chip-win');
      else if (data.net > 0) showToast('+' + data.payout + ' TICKETS', 'POWER ' + finalPower, 'chip-win');
      else showToast(data.net + ' TICKETS', 'POWER ' + finalPower, 'chip-loss');
    }
    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = 'SWING (' + document.querySelector('.hs-controls .btn-primary').dataset.entry + ' TICKETS)';
    }, 1500);
  } catch (e) {
    setResult('NETWORK ERROR', 'weak');
    btn.disabled = false;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('btn-swing');
  btn.dataset.entry = btn.textContent.match(/\d+/)[0];

  btn.addEventListener('mousedown',  startCharge);
  btn.addEventListener('touchstart', (e) => { e.preventDefault(); startCharge(); });
  btn.addEventListener('mouseup',    releaseSwing);
  btn.addEventListener('mouseleave', () => { if (_charging) releaseSwing(); });
  btn.addEventListener('touchend',   (e) => { e.preventDefault(); releaseSwing(); });
});
