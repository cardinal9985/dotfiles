// Dice Hi-Lo client

let _selected = "over";
let _rolling = false;

function renderPips(dieEl, face) {
  dieEl.dataset.face = face;
  dieEl.innerHTML = '';
  for (let i = 0; i < face; i++) {
    const p = document.createElement('div');
    p.className = 'pip';
    dieEl.appendChild(p);
  }
}

function selectBox(kind) {
  _selected = kind;
  document.querySelectorAll('.bet-box').forEach(b => {
    b.classList.toggle('selected', b.dataset.bet === kind);
  });
}

async function roll() {
  if (_rolling) return;
  const bo = parseInt(document.getElementById('bet-over').value,  10) || 0;
  const bu = parseInt(document.getElementById('bet-under').value, 10) || 0;
  const be = parseInt(document.getElementById('bet-equal').value, 10) || 0;
  if (bo + bu + be <= 0) { alert('Place a bet'); return; }

  const d1 = document.getElementById('die-1');
  const d2 = document.getElementById('die-2');
  d1.classList.remove('win', 'loss'); d2.classList.remove('win', 'loss');
  d1.classList.add('rolling'); d2.classList.add('rolling');
  const banner = document.getElementById('dice-result');
  banner.className = 'dice-result';
  banner.textContent = '';
  _rolling = true;

  const shuffle1 = setInterval(() => renderPips(d1, Math.floor(Math.random() * 6) + 1), 110);
  const shuffle2 = setInterval(() => renderPips(d2, Math.floor(Math.random() * 6) + 1), 110);

  let data = null;
  try {
    const res = await fetch('/dice/api/roll', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ bet_over: bo, bet_under: bu, bet_equal: be }),
    });
    data = await res.json();
    if (!res.ok || data.error) {
      clearInterval(shuffle1); clearInterval(shuffle2);
      d1.classList.remove('rolling'); d2.classList.remove('rolling');
      _rolling = false;
      alert(data.error || 'Error');
      return;
    }
  } catch (e) {
    clearInterval(shuffle1); clearInterval(shuffle2);
    d1.classList.remove('rolling'); d2.classList.remove('rolling');
    _rolling = false;
    return;
  }

  // Stagger stops - each interval cleared independently so the settled die
  // doesn't get repainted with a random face
  setTimeout(() => {
    clearInterval(shuffle1);
    d1.classList.remove('rolling');
    renderPips(d1, data.d1);
  }, 800);
  setTimeout(() => {
    clearInterval(shuffle2);
    d2.classList.remove('rolling');
    renderPips(d2, data.d2);
    finish(data);
  }, 1200);
}

function finish(data) {
  _rolling = false;
  const d1 = document.getElementById('die-1');
  const d2 = document.getElementById('die-2');
  const banner = document.getElementById('dice-result');
  banner.textContent = 'TOTAL ' + data.total;
  document.getElementById('chip-balance').textContent = data.new_balance;

  const win = data.net > 0;
  if (win) {
    d1.classList.add('win'); d2.classList.add('win');
    banner.classList.add('win');
    banner.textContent = 'TOTAL ' + data.total + ' :: +' + data.net + ' TICKETS';
    if (window.showToast) showToast('+' + data.payout + ' TICKETS', 'TOTAL ' + data.total + ' :: net +' + data.net, 'chip-win');
  } else if (data.net === 0) {
    banner.textContent = 'TOTAL ' + data.total + ' :: PUSH';
  } else {
    d1.classList.add('loss'); d2.classList.add('loss');
    banner.classList.add('loss');
    banner.textContent = 'TOTAL ' + data.total + ' :: ' + data.net + ' TICKETS';
    if (window.showToast) showToast(data.net + ' TICKETS', 'TOTAL ' + data.total + ' :: BET LOST', 'chip-loss');
  }
}

function clearBets() {
  ['bet-over', 'bet-under', 'bet-equal'].forEach(id => { document.getElementById(id).value = 0; });
}

document.addEventListener('DOMContentLoaded', () => {
  renderPips(document.getElementById('die-1'), 1);
  renderPips(document.getElementById('die-2'), 1);

  document.querySelectorAll('.bet-box').forEach(box => {
    box.addEventListener('click', (e) => {
      if (e.target.tagName === 'INPUT') return;
      selectBox(box.dataset.bet);
    });
  });
  selectBox('over');

  document.querySelectorAll('.chip-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = document.getElementById('bet-' + _selected);
      if (btn.dataset.clear) input.value = 0;
      else if (btn.dataset.add) {
        input.value = (parseInt(input.value, 10) || 0) + parseInt(btn.dataset.add, 10);
      }
    });
  });

  document.getElementById('btn-roll').addEventListener('click', roll);
  document.getElementById('btn-clear-bets').addEventListener('click', clearBets);
});
