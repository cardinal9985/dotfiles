// Live game client - SocketIO + ChessBoard

let _board, _socket, _cfg, _pendingPromo;
let _lastPieceCount = 32;
let _lastMoveCount = 0;
let _audioCtx = null;
let _muted = false;

let _whiteMs = 0;
let _blackMs = 0;
let _currentTurn = 'white';
let _timedGame = false;
let _clockTimerId = null;
let _lastServerSyncTs = 0;

let _duckSquare = null;
let _duckPending = false;
let _variant = 'standard';
let _gameOver = false;

function initGame(cfg) {
  _cfg = cfg;
  _variant = cfg.variant || 'standard';
  _timedGame = cfg.timeControl && cfg.timeControl !== 'unlimited';

  const flipped = cfg.myColor === 'black';
  const interactive = !!cfg.myColor && cfg.status !== 'completed';

  _board = new ChessBoard('board', {
    flipped,
    interactive,
    onMove: handleMove,
    onSquareClick: handleSquareClick,
  });

  _socket = io({ transports: ['websocket'] });

  _socket.on('connect', () => {
    _socket.emit('join_game', { game_id: cfg.gameId });
  });

  _socket.on('your_color', (data) => {
    if (!data.color) return;
    if (_cfg.myColor === data.color) return;
    _cfg.myColor = data.color;
    const shouldFlip = data.color === 'black';
    if (_board.flipped !== shouldFlip) _board.flip();
  });

  _socket.on('game_state', (state) => {
    const myTurn = state.turn === cfg.myColor;
    const lm = myTurn && !state.duck_pending ? state.legal_moves : {};
    const moves = state.move_stack || [];
    let lastMove = null;
    if (moves.length >= 1) {
      const last = moves[moves.length - 1];
      lastMove = { from: last.slice(0, 2), to: last.slice(2, 4) };
    }
    const inCheck = state.in_check ? state.turn : null;

    const pieceCount = (state.fen.split(' ')[0].match(/[a-zA-Z]/g) || []).length;
    if (moves.length > _lastMoveCount && _lastMoveCount > 0) {
      if (state.in_check)                 playSound('check');
      else if (pieceCount < _lastPieceCount) playSound('capture');
      else                                playSound('move');
    }
    _lastPieceCount = pieceCount;
    _lastMoveCount = moves.length;

    _duckSquare = (state.duck_square === undefined ? null : state.duck_square);
    _duckPending = !!state.duck_pending;
    _currentTurn = state.turn;

    _board.duckSquare = _duckSquare;
    _board.duckPickerActive = _duckPending && isMyDuckToPlace(state);
    _board.interactive = myTurn && !!cfg.myColor && !state.duck_pending;
    _board.legalMoves = lm;
    _board.setPosition(state.fen, lm, lastMove, inCheck, state.turn);

    updateStatusText(state);
    updateDuckHint(state);
    updateCheckCounter(state.check_counts);
    updateTabTitle(state, myTurn);

    if (state.white) document.getElementById('white-name').textContent =
      state.white_is_ai ? (state.bot_name || 'BOT') : state.white;
    if (state.black) document.getElementById('black-name').textContent =
      state.black_is_ai ? (state.bot_name || 'BOT') : state.black;

    _whiteMs = state.white_time_ms || 0;
    _blackMs = state.black_time_ms || 0;
    _lastServerSyncTs = performance.now();
    if (_timedGame) startClockLoop();
    renderClocks();

    const displayMoves = (state.san_stack && state.san_stack.length === moves.length)
      ? state.san_stack : uciToDisplay(moves);
    renderMoveList(displayMoves, moves.length - 1);
  });

  _socket.on('game_over', (data) => {
    _gameOver = true;
    stopClockLoop();
    document.title = _defaultTitle;
    const panel = document.getElementById('game-over-panel');
    const text  = document.getElementById('game-over-text');
    panel.style.display = 'flex';
    const labels = {
      white_wins: 'WHITE WINS',
      black_wins: 'BLACK WINS',
      draw:       'DRAW',
      cancelled:  'GAME CANCELLED',
    };
    let msg = labels[data.result] || data.result.toUpperCase();
    if (data.resigned && data.result !== 'cancelled') msg += ` : ${data.resigned} RESIGNED`;
    if (data.timeout) msg += ` : ${data.timeout.toUpperCase()} FLAGGED`;
    text.textContent = msg;
    document.getElementById('status-text').textContent = msg;
    _board.interactive = false;
    _board.duckPickerActive = false;
    playSound(data.timeout ? 'timeout' : 'end');
    if (data.result === 'cancelled') {
      const a = document.getElementById('analysis-link');
      const p = document.getElementById('pgn-link');
      if (a) a.style.display = 'none';
      if (p) p.style.display = 'none';
    }
    if (data.rating_change) {
      const rc = data.rating_change;
      const fmt = (d) => `${d.user} ${d.new} (${d.delta >= 0 ? '+' : ''}${d.delta})`;
      const el = document.getElementById('rating-change-text');
      if (el) {
        el.textContent = `ELO :: ${fmt(rc.white)} :: ${fmt(rc.black)}`;
        el.style.display = 'block';
      }
    }
  });

  _socket.on('draw_offered', (data) => {
    if (data.by !== cfg.myColor) {
      document.getElementById('draw-offer-ui').style.display = 'flex';
    }
  });

  _socket.on('error', (data) => {
    console.warn('Chess error:', data.message);
  });

  const btnResign = document.getElementById('btn-resign');
  if (btnResign) {
    btnResign.addEventListener('click', () => {
      if (confirm('RESIGN THIS GAME?')) {
        _socket.emit('resign', { game_id: cfg.gameId });
      }
    });
  }

  const btnDraw = document.getElementById('btn-draw');
  if (btnDraw) {
    btnDraw.addEventListener('click', () => {
      _socket.emit('offer_draw', { game_id: cfg.gameId });
      btnDraw.textContent = 'DRAW OFFERED';
      btnDraw.disabled = true;
    });
  }

  const btnAcceptDraw = document.getElementById('btn-accept-draw');
  if (btnAcceptDraw) {
    btnAcceptDraw.addEventListener('click', () => {
      _socket.emit('accept_draw', { game_id: cfg.gameId });
      document.getElementById('draw-offer-ui').style.display = 'none';
    });
  }

  const btnDeclineDraw = document.getElementById('btn-decline-draw');
  if (btnDeclineDraw) {
    btnDeclineDraw.addEventListener('click', () => {
      document.getElementById('draw-offer-ui').style.display = 'none';
    });
  }

  const btnMute = document.getElementById('btn-mute');
  if (btnMute) {
    btnMute.addEventListener('click', () => {
      _muted = !_muted;
      btnMute.textContent = _muted ? 'SOUND: OFF' : 'SOUND: ON';
    });
  }

  document.querySelectorAll('.promo-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (_pendingPromo) {
        const { from, to } = _pendingPromo;
        _pendingPromo = null;
        document.getElementById('promotion-ui').style.display = 'none';
        sendMove(from, to, btn.dataset.piece);
      }
    });
  });

  if (_timedGame) {
    document.getElementById('white-clock').style.display = 'inline-block';
    document.getElementById('black-clock').style.display = 'inline-block';
  }
}

function isMyDuckToPlace(state) {
  if (!state.duck_pending) return false;
  const placerColor = state.turn === 'white' ? 'black' : 'white';
  return placerColor === _cfg.myColor;
}

function updateStatusText(state) {
  const el = document.getElementById('status-text');
  if (state.status === 'waiting') el.textContent = 'WAITING FOR OPPONENT';
  else if (state.duck_pending) {
    const placer = state.turn === 'white' ? 'BLACK' : 'WHITE';
    el.textContent = `${placer} PLACES DUCK`;
  } else el.textContent = state.turn.toUpperCase() + ' TO MOVE';
}

function updateDuckHint(state) {
  const hint = document.getElementById('duck-hint');
  if (!hint) return;
  hint.style.display = (state.duck_pending && isMyDuckToPlace(state)) ? 'inline-block' : 'none';
}

const _defaultTitle = document.title;
function updateTabTitle(state, myTurn) {
  if (_gameOver || state.status !== 'active') { document.title = _defaultTitle; return; }
  const duckMine = state.duck_pending && isMyDuckToPlace(state);
  if ((myTurn && !state.duck_pending) || duckMine) {
    document.title = `[!] YOUR TURN - ${_defaultTitle}`;
  } else {
    document.title = _defaultTitle;
  }
}

function updateCheckCounter(counts) {
  const el = document.getElementById('check-counter');
  if (!el) return;
  if (!counts) { el.style.display = 'none'; return; }
  el.style.display = 'inline';
  const wRem = counts.white, bRem = counts.black;
  el.textContent = `CHECKS: W ${3 - wRem}/3  B ${3 - bRem}/3`;
}

function handleMove(from, to) {
  if (_duckPending) return;
  const fen = _board.fen;
  const fromIdx = sqNameToIdx(from);
  const pieces  = parseFen(fen);
  const piece   = pieces[fromIdx];
  const toRank  = to[1];

  const isPromo = piece &&
    piece[1] === 'P' &&
    ((piece[0] === 'w' && toRank === '8') || (piece[0] === 'b' && toRank === '1'));

  if (isPromo) {
    _pendingPromo = { from, to };
    document.getElementById('promotion-ui').style.display = 'flex';
    return;
  }
  sendMove(from, to, 'q');
}

function handleSquareClick(sqName) {
  if (!_duckPending || !isMyDuckToPlace({ turn: _currentTurn, duck_pending: _duckPending })) return;
  const idx = sqNameToIdx(sqName);
  const pieces = parseFen(_board.fen);
  if (pieces[idx]) return;
  _socket.emit('place_duck', { game_id: _cfg.gameId, square: sqName });
}

function sendMove(from, to, promotion) {
  _socket.emit('make_move', {
    game_id:    _cfg.gameId,
    move:       from + to,
    promotion:  promotion || 'q',
  });
}

function uciToDisplay(moves) {
  return moves.map((uci) => {
    const from = uci.slice(0, 2);
    const to   = uci.slice(2, 4);
    const promo = uci[4] ? uci[4].toUpperCase() : '';
    return from + '-' + to + promo;
  });
}

function fmtClock(ms) {
  if (ms < 0) ms = 0;
  const total = Math.ceil(ms / 1000);
  const m = Math.floor(total / 60);
  const s = total % 60;
  if (m >= 1 || ms > 10000) {
    return `${m}:${s.toString().padStart(2, '0')}`;
  }
  return (ms / 1000).toFixed(1);
}

function renderClocks() {
  if (!_timedGame) return;
  const wEl = document.getElementById('white-clock');
  const bEl = document.getElementById('black-clock');
  if (!wEl || !bEl) return;

  let wMs = _whiteMs, bMs = _blackMs;
  if (!_gameOver) {
    const elapsed = performance.now() - _lastServerSyncTs;
    if (_currentTurn === 'white') wMs -= elapsed;
    else bMs -= elapsed;
  }

  wEl.textContent = fmtClock(wMs);
  bEl.textContent = fmtClock(bMs);

  wEl.classList.toggle('ticking', _currentTurn === 'white' && !_gameOver);
  bEl.classList.toggle('ticking', _currentTurn === 'black' && !_gameOver);
  wEl.classList.toggle('low', wMs < 20000);
  bEl.classList.toggle('low', bMs < 20000);
}

function startClockLoop() {
  if (_clockTimerId) return;
  _clockTimerId = setInterval(renderClocks, 100);
}
function stopClockLoop() {
  if (_clockTimerId) { clearInterval(_clockTimerId); _clockTimerId = null; }
}

function playSound(kind) {
  if (_muted) return;
  try {
    if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const ctx = _audioCtx;
    const now = ctx.currentTime;

    const beep = (freq, dur, type, vol, startOffset) => {
      const osc = ctx.createOscillator();
      const g = ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, now + startOffset);
      g.gain.setValueAtTime(vol, now + startOffset);
      g.gain.exponentialRampToValueAtTime(0.001, now + startOffset + dur);
      osc.connect(g); g.connect(ctx.destination);
      osc.start(now + startOffset);
      osc.stop(now + startOffset + dur);
    };

    if (kind === 'move')         beep(520, 0.08, 'sine', 0.14, 0);
    else if (kind === 'capture') { beep(180, 0.15, 'square', 0.18, 0); beep(90, 0.18, 'square', 0.14, 0.02); }
    else if (kind === 'check')   { beep(880, 0.06, 'triangle', 0.18, 0); beep(660, 0.06, 'triangle', 0.18, 0.07); beep(880, 0.08, 'triangle', 0.18, 0.14); }
    else if (kind === 'end')     [660, 550, 440, 330].forEach((f, i) => beep(f, 0.15, 'sine', 0.15, i * 0.1));
    else if (kind === 'timeout') beep(200, 0.3, 'sawtooth', 0.2, 0);
  } catch (e) {}
}
