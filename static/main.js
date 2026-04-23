let barData = Array(10).fill(120);
let faulted = false;
let faultTime = null;

function now() {
  return new Date().toLocaleTimeString();
}

function addLog(level, msg) {
  const feed = document.getElementById('logFeed');
  if (!feed) return;
  const el = document.createElement('div');
  el.className = `log-entry log-${level}`;
  el.textContent = `[${now()}] [${level}] ${msg}`;
  feed.appendChild(el);
  feed.scrollTop = feed.scrollHeight;
  if (feed.children.length > 30) feed.removeChild(feed.children[0]);
}

function addTimeline(color, label, sub) {
  const tl = document.getElementById('timeline');
  if (!tl) return;
  const el = document.createElement('div');
  el.className = 'tl-row';
  el.innerHTML = `
    <div class="tl-dot" style="background:${color}"></div>
    <div>
      <div class="tl-label">${label}</div>
      <div class="tl-sub">${sub}</div>
    </div>`;
  tl.appendChild(el);
}

function renderBars() {
  const chart = document.getElementById('barChart');
  if (!chart) return;
  chart.innerHTML = '';
  const max = Math.max(...barData, 1);
  barData.forEach(v => {
    const b = document.createElement('div');
    b.className = 'bar';
    b.style.height = Math.round((v / (max * 1.2)) * 100) + '%';
    b.style.background = v > 1000 ? '#fc8181' : v > 400 ? '#f6ad55' : '#68d391';
    chart.appendChild(b);
  });
}

async function fetchMetrics() {
  if (faulted) return;
  try {
    const res = await fetch('/api/metrics');
    const d = await res.json();
    document.getElementById('cpu').textContent = d.cpu + '%';
    document.getElementById('resp').textContent = d.response_time + 'ms';
    document.getElementById('errRate').textContent = d.error_rate + '%';
    document.getElementById('cpu').className = 'value ok';
    document.getElementById('resp').className = 'value ok';
    document.getElementById('errRate').className = 'value ok';
    barData.shift(); barData.push(d.response_time);
    renderBars();
    addLog('INFO', `GET /api/data 200 OK — ${d.response_time}ms`);
  } catch (e) {
    addLog('ERROR', 'Failed to fetch metrics');
  }
}


// ─── Inject Fault ─────────────────────────────────────
async function injectFault() {
  if (faulted) return;
  const select = document.getElementById('faultSelect');
  const fault_type = select ? select.value : 'null_pointer';

  faulted = true;
  faultTime = Date.now();

  document.getElementById('statusDot').className = 'dot fault';
  document.getElementById('statusBadge').textContent = 'FAULT';
  document.getElementById('statusBadge').className = 'badge fault';
  document.getElementById('statusText').textContent = 'Fault Detected';

  const res = await fetch('/api/inject', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ fault_type })
  });
  const data = await res.json();

  // Show fault metrics
  document.getElementById('cpu').textContent = data.cpu + '%';
  document.getElementById('cpu').className = 'value danger';
  document.getElementById('resp').textContent = data.response_time + 'ms';
  document.getElementById('resp').className = 'value danger';
  document.getElementById('errRate').textContent = data.error_rate + '%';
  document.getElementById('errRate').className = 'value danger';

  barData.shift(); barData.push(data.response_time);
  renderBars();

  // Show logs from DB
  const logsRes = await fetch('/api/logs');
  const logs = await logsRes.json();
  logs.slice(0, 3).reverse().forEach(l => addLog(l.level, l.message));

  const detectedIn = Math.round((Date.now() - faultTime) / 1000);
  addTimeline('#fc8181', `Fault: ${data.fault_type}`, `Detected at ${now()}`);
  addTimeline('#f6ad55', 'Alert triggered', `Engineer notified in ${detectedIn}s`);

  document.getElementById('infoBox').innerHTML =
    `<strong>Fault Detected: ${data.fault_type}</strong> — Logs captured instantly. Alert triggered in <strong>${detectedIn}s</strong>. Without monitoring this could take hours.`;

  // Auto recover after 6s
  setTimeout(async () => {
    const totalTime = Math.round((Date.now() - faultTime) / 1000);
    addLog('INFO', 'Hotfix deployed — service recovering');
    addTimeline('#68d391', 'System recovered', `Total time: ${totalTime}s with monitoring`);

    document.getElementById('infoBox').innerHTML =
      `<strong>Recovery complete!</strong> Fault: <strong>${data.fault_type}</strong> — Total corrective maintenance time: <strong>${totalTime}s</strong>. Monitoring made this fast!`;

    document.getElementById('statusDot').className = 'dot';
    document.getElementById('statusBadge').textContent = 'ONLINE';
    document.getElementById('statusBadge').className = 'badge online';
    document.getElementById('statusText').textContent = 'System Online';
    faulted = false;
  }, 6000);
}

// ─── Reset ────────────────────────────────────────────
async function resetSystem() {
  await fetch('/api/reset', { method: 'POST' });
  document.getElementById('logFeed').innerHTML = '';
  document.getElementById('timeline').innerHTML = `
    <div class="tl-row">
      <div class="tl-dot" style="background:#68d391"></div>
      <div>
        <div class="tl-label">System running normally</div>
        <div class="tl-sub">No faults detected</div>
      </div>
    </div>`;
  document.getElementById('statusDot').className = 'dot';
  document.getElementById('statusBadge').textContent = 'ONLINE';
  document.getElementById('statusBadge').className = 'badge online';
  document.getElementById('statusText').textContent = 'System Online';
  document.getElementById('infoBox').innerHTML =
    'System is running normally. Press <strong>Inject Fault</strong> to simulate a bug.';
  barData = Array(10).fill(120);
  renderBars();
  faulted = false;
  addLog('INFO', 'System reset — all services healthy');
}

// ─── Start ────────────────────────────────────────────
renderBars();
addLog('INFO', 'Monitoring system started');
addLog('INFO', 'Connected to MongoDB successfully');
setInterval(fetchMetrics, 2000);
fetchMetrics();