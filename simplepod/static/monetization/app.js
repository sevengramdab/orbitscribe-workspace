/**
 * SimplePod Monetization Dashboard SPA
 * Vanilla JS — no frameworks.
 */

/* -------------------------------------------------------------------------- */
/*                               CONFIGURATION                                */
/* -------------------------------------------------------------------------- */

const API_BASE = '/monetization/api';
const POLL_INTERVAL_MS = 10000;

function getApiToken() {
  return localStorage.getItem('simplepod_token') || 'simplepod-default-token';
}

/* -------------------------------------------------------------------------- */
/*                                DEMO DATA                                   */
/* -------------------------------------------------------------------------- */

const DEMO = {
  status: {
    active_agents: 12,
    queue_depth: 3,
    revenue_today: 847.50,
    revenue_month: 12430.00,
    uptime_pct: 99.97,
    last_event: 'Sale via affiliate link #A7F2'
  },
  agents: [
    { id: 'agent-1', name: 'Affiliate Scout', status: 'running', tasks_completed: 1240, revenue: 5430.20, last_active: '2 min ago' },
    { id: 'agent-2', name: 'DropSurf Bot', status: 'running', tasks_completed: 890, revenue: 3210.50, last_active: '5 min ago' },
    { id: 'agent-3', name: 'POD Designer', status: 'idle', tasks_completed: 340, revenue: 1200.00, last_active: '1 hr ago' },
    { id: 'agent-4', name: 'Email Drip', status: 'running', tasks_completed: 5600, revenue: 890.30, last_active: '1 min ago' },
    { id: 'agent-5', name: 'Social Poster', status: 'error', tasks_completed: 120, revenue: 45.00, last_active: '3 hr ago' }
  ],
  pl: {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    revenue: [3200, 4100, 3800, 5200, 6100, 7300],
    costs: [1200, 1500, 1400, 1800, 2100, 2400],
    profit: [2000, 2600, 2400, 3400, 4000, 4900],
    breakdown: [
      { category: 'Affiliate Commissions', amount: 4200.00, pct: 34 },
      { category: 'POD Sales', amount: 3800.00, pct: 31 },
      { category: 'App Subscriptions', amount: 2100.00, pct: 17 },
      { category: 'Dropshipping Margin', amount: 1500.00, pct: 12 },
      { category: 'Other', amount: 830.00, pct: 6 }
    ]
  },
  vault: {
    balance: 12430.00,
    pending: 2100.00,
    last_payout: 847.50,
    last_payout_date: '2026-05-26',
    transactions: [
      { id: 'tx-1', date: '2026-05-27', description: 'Affiliate Commission — Amazon', amount: 120.00, type: 'credit' },
      { id: 'tx-2', date: '2026-05-27', description: 'POD Sale — Printful', amount: 45.50, type: 'credit' },
      { id: 'tx-3', date: '2026-05-26', description: 'Payout to Bank', amount: 847.50, type: 'debit' },
      { id: 'tx-4', date: '2026-05-25', description: 'App Subscription Renewal', amount: 299.00, type: 'credit' },
      { id: 'tx-5', date: '2026-05-24', description: 'Ad Spend Reimbursement', amount: 150.00, type: 'credit' }
    ]
  },
  settings: {
    default_markup_pct: 30,
    auto_payout_threshold: 500.00,
    payout_method: 'bank_transfer',
    notification_email: 'admin@simplepod.dev',
    enable_auto_ads: true,
    ad_budget_daily: 50.00
  },
  credentials: [
    { id: 'cred-1', service: 'Amazon Associates', username: 'simplepod_amz', password: '••••••••••••', updated: '2026-05-01' },
    { id: 'cred-2', service: 'Printful API', username: 'simplepod_pf', password: '••••••••••••', updated: '2026-04-15' },
    { id: 'cred-3', service: 'Stripe', username: 'sk_live_****', password: '••••••••••••', updated: '2026-05-20' }
  ],
  links: [
    { id: 'link-1', name: 'Summer Tee Launch', url: 'https://amzn.to/summer-tee-2026', category: 'affiliate', clicks: 1240, conversions: 45, revenue: 320.50, status: 'active' },
    { id: 'link-2', name: 'Desk Setup Guide', url: 'https://amzn.to/desk-setup', category: 'affiliate', clicks: 890, conversions: 23, revenue: 180.00, status: 'active' },
    { id: 'link-3', name: 'Printful Storefront', url: 'https://simplepod.printful.store', category: 'pod', clicks: 560, conversions: 12, revenue: 240.00, status: 'active' },
    { id: 'link-4', name: 'App Download Landing', url: 'https://simplepod.dev/download', category: 'app', clicks: 340, conversions: 89, revenue: 0.00, status: 'active' },
    { id: 'link-5', name: 'Winter Campaign', url: 'https://amzn.to/winter-2025', category: 'affiliate', clicks: 2100, conversions: 12, revenue: 45.00, status: 'paused' }
  ],
  control: {
    mode: 'auto',
    master_switch: true,
    agents: [
      { id: 'agent-1', name: 'Affiliate Scout', enabled: true, running: true },
      { id: 'agent-2', name: 'DropSurf Bot', enabled: true, running: true },
      { id: 'agent-3', name: 'POD Designer', enabled: false, running: false },
      { id: 'agent-4', name: 'Email Drip', enabled: true, running: true },
      { id: 'agent-5', name: 'Social Poster', enabled: true, running: false }
    ],
    log: [
      { time: '11:18:42', level: 'info', message: 'Affiliate Scout found 3 new products' },
      { time: '11:15:10', level: 'success', message: 'Sale recorded via link #A7F2 ($32.00)' },
      { time: '11:10:05', level: 'warn', message: 'Social Poster rate-limited by Twitter API' },
      { time: '11:05:00', level: 'info', message: 'Auto-optimization adjusted ad bid +$0.50' },
      { time: '10:58:33', level: 'error', message: 'POD Designer render queue stalled — retrying' }
    ]
  }
};

/* -------------------------------------------------------------------------- */
/*                              STATE & REFS                                  */
/* -------------------------------------------------------------------------- */

let pollTimer = null;
let currentPage = 'overview';
const chartInstances = {}; // Cache Chart.js instances for cleanup

/* -------------------------------------------------------------------------- */
/*                               FETCH HELPERS                                */
/* -------------------------------------------------------------------------- */

async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

async function apiPost(path, data) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Token': getApiToken()
    },
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json();
}

async function apiDelete(path) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers: { 'X-Token': getApiToken() }
  });
  if (!res.ok) throw new Error(`DELETE ${path} failed: ${res.status}`);
  return res.json();
}

/* Unwrap API responses — backend wraps in {ok, data_field} */

async function fetchStatus() {
  const res = await apiGet('/status');
  return res.ok ? res : {};
}

async function fetchAgents() {
  const res = await apiGet('/agents');
  return res.ok ? (res.agents || []) : [];
}

async function fetchPL() {
  const res = await apiGet('/pl');
  return res.ok ? (res.pl || {}) : {};
}

async function fetchVault() {
  const res = await apiGet('/vault');
  return res.ok ? (res.vault || {}) : {};
}

async function fetchSettings() {
  const res = await apiGet('/settings');
  return res.ok ? (res.settings || {}) : {};
}

async function saveSettings(data) {
  const res = await apiPost('/settings', data);
  if (!res.ok) throw new Error(res.error || 'Save failed');
  return res;
}

async function fetchCredentials() {
  const res = await apiGet('/credentials');
  return res.ok ? (res.credentials || []) : [];
}

async function saveCredential(data) {
  const res = await apiPost('/credentials', data);
  if (!res.ok) throw new Error(res.error || 'Save failed');
  return res;
}

async function deleteCredential(id) {
  const res = await apiDelete(`/credentials/${id}`);
  if (!res.ok) throw new Error(res.error || 'Delete failed');
  return res;
}

async function fetchLinks() {
  const res = await apiGet('/links');
  return res.ok ? (res.links || []) : [];
}

async function saveLink(data) {
  const res = await apiPost('/links', data);
  if (!res.ok) throw new Error(res.error || 'Save failed');
  return res;
}

async function deleteLink(id) {
  const res = await apiDelete(`/links/${id}`);
  if (!res.ok) throw new Error(res.error || 'Delete failed');
  return res;
}

async function fetchControlState() {
  const res = await apiGet('/control');
  return res.ok ? (res.control || {}) : {};
}

async function saveControlState(data) {
  const res = await apiPost('/control', data);
  if (!res.ok) throw new Error(res.error || 'Save failed');
  return res;
}

async function injectDecision(data) {
  const res = await apiPost('/inject', data);
  if (!res.ok) throw new Error(res.error || 'Injection failed');
  return res;
}

/* -------------------------------------------------------------------------- */
/*                          MONEY ENGINE HELPERS                              */
/* -------------------------------------------------------------------------- */

async function fetchMoneyEngineStatus() {
  const res = await apiGet('/money-engine/status');
  return res.ok ? res : null;
}

async function startMoneyEngine(verticals, autonomyTier, oneShot) {
  const res = await apiPost('/money-engine/start', {
    verticals,
    autonomy_tier: autonomyTier,
    interval_seconds: 300,
    one_shot: oneShot,
  });
  if (!res.ok) throw new Error(res.error || 'Start failed');
  return res;
}

async function stopMoneyEngine() {
  const res = await apiPost('/money-engine/stop', {});
  if (!res.ok) throw new Error(res.error || 'Stop failed');
  return res;
}

async function injectMoneyEngineDecision(agentId, action, params) {
  const res = await apiPost('/money-engine/inject', { agent_id: agentId, action, params });
  if (!res.ok) throw new Error(res.error || 'Inject failed');
  return res;
}

/* -------------------------------------------------------------------------- */
/*                               TOAST SYSTEM                                 */
/* -------------------------------------------------------------------------- */

function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.style.cssText = `
      position: fixed; top: 1rem; right: 1rem; z-index: 9999;
      display: flex; flex-direction: column; gap: 0.5rem;
    `;
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  const colors = {
    success: '#22c55e',
    error:   '#ef4444',
    warn:    '#f59e0b',
    info:    '#3b82f6'
  };
  toast.style.cssText = `
    background: ${colors[type] || colors.info}; color: #fff;
    padding: 0.75rem 1rem; border-radius: 0.5rem;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1); font-size: 0.875rem;
    max-width: 320px; word-break: break-word; opacity: 0;
    transform: translateX(100%); transition: all 0.3s ease;
  `;
  toast.textContent = message;
  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateX(0)';
  });

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

/* -------------------------------------------------------------------------- */
/*                             NAVIGATION / ROUTER                            */
/* -------------------------------------------------------------------------- */

function initRouter() {
  const sidebar = document.querySelector('.sidebar') || document.getElementById('sidebar');
  if (sidebar) {
    sidebar.addEventListener('click', (e) => {
      const link = e.target.closest('[data-page]');
      if (link) {
        e.preventDefault();
        const page = link.getAttribute('data-page');
        window.location.hash = page;
      }
    });
  }

  window.addEventListener('hashchange', handleRoute);
  handleRoute();
}

function handleRoute() {
  const page = window.location.hash.replace('#', '') || 'overview';
  currentPage = page;

  document.querySelectorAll('.page').forEach((el) => el.classList.add('hidden'));

  const target = document.getElementById(`page-${page}`);
  if (target) target.classList.remove('hidden');

  document.querySelectorAll('[data-page]').forEach((el) => {
    el.classList.toggle('active', el.getAttribute('data-page') === page);
  });

  loadPageData(page);
  managePolling();
}

/* -------------------------------------------------------------------------- */
/*                            PAGE DATA LOADERS                               */
/* -------------------------------------------------------------------------- */

async function loadPageData(page) {
  try {
    switch (page) {
      case 'overview': {
        const status = await fetchWithFallback(fetchStatus, DEMO.status);
        const meStatus = await fetchWithFallback(fetchMoneyEngineStatus, null);
        renderOverview(status, meStatus);
        break;
      }
      case 'financial': {
        const pl = await fetchWithFallback(fetchPL, DEMO.pl);
        const vault = await fetchWithFallback(fetchVault, DEMO.vault);
        renderFinancial({ pl, vault });
        break;
      }
      case 'settings': {
        const settings = await fetchWithFallback(fetchSettings, DEMO.settings);
        renderSettings(settings);
        break;
      }
      case 'credentials': {
        const creds = await fetchWithFallback(fetchCredentials, DEMO.credentials);
        renderCredentials(creds);
        break;
      }
      case 'marketplace': {
        const links = await fetchWithFallback(fetchLinks, DEMO.links);
        renderMarketplace(links);
        break;
      }
      case 'stats': {
        const agents = await fetchWithFallback(fetchAgents, DEMO.agents);
        const meStatus = await fetchWithFallback(fetchMoneyEngineStatus, null);
        renderStats(agents, meStatus);
        break;
      }
      case 'links': {
        const links = await fetchWithFallback(fetchLinks, DEMO.links);
        renderLinks(links);
        break;
      }
      case 'swarm': {
        const control = await fetchWithFallback(fetchControlState, DEMO.control);
        const meStatus = await fetchWithFallback(fetchMoneyEngineStatus, null);
        renderSwarmControl(control, meStatus);
        break;
      }
    }
  } catch (err) {
    console.error(`Failed to load page "${page}":`, err);
    showToast(`Error loading ${page}: ${err.message}`, 'error');
  }
}

async function fetchWithFallback(fetchFn, fallback) {
  try {
    const data = await fetchFn();
    if (data === null || data === undefined) return fallback;
    if (Array.isArray(data) && data.length === 0) return fallback;
    if (typeof data === 'object' && Object.keys(data).length === 0) return fallback;
    return data;
  } catch (e) {
    console.warn('API fallback used:', e.message);
    return fallback;
  }
}

/* -------------------------------------------------------------------------- */
/*                              AUTO-REFRESH POLL                             */
/* -------------------------------------------------------------------------- */

function managePolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }

  if (currentPage === 'overview' || currentPage === 'stats') {
    pollTimer = setInterval(() => {
      loadPageData(currentPage);
    }, POLL_INTERVAL_MS);
  }
}

/* -------------------------------------------------------------------------- */
/*                             RENDER: OVERVIEW                               */
/* -------------------------------------------------------------------------- */

function renderOverview(data, meStatus) {
  const container = document.getElementById('page-overview');
  if (!container) return;

  const safe = (v, fmt) => {
    if (v === undefined || v === null) return '—';
    return fmt ? fmt(v) : v;
  };
  const money = (n) => `$${Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const pct = (n) => `${Number(n).toFixed(2)}%`;

  // Merge Money Engine data if available
  const activeAgents = meStatus ? Object.keys(meStatus.agents || {}).length : data.active_agents;
  const revenueToday = meStatus ? meStatus.total_revenue : data.revenue_today;
  const netProfit = meStatus ? meStatus.net_profit : 0;
  const lastEvent = meStatus ? `Money Engine: ${meStatus.autonomy_tier} mode` : data.last_event;

  container.innerHTML = `
    <h2 class="page-title">Overview</h2>
    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-label">Active Agents</div>
        <div class="metric-value">${safe(activeAgents)}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Queue Depth</div>
        <div class="metric-value">${safe(data.queue_depth)}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Revenue Today</div>
        <div class="metric-value">${safe(revenueToday, money)}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Net Profit</div>
        <div class="metric-value" style="color:${netProfit >= 0 ? '#22c55e' : '#ef4444'}">${safe(netProfit, money)}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Uptime</div>
        <div class="metric-value">${safe(data.uptime_pct, pct)}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Last Event</div>
        <div class="metric-value" style="font-size:1rem">${safe(lastEvent)}</div>
      </div>
    </div>
  `;
}

/* -------------------------------------------------------------------------- */
/*                            RENDER: FINANCIAL                               */
/* -------------------------------------------------------------------------- */

function renderFinancial(data) {
  const container = document.getElementById('page-financial');
  if (!container) return;

  const pl = data.pl || DEMO.pl;
  const vault = data.vault || DEMO.vault;

  container.innerHTML = `
    <h2 class="page-title">Financial</h2>

    <div class="section">
      <h3>Profit &amp; Loss</h3>
      <div class="chart-row">
        <div class="chart-box"><canvas id="chart-pl-bar"></canvas></div>
        <div class="chart-box"><canvas id="chart-pl-doughnut"></canvas></div>
      </div>
      <table class="data-table">
        <thead><tr><th>Category</th><th>Amount</th><th>Share</th></tr></thead>
        <tbody>
          ${pl.breakdown.map(b => `
            <tr>
              <td>${escapeHtml(b.category)}</td>
              <td>$${Number(b.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
              <td>${b.pct}%</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>

    <div class="section">
      <h3>Vault</h3>
      <div class="metrics-grid small">
        <div class="metric-card"><div class="metric-label">Balance</div><div class="metric-value">$${Number(vault.balance).toLocaleString('en-US', { minimumFractionDigits: 2 })}</div></div>
        <div class="metric-card"><div class="metric-label">Pending</div><div class="metric-value">$${Number(vault.pending).toLocaleString('en-US', { minimumFractionDigits: 2 })}</div></div>
        <div class="metric-card"><div class="metric-label">Last Payout</div><div class="metric-value">$${Number(vault.last_payout).toLocaleString('en-US', { minimumFractionDigits: 2 })}</div></div>
        <div class="metric-card"><div class="metric-label">Last Payout Date</div><div class="metric-value">${escapeHtml(vault.last_payout_date)}</div></div>
      </div>
      <table class="data-table">
        <thead><tr><th>Date</th><th>Description</th><th>Amount</th><th>Type</th></tr></thead>
        <tbody>
          ${vault.transactions.map(tx => `
            <tr>
              <td>${escapeHtml(tx.date)}</td>
              <td>${escapeHtml(tx.description)}</td>
              <td style="color:${tx.type==='debit'?'#ef4444':'#22c55e'}">$${Number(tx.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
              <td><span class="badge ${tx.type}">${tx.type}</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;

  drawChart('chart-pl-bar', 'bar', {
    labels: pl.labels,
    datasets: [
      { label: 'Revenue', data: pl.revenue, backgroundColor: '#3b82f6' },
      { label: 'Costs',   data: pl.costs,   backgroundColor: '#ef4444' },
      { label: 'Profit',  data: pl.profit,  backgroundColor: '#22c55e' }
    ]
  }, { responsive: true, plugins: { legend: { position: 'top' } } });

  drawChart('chart-pl-doughnut', 'doughnut', {
    labels: pl.breakdown.map(b => b.category),
    datasets: [{
      data: pl.breakdown.map(b => b.pct),
      backgroundColor: ['#3b82f6','#22c55e','#f59e0b','#ef4444','#8b5cf6']
    }]
  }, { responsive: true, plugins: { legend: { position: 'right' } } });
}

/* -------------------------------------------------------------------------- */
/*                             RENDER: SETTINGS                               */
/* -------------------------------------------------------------------------- */

function renderSettings(data) {
  const container = document.getElementById('page-settings');
  if (!container) return;

  const storedToken = localStorage.getItem('simplepod_token') || '';

  container.innerHTML = `
    <h2 class="page-title">Settings</h2>
    <form id="settings-form" class="settings-form">
      <div class="form-group">
        <label>Default Markup (%)</label>
        <input type="number" name="default_markup_pct" value="${data.default_markup_pct ?? 30}" required />
      </div>
      <div class="form-group">
        <label>Auto Payout Threshold ($)</label>
        <input type="number" step="0.01" name="auto_payout_threshold" value="${data.auto_payout_threshold ?? 500}" required />
      </div>
      <div class="form-group">
        <label>Payout Method</label>
        <select name="payout_method">
          <option value="bank_transfer" ${data.payout_method === 'bank_transfer' ? 'selected' : ''}>Bank Transfer</option>
          <option value="paypal" ${data.payout_method === 'paypal' ? 'selected' : ''}>PayPal</option>
          <option value="crypto" ${data.payout_method === 'crypto' ? 'selected' : ''}>Crypto</option>
        </select>
      </div>
      <div class="form-group">
        <label>Notification Email</label>
        <input type="email" name="notification_email" value="${escapeHtml(data.notification_email || '')}" required />
      </div>
      <div class="form-group inline">
        <label><input type="checkbox" name="enable_auto_ads" ${data.enable_auto_ads ? 'checked' : ''} /> Enable Auto Ads</label>
      </div>
      <div class="form-group">
        <label>Daily Ad Budget ($)</label>
        <input type="number" step="0.01" name="ad_budget_daily" value="${data.ad_budget_daily ?? 50}" required />
      </div>
      <div class="form-group">
        <label>API Token (for write operations)</label>
        <input type="password" id="token-input" value="${escapeHtml(storedToken)}" placeholder="simplepod-default-token" />
        <small>Leave empty to use default token</small>
      </div>
      <button type="submit" class="btn-primary">Save Settings</button>
    </form>
  `;

  document.getElementById('settings-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const tokenInput = document.getElementById('token-input');
    if (tokenInput && tokenInput.value.trim()) {
      localStorage.setItem('simplepod_token', tokenInput.value.trim());
    } else {
      localStorage.removeItem('simplepod_token');
    }
    const payload = {
      default_markup_pct: Number(fd.get('default_markup_pct')),
      auto_payout_threshold: Number(fd.get('auto_payout_threshold')),
      payout_method: fd.get('payout_method'),
      notification_email: fd.get('notification_email'),
      enable_auto_ads: fd.has('enable_auto_ads'),
      ad_budget_daily: Number(fd.get('ad_budget_daily'))
    };
    try {
      await saveSettings(payload);
      showToast('Settings saved successfully', 'success');
    } catch (err) {
      showToast(`Save failed: ${err.message}`, 'error');
    }
  });
}

/* -------------------------------------------------------------------------- */
/*                           RENDER: CREDENTIALS                              */
/* -------------------------------------------------------------------------- */

function renderCredentials(data) {
  const container = document.getElementById('page-credentials');
  if (!container) return;

  container.innerHTML = `
    <h2 class="page-title">Credentials</h2>
    <table class="data-table">
      <thead>
        <tr><th>Service</th><th>Username / Key</th><th>Password</th><th>Updated</th><th>Actions</th></tr>
      </thead>
      <tbody>
        ${(data || []).map(c => `
          <tr data-id="${c.id}">
            <td>${escapeHtml(c.service)}</td>
            <td>${escapeHtml(c.username)}</td>
            <td>
              <span class="password-mask" data-password="${escapeHtml(c.password)}">••••••••</span>
              <button type="button" class="btn-icon toggle-password" title="Show/Hide">👁</button>
            </td>
            <td>${escapeHtml(c.updated)}</td>
            <td>
              <button type="button" class="btn-danger btn-sm delete-cred">Delete</button>
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>

    <h3>Add Credential</h3>
    <form id="cred-form" class="inline-form">
      <input name="service" placeholder="Service" required />
      <input name="username" placeholder="Username / Key" required />
      <div class="pw-input-wrap">
        <input name="password" type="password" placeholder="Password" required />
        <button type="button" class="btn-icon toggle-password-input">👁</button>
      </div>
      <button type="submit" class="btn-primary">Add</button>
    </form>
  `;

  container.querySelectorAll('.toggle-password').forEach(btn => {
    btn.addEventListener('click', () => {
      const span = btn.parentElement.querySelector('.password-mask');
      const isHidden = span.textContent.startsWith('•');
      span.textContent = isHidden ? span.dataset.password : '••••••••';
    });
  });

  container.querySelectorAll('.delete-cred').forEach(btn => {
    btn.addEventListener('click', async () => {
      const row = btn.closest('tr');
      const id = row.dataset.id;
      if (!confirm('Delete this credential?')) return;
      try {
        await deleteCredential(id);
        row.remove();
        showToast('Credential deleted', 'success');
      } catch (err) {
        showToast(`Delete failed: ${err.message}`, 'error');
      }
    });
  });

  const pwToggle = container.querySelector('.toggle-password-input');
  if (pwToggle) {
    pwToggle.addEventListener('click', () => {
      const input = pwToggle.previousElementSibling;
      input.type = input.type === 'password' ? 'text' : 'password';
    });
  }

  document.getElementById('cred-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const payload = {
      service: fd.get('service'),
      username: fd.get('username'),
      password: fd.get('password')
    };
    try {
      await saveCredential(payload);
      showToast('Credential added', 'success');
      e.target.reset();
      loadPageData('credentials');
    } catch (err) {
      showToast(`Add failed: ${err.message}`, 'error');
    }
  });
}

/* -------------------------------------------------------------------------- */
/*                           RENDER: MARKETPLACE                              */
/* -------------------------------------------------------------------------- */

function renderMarketplace(data) {
  const container = document.getElementById('page-marketplace');
  if (!container) return;

  const items = Array.isArray(data) ? data : [];

  container.innerHTML = `
    <h2 class="page-title">Marketplace</h2>
    <div class="product-grid">
      ${items.map(item => `
        <div class="product-card" data-id="${item.id}">
          <div class="product-header">
            <strong>${escapeHtml(item.name || item.title || 'Unnamed')}</strong>
            <span class="badge ${item.status || 'active'}">${item.status || 'active'}</span>
          </div>
          <div class="product-meta">
            <label>Price
              <input type="number" step="0.01" class="price-input" value="${item.price ?? item.revenue ?? 0}" />
            </label>
            <label>Status
              <select class="status-input">
                <option value="active" ${(item.status === 'active') ? 'selected' : ''}>Active</option>
                <option value="paused" ${(item.status === 'paused') ? 'selected' : ''}>Paused</option>
                <option value="archived" ${(item.status === 'archived') ? 'selected' : ''}>Archived</option>
              </select>
            </label>
          </div>
          <button type="button" class="btn-primary btn-sm save-product">Save</button>
        </div>
      `).join('')}
    </div>
  `;

  container.querySelectorAll('.save-product').forEach(btn => {
    btn.addEventListener('click', async () => {
      const card = btn.closest('.product-card');
      const id = card.dataset.id;
      const payload = {
        id,
        price: Number(card.querySelector('.price-input').value),
        status: card.querySelector('.status-input').value
      };
      try {
        await saveLink(payload);
        showToast('Product updated', 'success');
      } catch (err) {
        showToast(`Update failed: ${err.message}`, 'error');
      }
    });
  });
}

/* -------------------------------------------------------------------------- */
/*                              RENDER: STATS                                 */
/* -------------------------------------------------------------------------- */

function renderStats(data, meStatus) {
  const container = document.getElementById('page-stats');
  if (!container) return;

  // Use Money Engine agents if available
  let agents = Array.isArray(data) ? data : [];
  if (meStatus && meStatus.agents) {
    agents = Object.entries(meStatus.agents).map(([aid, a]) => ({
      id: aid,
      name: (a.vertical || aid).replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()) + ' Agent',
      status: a.status || 'idle',
      tasks_completed: a.decisions_executed || 0,
      revenue: a.revenue || 0,
      last_active: a.last_run ? new Date(a.last_run * 1000).toLocaleTimeString() : '—',
    }));
  }

  container.innerHTML = `
    <h2 class="page-title">Stats</h2>
    <div class="agent-grid">
      ${agents.map(a => `
        <div class="agent-card ${a.status}">
          <div class="agent-name">${escapeHtml(a.name)}</div>
          <div class="agent-status">${a.status}</div>
          <div class="agent-metrics">
            <div><span>Decisions</span><strong>${Number(a.tasks_completed || 0).toLocaleString()}</strong></div>
            <div><span>Revenue</span><strong>$${Number(a.revenue || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</strong></div>
          </div>
          <div class="agent-meta">Last active: ${escapeHtml(a.last_active || '—')}</div>
        </div>
      `).join('')}
    </div>

    <h3>Recent Activity</h3>
    <table class="data-table">
      <thead><tr><th>Agent</th><th>Status</th><th>Decisions</th><th>Revenue</th><th>Last Active</th></tr></thead>
      <tbody>
        ${agents.map(a => `
          <tr>
            <td>${escapeHtml(a.name)}</td>
            <td><span class="badge ${a.status}">${a.status}</span></td>
            <td>${Number(a.tasks_completed || 0).toLocaleString()}</td>
            <td>$${Number(a.revenue || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
            <td>${escapeHtml(a.last_active || '—')}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

/* -------------------------------------------------------------------------- */
/*                              RENDER: LINKS                                 */
/* -------------------------------------------------------------------------- */

function renderLinks(data) {
  const container = document.getElementById('page-links');
  if (!container) return;

  const links = Array.isArray(data) ? data : [];
  const categories = [...new Set(links.map(l => l.category).filter(Boolean))];

  container.innerHTML = `
    <h2 class="page-title">Links</h2>
    <input type="text" id="link-search" placeholder="Search links..." class="search-input" />
    <div id="links-categorized">
      ${categories.map(cat => `
        <div class="link-category" data-category="${escapeHtml(cat)}">
          <h3>${escapeHtml(cat.charAt(0).toUpperCase() + cat.slice(1))}</h3>
          <div class="card-list">
            ${links.filter(l => l.category === cat).map(l => `
              <div class="link-card" data-id="${l.id}" data-name="${escapeHtml(l.name)}" data-url="${escapeHtml(l.url)}">
                <div class="link-header">
                  <strong>${escapeHtml(l.name)}</strong>
                  <span class="badge ${l.status}">${l.status}</span>
                </div>
                <div class="link-url"><a href="${escapeHtml(l.url)}" target="_blank">${escapeHtml(truncate(l.url, 60))}</a></div>
                <div class="link-metrics">
                  <span>Clicks: ${Number(l.clicks || 0).toLocaleString()}</span>
                  <span>Conv: ${Number(l.conversions || 0).toLocaleString()}</span>
                  <span>Rev: $${Number(l.revenue || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
                </div>
                <div class="link-actions">
                  <button type="button" class="btn-danger btn-sm delete-link">Delete</button>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `).join('')}
    </div>

    <h3>Add Link</h3>
    <form id="link-form" class="inline-form">
      <input name="name" placeholder="Name" required />
      <input name="url" placeholder="URL" required />
      <select name="category">
        <option value="affiliate">Affiliate</option>
        <option value="pod">POD</option>
        <option value="app">App</option>
        <option value="other">Other</option>
      </select>
      <button type="submit" class="btn-primary">Add</button>
    </form>
  `;

  const searchInput = document.getElementById('link-search');
  searchInput.addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase();
    container.querySelectorAll('.link-card').forEach(card => {
      const text = (card.dataset.name + ' ' + card.dataset.url).toLowerCase();
      card.style.display = text.includes(q) ? '' : 'none';
    });
  });

  container.querySelectorAll('.delete-link').forEach(btn => {
    btn.addEventListener('click', async () => {
      const card = btn.closest('.link-card');
      const id = card.dataset.id;
      if (!confirm('Delete this link?')) return;
      try {
        await deleteLink(id);
        card.remove();
        showToast('Link deleted', 'success');
      } catch (err) {
        showToast(`Delete failed: ${err.message}`, 'error');
      }
    });
  });

  document.getElementById('link-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const payload = {
      name: fd.get('name'),
      url: fd.get('url'),
      category: fd.get('category')
    };
    try {
      await saveLink(payload);
      showToast('Link added', 'success');
      e.target.reset();
      loadPageData('links');
    } catch (err) {
      showToast(`Add failed: ${err.message}`, 'error');
    }
  });
}

/* -------------------------------------------------------------------------- */
/*                           RENDER: SWARM CONTROL                            */
/* -------------------------------------------------------------------------- */

function renderSwarmControl(data, meStatus) {
  const container = document.getElementById('page-swarm');
  if (!container) return;

  const control = data || DEMO.control;
  const isRunning = meStatus ? meStatus.running : control.master_switch;
  const mode = meStatus ? (meStatus.autonomy_tier === 'AUTOPILOT' ? 'auto' : 'manual') : (control.mode || 'manual');

  // Build agent list from Money Engine if available
  let agents = control.agents || [];
  if (meStatus && meStatus.registered_verticals) {
    agents = meStatus.registered_verticals.map(v => {
      const meAgent = Object.values(meStatus.agents || {}).find(a => a.vertical === v);
      return {
        id: v,
        name: v.charAt(0).toUpperCase() + v.slice(1) + ' Agent',
        enabled: !!meAgent,
        running: meAgent && (meAgent.status === 'running' || meAgent.status === 'completed'),
        status: meAgent ? meAgent.status : 'idle',
        revenue: meAgent ? meAgent.revenue : 0,
        decisions: meAgent ? meAgent.decisions_executed : 0,
      };
    });
  }

  container.innerHTML = `
    <h2 class="page-title">Swarm Control</h2>

    <div class="control-header">
      <div class="control-status">
        <span class="status-dot ${isRunning ? 'on' : 'off'}"></span>
        <strong>Money Engine:</strong> ${isRunning ? 'RUNNING' : 'STOPPED'}
      </div>
      <div class="control-mode">
        <strong>Mode:</strong> ${escapeHtml(mode)}
      </div>
      <div class="control-actions">
        <button type="button" id="btn-me-start" class="btn-primary" ${isRunning ? 'disabled' : ''}>Start</button>
        <button type="button" id="btn-me-stop" class="btn-danger" ${!isRunning ? 'disabled' : ''}>Stop</button>
        <button type="button" id="btn-me-autopilot" class="btn-secondary ${mode === 'auto' ? 'active' : ''}">Autopilot</button>
        <button type="button" id="btn-me-manual" class="btn-secondary ${mode !== 'auto' ? 'active' : ''}">Manual</button>
      </div>
    </div>

    <div class="agent-grid">
      ${agents.map(a => `
        <div class="agent-control-card ${a.enabled ? 'enabled' : 'disabled'}" data-id="${a.id}">
          <div class="agent-name">${escapeHtml(a.name)}</div>
          <div class="agent-state">
            <span class="badge ${a.running ? 'running' : 'idle'}">${a.running ? 'Running' : 'Idle'}</span>
          </div>
          <div class="agent-mini-metrics" style="font-size:0.75rem;color:#888;margin:4px 0">
            Rev: $${Number(a.revenue || 0).toFixed(2)} | Decisions: ${a.decisions || 0}
          </div>
          <button type="button" class="btn-sm btn-secondary cycle-agent" data-id="${a.id}">Cycle</button>
        </div>
      `).join('')}
    </div>

    <div class="injection-section">
      <h3>Inject Decision</h3>
      <form id="inject-form" class="inline-form">
        <select name="agent_id" required>
          <option value="">Select Agent</option>
          ${agents.map(a => `<option value="${a.id}">${escapeHtml(a.name)}</option>`).join('')}
        </select>
        <input name="action" placeholder="Action (e.g., generate_blog, publish)" required />
        <input name="target" placeholder="Target / Params (JSON)" />
        <button type="submit" class="btn-primary">Inject</button>
      </form>
    </div>

    <div class="log-section">
      <h3>Activity Log</h3>
      <div class="log-panel">
        ${(meStatus && meStatus.logs ? meStatus.logs : (control.log || [])).map(entry => {
          const isString = typeof entry === 'string';
          const time = isString ? entry.slice(1, 20) : (entry.time || '—');
          const level = isString ? 'info' : (entry.level || 'info');
          const message = isString ? entry.slice(21) : (entry.message || '');
          return `
          <div class="log-entry ${level}">
            <span class="log-time">${escapeHtml(time)}</span>
            <span class="log-level">${String(level).toUpperCase()}</span>
            <span class="log-message">${escapeHtml(message)}</span>
          </div>
        `}).join('')}
      </div>
    </div>
  `;

  const startBtn = document.getElementById('btn-me-start');
  const stopBtn = document.getElementById('btn-me-stop');

  if (startBtn) {
    startBtn.addEventListener('click', async () => {
      try {
        const autonomy = mode === 'auto' ? 'AUTOPILOT' : 'DEFAULT';
        await startMoneyEngine(null, autonomy, false);
        showToast('Money Engine started', 'success');
        loadPageData('swarm');
      } catch (err) {
        showToast(`Start failed: ${err.message}`, 'error');
      }
    });
  }

  if (stopBtn) {
    stopBtn.addEventListener('click', async () => {
      try {
        await stopMoneyEngine();
        showToast('Money Engine stopped', 'success');
        loadPageData('swarm');
      } catch (err) {
        showToast(`Stop failed: ${err.message}`, 'error');
      }
    });
  }

  const autopilotBtn = document.getElementById('btn-me-autopilot');
  if (autopilotBtn) {
    autopilotBtn.addEventListener('click', async () => {
      try {
        await apiPost('/money-engine/autonomy', { tier: 'AUTOPILOT' });
        showToast('Switched to AUTOPILOT', 'success');
        loadPageData('swarm');
      } catch (err) {
        showToast(`Mode switch failed: ${err.message}`, 'error');
      }
    });
  }

  const manualBtn = document.getElementById('btn-me-manual');
  if (manualBtn) {
    manualBtn.addEventListener('click', async () => {
      try {
        await apiPost('/money-engine/autonomy', { tier: 'DEFAULT' });
        showToast('Switched to MANUAL (Kimi approval required)', 'success');
        loadPageData('swarm');
      } catch (err) {
        showToast(`Mode switch failed: ${err.message}`, 'error');
      }
    });
  }

  container.querySelectorAll('.cycle-agent').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.id;
      try {
        await injectMoneyEngineDecision(id, 'cycle', {});
        showToast(`Cycled ${id}`, 'success');
        loadPageData('swarm');
      } catch (err) {
        showToast(`Cycle failed: ${err.message}`, 'error');
      }
    });
  });

  const injectForm = document.getElementById('inject-form');
  if (injectForm) {
    injectForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      let params = {};
      try {
        const raw = fd.get('target');
        if (raw) params = JSON.parse(raw);
      } catch {}
      try {
        await injectMoneyEngineDecision(fd.get('agent_id'), fd.get('action'), params);
        showToast('Decision injected into Money Engine', 'success');
        e.target.reset();
        loadPageData('swarm');
      } catch (err) {
        showToast(`Injection failed: ${err.message}`, 'error');
      }
    });
  }
}

/* -------------------------------------------------------------------------- */
/*                              CHART HELPERS                                 */
/* -------------------------------------------------------------------------- */

function drawChart(canvasId, type, data, options = {}) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (typeof Chart === 'undefined') {
    console.warn('Chart.js not loaded');
    return;
  }
  if (chartInstances[canvasId]) {
    chartInstances[canvasId].destroy();
  }
  chartInstances[canvasId] = new Chart(ctx, { type, data, options });
}

/* -------------------------------------------------------------------------- */
/*                             UTILITY FUNCTIONS                              */
/* -------------------------------------------------------------------------- */

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function truncate(str, maxLen) {
  if (!str || str.length <= maxLen) return str;
  return str.slice(0, maxLen) + '…';
}

/* -------------------------------------------------------------------------- */
/*                                BOOTSTRAP                                   */
/* -------------------------------------------------------------------------- */

document.addEventListener('DOMContentLoaded', () => {
  initRouter();
});
