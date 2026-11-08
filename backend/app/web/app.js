/* Platen Superheater Digital Twin — web HMI.
 *
 * Vanilla ES2020, no build step. Talks to the same REST + WSS endpoints the
 * Android client uses; every displayed number is t/h, °C, bar, MW or W/m²K.
 */
'use strict';

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const COLORS = ['#22d3ee', '#f59e0b', '#a78bfa', '#34d399', '#f472b6', '#60a5fa'];

const state = {
  op: {
    m_main_tph: 1000,
    T_main_C: 540,
    P_main_bar: 167,
    m_spray_tph: 30,
    T_LT_out_C: 490,
    Q_platen_MW: 60,
    htc_method: 'gnielinski',
  },
  transient: null,
  charts: {},
  ws: null,
  live: {
    running: false,
    burners: new Map(),
    t: [], tout: [], tmetal: [], qb: [], qg: [], h: [],
    maxPoints: 900,
    lastPaint: 0,
    pending: false,
  },
};

/* ------------------------------------------------------------------ utils */
const fmt = (value, decimals = 1) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  if (!Number.isFinite(Number(value))) return '—';
  return Number(value).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};

const int = (value) => fmt(value, 0);

function setStatus(el, text, kind = '') {
  el.textContent = text;
  el.className = 'status' + (kind ? ' ' + kind : '');
}

function describeError(payload, fallback) {
  const detail = payload && payload.detail;
  if (!detail) return fallback;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join('; ');
  }
  return detail.message_en || detail.message_fa || fallback;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(describeError(data, `HTTP ${response.status}`));
  }
  return data;
}

/* ----------------------------------------------------------------- charts */
function baseOption({ title, xName, series, yLeft, yRight }) {
  const prepared = series.map((item, index) => ({
    name: item.name,
    type: 'line',
    showSymbol: false,
    smooth: false,
    sampling: 'lttb',
    yAxisIndex: item.axisIndex || 0,
    lineStyle: { width: item.width || 2, color: item.color || COLORS[index % COLORS.length] },
    itemStyle: { color: item.color || COLORS[index % COLORS.length] },
    emphasis: { focus: 'series' },
    areaStyle: item.area ? { opacity: 0.08 } : undefined,
    data: item.data,
    unit: item.unit,
    markLine: item.markLine,
  }));
  return {
    backgroundColor: 'transparent',
    animation: false,
    color: COLORS,
    textStyle: { color: '#8aa0b6', fontSize: 11 },
    title: {
      text: title,
      left: 6,
      top: 0,
      textStyle: { color: '#c3d3e3', fontSize: 12, fontWeight: 'normal' },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(10,17,25,.94)',
      borderColor: '#1e2d3f',
      textStyle: { color: '#e2e8f0', fontSize: 11 },
      axisPointer: { type: 'cross', label: { backgroundColor: '#12202f' } },
      formatter: (params) => {
        if (!params.length) return '';
        const head = `t = ${fmt(params[0].value[0], 1)} s`;
        const rows = params.map((p) => {
          const unit = p.seriesName.includes('(') ? '' : ` ${p.series.unit || ''}`;
          const color = p.color;
          return `<div style="display:flex;gap:10px;justify-content:space-between">
            <span><i style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${color};margin-right:6px"></i>${p.seriesName}</span>
            <b>${fmt(p.value[1], 1)}${unit}</b></div>`;
        });
        return `<div style="font-size:11px">${head}${rows.join('')}</div>`;
      },
    },
    legend: {
      top: 2,
      right: 8,
      type: 'scroll',
      itemWidth: 12,
      itemHeight: 8,
      textStyle: { color: '#8aa0b6', fontSize: 10.5 },
      inactiveColor: '#3d4f63',
    },
    grid: { left: 64, right: yRight ? 68 : 20, top: 56, bottom: 62, containLabel: false },
    dataZoom: [
      { type: 'inside', filterMode: 'none' },
      { type: 'slider', height: 18, bottom: 8, borderColor: '#1e2d3f',
        fillerColor: 'rgba(34,211,238,.14)', handleStyle: { color: '#22d3ee' },
        textStyle: { color: '#6c8299', fontSize: 10 } },
    ],
    toolbox: {
      right: 8, top: 24, itemSize: 12, iconStyle: { borderColor: '#6c8299' },
      feature: {
        saveAsImage: { title: 'PNG', backgroundColor: '#070b12', name: 'platen-chart' },
        dataZoom: { title: { zoom: 'Zoom', back: 'Undo zoom' } },
        restore: { title: 'Reset' },
      },
    },
    xAxis: {
      type: 'value',
      name: xName,
      nameLocation: 'middle',
      nameGap: 26,
      min: 0,
      axisLine: { lineStyle: { color: '#22334a' } },
      axisLabel: { color: '#6c8299', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,.05)' } },
      axisPointer: { label: { show: false } },
    },
    yAxis: [
      {
        type: 'value',
        name: yLeft,
        nameTextStyle: { color: '#6c8299', fontSize: 10 },
        axisLabel: { color: '#6c8299', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,.06)' } },
        scale: true,
      },
      yRight ? {
        type: 'value',
        name: yRight,
        nameTextStyle: { color: '#6c8299', fontSize: 10 },
        axisLabel: { color: '#6c8299', fontSize: 10 },
        splitLine: { show: false },
        scale: true,
      } : undefined,
    ].filter(Boolean),
    series: prepared,
  };
}

function chartOf(id) {
  if (!state.charts[id]) {
    const node = document.getElementById(id);
    if (!node || !window.echarts) return null;
    state.charts[id] = window.echarts.init(node, null, { renderer: 'canvas' });
    window.addEventListener('resize', () => state.charts[id] && state.charts[id].resize());
  }
  return state.charts[id];
}

/* ------------------------------------------------------------- op form UI */
const OP_FIELDS = [
  { key: 'm_main_tph', label: 'Main steam flow', unit: 't/h', step: 10, min: 1, max: 2000 },
  { key: 'T_main_C', label: 'Main steam temperature', unit: '°C', step: 1, min: -20, max: 700 },
  { key: 'P_main_bar', label: 'Main steam pressure', unit: 'bar', step: 1, min: 1, max: 300 },
  { key: 'm_spray_tph', label: 'Spray flow (1st stage)', unit: 't/h', step: 1, min: 0, max: 300 },
  { key: 'T_LT_out_C', label: 'LT superheater outlet', unit: '°C', step: 1, min: -20, max: 700 },
  { key: 'Q_platen_MW', label: 'Platen heat absorption', unit: 'MW', step: 1, min: 0, max: 600 },
  { key: 'htc_method', label: 'Turbulent correlation', wide: true,
    options: [['gnielinski', 'Gnielinski'], ['dittus_boelter', 'Dittus–Boelter']] },
];

function renderOpForm(container) {
  container.innerHTML = '';
  OP_FIELDS.forEach((field) => {
    const label = document.createElement('label');
    if (field.wide) label.classList.add('wide');
    label.textContent = field.label;
    if (field.unit) {
      const unit = document.createElement('span');
      unit.className = 'unit';
      unit.textContent = ' ' + field.unit;
      label.appendChild(unit);
    }
    let input;
    if (field.options) {
      input = document.createElement('select');
      field.options.forEach(([value, text]) => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = text;
        input.appendChild(option);
      });
      input.value = state.op[field.key];
      input.addEventListener('change', () => {
        state.op[field.key] = input.value;
        syncOpForms();
      });
    } else {
      input = document.createElement('input');
      input.type = 'number';
      input.step = field.step;
      input.min = field.min;
      input.max = field.max;
      input.value = state.op[field.key];
      input.addEventListener('input', () => {
        const value = Number(input.value);
        input.classList.toggle('invalid', !Number.isFinite(value) || value < field.min || value > field.max);
        if (Number.isFinite(value)) {
          state.op[field.key] = value;
          syncOpForms();
        }
      });
    }
    input.dataset.key = field.key;
    label.appendChild(input);
    container.appendChild(label);
  });
}

function syncOpForms() {
  $$('[data-key]').forEach((input) => {
    const key = input.dataset.key;
    if (key in state.op && String(input.value) !== String(state.op[key])) {
      input.value = state.op[key];
    }
  });
}

function opPayload() {
  return { ...state.op };
}

/* ---------------------------------------------------------------- steady */
async function runSteady() {
  const status = $('#ss-status');
  setStatus(status, 'Solving IF97 state…');
  try {
    const result = await api('/api/steady', { method: 'POST', body: JSON.stringify(opPayload()) });
    $('#s-tin').textContent = fmt(result.T_platen_in_C, 2);
    $('#s-tout').textContent = fmt(result.T_platen_out_C, 2);
    $('#s-drop').textContent = fmt(result.deltaT_spray_C, 2);
    $('#s-q').textContent = fmt(result.heat_absorbed_MW, 1);
    $('#s-re').textContent = int(result.Re);
    $('#s-h').textContent = int(result.h_W_m2K);

    const regime = $('#s-regime');
    regime.textContent = result.regime;
    regime.className = 'chip ' + (result.regime === 'turbulent' ? 'chip-ok'
      : result.regime === 'transition' ? 'chip-warn' : 'chip-bad');

    const chart = chartOf('steady-chart');
    if (chart) {
      chart.setOption({
        backgroundColor: 'transparent',
        animation: false,
        title: { text: 'Nusselt number by correlation', left: 6, top: 0,
          textStyle: { color: '#c3d3e3', fontSize: 12, fontWeight: 'normal' } },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' },
          backgroundColor: 'rgba(10,17,25,.94)', borderColor: '#1e2d3f',
          textStyle: { color: '#e2e8f0', fontSize: 11 } },
        grid: { left: 64, right: 24, top: 48, bottom: 40 },
        xAxis: {
          type: 'category',
          data: ['Selected', 'Dittus–Boelter', 'Gnielinski'],
          axisLine: { lineStyle: { color: '#22334a' } },
          axisLabel: { color: '#8aa0b6', fontSize: 11 },
        },
        yAxis: {
          type: 'value', name: 'Nu', scale: true,
          nameTextStyle: { color: '#6c8299', fontSize: 10 },
          axisLabel: { color: '#6c8299', fontSize: 10 },
          splitLine: { lineStyle: { color: 'rgba(255,255,255,.06)' } },
        },
        series: [{
          type: 'bar',
          barWidth: '46%',
          data: [
            { value: result.Nu, itemStyle: { color: COLORS[0] } },
            { value: result.Nu_DB, itemStyle: { color: COLORS[1] } },
            { value: result.Nu_Gnielinski, itemStyle: { color: COLORS[2] } },
          ],
          label: { show: true, position: 'top', color: '#c3d3e3', fontSize: 11,
            formatter: (p) => fmt(p.value, 1) },
        }],
      }, true);
    }

    const rows = [
      ['Reynolds number', int(result.Re)],
      ['Prandtl number', fmt(result.Pr, 2)],
      ['Nusselt (selected)', fmt(result.Nu, 1)],
      ['Nusselt Dittus–Boelter', fmt(result.Nu_DB, 1)],
      ['Nusselt Gnielinski', fmt(result.Nu_Gnielinski, 1)],
      ['Friction factor f', fmt(result.f, 4)],
      ['NTU', fmt(result.NTU, 3)],
      ['h', `${int(result.h_W_m2K)} W/m²K`],
      ['Total steam', `${fmt(result.m_total_tph, 1)} t/h`],
      ['Regime', result.regime],
      ['Correlation', result.htc_method],
      ['Pressure', `${fmt(result.P_bar, 1)} bar`],
    ];
    $('#ss-detail').innerHTML = rows
      .map(([k, v]) => `<div><span>${k}</span><span>${v}</span></div>`).join('');

    setStatus(status, `Solved: outlet ${fmt(result.T_platen_out_C, 2)} °C.`, 'ok');
  } catch (error) {
    setStatus(status, error.message, 'err');
  }
}

/* ------------------------------------------------------------- transient */
async function resolvePreviousRun() {
  const runs = await api('/api/runs?limit=1');
  if (!runs || !runs.length) throw new Error('No stored run yet — run a simulation first.');
  return runs[0].id;
}

async function runTransient() {
  const status = $('#tr-status');
  const button = $('#tr-run');
  button.disabled = true;
  setStatus(status, 'Integrating single-node model…');
  try {
    const mode = $('#tr-mode').value;
    const payload = {
      ...opPayload(),
      duration_s: Number($('#tr-duration').value),
      dt_s: Number($('#tr-dt').value),
      initial_mode: mode,
      htc_method: state.op.htc_method,
    };
    if (mode === 'temperature') payload.T_metal_init_C = Number($('#tr-tmetal').value);
    if (mode === 'heat_flux') payload.Q_platen_init_MW = Number($('#tr-q').value);
    if (mode === 'previous_run') payload.previous_run_id = await resolvePreviousRun();

    // A consistent initial state with constant boundaries integrates to a flat
    // line, so scenarios drive the burners and give the platen a real transient.
    const scenario = $('#tr-scenario').value;
    let result;
    if (scenario === 'none') {
      result = await api('/api/transient', { method: 'POST', body: JSON.stringify(payload) });
    } else {
      // 10 × 40 MW × 0.15 ≈ 60 MW, i.e. the platen heat the steady form assumes,
      // so the curve settles instead of drifting away from the starting point.
      const tags = ['FA1', 'FA2', 'FA3', 'FA4', 'FB1', 'FB2', 'FB3', 'FB4', 'FC1', 'FC2'];
      const schedule = tags.map((tag) => ({
        tag,
        time_s: 0,
        state: 'on',
        target_load_fraction: 1.0,
        ramp_time_s: 60,
      }));
      result = await api('/api/burner_startup', {
        method: 'POST',
        body: JSON.stringify({
          ...payload,
          preset: scenario === 'ten_burners' ? null : scenario,
          burner_schedule: scenario === 'ten_burners' ? schedule : [],
          q_platen_fraction: 0.15,
          gas_to_metal_lag_s: 5,
        }),
      });
    }
    state.transient = result;
    renderTransient(result);
    setStatus(status, `Done: ${result.n_steps} steps · dt ${fmt(result.dt_s, 2)} s.`, 'ok');
    $('#tr-csv').disabled = false;
  } catch (error) {
    setStatus(status, error.message, 'err');
  } finally {
    button.disabled = false;
  }
}

function renderTransient(result) {
  const time = result.time_s;
  $('#k-tout').textContent = fmt(result.T_out_C[result.T_out_C.length - 1], 1);
  $('#k-tmetal').textContent = fmt(result.T_metal_C[result.T_metal_C.length - 1], 1);
  $('#k-tau').textContent = fmt(result.tau_s, 0);
  $('#k-t63').textContent = result.t63_s === null ? '—' : fmt(result.t63_s, 0);
  $('#k-t95').textContent = result.t95_s === null ? '—' : fmt(result.t95_s, 0);
  $('#k-h').textContent = int(result.h_W_m2K[result.h_W_m2K.length - 1]);

  const regime = result.regime[result.regime.length - 1] || '—';
  const chip = $('#tr-regime');
  chip.textContent = regime;
  chip.className = 'chip ' + (regime === 'turbulent' ? 'chip-ok'
    : regime === 'transition' ? 'chip-warn' : 'chip-bad');

  const markLine = (items) => {
    const data = items
      .filter(([value]) => value !== null && value !== undefined)
      .map(([value, label, color]) => ({
        xAxis: value,
        lineStyle: { color, type: 'dashed', width: 1 },
        label: {
          formatter: `${label} ${fmt(value, 0)} s`,
          color,
          fontSize: 10,
          position: 'insideEndTop',
        },
      }));
    return data.length ? { symbol: 'none', silent: true, label: { show: true }, data } : undefined;
  };

  const tOutSeries = {
    name: 'Outlet T', unit: '°C', axisIndex: 0,
    data: time.map((t, i) => [t, result.T_out_C[i]]),
    color: COLORS[0],
    markLine: markLine([[result.t63_s, 't63', '#22d3ee'], [result.t95_s, 't95', '#a78bfa']]),
  };

  const series = [
    tOutSeries,
    { name: 'Metal T', unit: '°C', axisIndex: 0, color: COLORS[1],
      data: time.map((t, i) => [t, result.T_metal_C[i]]) },
    { name: 'Inlet T', unit: '°C', axisIndex: 0, color: COLORS[4], width: 1.4,
      data: time.map((t, i) => [t, result.T_in_C[i]]) },
    { name: 'Q_gas', unit: 'MW', axisIndex: 1, color: COLORS[3], width: 1.5,
      data: time.map((t, i) => [t, result.Q_MW[i]]) },
    { name: 'h', unit: 'W/m²K', axisIndex: 1, color: COLORS[2], width: 1.3,
      data: time.map((t, i) => [t, result.h_W_m2K[i]]) },
  ];

  if (Array.isArray(result.Q_burners_MW)) {
    series.push({
      name: 'Q_burners', unit: 'MW', axisIndex: 1, color: COLORS[5], width: 1.2,
      data: time.map((t, i) => [t, result.Q_burners_MW[i]]),
    });
  }

  const chart = chartOf('transient-chart');
  if (!chart) return;
  chart.setOption(baseOption({
    title: `Transient response · ${fmt(result.duration_s, 0)} s · ${result.htc_method}`,
    xName: 'time (s)',
    yLeft: '°C',
    yRight: 'MW · W/m²K',
    series,
  }), true);

  const warnings = result.warnings || [];
  $('#tr-warnings').innerHTML = warnings.length
    ? warnings.map((w) => `<span class="warn">${w}</span>`).join('')
    : '<span class="chip chip-ok">No warnings</span>';
}


function downloadCsv() {
  const result = state.transient;
  if (!result) return;
  const header = ['time_s', 'T_in_C', 'T_out_C', 'T_metal_C', 'Q_MW', 'Re', 'Nu', 'h_W_m2K', 'regime'];
  const lines = [header.join(',')];
  result.time_s.forEach((t, i) => {
    lines.push([
      t, result.T_in_C[i], result.T_out_C[i], result.T_metal_C[i], result.Q_MW[i],
      result.Re[i], result.Nu[i], result.h_W_m2K[i], result.regime[i],
    ].join(','));
  });
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'platen-transient.csv';
  link.click();
  URL.revokeObjectURL(url);
}

/* --------------------------------------------------------------- burners */
async function loadBurners() {
  const specs = await api('/api/burners');
  const grid = $('#burner-grid');
  grid.innerHTML = '';
  const levels = ['C', 'B', 'A'];
  const rows = [['front', 'F'], ['rear', 'R']];
  levels.forEach((level) => {
    const spec0 = specs.find((b) => b.level === level);
    const levelBox = document.createElement('div');
    levelBox.className = 'level';
    levelBox.innerHTML = `<div class="level-head"><span>Level ${level}</span>
      <span>${spec0 ? fmt(spec0.elevation_m, 1) : '—'} m · 8 × 40 MW</span></div>`;
    rows.forEach(([rowName, prefix]) => {
      const row = document.createElement('div');
      row.className = 'row';
      row.innerHTML = `<span class="row-label">${rowName}</span>`;
      const cells = document.createElement('div');
      cells.className = 'row-cells';
      for (let index = 1; index <= 4; index += 1) {
        const tag = `${prefix}${level}${index}`;
        const button = document.createElement('button');
        button.className = 'burner';
        button.dataset.tag = tag;
        button.innerHTML = `<span class="flame">🔥</span><span class="tag">${tag}</span><span class="load">0 %</span>`;
        button.addEventListener('click', () => toggleBurner(tag));
        cells.appendChild(button);
        state.live.burners.set(tag, { on: false, load: 0 });
      }
      row.appendChild(cells);
      levelBox.appendChild(row);
    });
    grid.appendChild(levelBox);
  });
}

function setBurnerVisual(tag, on, load) {
  const node = document.querySelector(`.burner[data-tag="${tag}"]`);
  if (!node) return;
  node.classList.toggle('on', !!on);
  const loadNode = node.querySelector('.load');
  if (loadNode) loadNode.textContent = `${Math.round((load || 0) * 100)} %`;
  const entry = state.live.burners.get(tag);
  if (entry) {
    entry.on = !!on;
    entry.load = load || 0;
  }
}

function toggleBurner(tag) {
  if (!state.live.running || !state.ws || state.ws.readyState !== WebSocket.OPEN) {
    setStatus($('#bn-status'), 'Start the live session first.', 'err');
    return;
  }
  const entry = state.live.burners.get(tag) || { on: false };
  const nextOn = !entry.on;
  state.ws.send(JSON.stringify({
    action: 'set_burner',
    tag,
    state: nextOn ? 'on' : 'off',
    target_load_fraction: 1.0,
    ramp_time_s: 30,
  }));
  setBurnerVisual(tag, nextOn, nextOn ? entry.load || 0 : 0);
  logEvent(`${tag} ${nextOn ? 'ignited' : 'shut down'}`, 'command');
}

function logEvent(text, time) {
  const list = $('#bn-log');
  if (list.querySelector('.muted')) list.innerHTML = '';
  const item = document.createElement('li');
  item.innerHTML = `<span>${text}</span><span class="t">${time}</span>`;
  list.prepend(item);
  while (list.children.length > 40) list.lastChild.remove();
}

function updateBurnerCount() {
  let on = 0;
  state.live.burners.forEach((entry) => { if (entry.on) on += 1; });
  $('#bn-count').textContent = `${on} / ${state.live.burners.size || 24} firing`;
}

function liveRequest() {
  return {
    ...opPayload(),
    duration_s: 7200,
    dt_s: 2,
    initial_mode: 'temperature',
    T_metal_init_C: Number($('#bn-tmetal').value),
    q_platen_fraction: Number($('#bn-fraction').value),
    gas_to_metal_lag_s: Number($('#bn-lag').value),
    preset: 'all_off',
    burner_schedule: [],
  };
}

function startLive() {
  if (state.live.running) return;
  const status = $('#bn-status');
  setStatus(status, 'Connecting…');
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${protocol}://${location.host}/ws/burner_startup`);
  state.ws = ws;

  ws.addEventListener('open', () => {
    const speed = Number($('#bn-speed').value);
    ws.send(JSON.stringify({ type: 'start', speed, request: liveRequest() }));
    state.live.running = true;
    state.live.t = []; state.live.tout = []; state.live.tmetal = [];
    state.live.qb = []; state.live.qg = []; state.live.h = [];
    $('#bn-start').disabled = true;
    $('#bn-stop').disabled = false;
    $('#bn-log').innerHTML = '<li class="muted">Session started.</li>';
    setStatus(status, `Live at ${speed}× — tap burners to ignite.`, 'ok');
  });

  ws.addEventListener('message', (event) => {
    const frame = JSON.parse(event.data);
    if (frame.type === 'ready') {
      logEvent(`Session ready · dt ${fmt(frame.dt_s, 1)} s`, '0 s');
    } else if (frame.type === 'frame') {
      applyLiveFrame(frame);
    } else if (frame.type === 'event_ack') {
      const ev = frame.event;
      if (ev) setBurnerVisual(ev.tag, ev.state === 'on', ev.target_load_fraction);
    } else if (frame.type === 'error') {
      setStatus(status, frame.message || 'Stream error', 'err');
      logEvent(`Error: ${frame.code}`, '');
    } else if (frame.type === 'done') {
      setStatus(status, 'Session finished.', 'ok');
    }
  });

  ws.addEventListener('close', () => {
    state.live.running = false;
    $('#bn-start').disabled = false;
    $('#bn-stop').disabled = true;
    setStatus(status, 'Session closed.');
  });

  ws.addEventListener('error', () => {
    setStatus(status, 'WebSocket error — is the backend reachable?', 'err');
  });
}

function stopLive() {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify({ type: 'stop' }));
    state.ws.close();
  }
  state.live.running = false;
  $('#bn-start').disabled = false;
  $('#bn-stop').disabled = true;
}

function applyLiveFrame(frame) {
  const live = state.live;
  live.t.push(frame.time_s);
  live.tout.push(frame.T_out_C);
  live.tmetal.push(frame.T_metal_C);
  live.qb.push(frame.Q_burners_MW);
  live.qg.push(frame.Q_gas_MW);
  live.h.push(frame.h_W_m2K);

  if (live.t.length > live.maxPoints) {
    [live.t, live.tout, live.tmetal, live.qb, live.qg, live.h].forEach((arr) => {
      for (let i = arr.length - 2; i >= 0; i -= 2) arr.splice(i, 1);
    });
  }

  $('#b-tout').textContent = fmt(frame.T_out_C, 1);
  $('#b-tmetal').textContent = fmt(frame.T_metal_C, 1);
  $('#b-qburn').textContent = fmt(frame.Q_burners_MW, 0);
  $('#b-qgas').textContent = fmt(frame.Q_gas_MW, 1);
  $('#b-h').textContent = int(frame.h_W_m2K);
  $('#b-time').textContent = fmt(frame.time_s, 0);

  if (frame.burner_states) {
    Object.entries(frame.burner_states).forEach(([tag, load]) => {
      setBurnerVisual(tag, load > 0.001, load);
    });
    updateBurnerCount();
  }

  const warnings = frame.warnings || [];
  $('#bn-warnings').innerHTML = warnings.length
    ? warnings.map((w) => `<span class="warn">${w}</span>`).join('')
    : '';

  schedulePaint();
}

function schedulePaint() {
  const now = performance.now();
  if (state.live.pending) return;
  if (now - state.live.lastPaint < 220) {
    state.live.pending = true;
    setTimeout(() => {
      state.live.pending = false;
      state.live.lastPaint = performance.now();
      paintLive();
    }, 220 - (now - state.live.lastPaint));
    return;
  }
  state.live.lastPaint = now;
  paintLive();
}

function paintLive() {
  const live = state.live;
  const chart = chartOf('burner-chart');
  if (!chart) return;
  const data = (arr) => live.t.map((t, i) => [t, arr[i]]);
  chart.setOption({
    title: { text: `Live burner response · ${fmt(live.t[live.t.length - 1] || 0, 0)} s` },
    series: [
      { name: 'Outlet T', data: data(live.tout) },
      { name: 'Metal T', data: data(live.tmetal) },
      { name: 'Q_burners', data: data(live.qb) },
      { name: 'Q_gas', data: data(live.qg) },
    ],
  });
}

function initLiveChart() {
  const chart = chartOf('burner-chart');
  if (!chart) return;
  chart.setOption(baseOption({
    title: 'Live burner response',
    xName: 'time (s)',
    yLeft: '°C',
    yRight: 'MW',
    series: [
      { name: 'Outlet T', unit: '°C', axisIndex: 0, color: COLORS[0], data: [] },
      { name: 'Metal T', unit: '°C', axisIndex: 0, color: COLORS[1], data: [] },
      { name: 'Q_burners', unit: 'MW', axisIndex: 1, color: COLORS[3], data: [], width: 1.5 },
      { name: 'Q_gas', unit: 'MW', axisIndex: 1, color: COLORS[2], data: [], width: 1.5 },
    ],
  }), true);
}

/* ------------------------------------------------------------------ misc */
async function loadHealth() {
  const chip = $('#health');
  try {
    const health = await api('/api/health');
    chip.textContent = `backend ${health.version} · IF97`;
    chip.className = 'chip chip-ok';
  } catch (error) {
    chip.textContent = 'backend offline';
    chip.className = 'chip chip-bad';
  }
}

async function loadGeometry() {
  try {
    const geometry = await api('/api/geometry');
    const rows = [
      ['Tubes', `${geometry.n_tubes} (${geometry.n_panels} × ${geometry.tubes_per_panel})`],
      ['Developed length', `${fmt(geometry.developed_length_m, 1)} m`],
      ['Steam-side area', `${fmt(geometry.inner_area_m2, 1)} m²`],
      ['Internal volume', `${fmt(geometry.internal_volume_m3, 3)} m³`],
      ['Metal mass', `${fmt(geometry.metal_mass_kg / 1000, 1)} t`],
      ['Metal capacity', `${fmt(geometry.metal_capacity_MJ_K, 1)} MJ/K`],
      ['Total capacity', `${fmt(geometry.total_capacity_MJ_K, 1)} MJ/K`],
      ['Time constant', `${fmt(geometry.tau_s, 0)} s`],
    ];
    $('#about-geometry').innerHTML = rows
      .map(([k, v]) => `<div><span>${k}</span><span>${v}</span></div>`).join('');
  } catch (error) {
    /* the About screen still renders without it */
  }
}

function activateTab(name) {
  $$('.tab').forEach((tab) => tab.classList.toggle('active', tab.dataset.tab === name));
  $$('.view').forEach((view) => view.classList.toggle('active', view.id === `view-${name}`));
  if (name === 'transient') {
    setTimeout(() => {
      const chart = chartOf('transient-chart');
      if (chart) chart.resize();
      if (!state.transient) runTransient();
    }, 40);
  }
  if (name === 'steady') {
    setTimeout(() => { const chart = chartOf('steady-chart'); if (chart) chart.resize(); }, 40);
  }
  if (name === 'burners') {
    setTimeout(() => {
      const chart = chartOf('burner-chart');
      if (chart) chart.resize();
      else initLiveChart();
    }, 40);
  }
}

function presetSchedule(name) {
  if (name === 'all_on') {
    state.live.burners.forEach((_, tag) => { if (!state.live.burners.get(tag).on) toggleBurner(tag); });
  } else if (name === 'all_off') {
    state.live.burners.forEach((entry, tag) => { if (entry.on) toggleBurner(tag); });
  } else if (name === 'level_a') {
    state.live.burners.forEach((entry, tag) => {
      if (tag.includes('A') && !entry.on) toggleBurner(tag);
    });
  } else if (name === 'cold_start') {
    const levels = ['A', 'B', 'C'];
    levels.forEach((level, index) => {
      setTimeout(() => {
        state.live.burners.forEach((entry, tag) => {
          if (tag.includes(level) && !entry.on) toggleBurner(tag);
        });
      }, index * 4000);
    });
  }
}

/* ---------------------------------------------------------------- startup */
document.addEventListener('DOMContentLoaded', () => {
  renderOpForm($('#op-transient'));
  renderOpForm($('#op-steady'));

  $('#tabs').addEventListener('click', (event) => {
    const tab = event.target.closest('.tab');
    if (tab) activateTab(tab.dataset.tab);
  });

  $('#tr-run').addEventListener('click', runTransient);
  $('#tr-csv').addEventListener('click', downloadCsv);
  $('#ss-run').addEventListener('click', runSteady);

  $('#tr-mode').addEventListener('change', () => {
    const mode = $('#tr-mode').value;
    $('#tr-tmetal-wrap').classList.toggle('hidden', mode !== 'temperature');
    $('#tr-q-wrap').classList.toggle('hidden', mode !== 'heat_flux');
  });

  $('#bn-start').addEventListener('click', startLive);
  $('#bn-stop').addEventListener('click', stopLive);
  $$('[data-preset]').forEach((button) => {
    button.addEventListener('click', () => presetSchedule(button.dataset.preset));
  });

  loadHealth();
  loadGeometry();
  loadBurners().then(() => {
    initLiveChart();
    updateBurnerCount();
  }).catch((error) => setStatus($('#bn-status'), error.message, 'err'));

  activateTab('transient');
});
