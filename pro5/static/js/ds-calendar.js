// DeepSeek — 自定义日历

let dsViewMode = 'browse';
let dsCalYear = new Date().getFullYear();
let dsCalMonth = new Date().getMonth() + 1;  // 1-based
let dsCalDates = {};  // { "YYYY-MM-DD": count }
let dsSelectedDate = '';

const DS_DOWS = ['日', '一', '二', '三', '四', '五', '六'];

function dsSetView(mode) {
  dsViewMode = mode;
  document.querySelectorAll('.ds-view-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.view === mode)
  );

  const picker = document.getElementById('ds-date-picker');
  const yearNav = document.getElementById('ds-year-nav');
  const monthNav = document.getElementById('ds-month-nav');

  if (mode === 'date') {
    picker.style.display = 'block';
    yearNav.style.display = 'none';
    monthNav.style.display = 'none';
    document.getElementById('main-header').style.display = 'none';
    document.getElementById('copy-btn-wrap').style.display = 'none';
    document.getElementById('main-body').innerHTML =
      '<div class="empty-main">← 选择日期查看对话</div>';

    // 初始化日历为今天
    const now = new Date();
    dsCalYear = now.getFullYear();
    dsCalMonth = now.getMonth() + 1;
    const today = fmtDate(now);
    dsSelectedDate = today;
    dsRenderCal();
    dsLoadCalDate(today);
  } else {
    picker.style.display = 'none';
    yearNav.style.display = 'flex';
    monthNav.style.display = 'none';
    document.getElementById('ds-session-list').innerHTML =
      '<div style="padding:20px;color:var(--text-secondary);font-size:13px;text-align:center">← 选择年月查看对话</div>';
    document.getElementById('main-header').style.display = 'none';
    document.getElementById('copy-btn-wrap').style.display = 'none';
    document.getElementById('main-body').innerHTML =
      '<div class="empty-main">← 选择一条对话查看详情</div>';
    dsState.year = '';
    dsState.month = '';
    loadDsStructure();
  }
}

function fmtDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

// 日历网格 DOM 缓存（初始化时建好，切换月份只更新内容）
let dsCalGridCells = [];  // 存 grid 中所有日期 cell 的引用
let dsCalDots = [];       // 存每个 cell 的 dot 元素

function dsInitCalGrid() {
  const grid = document.getElementById('ds-cal-grid');
  // 只首次调用时构建 DOM
  if (grid.children.length > 0) return;

  const frag = document.createDocumentFragment();

  // 星期行
  DS_DOWS.forEach(d => {
    const el = document.createElement('div');
    el.className = 'ds-cal-dow';
    el.textContent = d;
    frag.appendChild(el);
  });

  // 6 行 × 7 列 = 42 个格子，一次性建好
  dsCalGridCells = [];
  dsCalDots = [];
  for (let i = 0; i < 42; i++) {
    const el = document.createElement('div');
    el.className = 'ds-cal-day other-month';
    el.dataset.idx = i;
    el.addEventListener('click', () => {
      const dateStr = el.dataset.date;
      if (dateStr) dsCalPickDay(dateStr);
    });
    frag.appendChild(el);

    // dot 元素也预先创建，按需显示
    const dot = document.createElement('span');
    dot.className = 'ds-cal-dot';
    dot.style.display = 'none';
    el.appendChild(dot);

    dsCalGridCells.push(el);
    dsCalDots.push(dot);
  }

  grid.appendChild(frag);
}

async function dsRenderCal() {
  // 确保网格 DOM 已初始化
  dsInitCalGrid();

  const title = document.getElementById('ds-cal-title');
  const monthStr = String(dsCalMonth).padStart(2, '0');
  title.textContent = `${dsCalYear}年${dsCalMonth}月`;

  // 获取该月有对话的日期（带缓存）
  const cacheKey = `${dsCalYear}-${monthStr}`;
  try {
    if (!dsDatesCache.has(cacheKey)) {
      dsDatesCache.set(cacheKey, deepseekGetDates(String(dsCalYear), monthStr));
    }
    const data = await dsDatesCache.get(cacheKey);
    dsCalDates = data.dates || {};
  } catch (e) {
    dsCalDates = {};
    dsDatesCache.delete(cacheKey);
  }

  // 计算网格数据
  const firstDay = new Date(dsCalYear, dsCalMonth - 1, 1);
  const lastDay = new Date(dsCalYear, dsCalMonth, 0);
  const startDow = firstDay.getDay();
  const daysInMonth = lastDay.getDate();
  const prevLastDay = new Date(dsCalYear, dsCalMonth - 1, 0).getDate();

  const now = new Date();
  const todayStr = fmtDate(now);
  const isCurrentMonth = now.getFullYear() === dsCalYear && now.getMonth() + 1 === dsCalMonth;

  // 局部更新每个格子：数字、样式、dot、data-date
  let day = 1;
  let nextMonthDay = 1;

  for (let i = 0; i < 42; i++) {
    const row = Math.floor(i / 7);
    const col = i % 7;
    const el = dsCalGridCells[i];
    const dot = dsCalDots[i];

    let dateStr = '';
    let text = '';
    let isOtherMonth = true;

    if ((row === 0 && col < startDow) || day > daysInMonth) {
      if (row === 0 && col < startDow) {
        text = String(prevLastDay - startDow + col + 1);
      } else {
        text = String(nextMonthDay);
        nextMonthDay++;
      }
      dateStr = '';
    } else {
      dateStr = `${dsCalYear}-${monthStr}-${String(day).padStart(2, '0')}`;
      text = String(day);
      isOtherMonth = false;
      day++;
    }

    // 只更新变化的属性，不动 DOM 结构
    el.dataset.date = dateStr;
    el.textContent = text;
    el.appendChild(dot);  // textContent 会清掉子元素，需要重新 append dot

    // 更新 class
    el.className = 'ds-cal-day';
    if (isOtherMonth) el.classList.add('other-month');
    if (isCurrentMonth && dateStr === todayStr) el.classList.add('today');
    if (dateStr && dateStr === dsSelectedDate) el.classList.add('selected');

    // 更新 dot
    const hasDot = !!dateStr && (dsCalDates[dateStr] > 0);
    dot.style.display = hasDot ? '' : 'none';
  }
}

function dsCalSwitchMonth(delta) {
  dsCalMonth += delta;
  if (dsCalMonth < 1) { dsCalMonth = 12; dsCalYear--; }
  if (dsCalMonth > 12) { dsCalMonth = 1; dsCalYear++; }
  dsSelectedDate = '';
  dsRenderCal();
}

function dsCalPickDay(dateStr) {
  dsSelectedDate = dateStr;
  // 局部更新高亮：只改 class，不查整个 DOM
  for (let i = 0; i < dsCalGridCells.length; i++) {
    const el = dsCalGridCells[i];
    el.classList.toggle('selected', el.dataset.date === dateStr);
  }
  dsLoadCalDate(dateStr);
}

// 创建单个会话条目 DOM 元素
function createSessionItem(s) {
  const el = document.createElement('div');
  el.className = 'ds-session-item';
  el.dataset.id = s.id;
  el.onclick = () => selectDsSession(s.id);

  const title = document.createElement('div');
  title.className = 'ds-session-title';
  const titleSpan = document.createElement('span');
  titleSpan.textContent = s.title;
  title.appendChild(titleSpan);
  if (s.message_count) {
    const countSpan = document.createElement('span');
    countSpan.className = 'ds-session-msg-count';
    countSpan.textContent = s.message_count + '条';
    title.appendChild(countSpan);
  }
  el.appendChild(title);

  const meta = document.createElement('div');
  meta.className = 'ds-session-meta';
  if (s.model) {
    const modelSpan = document.createElement('span');
    modelSpan.textContent = '🤖 ' + s.model;
    meta.appendChild(modelSpan);
  }
  el.appendChild(meta);

  return el;
}

// 用 DocumentFragment 批次插入会话列表
function renderDsSessionList(listEl, sessions, headerText) {
  if (!sessions || !Array.isArray(sessions)) return;

  const frag = document.createDocumentFragment();

  if (headerText) {
    const header = document.createElement('div');
    header.style.cssText = 'padding:8px 4px 6px;font-size:12px;color:var(--text-secondary)';
    header.textContent = headerText;
    frag.appendChild(header);
  }

  for (const s of sessions) {
    frag.appendChild(createSessionItem(s));
  }

  listEl.textContent = '';
  listEl.appendChild(frag);
}

async function dsLoadCalDate(dateStr) {
  const list = document.getElementById('ds-session-list');
  const loadingEl = document.createElement('div');
  loadingEl.className = 'loading';
  loadingEl.style.cssText = 'padding:20px';
  loadingEl.textContent = '加载中';
  list.textContent = '';
  list.appendChild(loadingEl);

  document.getElementById('main-header').style.display = 'none';
  document.getElementById('copy-btn-wrap').style.display = 'none';
  document.getElementById('main-body').textContent = '';
  const emptyMsg = document.createElement('div');
  emptyMsg.className = 'empty-main';
  emptyMsg.textContent = '← 选择一条对话查看详情';
  document.getElementById('main-body').appendChild(emptyMsg);

  try {
    const data = await deepseekGetSessionsByDate(dateStr);
    const sessions = data.sessions || [];

    if (sessions.length === 0) {
      list.textContent = '';
      const empty = document.createElement('div');
      empty.style.cssText = 'padding:16px;text-align:center';
      const msg = document.createElement('div');
      msg.style.cssText = 'font-size:13px;color:var(--text-secondary);margin-bottom:8px';
      msg.textContent = `📅 ${dateStr} 暂无对话`;
      empty.appendChild(msg);
      list.appendChild(empty);
      return;
    }

    renderDsSessionList(list, sessions, `📅 ${dateStr}  ·  ${sessions.length} 个对话`);
  } catch (e) {
    list.textContent = '';
    const err = document.createElement('div');
    err.style.cssText = 'padding:20px;color:#d93025;font-size:13px';
    err.textContent = '加载失败：' + e.message;
    list.appendChild(err);
  }
}


// ============================================================
// 统计大屏
// ============================================================

// 缓存统计原始数据，供 JSON 复制使用
let statsDataCache = null;

// 年热力图全局状态
let _heatmapDailyData = null;
let _heatmapCurrentYear = null;

const _GH_COLORS = ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39'];
const _MONTH_NAMES = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'];


function buildYearHeatmapGridHtml(dailyData, year) {
  const startDate = new Date(year, 0, 1);
  const endDate = new Date(year, 11, 31);
  const totalDays = Math.floor((endDate - startDate) / 86400000) + 1;
  const jan1Dow = startDate.getDay();
  const numCols = Math.ceil((jan1Dow + totalDays) / 7);
  const numGridCols = numCols + 1; // +1 for weekday labels

  const grid = Array.from({ length: 7 }, () => Array(numCols).fill(null));
  const maxCount = Math.max(...Object.values(dailyData), 1);

  function cellLevel(v) {
    if (v === 0) return 0;
    if (maxCount <= 4) {
      if (v === 1) return 1;
      if (v === 2) return 2;
      if (v === 3) return 3;
      return 4;
    }
    const r = v / maxCount;
    if (r > 0.75) return 4;
    if (r > 0.5) return 3;
    if (r > 0.25) return 2;
    return 1;
  }

  for (let d = 0; d < totalDays; d++) {
    const date = new Date(startDate);
    date.setDate(startDate.getDate() + d);
    const dow = date.getDay();
    const col = Math.floor((jan1Dow + d) / 7);
    const ymd = date.getFullYear() + '-' + String(date.getMonth() + 1).padStart(2, '0') + '-' + String(date.getDate()).padStart(2, '0');
    const count = dailyData[ymd] || 0;
    grid[dow][col] = { date: ymd, count };
  }

  // 月份列区间
  function getMonthCols() {
    const months = [];
    let curMonth = -1;
    let startCol = 0;
    for (let c = 0; c < numCols; c++) {
      let monthInCol = -1;
      for (let r = 0; r < 7; r++) {
        if (grid[r][c]) {
          monthInCol = new Date(grid[r][c].date).getMonth();
          break;
        }
      }
      if (monthInCol >= 0 && monthInCol !== curMonth) {
        if (curMonth >= 0) months.push({ m: curMonth, col: startCol, span: c - startCol });
        curMonth = monthInCol;
        startCol = c;
      }
    }
    if (curMonth >= 0) months.push({ m: curMonth, col: startCol, span: numCols - startCol });
    return months;
  }

  const monthCols = getMonthCols();
  const dows = ['', '一', '', '三', '', '五', ''];

  // 构建 CSS Grid
  let html = '<div class="gh-grid" style="grid-template-columns:18px repeat(' + numCols + ',11px);gap:2px">';

  // 月份标签行 (grid-row: 1)
  html += '<div class="gh-dow" style="grid-row:1;grid-column:1"></div>';
  for (const mc of monthCols) {
    const startCol = mc.col + 2; // +2 for 1-based + dow column
    html += '<div class="gh-month-label" style="grid-row:1;grid-column:' + startCol + '/span ' + mc.span + '">' + _MONTH_NAMES[mc.m] + '</div>';
  }

  // 数据行 (grid-row: 2..8)
  for (let r = 0; r < 7; r++) {
    const gridRow = r + 2;
    html += '<div class="gh-dow" style="grid-row:' + gridRow + ';grid-column:1">' + dows[r] + '</div>';
    for (let c = 0; c < numCols; c++) {
      const cell = grid[r][c];
      const gridCol = c + 2;
      if (cell) {
        const level = cellLevel(cell.count);
        html += '<div class="gh-cell" style="background:' + _GH_COLORS[level] + ';grid-row:' + gridRow + ';grid-column:' + gridCol + '" title="' + cell.date + ': ' + cell.count + ' 场对话"></div>';
      } else {
        html += '<div class="gh-cell gh-cell-empty" style="grid-row:' + gridRow + ';grid-column:' + gridCol + '"></div>';
      }
    }
  }

  html += '</div>';
  return html;
}

function switchHeatmapYear(year) {
  const container = document.getElementById('heatmap-year-grid');
  if (!container) return;
  _heatmapCurrentYear = parseInt(year);
  container.innerHTML = buildYearHeatmapGridHtml(_heatmapDailyData, parseInt(year));
}


function renderStatsDashboard(data) {
  statsDataCache = data;
  const mainBody = document.getElementById('main-body');

  const {
    total_conversations: totalConversations,
    total_messages: totalMessages,
    time_span_days: days,
    model_count: modelCount,
    min_date: minDate,
    max_date: maxDate,
    monthly_trend: monthlyTrend,
    model_distribution: modelData,
    length_distribution: lengthData,
  } = data;

  const maxCount = Math.max(...monthlyTrend.map(d => d.count), 1);
  const modelTotal = modelData.reduce((s, m) => s + m.count, 0);

  const html = `
    <div class="stats-dashboard">
      <div class="stats-title">📊 DeepSeek 对话统计</div>

      <!-- 顶栏卡片 -->
      <div class="stats-cards">
        <div class="stats-card">
          <div class="stats-card-value">${totalConversations.toLocaleString()}</div>
          <div class="stats-card-label">💬 对话总数</div>
        </div>
        <div class="stats-card">
          <div class="stats-card-value">${totalMessages.toLocaleString()}</div>
          <div class="stats-card-label">📝 消息总数</div>
        </div>
        <div class="stats-card">
          <div class="stats-card-value">${days} 天</div>
          <div class="stats-card-label">📅 ${minDate} → ${maxDate}</div>
        </div>
        <div class="stats-card">
          <div class="stats-card-value">${modelCount}</div>
          <div class="stats-card-label">🤖 使用模型</div>
        </div>
      </div>

      <!-- 月度趋势 -->
      <div class="stats-section">
        <div class="stats-section-title">📈 月度对话量趋势</div>
        <div class="stats-chart-bar-wrap">
          ${monthlyTrend.map(d => {
            const label = d.month.slice(2).replace('-', '/');
            return `
              <div class="stats-bar-col">
                <div class="stats-bar-inner">
                  <div class="stats-bar" style="height:${Math.round(d.count / maxCount * 100)}%" title="${d.month}: ${d.count}"></div>
                </div>
                <div class="stats-bar-label">${label}</div>
              </div>
            `;
          }).join('')}
        </div>
      </div>

      <!-- 模型分布 + 长度分布 -->
      <div class="stats-row">
        <div class="stats-section stats-half">
          <div class="stats-section-title">🤖 模型分布</div>
          ${modelData.map((m, i) => {
            const pct = Math.round(m.count / modelTotal * 100);
            const color = i === 0 ? '#4a90d9' : '#7b61ff';
            return `
              <div class="stats-legend-item">
                <div class="stats-legend-label">
                  <span class="stats-dot" style="background:${color}"></span>
                  ${m.name}
                </div>
                <div class="stats-legend-bar">
                  <div class="stats-legend-fill" style="width:${pct}%;background:${color}"></div>
                </div>
                <div class="stats-legend-pct">${pct}%</div>
              </div>
            `;
          }).join('')}
        </div>
        <div class="stats-section stats-half">
          <div class="stats-section-title">📏 对话长度分布</div>
          ${lengthData.map(d => {
            const totalB = lengthData.reduce((s, x) => s + x.count, 0);
            const pct = Math.round(d.count / totalB * 100);
            return `
              <div class="stats-legend-item">
                <div class="stats-legend-label">${d.label}</div>
                <div class="stats-legend-bar">
                  <div class="stats-legend-fill" style="width:${pct}%;background:${d.color}"></div>
                </div>
                <div class="stats-legend-pct">${pct}%</div>
              </div>
            `;
          }).join('')}
        </div>
      </div>

      <!-- 活跃度热力图（GitHub 风格） -->
      ${(() => {
        const dailyData = data.daily_conversations || {};
        const years = data.available_years || [];
        if (years.length === 0) return '';

        // 存全局供切换年份用
        _heatmapDailyData = dailyData;

        const selYear = _heatmapCurrentYear || years[years.length - 1];
        _heatmapCurrentYear = selYear;

        const yearOpts = years.map(y => `<option value="${y}"${y === selYear ? ' selected' : ''}>${y}</option>`).join('');

        const gridHtml = buildYearHeatmapGridHtml(dailyData, selYear);

        return `
        <div class="stats-section">
          <div class="stats-section-title" style="display:flex;align-items:center;gap:10px">
            🔥 活跃度日历
            <select class="stats-year-select" onchange="switchHeatmapYear(this.value)">${yearOpts}</select>
          </div>
          <div class="stats-heatmap-wrap">
            <div id="heatmap-year-grid">${gridHtml}</div>
            <div class="stats-heatmap-legend">
              <span>少</span>
              ${['#ebedf0','#9be9a8','#40c463','#30a14e','#216e39'].map(c => `<span class="gh-cell" style="background:${c}"></span>`).join('')}
              <span>多</span>
            </div>
          </div>
        </div>`;
      })()}

      <!-- 时段分布 -->
      <div class="stats-section">
        <div class="stats-section-title">🕐 时段分布（24h）</div>

        ${(() => {
          const dist = data.hourly_distribution;
          if (!dist || !dist.all) return '<div class="empty-main">暂无数据</div>';

          const all = dist.all;
          const wd = dist.weekday;
          const we = dist.weekend;
          const maxAll = Math.max(...all.map(h => h.count), 1);
          const maxWd = Math.max(...wd.map(h => h.count), 1);
          const maxWe = Math.max(...we.map(h => h.count), 1);

          // 判断用户类型
          const peakAll = all.reduce((a, b) => a.count > b.count ? a : b);
          const peakH = peakAll.hour;
          let userType, userTypeEmoji;
          if (peakH >= 5 && peakH < 12) { userType = '☀️ 早起型'; userTypeEmoji = '🌅'; }
          else if (peakH >= 12 && peakH < 18) { userType = '🌤️ 午后型'; userTypeEmoji = '☕'; }
          else if (peakH >= 18 && peakH < 23) { userType = '🌙 夜猫子型'; userTypeEmoji = '🦉'; }
          else { userType = '🌃 深夜型'; userTypeEmoji = '🌌'; }

          // 质量最高时段（按 avg_messages 取 top 3）
          const topQuality = [...all].filter(h => h.count > 0).sort((a, b) => b.avg_messages - a.avg_messages).slice(0, 3);

          // 生成柱状图
          function hourlyBars(dataArr, max) {
            return dataArr.map(h => {
              const pct = Math.round(h.count / max * 100);
              const label = String(h.hour).padStart(2, '0');
              const avgStr = h.avg_messages !== undefined ? `，均 ${h.avg_messages} 条` : '';
              return `
                <div class="stats-hbar-col">
                  <div class="stats-hbar-val">${h.count}</div>
                  <div class="stats-hbar-inner">
                    <div class="stats-hbar" style="height:${Math.max(pct, 1)}%" title="${label}:00 — ${h.count} 场对话${avgStr}"></div>
                  </div>
                  <div class="stats-hbar-tic">${label}</div>
                </div>
              `;
            }).join('');
          }

          // 质量 TOP3 标签
          const qualityStr = topQuality.map(h => `${String(h.hour).padStart(2, '0')}:00（均${h.avg_messages}条）`).join('、');

          return `
            <div class="stats-type-badge">
              ${userTypeEmoji} 你的活跃峰值在 <strong>${String(peakH).padStart(2, '0')}:00</strong>，你是 <strong>${userType}</strong>
              &nbsp;·&nbsp; 🧠 深度对话高峰：${qualityStr}
            </div>

            <div class="stats-hourly-chart">
              ${hourlyBars(all, maxAll)}
            </div>

            <div class="stats-hourly-dual-title">📅 工作日 vs 周末</div>
            <div class="stats-hourly-dual">
              <div class="stats-hourly-half">
                <div class="stats-hourly-half-label">工作日</div>
                <div class="stats-hourly-chart stats-hourly-chart-sm">${hourlyBars(wd, maxWd)}</div>
              </div>
              <div class="stats-hourly-half">
                <div class="stats-hourly-half-label">周末</div>
                <div class="stats-hourly-chart stats-hourly-chart-sm">${hourlyBars(we, maxWe)}</div>
              </div>
            </div>
          `;
        })()}
      </div>

      <!-- 对话时长 -->
      <div class="stats-section">
        <div class="stats-section-title">⏱️ 对话时长分布</div>

        ${(() => {
          const dur = data.duration_distribution;
          const scat = data.scatter_data || [];
          const modelDur = data.model_duration_avg || [];
          if (!dur) return '<div class="empty-main">暂无数据</div>';

          const totalDur = dur.reduce((s, d) => s + d.count, 0);

          // 时长分桶（复用 legend 样式）
          const durBars = dur.map(d => {
            const pct = totalDur > 0 ? Math.round(d.count / totalDur * 100) : 0;
            return `
              <div class="stats-legend-item">
                <div class="stats-legend-label">
                  <span class="stats-dot" style="background:${d.color}"></span>
                  ${d.label}
                </div>
                <div class="stats-legend-bar">
                  <div class="stats-legend-fill" style="width:${pct}%;background:${d.color}"></div>
                </div>
                <div class="stats-legend-pct">${pct}%</div>
              </div>
            `;
          }).join('');

          // 模型平均时长
          const maxModelDur = Math.max(...modelDur.map(m => m.avg_min), 1);
          const modelDurBars = modelDur.map((m, i) => {
            const pct = Math.round(m.avg_min / maxModelDur * 100);
            const color = i === 0 ? '#4a90d9' : '#7b61ff';
            return `
              <div class="stats-legend-item">
                <div class="stats-legend-label">
                  <span class="stats-dot" style="background:${color}"></span>
                  ${m.name}
                </div>
                <div class="stats-legend-bar">
                  <div class="stats-legend-fill" style="width:${pct}%;background:${color}"></div>
                </div>
                <div class="stats-legend-pct">${m.avg_min}min (${m.count})</div>
              </div>
            `;
          }).join('');

          return `
            <div class="stats-section-subtitle">📊 时长区间</div>
            <div style="margin-bottom:16px">${durBars}</div>

            <div class="stats-section-subtitle">📈 时长 vs 消息条数（散点图）</div>
            <div class="stats-scatter-wrap">
              <canvas id="stats-scatter-canvas" class="stats-scatter-canvas"></canvas>
            </div>

            <div class="stats-section-subtitle">🤖 各模型平均时长</div>
            <div>${modelDurBars}</div>
          `;
        })()}
      </div>

      <div class="stats-footer">📊 数据最后更新: ${maxDate || '-'}</div>

      <!-- 复制 JSON 按钮 -->
      <div class="stats-copy-row">
        <button class="stats-copy-btn stats-copy-summary" data-orig="📋 复制统计摘要" onclick="copyStatsAsJson()">📋 复制统计摘要</button>
        <button class="stats-copy-btn stats-copy-full" data-orig="📦 复制完整数据" onclick="copyStatsFullJson()">📦 复制完整数据</button>
      </div>
    </div>
  `;

  mainBody.innerHTML = html;

  // 绘制散点图
  setTimeout(() => drawScatterPlot(data.scatter_data || []), 50);
}


function drawScatterPlot(points) {
  const canvas = document.getElementById('stats-scatter-canvas');
  if (!canvas || points.length === 0) return;

  // 最多 500 个点
  const data = points.length > 500 ? points.filter(() => Math.random() > 0.5) : points;

  const wrap = canvas.parentElement;
  const rect = wrap.getBoundingClientRect();
  const w = Math.min(rect.width - 4, 900);
  const h = 280;
  canvas.width = w;
  canvas.height = h;

  const pad = { top: 24, right: 20, bottom: 44, left: 52 };
  const pw = w - pad.left - pad.right;
  const ph = h - pad.top - pad.bottom;

  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, w, h);

  // 找范围
  const maxX = Math.max(...data.map(p => p.duration_min), 1);
  const maxY = Math.max(...data.map(p => p.message_count), 1);

  const scaleX = (v) => pad.left + (v / maxX) * pw;
  const scaleY = (v) => pad.top + ph - (v / maxY) * ph;

  // 背景
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, w, h);

  // 网格线
  ctx.strokeStyle = '#f0f0f0';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i++) {
    const x = pad.left + (i / 5) * pw;
    ctx.beginPath();
    ctx.moveTo(x, pad.top);
    ctx.lineTo(x, pad.top + ph);
    ctx.stroke();

    const y = pad.top + (i / 5) * ph;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(pad.left + pw, y);
    ctx.stroke();
  }

  // 轴标签
  ctx.fillStyle = '#666';
  ctx.font = '11px sans-serif';
  ctx.textAlign = 'center';
  for (let i = 0; i <= 5; i++) {
    const xv = Math.round((i / 5) * maxX);
    ctx.fillText(xv + 'min', pad.left + (i / 5) * pw, pad.top + ph + 18);

    const yv = Math.round((i / 5) * maxY);
    ctx.textAlign = 'right';
    ctx.fillText(yv, pad.left - 8, pad.top + ph - (i / 5) * ph + 4);
    ctx.textAlign = 'center';
  }

  // 轴标题
  ctx.fillStyle = '#888';
  ctx.font = '12px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('对话时长 (分钟) →', pad.left + pw / 2, pad.top + ph + 36);

  ctx.save();
  ctx.translate(14, pad.top + ph / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText('消息条数 ↑', 0, 0);
  ctx.restore();

  // 绘制散点
  const colors = ['#4a90d9', '#50c878', '#f5a623', '#ff7a59', '#d973bf', '#7b61ff', '#d93025'];
  data.forEach((p, i) => {
    const x = scaleX(Math.min(p.duration_min, maxX));
    const y = scaleY(Math.min(p.message_count, maxY));
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fillStyle = colors[i % colors.length];
    ctx.globalAlpha = 0.6;
    ctx.fill();
    ctx.globalAlpha = 1;
  });

  // 边框
  ctx.strokeStyle = '#e0e0e0';
  ctx.strokeRect(pad.left, pad.top, pw, ph);
}


function copyStatsAsJson() {
  if (!statsDataCache) return;

  // 去掉原始数据点，只保留聚合统计
  const cleaned = { ...statsDataCache };
  delete cleaned.scatter_data;
  const json = JSON.stringify(cleaned);
  doCopy(json, '.stats-copy-summary');
}


function copyStatsFullJson() {
  if (!statsDataCache) return;
  doCopy(JSON.stringify(statsDataCache), '.stats-copy-full');
}


function doCopy(json, btnSelector) {
  if (!navigator.clipboard) {
    fallbackCopy(json, btnSelector);
    return;
  }
  navigator.clipboard.writeText(json).then(() => {
    showCopyFeedback(true, btnSelector);
  }).catch(() => {
    fallbackCopy(json, btnSelector);
  });
}




function showCopyFeedback(success, btnSelector) {
  const btn = btnSelector ? document.querySelector(btnSelector) : document.querySelector('.stats-copy-btn');
  if (!btn) return;
  const origText = btn.getAttribute('data-orig') || '📋 复制';
  btn.textContent = success ? '✅ 已复制!' : '❌ 复制失败';
  btn.classList.add(success ? 'copied' : 'failed');
  setTimeout(() => {
    btn.textContent = origText;
    btn.classList.remove('copied', 'failed');
  }, 2000);
}


function fallbackCopy(text, btnSelector) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.left = '-9999px';
  document.body.appendChild(ta);
  ta.select();
  try {
    document.execCommand('copy');
    showCopyFeedback(true, btnSelector);
  } catch (e) {
    showCopyFeedback(false, btnSelector);
  }
  document.body.removeChild(ta);
}


// ============================================================
// 初始化
// ============================================================
loadSessions();
