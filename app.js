let allData = {}; 
let portfolioData = null;
let activeTab = 'portfolio'; // Default to portfolio tab now!
let activeTimeframe = '1y';
let activeCompany = null;
let priceChart = null;
let indChart = null;

const STRATEGY_NAMES = {
    semi: 'High-Velocity Swing',
    ancillary: 'High-Velocity Swing',
    nuclear: 'High-Velocity Swing',
    water: 'High-Velocity Swing',
    drone: 'High-Velocity Swing',
    datacenter: 'High-Velocity Swing',
    hydrogen: 'High-Velocity Swing'
};

Promise.all([
    fetch('semi_data.json?v=' + Date.now()).then(r => r.json()).catch(() => ({})),
    fetch('data.json?v=' + Date.now()).then(r => r.json()).catch(() => ({})),
    fetch('nuclear_data.json?v=' + Date.now()).then(r => r.json()).catch(() => ({})),
    fetch('water_data.json?v=' + Date.now()).then(r => r.json()).catch(() => ({})),
    fetch('drone_data.json?v=' + Date.now()).then(r => r.json()).catch(() => ({})),
    fetch('datacenter_data.json?v=' + Date.now()).then(r => r.json()).catch(() => ({})),
    fetch('hydrogen_data.json?v=' + Date.now()).then(r => r.json()).catch(() => ({})),
    fetch('portfolio.json?v=' + Date.now()).then(r => r.json()).catch(() => null)
]).then(([semi, anc, nuclear, water, drone, datacenter, hydrogen, port]) => {
    allData = { semi, ancillary: anc, nuclear, water, drone, datacenter, hydrogen };
    portfolioData = port;
    switchTab('portfolio'); // Initialize
}).catch(err => {
    console.error(err);
    document.querySelector('.dashboard').innerHTML = `<div style="text-align:center;margin-top:100px;width:100%;"><h1 style="color:#ef4444">Data Failed to Load</h1><p style="color:#94a3b8;margin-top:16px;">Check GitHub Actions logs.</p></div>`;
});

window.switchTab = function(tab) {
    activeTab = tab;
    document.querySelectorAll('.tab-btn[data-tab]').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    
    const sidebarElements = document.getElementById('company-sidebar-elements');
    const compView = document.getElementById('company-view');
    const portView = document.getElementById('portfolio-view');
    const strategyName = document.getElementById('strategy-name-display');
    
    if (tab === 'portfolio') {
        sidebarElements.style.display = 'none';
        compView.style.display = 'none';
        portView.style.display = 'block';
        strategyName.textContent = 'Account Ledger';
        if (portfolioData) renderPortfolio();
    } else {
        sidebarElements.style.display = 'block';
        compView.style.display = 'block';
        portView.style.display = 'none';
        strategyName.textContent = STRATEGY_NAMES[tab] || 'Unknown';
        initSidebar();
    }
};

window.switchTimeframe = function(tf) {
    activeTimeframe = tf;
    document.querySelectorAll('.tf-btn').forEach(b => b.classList.toggle('active', b.dataset.tf === tf));
    initSidebar();
};

function getCurrentData() {
    const tabData = allData[activeTab];
    return tabData && tabData[activeTimeframe] ? tabData[activeTimeframe] : {};
}

// ---------------------------------------------------------
// PORTFOLIO RENDERING LOGIC
// ---------------------------------------------------------
function renderPortfolio() {
    if (!portfolioData) return;
    
    // Helper to find latest price from allData
    const getLatestPrice = (compName) => {
        for (const sec in allData) {
            if (allData[sec] && allData[sec]['1y'] && allData[sec]['1y'][compName]) {
                return allData[sec]['1y'][compName].current_price;
            }
        }
        return null; // not found
    };

    let totalVal = portfolioData.cash;
    const TRADE_SIZE = 150000.0;
    
    const activeTbody = document.getElementById('active-positions-tbody');
    activeTbody.innerHTML = '';
    
    if (!portfolioData.active_positions || Object.keys(portfolioData.active_positions).length === 0) {
        activeTbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:20px;color:#94a3b8;">No active positions. 100% in cash.</td></tr>';
    } else {
        for (const [comp, pos] of Object.entries(portfolioData.active_positions)) {
            let livePrice = getLatestPrice(comp);
            let displayPrice = livePrice || pos.entry_price;
            
            let posSize = pos.position_size || 1.0;
            let sizeLabel = posSize === 1.0 ? "Full" : "Runner (50%)";
            let shares = pos.shares || Math.floor(150000.0 / pos.entry_price);
            let capital = pos.capital_deployed || (shares * pos.entry_price);
            
            let targetLabel = posSize === 1.0 ? `₹${pos.target.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : "Trailing Infinite";
            
            let unrealizedPct = ((displayPrice - pos.entry_price) / pos.entry_price) * 100;
            let unrealizedVal = shares * (displayPrice - pos.entry_price);
            
            totalVal += (capital + unrealizedVal);
            
            let color = unrealizedPct >= 0 ? '#10b981' : '#ef4444';
            let sign = unrealizedPct >= 0 ? '+' : '';
            
            let tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${pos.entry_date}<br><small style="color:#a855f7">${sizeLabel}</small></td>
                <td><strong>${comp}</strong></td>
                <td>${shares}</td>
                <td>₹${pos.entry_price.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}<br><small style="color:#94a3b8">Cap: ₹${capital.toLocaleString('en-IN', {minimumFractionDigits:0})}</small></td>
                <td style="color:#10b981">${targetLabel}</td>
                <td style="color:#ef4444">₹${pos.stop.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td>₹${displayPrice.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td style="color:${color}; font-weight:bold;">${sign}${unrealizedPct.toFixed(2)}% (₹${unrealizedVal.toLocaleString('en-IN', {minimumFractionDigits:0})})</td>
            `;
            activeTbody.appendChild(tr);
        }
    }

    // Top Ribbon Stats
    document.getElementById('port-val').textContent = '₹' + totalVal.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    document.getElementById('port-val').style.color = totalVal >= portfolioData.starting_balance ? '#10b981' : '#ef4444';
    
    document.getElementById('port-cash').textContent = '₹' + portfolioData.cash.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    
    let pnlPct = (portfolioData.realized_pnl / portfolioData.starting_balance) * 100;
    let pnlSign = pnlPct >= 0 ? '+' : '';
    document.getElementById('port-pnl').textContent = `₹${portfolioData.realized_pnl.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})} (${pnlSign}${pnlPct.toFixed(2)}%)`;
    document.getElementById('port-pnl').style.color = pnlPct >= 0 ? '#10b981' : '#ef4444';
    
    let totalTrades = portfolioData.trades_won + portfolioData.trades_lost;
    let winRate = totalTrades > 0 ? (portfolioData.trades_won / totalTrades) * 100 : 0;
    document.getElementById('port-win').textContent = `${winRate.toFixed(1)}% (${totalTrades} Trades)`;

    // Closed Trades
    const closedTbody = document.getElementById('closed-trades-tbody');
    closedTbody.innerHTML = '';
    
    if (!portfolioData.closed_trades || portfolioData.closed_trades.length === 0) {
        closedTbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:20px;color:#94a3b8;">No closed trades yet.</td></tr>';
    } else {
        const reversed = [...portfolioData.closed_trades].reverse();
        reversed.forEach(t => {
            let color = t.pnl >= 0 ? '#10b981' : '#ef4444';
            let sign = t.pnl >= 0 ? '+' : '';
            let tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${t.entry_date}</td>
                <td>${t.exit_date}</td>
                <td><strong>${t.comp}</strong></td>
                <td>${t.shares_sold || '-'}</td>
                <td>₹${t.entry_price.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td>₹${t.exit_price.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td style="color:${color}; font-weight:bold;">${sign}₹${t.pnl.toLocaleString('en-IN', {minimumFractionDigits:0})}</td>
                <td>${t.reason}</td>
            `;
            closedTbody.appendChild(tr);
        });
    }
}

// ---------------------------------------------------------
// EXISTING COMPANY VIEW LOGIC
// ---------------------------------------------------------

function initSidebar() {
    const data = getCurrentData();
    const list = document.getElementById('company-list');
    list.innerHTML = '';

    const getPriority = (s) => {
        if (!s || s.includes('NO DATA')) return 7;
        if (s.includes('BUY') || s.includes('BREAKOUT') || s.includes('BULLISH')) return 1;
        if (s.includes('APPROACHING') && !s.includes('SELL')) return 2;
        if (s.includes('NEAR') || s.includes('BUILDING')) return 3;
        if (s.includes('SELL') || s.includes('BEARISH') || s.includes('EXIT') || s.includes('EXHAUSTION')) return 6;
        if (s.includes('APPROACHING SELL')) return 5;
        return 4; // NEUTRAL
    };
    const sorted = Object.entries(data).sort((a, b) => getPriority(a[1].buy_zone_status) - getPriority(b[1].buy_zone_status));

    // Aggregate
    let tRet = 0, tBH = 0, prof = 0, n = 0;
    sorted.forEach(([_, d]) => { tRet += d.backtest.total_return_pct; tBH += d.buy_hold_return_pct; if (d.backtest.total_return_pct > 0) prof++; n++; });
    const alpha = tRet - tBH;
    document.getElementById('tab-aggregate').innerHTML = n > 0 ? `
        <div class="agg-row"><span>Strategy Total</span><strong class="${tRet > 0 ? 'positive' : 'negative'}">${tRet > 0 ? '+' : ''}${tRet.toFixed(1)}%</strong></div>
        <div class="agg-row"><span>Buy & Hold Total</span><strong>${tBH > 0 ? '+' : ''}${tBH.toFixed(1)}%</strong></div>
        <div class="agg-row"><span>Total Alpha</span><strong class="${alpha > 0 ? 'positive' : 'negative'}">${alpha > 0 ? '+' : ''}${alpha.toFixed(1)}%</strong></div>
        <div class="agg-row"><span>Profitable</span><strong>${prof}/${n}</strong></div>` : '<div class="agg-row"><span>No data for this timeframe</span></div>';

    sorted.forEach(([company, cdata]) => {
        const div = document.createElement('div');
        div.className = 'company-item';
        const s = cdata.buy_zone_status;
        const ret = cdata.backtest.total_return_pct;
        let dc = 'dot-neutral';
        if (s.includes('BUY') || s.includes('BULLISH') || s.includes('BREAKOUT')) dc = 'dot-buy';
        else if (s.includes('APPROACHING') && !s.includes('SELL')) dc = 'dot-approach';
        else if (s.includes('NEAR') || s.includes('BUILDING')) dc = 'dot-near';
        else if (s.includes('SELL') || s.includes('BEARISH') || s.includes('EXIT')) dc = 'dot-sell';
        const rc = ret > 0 ? '#10b981' : ret < 0 ? '#ef4444' : '#94a3b8';
        div.innerHTML = `<span class="dot ${dc}"></span><span style="flex:1">${company}</span><span style="color:${rc};font-size:0.78rem;font-weight:600">${ret > 0 ? '+' : ''}${ret}%</span>`;
        div.style.cssText = 'display:flex;align-items:center';
        div.onclick = () => { document.querySelectorAll('.company-item').forEach(e => e.classList.remove('active')); div.classList.add('active'); loadCompany(company); };
        list.appendChild(div);
    });

    if (sorted.length > 0) {
        if (activeCompany && data[activeCompany]) {
            loadCompany(activeCompany);
            const items = list.querySelectorAll('.company-item');
            items.forEach(i => { if (i.textContent.includes(activeCompany)) i.classList.add('active'); });
        } else {
            list.firstChild.classList.add('active');
            loadCompany(sorted[0][0]);
        }
    }
}

function loadCompany(company) {
    const data = getCurrentData()[company];
    if (!data) return;
    activeCompany = company;

    document.getElementById('header-title').textContent = company + ' (' + activeTimeframe.toUpperCase() + ')';
    document.getElementById('stat-price').textContent = '\u20b9' + data.current_price.toLocaleString('en-IN');

    const rsiEl = document.getElementById('stat-rsi');
    rsiEl.textContent = data.current_rsi;
    rsiEl.style.color = data.current_rsi < 30 ? '#10b981' : data.current_rsi > 70 ? '#ef4444' : data.current_rsi < 40 ? '#34d399' : '#f8fafc';

    const badgeEl = document.getElementById('stat-zone');
    badgeEl.textContent = data.buy_zone_status;
    badgeEl.className = 'zone-badge';
    const s = data.buy_zone_status;
    if (s.includes('BUY') || s.includes('BULLISH') || s.includes('BREAKOUT')) badgeEl.classList.add('zone-buy');
    else if (s.includes('APPROACHING') && s.includes('BUY')) badgeEl.classList.add('zone-approach');
    else if (s.includes('NEAR') || s.includes('BUILDING')) badgeEl.classList.add('zone-near');
    else if (s.includes('SELL') || s.includes('BEARISH') || s.includes('EXIT')) badgeEl.classList.add('zone-sell');
    else badgeEl.classList.add('zone-neutral');

    const bhEl = document.getElementById('stat-bh');
    bhEl.textContent = (data.buy_hold_return_pct > 0 ? '+' : '') + data.buy_hold_return_pct + '%';
    bhEl.style.color = data.buy_hold_return_pct > 0 ? '#10b981' : '#ef4444';

    renderCharts(data.chart_data, data.backtest);
    renderBacktest(data.backtest, data.buy_hold_return_pct);
}

function renderCharts(cd, bt) {
    const labels = cd.map(d => d.time);
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.font.family = "'Inter', sans-serif";
    if (priceChart) priceChart.destroy();
    if (indChart) indChart.destroy();

    const bp = [], sp = [];
    if (bt) { bt.buy_signals.forEach(s => bp.push({ x: s.date, y: s.price })); bt.sell_signals.forEach(s => sp.push({ x: s.date, y: s.price })); }

    priceChart = new Chart(document.getElementById('priceChart').getContext('2d'), {
        type: 'line',
        data: { labels, datasets: [
            { label: 'Close', data: cd.map(d => d.close), borderColor: '#f8fafc', borderWidth: 2, pointRadius: 0, tension: 0.1, fill: false },
            { label: '50 DMA', data: cd.map(d => d.sma_50), borderColor: '#3b82f6', borderWidth: 1.5, borderDash: [5,5], pointRadius: 0, tension: 0.1, fill: false },
            { label: '200 DMA', data: cd.map(d => d.sma_200), borderColor: '#a855f7', borderWidth: 1.5, pointRadius: 0, tension: 0.1, fill: false },
            { label: 'BUY', data: bp, type: 'scatter', pointBackgroundColor: '#10b981', pointBorderColor: '#10b981', pointRadius: 8, pointStyle: 'triangle', showLine: false },
            { label: 'SELL', data: sp, type: 'scatter', pointBackgroundColor: '#ef4444', pointBorderColor: '#ef4444', pointRadius: 8, pointStyle: 'rectRot', showLine: false }
        ]},
        options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
            plugins: { legend: { position: 'top', labels: { usePointStyle: true, padding: 14 } } },
            scales: { x: { type: 'time', time: { unit: 'month', displayFormats: { month: 'MMM yy' } }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { callback: v => '\u20b9' + v.toLocaleString('en-IN') } } } }
    });

    indChart = new Chart(document.getElementById('indicatorChart').getContext('2d'), {
        type: 'line',
        data: { labels, datasets: [
            { label: 'RSI', data: cd.map(d => d.rsi), borderColor: '#10b981', borderWidth: 2, pointRadius: 0, tension: 0.1, fill: false, yAxisID: 'y' },
            { label: '30', data: labels.map(() => 30), borderColor: 'rgba(16,185,129,0.4)', borderWidth: 1, borderDash: [6,4], pointRadius: 0, fill: false, yAxisID: 'y' },
            { label: '40', data: labels.map(() => 40), borderColor: 'rgba(245,158,11,0.3)', borderWidth: 1, borderDash: [4,4], pointRadius: 0, fill: false, yAxisID: 'y' },
            { label: '70', data: labels.map(() => 70), borderColor: 'rgba(239,68,68,0.4)', borderWidth: 1, borderDash: [6,4], pointRadius: 0, fill: false, yAxisID: 'y' },
            { label: 'MACD', data: cd.map(d => d.macd), borderColor: '#3b82f6', borderWidth: 1.5, pointRadius: 0, fill: false, yAxisID: 'y1' },
            { label: 'Signal', data: cd.map(d => d.macd_signal), borderColor: '#f59e0b', borderWidth: 1, borderDash: [3,3], pointRadius: 0, fill: false, yAxisID: 'y1' }
        ]},
        options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
            plugins: { legend: { position: 'top', labels: { usePointStyle: true, padding: 14 } } },
            scales: { x: { type: 'time', time: { unit: 'month', displayFormats: { month: 'MMM yy' } }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { position: 'left', min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.05)' }, title: { display: true, text: 'RSI', color: '#10b981' } },
                y1: { position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'MACD', color: '#3b82f6' } } } }
    });
}

function renderBacktest(bt, bh) {
    const re = document.getElementById('bt-return'); re.textContent = (bt.total_return_pct > 0 ? '+' : '') + bt.total_return_pct + '%'; re.className = bt.total_return_pct > 0 ? 'positive' : 'negative';
    const we = document.getElementById('bt-winrate'); we.textContent = bt.win_rate_pct + '%'; we.className = bt.win_rate_pct >= 50 ? 'positive' : 'negative';
    document.getElementById('bt-trades').textContent = bt.total_trades;
    const a = bt.total_return_pct - bh; const ae = document.getElementById('bt-alpha'); ae.textContent = (a > 0 ? '+' : '') + a.toFixed(2) + '%'; ae.className = a > 0 ? 'positive' : 'negative';

    const tbody = document.getElementById('trade-tbody'); tbody.innerHTML = '';
    let all = [];
    bt.buy_signals.forEach(b => all.push({ t: 'BUY', d: b.date, p: b.price, n: b.note || '' }));
    bt.sell_signals.forEach(s => all.push({ t: 'SELL', d: s.date, p: s.price, n: s.note || '' }));
    all.sort((a, b) => new Date(a.d) - new Date(b.d));

    if (!all.length) { tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:24px;">No trades triggered.</td></tr>'; return; }

    let idx = 0;
    all.forEach(t => {
        const tr = document.createElement('tr');
        let pnl = '';
        if (t.t === 'SELL' && bt.individual_trades_pct && idx < bt.individual_trades_pct.length) {
            const p = bt.individual_trades_pct[idx]; pnl = `<span class="${p > 0 ? 'positive' : 'negative'}">${p > 0 ? '+' : ''}${p.toFixed(2)}%</span>`; idx++;
        }
        tr.innerHTML = `<td class="${t.t === 'BUY' ? 'trade-buy' : 'trade-sell'}">${t.t}${t.n ? ' <small style="color:#64748b">(' + t.n + ')</small>' : ''}</td><td>${t.d}</td><td>\u20b9${t.p.toLocaleString('en-IN')}</td><td>${pnl}</td>`;
        tbody.appendChild(tr);
    });
}
