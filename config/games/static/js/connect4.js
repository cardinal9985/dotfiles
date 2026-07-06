// Connect 4 client

let _socket, _cfg, _gameState;

function renderBoard(state) {
  const boardStr = state.board;
  const cols = _cfg.cols;
  const rows = _cfg.rows;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const cell = document.querySelector(`.c4-cell[data-row="${r}"][data-col="${c}"]`);
      if (!cell) continue;
      const ch = boardStr[r * cols + c];
      cell.classList.remove('a', 'b', 'last');
      if (ch === 'a') cell.classList.add('a');
      else if (ch === 'b') cell.classList.add('b');
      if (state.last_col === c && state.last_row === r) cell.classList.add('last');
    }
  }
}

function updateControls(state) {
  const myTurn = state.status === 'active' && _cfg.myRole === state.turn;
  document.querySelectorAll('.c4-drop-btn').forEach(btn => {
    const col = parseInt(btn.dataset.col, 10);
    const topCell = document.querySelector(`.c4-cell[data-row="${_cfg.rows - 1}"][data-col="${col}"]`);
    const full = topCell && (topCell.classList.contains('a') || topCell.classList.contains('b'));
    btn.disabled = !myTurn || full;
  });
}

function applyState(state) {
  _gameState = state;
  document.getElementById('a-name').textContent = state.player_a || '···';
  document.getElementById('b-name').textContent = state.player_b || '···';
  document.getElementById('pot-display').textContent = state.pot;

  const status = document.getElementById('c4-status');
  if (state.status === 'waiting') {
    status.textContent = 'WAITING FOR OPPONENT';
  } else if (state.status === 'active') {
    const activeName = state.turn === 'a' ? state.player_a : state.player_b;
    status.textContent = activeName ? activeName.toUpperCase() + ' TO PLAY' : 'READY';
  } else {
    status.textContent = 'COMPLETED';
  }

  renderBoard(state);
  updateControls(state);
}

function handleGameOver(state) {
  const panel = document.getElementById('game-over-panel');
  const text  = document.getElementById('game-over-text');
  const pay   = document.getElementById('pot-payout-text');
  panel.style.display = 'flex';
  if (state.winner) {
    text.textContent = state.winner.toUpperCase() + ' TAKES THE POT';
    pay.textContent = '+' + state.pot + ' CHIPS';
  } else {
    text.textContent = 'DRAW';
  }
  document.querySelectorAll('.c4-drop-btn').forEach(btn => btn.disabled = true);
}

function initConnect4(cfg) {
  _cfg = cfg;
  _socket = io('/connect4', { transports: ['websocket'] });
  _socket.on('connect', () => _socket.emit('join_game', { game_id: cfg.gameId }));

  _socket.on('game_state', (state) => {
    if (state.arbiter) {
      applyState(state);
      playArbiter(state.arbiter, () => { hideArbiter(); });
    } else {
      applyState(state);
    }
  });
  _socket.on('game_over', (state) => handleGameOver(state));
  _socket.on('error',     (data)  => alert(data.message || 'Error'));

  document.querySelectorAll('.c4-drop-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const col = parseInt(btn.dataset.col, 10);
      _socket.emit('drop', { game_id: cfg.gameId, col });
    });
  });

  if (cfg.initState) applyState(cfg.initState);
}

window.initConnect4 = initConnect4;
