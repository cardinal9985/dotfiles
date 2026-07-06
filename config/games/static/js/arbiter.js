// Shared Arbiter animation - callable from any game module.
// Given the arbiter payload from the server, plays a coin flip or RPS reveal
// animation inside the #arbiter-panel div, then calls callback(payload) once
// the reveal is complete.

const RPS_EMOJI = { rock: "✊", paper: "✋", scissors: "✌" };

window.playArbiter = function(payload, callback) {
  const panel   = document.getElementById('arbiter-panel');
  const modeEl  = document.getElementById('arbiter-mode');
  const visual  = document.getElementById('arbiter-visual');
  const verdict = document.getElementById('arbiter-verdict');
  if (!panel || !payload) { if (callback) callback(payload); return; }

  panel.style.display = 'block';
  verdict.innerHTML   = '';

  if (payload.mode === 'coin') {
    modeEl.textContent = 'COIN FLIP';
    visual.innerHTML = '<span class="coin-spinning">🪙</span>';
    setTimeout(() => {
      const roll = payload.detail.roll.toUpperCase();
      visual.innerHTML = `<span style="font-size:2rem;color:var(--bright-amber)">${roll}</span>`;
      verdict.innerHTML = `<span class="winner">${payload.winner}</span> WINS :: +${payload.prize} CHIPS`;
      if (window.showToast) showToast('+' + payload.prize + ' CHIPS', 'ARBITER RULING :: coin flip', 'arbiter');
      if (callback) setTimeout(() => callback(payload), 1500);
    }, 900);
  } else {
    modeEl.textContent = 'ROCK PAPER SCISSORS';
    visual.innerHTML = '<span class="rps-hand" id="rps-a">✊</span> <span style="color:var(--cyan)">VS</span> <span class="rps-hand" id="rps-b">✊</span>';
    let ticks = 0;
    const shuffle = setInterval(() => {
      const a = ['rock','paper','scissors'][ticks % 3];
      const b = ['scissors','rock','paper'][ticks % 3];
      document.getElementById('rps-a').textContent = RPS_EMOJI[a];
      document.getElementById('rps-b').textContent = RPS_EMOJI[b];
      ticks++;
      if (ticks >= 6) {
        clearInterval(shuffle);
        document.getElementById('rps-a').textContent = RPS_EMOJI[payload.detail.a];
        document.getElementById('rps-b').textContent = RPS_EMOJI[payload.detail.b];
        document.getElementById('rps-a').classList.add('chosen');
        document.getElementById('rps-b').classList.add('chosen');
        verdict.innerHTML = `<span class="winner">${payload.winner}</span> WINS :: +${payload.prize} CHIPS`;
        if (window.showToast) showToast('+' + payload.prize + ' CHIPS', 'ARBITER RULING :: rock paper scissors', 'arbiter');
        if (callback) setTimeout(() => callback(payload), 1500);
      }
    }, 130);
  }
};

window.hideArbiter = function() {
  const panel = document.getElementById('arbiter-panel');
  if (panel) panel.style.display = 'none';
};
