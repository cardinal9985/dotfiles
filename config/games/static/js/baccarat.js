// Baccarat client

const RED_SUITS = new Set(["♥", "♦"]);
let _selected = "player";

function renderCard(container, [rank, suit]) {
  const div = document.createElement('div');
  div.className = 'card ' + (RED_SUITS.has(suit) ? 'red' : 'black');
  const r = document.createElement('div'); r.className = 'card-rank'; r.textContent = rank;
  const s = document.createElement('div'); s.className = 'card-suit'; s.textContent = suit;
  div.appendChild(r); div.appendChild(s);
  container.appendChild(div);
}

function renderHand(elId, cards) {
  const el = document.getElementById(elId);
  el.innerHTML = '';
  cards.forEach(c => renderCard(el, c));
}

function clearTable() {
  document.getElementById('player-cards').innerHTML = '';
  document.getElementById('banker-cards').innerHTML = '';
  document.getElementById('player-total').textContent = '';
  document.getElementById('banker-total').textContent = '';
  document.getElementById('bacc-vs').className = 'bacc-vs';
  document.getElementById('bacc-vs').textContent = 'VS';
  document.getElementById('bacc-result').textContent = '';
}

function selectBox(kind) {
  _selected = kind;
  document.querySelectorAll('.bet-box').forEach(b => {
    b.classList.toggle('selected', b.dataset.bet === kind);
  });
}

async function deal() {
  const bp_bet = parseInt(document.getElementById('bet-player').value, 10) || 0;
  const bb_bet = parseInt(document.getElementById('bet-banker').value, 10) || 0;
  const bt_bet = parseInt(document.getElementById('bet-tie').value, 10)    || 0;
  if (bp_bet + bb_bet + bt_bet <= 0) { alert('Place a bet'); return; }

  clearTable();

  const res = await fetch('/baccarat/api/deal', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ bet_player: bp_bet, bet_banker: bb_bet, bet_tie: bt_bet }),
  });
  const data = await res.json();
  if (!res.ok || data.error) { alert(data.error || 'Error'); return; }

  renderHand('player-cards', data.player);
  renderHand('banker-cards', data.banker);
  document.getElementById('player-total').textContent = data.player_total;
  document.getElementById('banker-total').textContent = data.banker_total;

  const vs = document.getElementById('bacc-vs');
  vs.className = 'bacc-vs ' + data.result;
  vs.textContent = data.result.toUpperCase() + ' WINS';

  const resEl = document.getElementById('bacc-result');
  if (data.net > 0)      resEl.textContent = '+' + data.net + ' TICKETS';
  else if (data.net < 0) resEl.textContent = data.net + ' TICKETS';
  else                    resEl.textContent = 'PUSH';

  document.getElementById('chip-balance').textContent = data.new_balance;

  if (window.showToast) {
    if (data.net > 0)      showToast('+' + data.payout + ' TICKETS', data.result.toUpperCase() + ' :: net +' + data.net, 'chip-win');
    else if (data.net < 0) showToast(data.net + ' TICKETS', data.result.toUpperCase() + ' :: bet lost', 'chip-loss');
    else                   showToast('BET PUSHED', data.result.toUpperCase() + ' :: no change', '');
  }
}

function clearBets() {
  ['bet-player', 'bet-banker', 'bet-tie'].forEach(id => { document.getElementById(id).value = 0; });
  clearTable();
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.bet-box').forEach(box => {
    box.addEventListener('click', (e) => {
      if (e.target.tagName === 'INPUT') return;
      selectBox(box.dataset.bet);
    });
  });
  selectBox('player');

  document.querySelectorAll('.chip-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = document.getElementById('bet-' + _selected);
      if (btn.dataset.clear) input.value = 0;
      else if (btn.dataset.add) {
        input.value = (parseInt(input.value, 10) || 0) + parseInt(btn.dataset.add, 10);
      }
    });
  });

  document.getElementById('btn-deal').addEventListener('click', deal);
  document.getElementById('btn-clear').addEventListener('click', clearBets);
});
