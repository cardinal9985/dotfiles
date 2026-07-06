// Roulette client

let _bets = {};  // key = kind+':'+target, value = amount
let _chipValue = 10;
let _spinning = false;

function betKey(kind, target) { return kind + ':' + target; }

function updateTotal() {
  const total = Object.values(_bets).reduce((a, b) => a + b, 0);
  document.getElementById('total-bet').textContent = total;
}

function updateSpotChip(el, kind, target) {
  const key = betKey(kind, target);
  const amt = _bets[key];
  let chip = el.querySelector('.chip-stack');
  if (amt) {
    if (!chip) { chip = document.createElement('div'); chip.className = 'chip-stack'; el.appendChild(chip); }
    chip.textContent = amt >= 1000 ? Math.floor(amt / 1000) + 'K' : amt;
  } else if (chip) {
    chip.remove();
  }
}

function addBet(el) {
  const kind = el.dataset.kind;
  const target = parseInt(el.dataset.target || '0', 10);
  const key = betKey(kind, target);
  _bets[key] = (_bets[key] || 0) + _chipValue;
  updateSpotChip(el, kind, target);
  updateTotal();
}

function clearBets() {
  _bets = {};
  document.querySelectorAll('.chip-stack').forEach(c => c.remove());
  updateTotal();
}

async function spin() {
  if (_spinning) return;
  const bets = Object.entries(_bets).map(([k, amount]) => {
    const [kind, target] = k.split(':');
    return { kind, target: parseInt(target, 10), amount };
  });
  if (!bets.length) { alert('Place a bet'); return; }

  _spinning = true;
  const banner = document.getElementById('roul-result');
  banner.className = 'roul-result spinning';
  banner.textContent = '···';

  const res = await fetch('/roulette/api/spin', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ bets }),
  });
  const data = await res.json();
  if (!res.ok || data.error) {
    _spinning = false;
    banner.className = 'roul-result';
    banner.textContent = 'READY';
    alert(data.error || 'Error');
    return;
  }

  // Delay reveal for tension
  setTimeout(() => {
    banner.className = 'roul-result ' + data.color;
    banner.textContent = data.result;
    document.getElementById('chip-balance').textContent = data.new_balance;

    // Highlight the winning number
    document.querySelectorAll('.roul-num.winner').forEach(el => el.classList.remove('winner'));
    document.querySelectorAll(`.roul-num[data-kind="straight"][data-target="${data.result}"]`).forEach(el => {
      el.classList.add('winner');
    });

    // Add to history strip
    const hist = document.getElementById('roul-history');
    const h = document.createElement('span');
    h.className = 'h-num ' + data.color;
    h.textContent = data.result;
    hist.prepend(h);
    while (hist.children.length > 12) hist.lastChild.remove();

    if (data.net > 0) {
      if (window.showToast) showToast('+' + data.payout + ' CHIPS', 'RESULT ' + data.result + ' :: net +' + data.net, 'chip-win');
    } else if (data.net < 0) {
      if (window.showToast) showToast(data.net + ' CHIPS', 'RESULT ' + data.result + ' :: bets lost', 'chip-loss');
    }
    clearBets();
    _spinning = false;
  }, 1400);
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.roul-num').forEach(el => {
    el.addEventListener('click', () => {
      if (_spinning) return;
      addBet(el);
    });
  });

  document.querySelectorAll('.chip-val-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      _chipValue = parseInt(btn.dataset.value, 10);
      document.querySelectorAll('.chip-val-btn').forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
    });
  });

  document.getElementById('btn-spin' ).addEventListener('click', spin);
  document.getElementById('btn-clear').addEventListener('click', clearBets);
});
