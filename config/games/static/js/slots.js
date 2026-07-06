// Slots client - HTTP-only

const REEL_SYMBOLS = ["🍒","🍋","🔔","⭐","7","☾"];
let _spinning = false;

async function spin() {
  if (_spinning) return;
  const bet = parseInt(document.getElementById('bet-input').value, 10);
  if (!bet || bet < 5) { alert('Enter a bet'); return; }

  const reels = [0, 1, 2].map(i => document.getElementById('reel-' + i));
  reels.forEach(r => { r.classList.add('spinning'); r.classList.remove('win', 'jackpot'); });
  const banner = document.getElementById('slot-banner');
  banner.className = 'slot-banner';
  banner.textContent = 'SPINNING...';
  _spinning = true;

  // Cycle symbols visually while waiting for server
  const interval = setInterval(() => {
    reels.forEach(r => { r.querySelector('span').textContent = REEL_SYMBOLS[Math.floor(Math.random() * REEL_SYMBOLS.length)]; });
  }, 80);

  let data = null;
  try {
    const res = await fetch('/slots/api/spin', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ bet }),
    });
    data = await res.json();
    if (!res.ok || data.error) {
      clearInterval(interval);
      _spinning = false;
      reels.forEach(r => r.classList.remove('spinning'));
      alert(data.error || 'Error');
      return;
    }
  } catch (e) {
    clearInterval(interval);
    _spinning = false;
    reels.forEach(r => r.classList.remove('spinning'));
    alert('Network error');
    return;
  }

  // Stagger the reel stops
  const stops = [700, 1100, 1500];
  stops.forEach((delay, i) => {
    setTimeout(() => {
      reels[i].classList.remove('spinning');
      reels[i].querySelector('span').textContent = data.reels[i];
      if (i === 2) {
        clearInterval(interval);
        setTimeout(() => finish(data), 200);
      }
    }, delay);
  });
}

function finish(data) {
  _spinning = false;
  document.getElementById('chip-balance').textContent = data.new_balance;
  const banner = document.getElementById('slot-banner');
  const reels = [0, 1, 2].map(i => document.getElementById('reel-' + i));

  if (data.combo.startsWith('triple_☾')) {
    banner.classList.add('jackpot');
    banner.textContent = 'JACKPOT :: +' + data.payout + ' TICKETS';
    reels.forEach(r => r.classList.add('jackpot'));
    if (window.showToast) showToast('+' + data.payout + ' TICKETS', 'JACKPOT :: TRIPLE CRESCENT', 'chip-win');
  } else if (data.combo.startsWith('triple_')) {
    banner.classList.add('win');
    banner.textContent = 'TRIPLE :: +' + data.payout + ' TICKETS';
    reels.forEach(r => r.classList.add('win'));
    if (window.showToast) showToast('+' + data.payout + ' TICKETS', 'TRIPLE :: net +' + data.net, 'chip-win');
  } else if (data.payout > 0) {
    banner.classList.add('win');
    banner.textContent = 'PAIR :: +' + data.payout + ' TICKETS';
    if (window.showToast && data.net > 0) showToast('+' + data.payout + ' TICKETS', 'PAIR :: net +' + data.net, 'chip-win');
    else if (window.showToast) showToast('BET RETURNED', 'PAIR :: no net change', '');
  } else {
    banner.classList.add('loss');
    banner.textContent = 'MISS';
    if (window.showToast) showToast('-' + data.bet + ' TICKETS', 'NO MATCH', 'chip-loss');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-spin').addEventListener('click', spin);
});
