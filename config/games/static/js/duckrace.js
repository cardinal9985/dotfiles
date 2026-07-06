// Duck Race client

let _socket, _cfg, _duckElements = {};

function renderTrack(state) {
  const track = document.getElementById('dr-track');
  const existing = new Set(Object.keys(_duckElements));

  state.ducks.forEach(duck => {
    const key = 'lane-' + duck.n;
    let lane = _duckElements[key];
    if (!lane) {
      lane = document.createElement('div');
      lane.className = 'dr-lane';
      lane.innerHTML = `
        <div class="dr-lane-name">
          <span class="duck-num">${duck.n}</span>${duck.name}
          <span class="duck-owner">${duck.user ? '- ' + duck.user : ''}</span>
        </div>
        <div class="dr-lane-strip"><span class="dr-duck">🦆</span></div>
      `;
      const finish = track.querySelector('.dr-finish');
      track.insertBefore(lane, finish);
      _duckElements[key] = lane;
    }
    const owner = lane.querySelector('.duck-owner');
    if (owner) owner.textContent = duck.user ? '- ' + duck.user : '';
    const duckEl = lane.querySelector('.dr-duck');
    if (duckEl) {
      const pct = Math.min(100, Math.max(0, duck.pos));
      duckEl.style.left = pct + '%';
      if (state.status === 'completed' && state.winner === duck.user) {
        duckEl.classList.add('winner');
      }
    }
    existing.delete(key);
  });
}

function updateStatus(state) {
  const status = document.getElementById('dr-status');
  const pot = document.getElementById('pot-display');
  if (pot) pot.textContent = state.pot;
  const filled = state.ducks.filter(d => d.user).length;
  if (state.status === 'waiting') {
    status.textContent = `WAITING :: ${filled}/6 ducks in the race`;
  } else if (state.status === 'active') {
    status.textContent = 'RACING...';
  } else {
    status.textContent = 'FINISHED';
  }
}

function handleRaceOver(state) {
  const panel = document.getElementById('game-over-panel');
  const text = document.getElementById('game-over-text');
  const pay = document.getElementById('pot-payout-text');
  panel.style.display = 'flex';
  if (state.winner) {
    text.textContent = state.winner.toUpperCase() + ' WON WITH ' + state.winner_duck.name;
    pay.textContent = '+' + state.pot + ' TICKETS';
    if (state.winner === _cfg.user && window.showToast) {
      showToast('+' + state.pot + ' TICKETS', 'DUCK RACE WON', 'chip-win');
    }
  }
  const startBtn = document.getElementById('btn-start');
  if (startBtn) startBtn.style.display = 'none';
}

function initDuckRace(cfg) {
  _cfg = cfg;
  _socket = io('/duckrace', { transports: ['websocket'] });
  _socket.on('connect', () => _socket.emit('join_race', { race_id: cfg.raceId }));

  _socket.on('race_state', (state) => {
    renderTrack(state);
    updateStatus(state);
  });
  _socket.on('race_tick', (state) => {
    renderTrack(state);
    updateStatus(state);
  });
  _socket.on('race_over', (state) => {
    renderTrack(state);
    updateStatus(state);
    handleRaceOver(state);
  });
  _socket.on('error', (data) => alert(data.message || 'Error'));

  const btn = document.getElementById('btn-start');
  if (btn) btn.addEventListener('click', () => {
    _socket.emit('start_race', { race_id: cfg.raceId });
  });

  if (cfg.initState) {
    renderTrack(cfg.initState);
    updateStatus(cfg.initState);
  }
}

window.initDuckRace = initDuckRace;
