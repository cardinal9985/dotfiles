// Live game client — SocketIO + ChessBoard

let _board, _socket, _cfg, _pendingPromo;

function initGame(cfg) {
  _cfg = cfg;
  const flipped = cfg.myColor === 'black';
  const interactive = !!cfg.myColor && cfg.status !== 'completed';

  _board = new ChessBoard('board', {
    flipped,
    interactive,
    onMove: handleMove,
  });

  _socket = io({ transports: ['websocket'] });

  _socket.on('connect', () => {
    _socket.emit('join_game', { game_id: cfg.gameId });
  });

  _socket.on('game_state', (state) => {
    const myTurn = state.turn === cfg.myColor;
    const lm = myTurn ? state.legal_moves : {};
    const moves = state.move_stack || [];
    let lastMove = null;
    if (moves.length >= 1) {
      const last = moves[moves.length - 1];
      lastMove = { from: last.slice(0, 2), to: last.slice(2, 4) };
    }
    const inCheck = state.in_check ? state.turn : null;

    _board.interactive = myTurn && !!cfg.myColor;
    _board.legalMoves = lm;
    _board.setPosition(state.fen, lm, lastMove, inCheck, state.turn);

    document.getElementById('status-text').textContent =
      state.status === 'waiting' ? 'WAITING FOR OPPONENT' :
      state.turn.toUpperCase() + ' TO MOVE';

    if (state.white) document.getElementById('white-name').textContent = state.white_is_ai ? 'AI' : state.white;
    if (state.black) document.getElementById('black-name').textContent = state.black_is_ai ? 'AI' : state.black;

    // Render move list — convert UCI to simple notation for display
    renderMoveList(uciToDisplay(moves), moves.length - 1);
  });

  _socket.on('game_over', (data) => {
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
    text.textContent = msg;
    document.getElementById('status-text').textContent = msg;
    _board.interactive = false;
    if (data.result === 'cancelled') {
      const link = document.getElementById('analysis-link');
      if (link) link.style.display = 'none';
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

  // Controls
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

  // Promotion
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
}

function handleMove(from, to) {
  // Check if pawn promotion is needed
  const fen = _board.fen;
  const fenParts = fen.split(' ');
  const placement = fenParts[0];
  const turn = fenParts[1]; // 'w' or 'b'

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

function sendMove(from, to, promotion) {
  _socket.emit('make_move', {
    game_id:    _cfg.gameId,
    move:       from + to,
    promotion:  promotion || 'q',
  });
}

// Convert UCI move list to human-readable for the move log
function uciToDisplay(moves) {
  return moves.map((uci, i) => {
    const from = uci.slice(0, 2);
    const to   = uci.slice(2, 4);
    const promo = uci[4] ? uci[4].toUpperCase() : '';
    return from + '-' + to + promo;
  });
}

// sqNameToIdx is defined in board.js
