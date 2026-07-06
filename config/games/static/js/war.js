// War 1v1 client

const RED_SUITS = new Set(["♥", "♦"]);
let _socket, _cfg, _muted = false;

function renderCard(container, [rank, suit]) {
  container.innerHTML = '';
  const div = document.createElement('div');
  div.className = 'card ' + (RED_SUITS.has(suit) ? 'red' : 'black');
  const r = document.createElement('div'); r.className = 'card-rank'; r.textContent = rank;
  const s = document.createElement('div'); s.className = 'card-suit'; s.textContent = suit;
  div.appendChild(r); div.appendChild(s);
  container.appendChild(div);
}

function clearSlot(id) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = '';
}

function applyState(state) {
  if (!state) return;
  document.getElementById('a-name').textContent = state.player_a || '···';
  document.getElementById('b-name').textContent = state.player_b || '···';
  document.getElementById('a-score').textContent = state.a_score;
  document.getElementById('b-score').textContent = state.b_score;
  document.getElementById('round-index').textContent = state.round_index;
  document.getElementById('pot-display').textContent = state.pot;

  const vs = document.getElementById('vs-indicator');
  const status = document.getElementById('war-status');
  const btnNext = document.getElementById('btn-next');

  if (state.status === 'waiting') {
    status.textContent = 'WAITING FOR OPPONENT';
    if (btnNext) btnNext.style.display = 'none';
    vs.className = 'war-vs'; vs.textContent = 'VS';
    return;
  }
  if (state.status === 'active') {
    status.textContent = state.round_index === 0 ? 'READY TO FLIP' : 'NEXT ROUND';
    if (btnNext && _cfg.myRole) btnNext.style.display = 'inline-block';
  } else {
    status.textContent = 'COMPLETED';
    if (btnNext) btnNext.style.display = 'none';
  }

  if (state.last_round) {
    renderCard(document.getElementById('a-slot'), state.last_round.a_card);
    renderCard(document.getElementById('b-slot'), state.last_round.b_card);
    vs.className = 'war-vs ' + (state.last_round.winner === 'a' ? 'a-win' : 'b-win');
    vs.textContent = state.last_round.winner === 'a' ? '◀' : '▶';
    playSound(state.last_round.a_card[0] === state.last_round.b_card[0] ? 'tie' : 'flip');
  }
}

function handleGameOver(state) {
  const panel = document.getElementById('game-over-panel');
  const text  = document.getElementById('game-over-text');
  const payText = document.getElementById('pot-payout-text');
  panel.style.display = 'flex';
  if (state.winner) {
    text.textContent = state.winner.toUpperCase() + ' TAKES THE POT';
    payText.textContent = '+' + state.pot + ' CHIPS';
    if (state.winner === (_cfg.myRole === 'a' ? state.player_a : state.player_b) && !_muted) playSound('win');
  } else {
    text.textContent = 'DRAW';
  }
  const btn = document.getElementById('btn-next');
  if (btn) btn.style.display = 'none';
}

function initWar(cfg) {
  _cfg = cfg;
  _socket = io('/war', { transports: ['websocket'] });
  _socket.on('connect', () => _socket.emit('join_game', { game_id: cfg.gameId }));

  _socket.on('game_state', (state) => {
    if (state.arbiter) {
      playArbiter(state.arbiter, () => { hideArbiter(); applyState(state); });
    } else {
      applyState(state);
    }
  });

  _socket.on('game_over', (state) => handleGameOver(state));
  _socket.on('error',     (data)  => alert(data.message || 'Error'));

  const btn = document.getElementById('btn-next');
  if (btn) btn.addEventListener('click', () => {
    clearSlot('a-slot'); clearSlot('b-slot');
    _socket.emit('next_round', { game_id: cfg.gameId });
  });

  const mute = document.getElementById('btn-mute');
  if (mute) mute.addEventListener('click', () => {
    _muted = !_muted;
    mute.textContent = _muted ? 'SOUND: OFF' : 'SOUND: ON';
  });

  if (cfg.initState) applyState(cfg.initState);
}

let _audioCtx = null;
function playSound(kind) {
  if (_muted) return;
  try {
    if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const ctx = _audioCtx;
    const now = ctx.currentTime;
    const beep = (f, dur, type, vol, off) => {
      const osc = ctx.createOscillator(); const g = ctx.createGain();
      osc.type = type; osc.frequency.setValueAtTime(f, now + off);
      g.gain.setValueAtTime(vol, now + off);
      g.gain.exponentialRampToValueAtTime(0.001, now + off + dur);
      osc.connect(g); g.connect(ctx.destination);
      osc.start(now + off); osc.stop(now + off + dur);
    };
    if (kind === 'flip')      beep(440, 0.08, 'sine', 0.14, 0);
    else if (kind === 'tie')  { beep(880, 0.06, 'triangle', 0.18, 0); beep(660, 0.06, 'triangle', 0.18, 0.07); }
    else if (kind === 'win')  [660, 880, 1100].forEach((f, i) => beep(f, 0.15, 'sine', 0.15, i * 0.12));
  } catch (e) {}
}

window.initWar = initWar;
