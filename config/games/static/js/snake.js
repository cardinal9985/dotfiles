// Snake client - classic solo

const GRID = 20;   // 20x20 cells
let CELL;          // cell pixel size (set on init)
let _canvas, _ctx;
let _snake, _dir, _pendingDir, _food, _score, _length, _alive, _tickId, _cfg;

function init() {
  _canvas = document.getElementById('snake-canvas');
  _ctx = _canvas.getContext('2d');
  CELL = _canvas.width / GRID;
  _cfg = window.SNAKE_CFG || { entry_fee: 10, points_per_ticket: 5 };

  document.getElementById('btn-start').addEventListener('click', startRun);
  document.addEventListener('keydown', onKey);
  drawIdle();
}

function drawIdle() {
  _ctx.fillStyle = '#0e1320';
  _ctx.fillRect(0, 0, _canvas.width, _canvas.height);
  _ctx.fillStyle = 'rgba(110,200,230,0.5)';
  _ctx.font = 'bold 20px Courier New';
  _ctx.textAlign = 'center';
  _ctx.fillText('CLICK START', _canvas.width / 2, _canvas.height / 2);
}

async function startRun() {
  const balance = parseInt(document.getElementById('chip-balance').textContent, 10);
  if (balance < _cfg.entry_fee) { alert('Not enough tickets'); return; }

  _snake = [{x: 10, y: 10}, {x: 9, y: 10}, {x: 8, y: 10}];
  _dir = { x: 1, y: 0 };
  _pendingDir = _dir;
  _food = randomFood();
  _score = 0;
  _length = 3;
  _alive = true;
  updateHud();

  document.getElementById('btn-start').disabled = true;
  document.getElementById('s-status').textContent = 'GO!';

  _canvas.focus();
  if (_tickId) clearInterval(_tickId);
  _tickId = setInterval(tick, 90);
}

function onKey(e) {
  const dirs = {
    ArrowUp:    {x: 0, y: -1}, w: {x: 0, y: -1}, W: {x: 0, y: -1},
    ArrowDown:  {x: 0, y:  1}, s: {x: 0, y:  1}, S: {x: 0, y:  1},
    ArrowLeft:  {x: -1, y: 0}, a: {x: -1, y: 0}, A: {x: -1, y: 0},
    ArrowRight: {x:  1, y: 0}, d: {x:  1, y: 0}, D: {x:  1, y: 0},
  };
  const d = dirs[e.key];
  if (!d) return;
  e.preventDefault();
  // Prevent 180deg turns
  if (d.x === -_dir.x && d.y === -_dir.y) return;
  _pendingDir = d;
}

function randomFood() {
  while (true) {
    const f = { x: Math.floor(Math.random() * GRID), y: Math.floor(Math.random() * GRID) };
    if (!_snake.some(s => s.x === f.x && s.y === f.y)) return f;
  }
}

function tick() {
  if (!_alive) return;
  _dir = _pendingDir;
  const head = _snake[0];
  const next = { x: head.x + _dir.x, y: head.y + _dir.y };

  // Wall collision
  if (next.x < 0 || next.x >= GRID || next.y < 0 || next.y >= GRID) return gameOver();

  // Self collision (exclude tail cell since it will move)
  for (let i = 0; i < _snake.length - 1; i++) {
    if (_snake[i].x === next.x && _snake[i].y === next.y) return gameOver();
  }

  _snake.unshift(next);
  if (next.x === _food.x && next.y === _food.y) {
    _score += 10;
    _length++;
    _food = randomFood();
  } else {
    _snake.pop();
  }
  updateHud();
  draw();
}

function draw() {
  _ctx.fillStyle = '#0e1320';
  _ctx.fillRect(0, 0, _canvas.width, _canvas.height);

  // Food
  _ctx.fillStyle = '#f0708a';
  _ctx.shadowColor = 'rgba(240,112,138,0.7)';
  _ctx.shadowBlur = 12;
  _ctx.fillRect(_food.x * CELL + 2, _food.y * CELL + 2, CELL - 4, CELL - 4);
  _ctx.shadowBlur = 0;

  // Snake
  _snake.forEach((seg, i) => {
    _ctx.fillStyle = i === 0 ? '#fbbf60' : '#6ec8e6';
    if (i === 0) {
      _ctx.shadowColor = 'rgba(251,191,96,0.6)';
      _ctx.shadowBlur = 8;
    }
    _ctx.fillRect(seg.x * CELL + 1, seg.y * CELL + 1, CELL - 2, CELL - 2);
    _ctx.shadowBlur = 0;
  });
}

function updateHud() {
  document.getElementById('s-score').textContent = _score;
  document.getElementById('s-length').textContent = _length;
}

async function gameOver() {
  _alive = false;
  if (_tickId) { clearInterval(_tickId); _tickId = null; }
  document.getElementById('s-status').textContent = 'GAME OVER :: SUBMITTING...';

  try {
    const res = await fetch('/snake/api/finish', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ score: _score, length: _length }),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      document.getElementById('s-status').textContent = 'ERROR: ' + (data.error || 'unknown');
      document.getElementById('btn-start').disabled = false;
      return;
    }
    document.getElementById('chip-balance').textContent = data.new_balance;
    document.getElementById('s-status').textContent =
      `GAME OVER :: SCORE ${data.score} :: ${data.net >= 0 ? '+' : ''}${data.net} TICKETS`;
    if (window.showToast) {
      if (data.net > 0) showToast('+' + data.payout + ' TICKETS', 'SCORE ' + data.score, 'chip-win');
      else showToast('SCORE ' + data.score, data.net + ' TICKETS', 'chip-loss');
    }
    document.getElementById('btn-start').disabled = false;
  } catch (e) {
    document.getElementById('s-status').textContent = 'NETWORK ERROR';
    document.getElementById('btn-start').disabled = false;
  }
}

document.addEventListener('DOMContentLoaded', init);
