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
    if (!cat) return;
    const scored = state.scorecard ? state.scorecard[cat] : null;
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
  // Pulse the available cells when the player MUST score
  const tbody = document.getElementById('ytz-scorecard');
  if (tbody) tbody.classList.toggle('must-score', state.status === 'playing' && state.rolls_left === 0);
  document.getElementById('ytz-upper-total').textContent =
    state.upper_total + (state.upper_total >= 63 ? ' (+35)' : '');
  document.getElementById('ytz-grand-total').textContent = state.grand_total;
}

function showGameOver(state, payout) {
  const panel = document.getElementById('ytz-gameover-panel');
  const scoreEl = document.getElementById('ytz-gameover-score');
  const payEl   = document.getElementById('ytz-gameover-payout');
  const fee = window.YTZ_ENTRY_FEE || 25;
  scoreEl.textContent = state.grand_total;
  const net = (payout || 0) - fee;
  if (net > 0) {
    payEl.className = 'ytz-gameover-payout win';
    payEl.textContent = 'WIN :: +' + payout + ' TICKETS (net +' + net + ')';
  } else if (net === 0) {
    payEl.className = 'ytz-gameover-payout push';
    payEl.textContent = 'BREAK EVEN :: entry returned';
  } else {
    payEl.className = 'ytz-gameover-payout loss';
    payEl.textContent = 'NO PAYOUT :: -' + fee + ' TICKETS';
  }
  panel.style.display = 'flex';
  panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function hideGameOver() {
  const panel = document.getElementById('ytz-gameover-panel');
  if (panel) panel.style.display = 'none';
}

function renderStatus(state) {
  const status = document.getElementById('ytz-status');
  const btnRoll = document.getElementById('btn-roll');
  const btnNew = document.getElementById('btn-new');
  const btnAbandon = document.getElementById('btn-abandon');

  if (!state) {
    status.textContent = 'CLICK NEW GAME TO START';
    btnRoll.style.display = 'none';
    btnAbandon.style.display = 'none';
    btnNew.style.display = 'inline-block';
    return;
  }
  if (state.status === 'completed') {
    status.textContent = `GAME OVER :: TOTAL ${state.grand_total}`;
    btnRoll.style.display = 'none';
    btnAbandon.style.display = 'none';
    btnNew.style.display = 'inline-block';
    return;
  }

  // Playing
  if (state.rolls_left > 0) {
    status.textContent = `TURN ${state.turn}/13 :: ${state.rolls_left} ROLL${state.rolls_left === 1 ? '' : 'S'} LEFT :: click a category to score`;
    btnRoll.style.display = 'inline-block';
    btnRoll.textContent = `ROLL (${state.rolls_left} left)`;
  } else {
    status.textContent = `TURN ${state.turn}/13 :: NO ROLLS LEFT :: MUST SCORE - click a highlighted category`;
    btnRoll.style.display = 'none';
  }
  btnNew.style.display = 'none';
  btnAbandon.style.display = 'inline-block';
}

function apply(state) {
  _state = state;
  renderDice(state);
  renderScorecard(state);
  renderStatus(state);
}

async function post(url, body) {
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body || {}),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      const msg = data.error || `HTTP ${res.status}`;
      if (window.showToast) showToast('ERROR', msg, 'chip-loss');
      else alert(msg);
      return null;
    }
    return data;
  } catch (e) {
    const msg = 'Network error: ' + e.message;
    if (window.showToast) showToast('ERROR', msg, 'chip-loss');
    else alert(msg);
    return null;
  }
}

async function newGame() {
  if (_state && _state.status === 'playing') {
    if (!confirm('Abandon current game and start new? (no ticket refund)')) return;
    await post('/yahtzee/api/abandon');
  }
  hideGameOver();
  const data = await post('/yahtzee/api/new');
  if (data) {
    if (data.new_balance !== undefined) document.getElementById('chip-balance').textContent = data.new_balance;
    const hint = document.getElementById('ytz-hint');
    if (hint) hint.style.display = 'none';
    apply(data.state);
  }
}

async function abandon() {
  if (!confirm('End the current game? Scored categories will be saved, no payout.')) return;
  const data = await post('/yahtzee/api/abandon');
  if (data) {
    _state = null;
    renderStatus(null);
    // Refresh page to show updated leaderboard/best
    setTimeout(() => window.location.reload(), 500);
  }
}

async function roll() {
  const held = _state ? _state.held : [false, false, false, false, false];
  const data = await post('/yahtzee/api/roll', { held });
  if (data) apply(data.state);
}

async function score(cat) {
  if (!_state) { alert('No active game - start a NEW GAME'); return; }
  if (_state.status !== 'playing') { alert('Game is not active'); return; }
  if (_state.scorecard[cat] !== null && _state.scorecard[cat] !== undefined) {
    if (window.showToast) showToast('CATEGORY LOCKED', 'already scored', '');
    return;
  }
  const data = await post('/yahtzee/api/score', { category: cat });
  if (!data) return;
  if (data.new_balance !== undefined) document.getElementById('chip-balance').textContent = data.new_balance;
  apply(data.state);
  if (data.total !== undefined) {
    // Game just finished
    showGameOver(data.state, data.payout);
    if (window.showToast) {
      if (data.payout > (window.YTZ_ENTRY_FEE || 25))
        showToast('+' + data.payout + ' TICKETS', 'YAHTZEE ' + data.total, 'chip-win');
      else
        showToast('YAHTZEE ' + data.total, 'no payout', 'chip-loss');
    }
  }
}

function toggleHold(idx) {
  if (!_state || _state.status !== 'playing') return;
  _state.held[idx] = !_state.held[idx];
  document.getElementById('ytz-die-' + idx).classList.toggle('held', _state.held[idx]);
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-new').addEventListener('click', newGame);
  document.getElementById('btn-roll').addEventListener('click', roll);
  document.getElementById('btn-abandon').addEventListener('click', abandon);
  const btnPanelNew = document.getElementById('btn-new-panel');
  if (btnPanelNew) btnPanelNew.addEventListener('click', newGame);

  for (let i = 0; i < 5; i++) {
    const el = document.getElementById('ytz-die-' + i);
    if (el) {
      el.addEventListener('click', () => toggleHold(i));
      renderPips(el, 1);
    }
  }

  document.querySelectorAll('.ytz-score').forEach(td => {
    td.addEventListener('click', () => score(td.dataset.cat));
  });

  if (window.YTZ_INIT_STATE) {
    apply(window.YTZ_INIT_STATE);
    const hint = document.getElementById('ytz-hint');
    if (hint) hint.style.display = 'none';
  }
});
