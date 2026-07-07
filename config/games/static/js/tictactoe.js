(function () {
  const page = document.querySelector('.ttt-page');
  if (!page) return;

  const LINES = [
    [0,1,2],[3,4,5],[6,7,8],
    [0,3,6],[1,4,7],[2,5,8],
    [0,4,8],[2,4,6],
  ];

  const chipEl   = document.getElementById('chip-balance');
  const pickerEl = document.getElementById('ttt-difficulty');
  const boardWrap = document.getElementById('ttt-board-wrap');
  const boardEl  = document.getElementById('ttt-board');
  const statusEl = document.getElementById('ttt-status');
  const newBtn   = document.getElementById('ttt-new');
  const cells    = Array.from(boardEl.querySelectorAll('.ttt-cell'));

  const state = {
    gameId: page.dataset.activeId || null,
    difficulty: page.dataset.activeDifficulty || null,
    board: JSON.parse(page.dataset.activeBoard || '[null,null,null,null,null,null,null,null,null]'),
    finished: false,
  };

  function renderBoard(highlight) {
    cells.forEach((c, i) => {
      c.classList.remove('taken', 'player', 'bot', 'win-line');
      const v = state.board[i];
      if (v === 'X') { c.textContent = 'X'; c.classList.add('taken', 'player'); }
      else if (v === 'O') { c.textContent = 'O'; c.classList.add('taken', 'bot'); }
      else { c.textContent = ''; }
    });
    if (highlight) highlight.forEach(i => cells[i].classList.add('win-line'));
  }

  function findWinLine() {
    for (const line of LINES) {
      const [a,b,c] = line;
      if (state.board[a] && state.board[a] === state.board[b] && state.board[b] === state.board[c]) {
        return line;
      }
    }
    return null;
  }

  function setStatus(text, kind) {
    statusEl.textContent = text;
    statusEl.classList.remove('win', 'lose', 'draw');
    if (kind) statusEl.classList.add(kind);
  }

  function showBoardView() {
    pickerEl.style.display = 'none';
    boardWrap.style.display = '';
  }

  function showPickerView() {
    pickerEl.style.display = '';
    boardWrap.style.display = 'none';
    state.gameId = null;
    state.difficulty = null;
    state.board = Array(9).fill(null);
    state.finished = false;
    renderBoard();
  }

  function startGame(difficulty) {
    fetch('/tictactoe/api/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ difficulty }),
    }).then(r => r.json().then(d => ({ ok: r.ok, d })))
      .then(({ ok, d }) => {
        if (!ok) {
          if (typeof window.showToast === 'function') window.showToast('TTT', d.error);
          return;
        }
        state.gameId = d.game_id;
        state.difficulty = d.difficulty;
        state.board = d.board;
        state.finished = false;
        if (d.new_balance != null) chipEl.textContent = d.new_balance;
        setStatus(`${d.difficulty.toUpperCase()} :: YOUR MOVE`);
        showBoardView();
        renderBoard();
      });
  }

  function sendMove(cell) {
    if (state.finished || !state.gameId) return;
    if (state.board[cell] !== null) return;
    fetch('/tictactoe/api/move', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: state.gameId, cell }),
    }).then(r => r.json().then(d => ({ ok: r.ok, d })))
      .then(({ ok, d }) => {
        if (!ok) {
          if (typeof window.showToast === 'function') window.showToast('TTT', d.error);
          return;
        }
        state.board = d.board;
        if (d.new_balance != null) chipEl.textContent = d.new_balance;

        if (d.status === 'active') {
          setStatus(`${state.difficulty.toUpperCase()} :: YOUR MOVE`);
          renderBoard();
        } else {
          state.finished = true;
          const line = findWinLine();
          renderBoard(line);
          if (d.status === 'won') {
            setStatus(`YOU WIN · +${d.payout} TICKETS`, 'win');
            if (typeof window.showToast === 'function') window.showToast('TTT', `+${d.payout} tickets`, 'chip-win');
          } else if (d.status === 'lost') {
            setStatus('YOU LOSE', 'lose');
          } else {
            setStatus(`DRAW · +${d.payout} TICKETS`, 'draw');
          }
        }
      });
  }

  pickerEl.addEventListener('click', (e) => {
    const btn = e.target.closest('.ttt-diff-btn');
    if (!btn) return;
    startGame(btn.dataset.difficulty);
  });

  boardEl.addEventListener('click', (e) => {
    const cell = e.target.closest('.ttt-cell');
    if (!cell) return;
    sendMove(parseInt(cell.dataset.cell, 10));
  });

  newBtn.addEventListener('click', showPickerView);

  // On load: resume active game if any
  if (state.gameId) {
    setStatus(`${(state.difficulty || '').toUpperCase()} :: YOUR MOVE`);
    showBoardView();
    renderBoard();
  }
})();
