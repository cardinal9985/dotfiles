// Chess board renderer — Dead Space theme
// Uses Unicode pieces styled with CSS; no external dependencies.

const PIECES = {
  // white pieces
  wK: '♔', wQ: '♕', wR: '♖', wB: '♗', wN: '♘', wP: '♙',
  // black pieces
  bK: '♚', bQ: '♛', bR: '♜', bB: '♝', bN: '♞', bP: '♟',
};

const FILES = ['a','b','c','d','e','f','g','h'];
const RANKS = ['8','7','6','5','4','3','2','1'];

// Parse FEN piece placement into a 64-element array indexed [rank8..rank1][a..h]
function parseFen(fen) {
  const placement = fen.split(' ')[0];
  const board = Array(64).fill(null);
  let idx = 0;
  for (const ch of placement) {
    if (ch === '/') continue;
    if (ch >= '1' && ch <= '8') { idx += parseInt(ch); continue; }
    const color = ch === ch.toUpperCase() ? 'w' : 'b';
    const type  = ch.toUpperCase();
    board[idx++] = color + type;
  }
  return board;
}

// Convert square name "e4" -> index 0-63 (rank8-file-a = 0)
function sqNameToIdx(name) {
  const f = FILES.indexOf(name[0]);
  const r = parseInt(name[1]);
  return (8 - r) * 8 + f;
}

function idxToSqName(idx) {
  return FILES[idx % 8] + (8 - Math.floor(idx / 8));
}

class ChessBoard {
  constructor(containerId, opts = {}) {
    this.el       = document.getElementById(containerId);
    this.flipped  = opts.flipped || false;
    this.onMove   = opts.onMove  || null;
    this.fen      = '8/8/8/8/8/8/8/8 w - - 0 1';
    this.legalMoves   = {};
    this.selected     = null;
    this.legalDests   = [];
    this.lastMove     = null;
    this.inCheckSq    = null;
    this.interactive  = opts.interactive !== false;
    this._build();
  }

  _build() {
    this.el.innerHTML = '';
    const ranks = this.flipped ? [...RANKS].reverse() : RANKS;
    const files = this.flipped ? [...FILES].reverse() : FILES;
    this.squares = [];
    for (let r = 0; r < 8; r++) {
      for (let f = 0; f < 8; f++) {
        const rank = ranks[r];
        const file = files[f];
        const sqName = file + rank;
        const isDark = (FILES.indexOf(file) + parseInt(rank)) % 2 === 0;
        const cell = document.createElement('div');
        cell.className = 'sq ' + (isDark ? 'dark' : 'light');
        cell.dataset.sq = sqName;
        if (f === 0) {
          const cl = document.createElement('span');
          cl.className = 'coord-rank';
          cl.textContent = rank;
          cell.appendChild(cl);
        }
        if (r === 7) {
          const cf = document.createElement('span');
          cf.className = 'coord-file';
          cf.textContent = file;
          cell.appendChild(cf);
        }
        if (this.interactive) {
          cell.addEventListener('click', () => this._onClick(sqName));
        }
        this.el.appendChild(cell);
        this.squares.push(cell);
      }
    }
  }

  _getSqEl(sqName) {
    return this.el.querySelector(`[data-sq="${sqName}"]`);
  }

  setPosition(fen, legalMoves, lastMove, inCheckColor, turn) {
    this.fen        = fen;
    this.legalMoves = legalMoves || {};
    this.lastMove   = lastMove   || null;
    this.turn       = turn;

    const pieces = parseFen(fen);
    const ranks  = this.flipped ? [...RANKS].reverse() : RANKS;
    const files  = this.flipped ? [...FILES].reverse() : FILES;

    // Find king in check
    this.inCheckSq = null;
    if (inCheckColor) {
      const kingPiece = inCheckColor === 'white' ? 'wK' : 'bK';
      for (let i = 0; i < 64; i++) {
        if (pieces[i] === kingPiece) {
          const f = FILES[i % 8];
          const r = 8 - Math.floor(i / 8);
          this.inCheckSq = f + r;
        }
      }
    }

    for (let r = 0; r < 8; r++) {
      for (let f = 0; f < 8; f++) {
        const rank = ranks[r];
        const file = files[f];
        const sqName = file + rank;
        const cell = this._getSqEl(sqName);
        if (!cell) continue;

        // Clear classes (keep dark/light)
        const isDark = cell.classList.contains('dark');
        cell.className = 'sq ' + (isDark ? 'dark' : 'light');

        // Highlights
        if (this.lastMove && (sqName === this.lastMove.from || sqName === this.lastMove.to)) {
          cell.classList.add('last-move');
        }
        if (this.selected === sqName) cell.classList.add('selected');
        if (this.legalDests.includes(sqName)) cell.classList.add('legal-dest');
        if (this.inCheckSq === sqName) cell.classList.add('in-check');

        // Remove old piece
        const old = cell.querySelector('.piece');
        if (old) old.remove();

        // Add piece
        const rawIdx = (8 - parseInt(rank)) * 8 + FILES.indexOf(file);
        const piece = pieces[rawIdx];
        if (piece) {
          const span = document.createElement('span');
          span.className = 'piece ' + (piece[0] === 'w' ? 'white-piece' : 'black-piece');
          span.textContent = PIECES[piece] || '?';
          cell.appendChild(span);
        }
      }
    }
  }

  _onClick(sqName) {
    if (!this.interactive) return;

    if (this.selected) {
      if (this.legalDests.includes(sqName)) {
        // Move
        const from = this.selected;
        this._clearSelection();
        if (this.onMove) this.onMove(from, sqName);
        return;
      }
      this._clearSelection();
      if (Object.keys(this.legalMoves).includes(sqName)) {
        this._select(sqName);
      }
    } else {
      if (Object.keys(this.legalMoves).includes(sqName)) {
        this._select(sqName);
      }
    }
  }

  _select(sqName) {
    this.selected    = sqName;
    this.legalDests  = this.legalMoves[sqName] || [];
    const cell = this._getSqEl(sqName);
    if (cell) cell.classList.add('selected');
    this.legalDests.forEach(dest => {
      const dc = this._getSqEl(dest);
      if (dc) dc.classList.add('legal-dest');
    });
  }

  _clearSelection() {
    if (this.selected) {
      const cell = this._getSqEl(this.selected);
      if (cell) cell.classList.remove('selected');
    }
    this.legalDests.forEach(dest => {
      const dc = this._getSqEl(dest);
      if (dc) dc.classList.remove('legal-dest');
    });
    this.selected   = null;
    this.legalDests = [];
  }

  flip() {
    this.flipped = !this.flipped;
    this._build();
    this.setPosition(this.fen, this.legalMoves, this.lastMove, null, this.turn);
  }
}

// Render move list into #move-list as paired rows
function renderMoveList(moves, activeIdx) {
  const el = document.getElementById('move-list');
  if (!el) return;
  el.innerHTML = '';
  for (let i = 0; i < moves.length; i += 2) {
    const row = document.createElement('div');
    row.className = 'move-pair';
    const num = document.createElement('span');
    num.className = 'move-num';
    num.textContent = (i / 2 + 1) + '.';
    row.appendChild(num);
    for (let j = 0; j < 2 && (i + j) < moves.length; j++) {
      const sp = document.createElement('span');
      sp.className = 'move-san' + ((i + j) === activeIdx ? ' active-move' : '');
      sp.textContent = moves[i + j];
      sp.dataset.idx = i + j;
      row.appendChild(sp);
    }
    el.appendChild(row);
  }
  // Scroll to bottom
  el.scrollTop = el.scrollHeight;
}
