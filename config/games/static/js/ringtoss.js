// Ring Toss client

let _state = 'idle';  // idle -> sweeping -> resolving
let _aim = 50;
let _direction = 1;
let _tickId = null;

function setResult(text, kind) {
  const el = document.getElementById('rt-result');
  el.className = 'rt-result ' + (kind || '');
  el.textContent = text;
}

function updateReticle() {
  document.getElementById('rt-reticle').style.left = _aim + '%';
}

function startSweep() {
  if (_state !== 'idle') return;
  _state = 'sweeping';
  _aim = 0;
  _direction = 1;
  setResult('CLICK TO RELEASE', '');
  document.getElementById('btn-throw').textContent = 'RELEASE!';
  const ring = document.getElementById('rt-ring');
  ring.style.display = 'none';
  _tickId = setInterval(() => {
    _aim += _direction * 1.6;
    if (_aim >= 100) { _aim = 100; _direction = -1; }
    else if (_aim <= 0) { _aim = 0; _direction = 1; }
    updateReticle();
  }, 15);
}

async function releaseRing() {
  if (_state !== 'sweeping') return;
  _state = 'resolving';
  if (_tickId) { clearInterval(_tickId); _tickId = null; }
  const finalAim = _aim;
  const btn = document.getElementById('btn-throw');
  btn.disabled = true;

  const ring = document.getElementById('rt-ring');
  ring.style.display = 'block';
  ring.style.left = finalAim + '%';
  ring.style.top = '20px';
  // Fly the ring down to peg area
  requestAnimationFrame(() => {
    ring.style.top = '100px';
  });

  try {
    const res = await fetch('/ringtoss/api/throw', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ aim: finalAim }),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      setResult('ERROR: ' + (data.error || 'unknown'), 'miss');
      _state = 'idle';
      btn.disabled = false;
      btn.textContent = 'START (' + btn.dataset.entry + ' TICKETS)';
      return;
    }
    document.getElementById('chip-balance').textContent = data.new_balance;
    setTimeout(() => {
      if (data.peg_idx >= 0) {
        setResult(`LANDED! +${data.payout} TICKETS`, 'win');
        if (window.showToast) showToast('+' + data.payout + ' TICKETS', 'RING LANDED', 'chip-win');
      } else {
        setResult(`MISS :: -${btn.dataset.entry} TICKETS`, 'miss');
        if (window.showToast) showToast('-' + btn.dataset.entry + ' TICKETS', 'MISSED THE PEGS', 'chip-loss');
      }
      _state = 'idle';
      btn.disabled = false;
      btn.textContent = 'START (' + btn.dataset.entry + ' TICKETS)';
    }, 700);
  } catch (e) {
    setResult('NETWORK ERROR', 'miss');
    _state = 'idle';
    btn.disabled = false;
    btn.textContent = 'START (' + btn.dataset.entry + ' TICKETS)';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('btn-throw');
  btn.dataset.entry = btn.textContent.match(/\d+/)[0];
  updateReticle();
  btn.addEventListener('click', () => {
    if (_state === 'idle') startSweep();
    else if (_state === 'sweeping') releaseRing();
  });
});
