'use strict';

const TIER = {
  0: { name: 'Safe',      color: '#059669', badge: 'badge-safe'  },
  1: { name: 'Watch',     color: '#d97706', badge: 'badge-watch' },
  2: { name: 'High Risk', color: '#ea580c', badge: 'badge-high'  },
  3: { name: 'Critical',  color: '#dc2626', badge: 'badge-crit'  },
};

const PLY_BASE = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor:  'rgba(0,0,0,0)',
  font: { family: "'Plus Jakarta Sans', system-ui, sans-serif", size: 11.5, color: '#4e5f73' },
};

const PLY_CFG = { displayModeBar: false, responsive: true, scrollZoom: true };

const Dashboard = (() => {

  let _drawn = { donut: false, scatter: false };
  let _cache = null;

  /* ── helpers ─────────────────────────────────────────────────────────── */

  function _set(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = typeof val === 'number' ? val.toLocaleString() : val;
  }

  /* ── donut ───────────────────────────────────────────────────────────── */

  function _donut(s) {
    const data = [{
      type: 'pie',
      hole: 0.58,
      values: [s.safe, s.watch, s.high_risk, s.critical],
      labels: ['Safe', 'Watch', 'High Risk', 'Critical'],
      marker: { colors: Object.values(TIER).map(t => t.color) },
      textinfo: 'percent',
      textfont: { family: "'Space Mono', monospace", size: 10.5 },
      hovertemplate: '<b>%{label}</b><br>%{value:,} students (%{percent})<extra></extra>',
      sort: false,
      direction: 'clockwise',
    }];

    const layout = {
      ...PLY_BASE,
      margin: { t: 0, r: 0, b: 0, l: 0 },
      showlegend: true,
      legend: {
        orientation: 'h',
        x: 0.5,
        xanchor: 'center',
        y: -0.08,
        font: { size: 11 },
        itemgap: 12,
      },
    };

    const fn = _drawn.donut ? Plotly.react : Plotly.newPlot;
    fn('chart-donut', data, layout, PLY_CFG);
    _drawn.donut = true;
  }

  /* ── scatter (WebGL) ─────────────────────────────────────────────────── */

  function _scatter(rows) {
    const groups = { 0: [], 1: [], 2: [], 3: [] };
    rows.forEach(d => { const t = d.risk ?? 0; if (groups[t]) groups[t].push(d); });

    const traces = [0, 1, 2, 3].map(tier => {
      const pts = groups[tier];
      return {
        type: 'scattergl',
        mode: 'markers',
        name: TIER[tier].name,
        x: pts.map(d => d.score),
        y: pts.map(d => d.clicks),
        text: pts.map(d => d.id),
        hovertemplate: [
          '<b>%{text}</b>',
          'Score: %{x:.1f}',
          'Clicks: %{y:,}',
          '<extra>' + TIER[tier].name + '</extra>',
        ].join('<br>'),
        marker: { color: TIER[tier].color, size: 4.5, opacity: 0.6 },
      };
    });

    const layout = {
      ...PLY_BASE,
      margin: { t: 8, r: 16, b: 52, l: 60 },
      xaxis: {
        title: { text: 'Average score', standoff: 10 },
        range: [-2, 102],
        gridcolor: '#edf2f7',
        zeroline: false,
        tickfont: { family: "'Space Mono', monospace", size: 10 },
      },
      yaxis: {
        title: { text: 'Total clicks', standoff: 10 },
        gridcolor: '#edf2f7',
        zeroline: false,
        tickfont: { family: "'Space Mono', monospace", size: 10 },
      },
      legend: { orientation: 'h', y: -0.16, font: { size: 11 }, itemgap: 16 },
      hovermode: 'closest',
    };

    const fn = _drawn.scatter ? Plotly.react : Plotly.newPlot;
    fn('chart-scatter', traces, layout, PLY_CFG);
    _drawn.scatter = true;

    _set('scatter-count', rows.length.toLocaleString());
  }

  /* ── attention list ──────────────────────────────────────────────────── */

  function _attentionList(rows) {
    const urgent = rows
      .filter(d => d.risk >= 2)
      .sort((a, b) => a.score - b.score)
      .slice(0, 8);

    const el = document.getElementById('attention-list');
    if (!el) return;

    if (!urgent.length) {
      el.innerHTML = '<div class="attention-empty text-3 text-sm">No critical or high-risk students found.</div>';
      return;
    }

    el.innerHTML = urgent.map(d => {
      const t    = TIER[d.risk];
      const pct  = Math.max(0, Math.min(100, d.score));
      const bar  = d.risk === 3 ? '#dc2626' : '#ea580c';
      return `
        <a class="attention-row" href="/students?search=${encodeURIComponent(d.id)}">
          <span class="attention-id">${d.id}</span>
          <span class="attention-score">
            <div class="flex jc-between items-c">
              <span class="attention-score-label">${d.score.toFixed(1)}</span>
              <span class="badge ${t.badge}" style="font-size:.6rem;">
                <i class="fas ${d.risk === 3 ? 'fa-user-slash' : 'fa-triangle-exclamation'}"></i>
                ${t.name}
              </span>
            </div>
            <div class="attention-score-bar-wrap">
              <div class="attention-score-bar" style="width:${pct}%;background:${bar};"></div>
            </div>
          </span>
        </a>`;
    }).join('');
  }

  /* ── fetch ───────────────────────────────────────────────────────────── */

  async function _fetch() {
    try {
      const res = await fetch('/api/realtime-data');
      if (!res.ok) throw new Error('API ' + res.status);
      const data = await res.json();
      _cache = data;

      const s = data.summary;
      _set('stat-total', s.total);
      _set('stat-safe',  s.safe);
      _set('stat-watch', s.watch);
      _set('stat-high',  s.high_risk);
      _set('stat-crit',  s.critical);

      if (s.last_updated) {
        _set('last-updated', 'Updated ' + s.last_updated);
      }

      _donut(s);
      _scatter(data.raw_data);
      _attentionList(data.raw_data);

    } catch (err) {
      console.error('[Dashboard]', err);
    }
  }

  /* ── public ──────────────────────────────────────────────────────────── */

  async function refresh() {
    const btn = document.getElementById('refresh-btn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-rotate-right fa-spin"></i>'; }
    try {
      await fetch('/api/refresh-cache', { method: 'POST' });
      await _fetch();
    } finally {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-rotate-right"></i> Refresh'; }
    }
  }

  function init() {
    _fetch();
    setInterval(_fetch, 15_000);
  }

  return { init, refresh };
})();

document.addEventListener('DOMContentLoaded', Dashboard.init);