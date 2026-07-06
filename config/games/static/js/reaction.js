// Reaction Time client

let _state = 'idle';
let _greenAt = 0;
let _pendingTimeout = null;

function setState(state, msg, hint) {
  const stage = document.getElementById('rt-stage');
  stage.dataset.state = state;
  document.getElementById('rt-msg').textContent = msg;
  if (hint !== undefined) document.getElementById('rt-hint').textContent = hint;
  _state = state;
}

function startAttempt() {
  const delayMs = 1000 + Math.floor(Math.random() * 3000);  // 1-4s
  setState('waiting', 'WAIT FOR GREEN', 'DO NOT CLICK YET');
  _pendingTimeout = setTimeout(() => {
    _greenAt = performance.now();
    setState('go', 'CLICK NOW', '');
    _pendingTimeout = null;
  }, delayMs);
}

async function handleClick() {
  if (_state === 'idle' || _state === 'result' || _state === 'foul') {
    startAttempt();
    return;
  }
  if (_state === 'waiting') {
    if (_pendingTimeout) { clearTimeout(_pendingTimeout); _pendingTimeout = null; }
    setState('foul', 'TOO EARLY', 'CLICK AGAIN TO RETRY');
    return;
  }
  if (_state === 'go') {
    const timeMs = Math.round(performance.now() - _greenAt);
    setState('result', timeMs + 'ms', 'SUBMITTING...');
    try {
      const res = await fetch('/reaction/api/attempt', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ time_ms: timeMs }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        setState('idle', 'CLICK TO START', data.error || 'error');
        return;
      }
      document.getElementById('chip-balance').textContent = data.new_balance;
      const hint = data.payout > 0
        ? `PAYOUT ${data.payout} - NET ${data.net >= 0 ? '+' : ''}${data.net} - CLICK AGAIN`
        : `NO PAYOUT - NET ${data.net} - CLICK AGAIN`;
      setState('result', timeMs + 'ms', hint);
      if (window.showToast) {
        if (data.net > 0)      showToast('+' + data.payout + ' TICKETS', timeMs + 'ms', 'chip-win');
        else if (data.net < 0) showToast(data.net + ' TICKETS', timeMs + 'ms :: slow', 'chip-loss');
      }
    } catch (e) {
      setState('idle', 'NETWORK ERROR', 'CLICK TO RETRY');
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('rt-stage').addEventListener('click', handleClick);
});
