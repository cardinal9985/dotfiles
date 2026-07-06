// Analysis board client

let _aBoard, _aSocket, _aCfg;
let _aMoves = [];
let _aEvals = [];
let _aBestMoves = [];
let _aCursor = 0;
let _aFens = [];

function initAnalysis(cfg) {
  _aCfg     = cfg;
  _aMoves   = cfg.moves   || [];
  _aEvals   = cfg.analysis  || Array(_aMoves.length).fill(null);
  _aBestMoves = cfg.bestMoves || Array(_aMoves.length).fill(null);

  _aBoard = new ChessBoard('board', { interactive: false });

  // Pre-compute FEN after each move
  _aFens = computeFens(_aMoves);

  _aCursor = _aMoves.length;
  renderPosition();
  renderMoveListAnalysis();

  document.getElementById('btn-start').addEventListener('click', () => { _aCursor = 0; renderPosition(); });
  document.getElementById('btn-end'  ).addEventListener('click', () => { _aCursor = _aMoves.length; renderPosition(); });
  document.getElementById('btn-prev' ).addEventListener('click', () => { if (_aCursor > 0) { _aCursor--; renderPosition(); } });
  document.getElementById('btn-next' ).addEventListener('click', () => { if (_aCursor < _aMoves.length) { _aCursor++; renderPosition(); } });

  document.getElementById('move-list').addEventListener('click', (e) => {
    if (e.target.dataset.idx !== undefined) {
      _aCursor = parseInt(e.target.dataset.idx) + 1;
      renderPosition();
    }
  });

  const btnAnalyze = document.getElementById('btn-analyze');
  if (btnAnalyze) {
    btnAnalyze.addEventListener('click', () => {
      btnAnalyze.textContent = 'ANALYZING...';
      btnAnalyze.disabled = true;
      _aSocket = io('/chess', { transports: ['websocket'] });
      _aSocket.on('connect', () => {
        _aSocket.emit('join_game', { game_id: cfg.gameId });
        _aSocket.emit('request_analysis', { game_id: cfg.gameId });
      });
      _aSocket.on('analysis_update', (data) => {
        _aEvals[data.move_number]    = data.evaluation;
        _aBestMoves[data.move_number] = data.best_move;
        renderMoveListAnalysis();
        if (_aCursor - 1 === data.move_number) renderPosition();
      });
      _aSocket.on('analysis_complete', () => {
        btnAnalyze.textContent = 'ANALYSIS COMPLETE';
      });
      _aSocket.on('analysis_error', (d) => {
        btnAnalyze.textContent = 'STOCKFISH UNAVAILABLE';
      });
    });
  }
}

function renderPosition() {
  const fen = _aFens[_aCursor] || 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
  let lastMove = null;
  if (_aCursor > 0) {
    const uci = _aMoves[_aCursor - 1];
    lastMove = { from: uci.slice(0, 2), to: uci.slice(2, 4) };
  }
  _aBoard.setPosition(fen, {}, lastMove, null, null);

  const eval_ = _aCursor > 0 ? _aEvals[_aCursor - 1] : 0;
  updateEvalBar(eval_);

  document.getElementById('move-counter').textContent =
    `${_aCursor} / ${_aMoves.length}`;

  renderMoveListAnalysis();
}

function renderMoveListAnalysis() {
  const el = document.getElementById('move-list');
  if (!el) return;
  el.innerHTML = '';
  for (let i = 0; i < _aMoves.length; i += 2) {
    const row = document.createElement('div');
    row.className = 'move-pair';
    const num = document.createElement('span');
    num.className = 'move-num';
    num.textContent = (i / 2 + 1) + '.';
    row.appendChild(num);
    for (let j = 0; j < 2 && (i + j) < _aMoves.length; j++) {
      const idx = i + j;
      const sp = document.createElement('span');
      sp.className = 'move-san' + (idx === _aCursor - 1 ? ' active-move' : '');
      const uci = _aMoves[idx];
      sp.textContent = uci.slice(0, 2) + '-' + uci.slice(2, 4) + (uci[4] ? uci[4].toUpperCase() : '');
      if (_aEvals[idx] !== null && _aEvals[idx] !== undefined) {
        const cp = _aEvals[idx];
        const pawn = (cp / 100).toFixed(1);
        sp.title = (cp >= 0 ? '+' : '') + pawn;
      }
      sp.dataset.idx = idx;
      row.appendChild(sp);
    }
    el.appendChild(row);
  }
  el.scrollTop = el.scrollHeight;
}

function updateEvalBar(cp) {
  const bar   = document.getElementById('eval-bar');
  const label = document.getElementById('eval-label');
  if (!bar || !label) return;
  if (cp === null || cp === undefined) {
    bar.style.height = '50%';
    label.textContent = '?';
    return;
  }
  // Clamp to ±1000cp for display
  const clamped = Math.max(-1000, Math.min(1000, cp));
  const pct = 50 + (clamped / 1000) * 50;
  bar.style.height = pct + '%';
  const pawn = (cp / 100).toFixed(2);
  label.textContent = (cp >= 0 ? '+' : '') + pawn;
}

// Replay all moves from start to produce FEN list using python-chess on backend
// For the client we do a naive incremental board — we just store FENs provided
// by replaying moves. Since we don't have chess.js, we use a simple approach:
// send moves to an API endpoint to get FENs. But to avoid the round trip,
// we'll implement a minimal FEN builder in JS.

function computeFens(moves) {
  // Use the server to get FENs — fetch synchronously via XHR
  const fens = ['rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'];
  if (!moves.length) return fens;
  try {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/chess/api/fens', false);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send(JSON.stringify({ moves }));
    if (xhr.status === 200) {
      return JSON.parse(xhr.responseText).fens;
    }
  } catch(e) {}
  return fens;
}
