// Blackjack client - HTTP-only, no sockets

const RED_SUITS = new Set(["♥", "♦"]);

function renderCard(container, [rank, suit], hidden=false) {
  const div = document.createElement('div');
  div.className = 'card ' + (hidden ? 'hidden' : (RED_SUITS.has(suit) ? 'red' : 'black'));
  if (!hidden) {
    const r = document.createElement('div'); r.className = 'card-rank'; r.textContent = rank;
    const s = document.createElement('div'); s.className = 'card-suit'; s.textContent = suit;
    div.appendChild(r); div.appendChild(s);
  }
  container.appendChild(div);
}

function renderHand(elId, cards, isHiddenHand=false) {
  const el = document.getElementById(elId);
  el.innerHTML = '';
  cards.forEach((c, i) => {
    const hidden = isHiddenHand && c[0] === '?';
    renderCard(el, c, hidden);
  });
}

function setTotal(elId, total, soft=false) {
  const el = document.getElementById(elId);
  if (total === null || total === undefined) { el.textContent = ''; return; }
  el.textContent = (soft ? 'SOFT ' : '') + total;
}

function setControls(state) {
  const betRow = document.getElementById('bet-row');
  const playRow = document.getElementById('play-row');
  const nextRow = document.getElementById('next-row');
  const btnDouble = document.getElementById('btn-double');

  if (!state) {
    betRow.style.display  = 'flex';
    playRow.style.display = 'none';
    nextRow.style.display = 'none';
    return;
  }
  if (state.status === 'playing') {
    betRow.style.display  = 'none';
    playRow.style.display = 'flex';
    nextRow.style.display = 'none';
    btnDouble.disabled = !state.can_double;
  } else {
    betRow.style.display  = 'none';
    playRow.style.display = 'none';
    nextRow.style.display = 'flex';
  }
}

function setBanner(state) {
  const el = document.getElementById('result-banner');
  el.className = 'bj-result-banner';
  if (!state) { el.textContent = ''; return; }
  if (state.status === 'playing') {
    el.classList.add('playing');
    el.textContent = 'YOUR MOVE';
    return;
  }
  const labels = {
    win:       'WIN',
    blackjack: 'BLACKJACK ★',
    loss:      'LOSS',
    push:      'PUSH',
  };
  el.classList.add(state.status);
  el.textContent = labels[state.status] || state.status.toUpperCase();
}

let _lastStatus = null;
function applyState(state) {
  if (!state) {
    renderHand('player-cards', []);
    renderHand('dealer-cards', []);
    setTotal('player-total', null);
    setTotal('dealer-total', null);
    setBanner(null);
    setControls(null);
    _lastStatus = null;
    return;
  }
  const dealerHidden = state.status === 'playing';
  renderHand('dealer-cards', state.dealer, dealerHidden);
  renderHand('player-cards', state.player);
  setTotal('player-total', state.player_total, state.player_soft);
  setTotal('dealer-total', state.dealer_total);
  setBanner(state);
  setControls(state);
  if (state.new_balance !== undefined && state.new_balance !== null) {
    document.getElementById('chip-balance').textContent = state.new_balance;
  }
  // Toast chip changes at result transitions
  if (window.showToast && state.status !== _lastStatus && state.status !== 'playing') {
    const bet = state.bet;
    const payout = state.payout || 0;
    const net = payout - bet;
    if (state.status === 'blackjack') {
      showToast('+' + net + ' TICKETS', 'BLACKJACK :: 3:2 payout', 'chip-win');
    } else if (state.status === 'win') {
      showToast('+' + net + ' TICKETS', 'WIN :: dealer beaten', 'chip-win');
    } else if (state.status === 'loss') {
      showToast('-' + bet + ' TICKETS', 'HAND LOST', 'chip-loss');
    } else if (state.status === 'push') {
      showToast('BET RETURNED', 'PUSH :: no ticket change', '');
    }
  }
  _lastStatus = state.status;
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

async function actDeal() {
  const bet = parseInt(document.getElementById('bet-input').value, 10);
  if (!bet || bet < 10) { alert('Enter a bet'); return; }
  const data = await post('/blackjack/api/deal', { bet });
  if (data) applyState(data.state);
}
async function actHit()    { const d = await post('/blackjack/api/hit');    if (d) applyState(d.state); }
async function actStand()  { const d = await post('/blackjack/api/stand');  if (d) applyState(d.state); }
async function actDouble() { const d = await post('/blackjack/api/double'); if (d) applyState(d.state); }
async function actNext() {
  await post('/blackjack/api/clear');
  applyState(null);
}

function init() {
  document.getElementById('btn-deal')  .addEventListener('click', actDeal);
  document.getElementById('btn-hit')   .addEventListener('click', actHit);
  document.getElementById('btn-stand') .addEventListener('click', actStand);
  document.getElementById('btn-double').addEventListener('click', actDouble);
  document.getElementById('btn-next')  .addEventListener('click', actNext);

  document.querySelectorAll('.chip-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = document.getElementById('bet-input');
      if (btn.dataset.clear) {
        input.value = 0;
      } else if (btn.dataset.add) {
        input.value = (parseInt(input.value, 10) || 0) + parseInt(btn.dataset.add, 10);
      }
    });
  });

  applyState(window.BJ_INIT_STATE || null);
}

document.addEventListener('DOMContentLoaded', init);
