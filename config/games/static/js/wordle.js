(function () {
  const page = document.querySelector('.wordle-page');
  if (!page) return;

  const MAX = parseInt(page.dataset.maxGuesses, 10);
  const LEN = parseInt(page.dataset.wordLen, 10);
  const TODAY = page.dataset.today;

  const grid = document.getElementById('w-grid');
  const banner = document.getElementById('w-banner');
  const keyboard = document.getElementById('w-keyboard');
  const countdownEl = document.getElementById('w-countdown');
  const chipEl = document.getElementById('chip-balance');
  const streakEl = document.getElementById('w-streak');
  const bestEl = document.getElementById('w-best');
  const shareBtn = document.getElementById('w-share-btn');

  const rows = Array.from(grid.querySelectorAll('.w-row'));

  const state = {
    finished: page.dataset.finished === 'true',
    guessesUsed: 0,
    current: '',
    keyMark: {}, // letter -> 'green'|'yellow'|'gray'
    history: [],  // {guess, feedback} per row
  };

  // Prime state from server-rendered rows
  rows.forEach((row, ri) => {
    const tiles = row.querySelectorAll('.w-tile');
    if (tiles[0].dataset.state) {
      const guess = Array.from(tiles).map(t => t.textContent.trim().toLowerCase()).join('');
      const feedback = Array.from(tiles).map(t => t.dataset.state);
      state.history.push({ guess, feedback });
      state.guessesUsed++;
      // update key marks
      for (let i = 0; i < LEN; i++) {
        updateKeyMark(guess[i], feedback[i]);
      }
    }
  });

  function updateKeyMark(letter, mark) {
    const rank = { green: 3, yellow: 2, gray: 1 };
    const current = state.keyMark[letter];
    if (!current || rank[mark] > rank[current]) {
      state.keyMark[letter] = mark;
      const key = keyboard.querySelector(`.w-key[data-key="${letter}"]`);
      if (key) key.dataset.mark = mark;
    }
  }

  function currentRow() {
    return rows[state.guessesUsed];
  }

  function renderCurrent() {
    const row = currentRow();
    if (!row) return;
    const tiles = row.querySelectorAll('.w-tile');
    for (let i = 0; i < LEN; i++) {
      tiles[i].textContent = (state.current[i] || '').toUpperCase();
    }
  }

  function shakeRow() {
    const row = currentRow();
    if (!row) return;
    row.classList.add('w-shake');
    setTimeout(() => row.classList.remove('w-shake'), 400);
  }

  function submitGuess() {
    if (state.finished) return;
    if (state.current.length !== LEN) { shakeRow(); return; }
    const guess = state.current;

    fetch('/wordle/api/guess', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ guess }),
    }).then(r => r.json().then(data => ({ ok: r.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          if (typeof window.showToast === 'function') {
            window.showToast('WORDLE', data.error || 'Bad guess');
          }
          shakeRow();
          return;
        }
        applyFeedback(guess, data.feedback);
        state.history.push({ guess, feedback: data.feedback });
        state.guessesUsed++;
        state.current = '';
        for (let i = 0; i < LEN; i++) updateKeyMark(guess[i], data.feedback[i]);

        if (data.finished) {
          state.finished = true;
          showBanner(data);
          if (typeof chipEl !== 'undefined' && data.new_balance != null) {
            chipEl.textContent = data.new_balance;
          }
          if (data.streak != null) streakEl.textContent = data.streak;
          if (data.best_streak != null) bestEl.textContent = data.best_streak;
        }
      })
      .catch(() => {
        if (typeof window.showToast === 'function') {
          window.showToast('WORDLE', 'Network error');
        }
        shakeRow();
      });
  }

  function applyFeedback(guess, feedback) {
    const row = currentRow();
    const tiles = row.querySelectorAll('.w-tile');
    for (let i = 0; i < LEN; i++) {
      const t = tiles[i];
      t.textContent = guess[i].toUpperCase();
      setTimeout(() => { t.dataset.state = feedback[i]; }, i * 120);
    }
  }

  function showBanner(data) {
    banner.classList.remove('w-hidden');
    if (data.solved) {
      banner.classList.add('w-banner-win');
      banner.classList.remove('w-banner-loss');
      banner.innerHTML =
        `<div class="w-banner-title">// SOLVED IN ${data.guess_count}</div>
         <div class="w-banner-body">+${data.payout} TICKETS · STREAK :: ${data.streak}</div>
         <button class="w-share" id="w-share-btn">COPY SHARE GRID</button>`;
    } else {
      banner.classList.add('w-banner-loss');
      banner.classList.remove('w-banner-win');
      banner.innerHTML =
        `<div class="w-banner-title">// OUT OF GUESSES</div>
         <div class="w-banner-body">Answer was <strong>${(data.answer || '').toUpperCase()}</strong> · Streak reset</div>
         <button class="w-share" id="w-share-btn">COPY SHARE GRID</button>`;
    }
    wireShare();
  }

  function buildShareText() {
    const emojiMap = { green: '\u{1F7E9}', yellow: '\u{1F7E8}', gray: '\u{2B1B}' };
    const lines = state.history.map(h => h.feedback.map(f => emojiMap[f]).join(''));
    const solved = state.history.length > 0 &&
      state.history[state.history.length - 1].feedback.every(f => f === 'green');
    const scoreCell = solved ? `${state.history.length}/${MAX}` : `X/${MAX}`;
    return `Ishimura Wordle ${TODAY} ${scoreCell}\n\n${lines.join('\n')}`;
  }

  function wireShare() {
    const btn = document.getElementById('w-share-btn');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const text = buildShareText();
      navigator.clipboard.writeText(text).then(() => {
        if (typeof window.showToast === 'function') {
          window.showToast('WORDLE', 'Share grid copied');
        }
      }).catch(() => {
        if (typeof window.showToast === 'function') {
          window.showToast('WORDLE', 'Copy failed - grid: ' + text.slice(0, 40));
        }
      });
    });
  }
  wireShare();

  function handleInput(k) {
    if (state.finished) return;
    if (k === 'enter') { submitGuess(); return; }
    if (k === 'back')  {
      state.current = state.current.slice(0, -1);
      renderCurrent();
      return;
    }
    if (/^[a-z]$/.test(k) && state.current.length < LEN) {
      state.current += k;
      renderCurrent();
    }
  }

  keyboard.addEventListener('click', (e) => {
    const btn = e.target.closest('.w-key');
    if (!btn) return;
    handleInput(btn.dataset.key);
  });

  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === 'Enter')      handleInput('enter');
    else if (e.key === 'Backspace') handleInput('back');
    else if (/^[a-zA-Z]$/.test(e.key)) handleInput(e.key.toLowerCase());
  });

  // Countdown ticker + midnight reload
  if (countdownEl) {
    let s = parseInt(countdownEl.dataset.seconds, 10) || 0;
    const fmt = (n) => {
      const h = Math.floor(n / 3600);
      const m = Math.floor((n % 3600) / 60);
      const ss = n % 60;
      return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(ss).padStart(2,'0')}`;
    };
    countdownEl.textContent = fmt(s);
    setInterval(() => {
      s -= 1;
      if (s <= 0) { window.location.reload(); return; }
      countdownEl.textContent = fmt(s);
    }, 1000);
  }
})();
