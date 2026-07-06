// Yahtzee client

let _state = null;

function renderPips(dieEl, face) {
  dieEl.dataset.face = face;
  dieEl.innerHTML = '';
  for (let i = 0; i < face; i++) {
    const p = document.createElement('div');
    p.className = 'pip';
    dieEl.appendChild(p);
  }
}

function renderDice(state) {
  for (let i = 0; i < 5; i++) {
    const el = document.getElementById('ytz-die-' + i);
    if (!el) continue;
    renderPips(el, state.dice[i]);
    el.classList.toggle('held', !!state.held[i]);
  }
}

function renderScorecard(state) {
  document.querySelectorAll('.ytz-score').forEach(td => {
    const cat = td.dataset.cat;
    const scored = state.scorecard[cat];
    if (scored !== null && scored !== undefined) {
      td.textContent = scored;
      td.className = 'ytz-score scored';
    } else if (state.preview && state.preview[cat] !== undefined) {
      td.textContent = state.preview[cat];
      td.className = 'ytz-score available';
    } else {
      td.textContent = '-';
      td.className = 'ytz-score';
    }
  });
  document.getElementById('ytz-upper-total').textContent = state.upper_total + (state.upper_total >= 63 ? ' (+35)' : '');
  document.getElementById('ytz-grand-total').textContent = state.grand_total;
}

function renderStatus(state) {
  const status = document.getElementById('ytz-status');
  const btnRoll = document.getElementById('btn-roll');
  const btnNew = document.getElementById('btn-new');

  if (!state) {
    status.textContent = 'CLICK NEW GAME TO START';
    btnRoll.style.display = 'none';
    btnNew.style.display = 'inline-block';
    return;
  }
  if (state.status === 'completed') {
    status.textContent = `GAME OVER :: TOTAL ${state.grand_total}`;
    btnRoll.style.display = 'none';
    btnNew.style.display = 'inline-block';
    return;
  }
  status.textContent = `TURN ${state.turn}/13 :: ROLLS LEFT ${state.rolls_left}`;
  btnRoll.style.display = state.rolls_left > 0 ? 'inline-block' : 'none';
  btnRoll.textContent = state.rolls_left === 2 && state.turn === 1 && !state.dice.some(d => d !== 1) ? 'ROLL' : `ROLL (${state.rolls_left} left)`;
  btnNew.style.display = 'none';
}

function apply(state) {
  _state = state;
  renderDice(state);
  renderScorecard(state);
  renderStatus(state);
}

async function post(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body || {}),
  });
  const data = await res.json();
  if (!res.ok || data.error) {
    alert(data.error || 'Error');
    return null;
  }
  return data;
}

async function newGame() {
  const data = await post('/yahtzee/api/new');
  if (data) {
    if (data.new_balance !== undefined) document.getElementById('chip-balance').textContent = data.new_balance;
    apply(data.state);
  }
}

async function roll() {
  const held = _state ? _state.held : [false,false,false,false,false];
  const data = await post('/yahtzee/api/roll', { held });
  if (data) apply(data.state);
}

async function score(cat) {
  if (!_state) return;
  if (_state.scorecard[cat] !== null && _state.scorecard[cat] !== undefined) return;
  if (_state.rolls_left === 3) { alert('Must roll first'); return; }
  const data = await post('/yahtzee/api/score', { category: cat });
  if (data) {
    if (data.new_balance !== undefined) document.getElementById('chip-balance').textContent = data.new_balance;
    apply(data.state);
    if (data.total !== undefined) {
      const msg = 'FINAL SCORE ' + data.total + ' :: PAYOUT ' + data.payout;
      if (window.showToast) {
        if (data.payout > 0) showToast('+' + data.payout + ' TICKETS', 'YAHTZEE ' + data.total, 'chip-win');
        else showToast('YAHTZEE ' + data.total, 'no payout', 'chip-loss');
      }
    }
  }
}

function toggleHold(idx) {
  if (!_state || _state.status !== 'playing' || _state.rolls_left === 2 && _state.turn === 1 && !_state.dice.some(d => d !== 1)) return;
  if (_state.rolls_left === 2 && _state.dice.every((d, i) => d === 1)) return;  // no rolling done yet
  _state.held[idx] = !_state.held[idx];
  document.getElementById('ytz-die-' + idx).classList.toggle('held', _state.held[idx]);
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-new').addEventListener('click', newGame);
  document.getElementById('btn-roll').addEventListener('click', roll);

  for (let i = 0; i < 5; i++) {
    const el = document.getElementById('ytz-die-' + i);
    if (el) el.addEventListener('click', () => toggleHold(i));
    renderPips(el, 1);
  }

  document.querySelectorAll('.ytz-score').forEach(td => {
    td.addEventListener('click', () => score(td.dataset.cat));
  });

  if (window.YTZ_INIT_STATE) apply(window.YTZ_INIT_STATE);
});
