/**
 * 对话管理 — 真实 API 版
 *
 * Step 3: 后端已实现，前端对接真实 API
 */
// ============================================================
// 1. 状态
// ============================================================

const state = {
  sessions: [],                // 从 API 加载
  archiveStats: null,          // 从 deepseekGetStats 加载
  currentFilter: 'raw',       // 'raw' | 'archived' | 'deleted'
  selectedIds: new Set(),
  allChecked: false,
  filterYear: '',             // '' = 全部年份
  filterMonth: '',             // '' = 全部月份
  filterQuery: '',             // 搜索关键词
  currentPage: 1,
  pageSize: 15,
  pendingId: '',               // 弹窗中待操作的对话 ID
  loading: false,
};

// ============================================================
// 2. 工具
// ============================================================

function formatDate(isoStr) {
  if (!isoStr) return '';
  return isoStr.slice(5); // "06-01"
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// 复制文本到剪贴板，按钮临时显示反馈
function copyText(text, btn) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.left = '-9999px';
  document.body.appendChild(ta);
  ta.select();
  try {
    document.execCommand('copy');
    if (btn) { btn.textContent = '✅ 已复制'; setTimeout(() => { btn.textContent = '📋 复制路径'; }, 1500); }
  } catch (e) {
    if (btn) { btn.textContent = '❌ 失败'; setTimeout(() => { btn.textContent = '📋 复制路径'; }, 1500); }
  }
  document.body.removeChild(ta);
}

// ============================================================
// 3. 从 sessions 推断可选年月
// ============================================================

function getAvailableDates() {
  const years = new Set();
  const months = new Set();
  state.sessions.forEach(s => {
    if (s.date) {
      years.add(s.date.slice(0, 4));
      months.add(s.date.slice(5, 7));
    }
  });
  return {
    years: [...years].sort(),
    months: [...months].sort(),
  };
}

function dateFilteredSessions() {
  let filtered = state.sessions;
  if (state.filterYear) {
    filtered = filtered.filter(s => s.date && s.date.slice(0, 4) === state.filterYear);
  }
  if (state.filterMonth) {
    filtered = filtered.filter(s => s.date && s.date.slice(5, 7) === state.filterMonth);
  }
  return filtered;
}

// ============================================================
// 4. 计算
// ============================================================

function calcStats() {
  const filtered = dateFilteredSessions();
  const total = filtered.length;
  const raw = filtered.filter(s => s.status === 'raw').length;
  const archived = filtered.filter(s => s.status === 'archived').length;
  const deleted = filtered.filter(s => s.status === 'deleted').length;
  const numerator = archived;
  const denominator = raw + archived;
  const completionRate = denominator > 0 ? (numerator / denominator * 100) : 0;
  return { total, raw, archived, deleted, completionRate };
}

function getFilteredSessions() {
  let filtered = dateFilteredSessions();
  if (state.currentFilter !== 'all') {
    filtered = filtered.filter(s => s.status === state.currentFilter);
  }
  if (state.filterQuery) {
    const q = state.filterQuery.toLowerCase();
    filtered = filtered.filter(s => s.title.toLowerCase().includes(q));
  }
  return filtered;
}

function getPaginatedSessions() {
  const all = getFilteredSessions();
  const start = (state.currentPage - 1) * state.pageSize;
  return {
    items: all.slice(start, start + state.pageSize),
    total: all.length,
    totalPages: Math.max(1, Math.ceil(all.length / state.pageSize)),
    page: state.currentPage,
  };
}

function resetPage() {
  state.currentPage = 1;
}

function getStatusDisplay(status) {
  const map = { raw: '🟢 待处理', archived: '🟡 已归档', deleted: '🔴 已删除' };
  return map[status] || status;
}

// ============================================================
// 5. 初始化筛选区（只执行一次，DOM 不销毁）
// ============================================================

function initFilterArea() {
  const container = document.getElementById('am-filter-area');
  if (!container) return;
  if (container.dataset.initialized === '1') return;
  container.dataset.initialized = '1';

  const dates = getAvailableDates();

  let yearOpts = `<option value="">全部年份</option>`;
  dates.years.forEach(y => {
    const sel = state.filterYear === y ? 'selected' : '';
    yearOpts += `<option value="${y}" ${sel}>${y}年</option>`;
  });

  let monthOpts = `<option value="">全部月份</option>`;
  dates.months.forEach(m => {
    const sel = state.filterMonth === m ? 'selected' : '';
    monthOpts += `<option value="${m}" ${sel}>${m}月</option>`;
  });

  container.innerHTML = `
    <div class="am-date-filter">
      <div class="am-date-selectors">
        📅
        <select class="am-date-select" onchange="amChangeFilterDate()" id="am-filter-year">
          ${yearOpts}
        </select>
        <span class="am-date-sep">年</span>
        <select class="am-date-select" onchange="amChangeFilterDate()" id="am-filter-month">
          ${monthOpts}
        </select>
        <span class="am-date-sep">月</span>
      </div>
      <div id="am-summary" class="am-date-summary"></div>
    </div>
    <div class="am-search-bar">
      <span class="am-search-icon">🔍</span>
      <input type="text" class="am-search-input" id="am-search-input"
             placeholder="搜索标题..."
             onkeydown="if(event.key==='Enter')amDoSearch()" spellcheck="false">
      <button class="am-search-btn" onclick="amDoSearch()">搜索</button>
      <button id="am-search-clear" class="am-search-clear-btn" style="display:none" onclick="amClearSearch()">✕ 清除</button>
    </div>
  `;
}

function updateFilterSummary() {
  const el = document.getElementById('am-summary');
  if (!el) return;
  const dateRqd = dateFilteredSessions();
  const totalAll = state.sessions.length;
  let summary;
  if (state.filterQuery) {
    const afterSearch = getFilteredSessions();
    summary = `🔍 "${state.filterQuery}" · 找到 ${afterSearch.length} 条`;
  } else if (state.filterYear || state.filterMonth) {
    summary = `${state.filterYear || '全部'}年${state.filterMonth || '全部'}月 · 共 ${dateRqd.length} / ${totalAll} 条`;
  } else {
    summary = `全部对话 · 共 ${totalAll} 条`;
  }
  el.textContent = summary;
}

window.amChangeFilterDate = function() {
  const yearEl = document.getElementById('am-filter-year');
  const monthEl = document.getElementById('am-filter-month');
  state.filterYear = yearEl ? yearEl.value : '';
  state.filterMonth = monthEl ? monthEl.value : '';
  state.selectedIds.clear();
  state.allChecked = false;
  resetPage();
  render();
};

window.amDoSearch = function() {
  state.filterQuery = (document.getElementById('am-search-input') || {}).value || '';
  state.selectedIds.clear();
  state.allChecked = false;
  resetPage();
  render();
};

window.amClearSearch = function() {
  state.filterQuery = '';
  const el = document.getElementById('am-search-input');
  if (el) el.value = '';
  state.selectedIds.clear();
  state.allChecked = false;
  resetPage();
  render();
};

// ============================================================
// 6. 渲染 — 状态卡片
// ============================================================

function renderCards() {
  const stats = calcStats();
  const statuses = [
    { key: 'raw', icon: '🟢', label: '待处理', count: stats.raw, pct: stats.total > 0 ? (stats.raw / stats.total * 100) : 0, color: '#4a90d9', bg: '#e8f0fe' },
    { key: 'archived', icon: '🟡', label: '已归档', count: stats.archived, pct: stats.total > 0 ? (stats.archived / stats.total * 100) : 0, color: '#f5a623', bg: '#fef9e7' },
    { key: 'deleted', icon: '🔴', label: '回收站', count: stats.deleted, pct: stats.total > 0 ? (stats.deleted / stats.total * 100) : 0, color: '#d93025', bg: '#fef2f2' },
  ];

  let html = `<div class="am-status-list">`;
  statuses.forEach(s => {
    const active = state.currentFilter === s.key;
    html += `
      <div class="am-status-row${active ? ' active' : ''}" onclick="amFilterByStatus('${s.key}')" style="${active ? 'background:' + s.bg + ';border-color:' + s.color : ''}">
        <div class="am-status-left">
          <span class="am-status-icon">${s.icon}</span>
          <span class="am-status-label">${s.label}</span>
        </div>
        <div class="am-status-right">
          <span class="am-status-count" style="color:${s.color}">${s.count}</span>
          <span class="am-status-pct">${s.pct.toFixed(1)}%</span>
        </div>
        <div class="am-status-bar-wrap">
          <div class="am-status-bar" style="width:${s.pct}%;background:${s.color}"></div>
        </div>
      </div>
    `;
  });
  html += `</div>`;

  html += `
    <div class="am-completion">
      <div class="am-completion-label">
        <span>📊 归档完成率</span>
        <span>${stats.completionRate.toFixed(1)}%</span>
      </div>
      <div class="am-completion-bar">
        <div class="am-completion-fill" style="width:${stats.completionRate}%"></div>
      </div>
      <div class="am-completion-sub">已归档 ${stats.archived} / 待处理 ${stats.raw}</div>
    </div>
  `;

  return html;
}

// ============================================================
// 7. 渲染 — 列表
// ============================================================

function renderPagination(paginated) {
  if (paginated.totalPages <= 1) return '';
  const { page, totalPages } = paginated;
  let html = `<div class="am-pagination">`;
  html += `<span class="am-page-info">第 ${page}/${totalPages} 页</span>`;
  html += `<div class="am-page-btns">`;
  html += `<button class="am-page-btn" onclick="amGoPage(${page - 1})" ${page <= 1 ? 'disabled' : ''}>◀</button>`;
  const maxShow = 5;
  let startP = Math.max(1, page - Math.floor(maxShow / 2));
  let endP = Math.min(totalPages, startP + maxShow - 1);
  if (endP - startP < maxShow - 1) startP = Math.max(1, endP - maxShow + 1);
  for (let p = startP; p <= endP; p++) {
    html += `<button class="am-page-btn${p === page ? ' active' : ''}" onclick="amGoPage(${p})">${p}</button>`;
  }
  html += `<button class="am-page-btn" onclick="amGoPage(${page + 1})" ${page >= totalPages ? 'disabled' : ''}>▶</button>`;
  html += `</div></div>`;
  return html;
}

window.amGoPage = function(p) {
  state.currentPage = p;
  render();
};

function renderList() {
  const paginated = getPaginatedSessions();
  const filtered = paginated.items;
  const hasSelection = state.selectedIds.size > 0;
  const filterStatus = state.currentFilter;

  let batchHtml = `<div class="am-batch-bar">`;
  batchHtml += `
    <label class="am-batch-check">
      <input type="checkbox" ${state.allChecked ? 'checked' : ''}
             onchange="amToggleAll(this.checked)">
      全选
    </label>
  `;
  if (hasSelection) {
    batchHtml += `<span style="font-size:11px;color:var(--text-secondary)">已选 ${state.selectedIds.size} 项</span>`;
    if (filterStatus === 'raw') {
      batchHtml += `<button class="am-batch-btn" onclick="amBatchArchive()">📦 归档选中</button>`;
      batchHtml += `<button class="am-batch-btn am-batch-btn-del" onclick="amBatchDelete()">🗑️ 删除选中</button>`;
    } else if (filterStatus === 'archived') {
      batchHtml += `<button class="am-batch-btn" onclick="amBatchRestore()">↩️ 恢复选中</button>`;
      batchHtml += `<button class="am-batch-btn am-batch-btn-del" onclick="amBatchDelete()">🗑️ 删除选中</button>`;
    } else if (filterStatus === 'deleted') {
      batchHtml += `<button class="am-batch-btn" onclick="amBatchRestore()">↩️ 恢复选中</button>`;
      batchHtml += `<button class="am-batch-btn am-batch-btn-del" onclick="amBatchPermanentDelete()">🔥 永久删除选中</button>`;
    }
  }
  batchHtml += `</div>`;

  let listHtml = `<div class="am-list">`;
  if (filtered.length === 0) {
    listHtml += `<div class="am-empty">📭 没有${filterStatus === 'raw' ? '待处理' : filterStatus === 'archived' ? '已归档' : '已删除'}的对话</div>`;
  } else {
    filtered.forEach(s => {
      const checked = state.selectedIds.has(s.id) ? 'checked' : '';
      const statusClass = `am-item-status-${s.status}`;
      const hasNotes = s.notes && s.notes.length > 0;

      listHtml += `
        <div class="am-item">
          <div class="am-item-check">
            <input type="checkbox" ${checked} onchange="amToggleItem('${s.id}', this.checked)">
          </div>
          <div class="am-item-body" onclick="amViewSession('${s.id}')">
            <div class="am-item-title">${escapeHtml(s.title)}</div>
            <div class="am-item-meta">
              <span>📅 ${s.date}</span>
              <span>💬 ${s.message_count}条</span>
              <span>🤖 ${escapeHtml(s.model)}</span>
              <span class="am-item-status ${statusClass}">${getStatusDisplay(s.status)}</span>
            </div>
            ${hasNotes ? `<div class="am-item-notes-preview">📝 ${escapeHtml(s.notes.slice(0, 40))}…</div>` : ''}
          </div>
          <div class="am-item-actions">
            ${s.status === 'raw' ? `
              <button class="am-action-btn am-action-btn-archive" onclick="event.stopPropagation(); amShowArchiveModal('${s.id}')">✏️ 归档</button>
              <button class="am-action-btn am-action-btn-del" onclick="event.stopPropagation(); amShowDeleteConfirm('${s.id}')">🗑️</button>
            ` : ''}
            ${s.status === 'archived' ? `
              <button class="am-action-btn am-action-btn-restore" onclick="event.stopPropagation(); amRestore('${s.id}')">↩️ 恢复</button>
              <button class="am-action-btn am-action-btn-del" onclick="event.stopPropagation(); amShowDeleteConfirm('${s.id}')">🗑️</button>
            ` : ''}
            ${s.status === 'deleted' ? `
              <button class="am-action-btn am-action-btn-restore" onclick="event.stopPropagation(); amRestore('${s.id}')">↩️ 恢复</button>
              <button class="am-action-btn am-action-btn-del" onclick="event.stopPropagation(); amShowPermanentDeleteConfirm('${s.id}')">🔥</button>
            ` : ''}
          </div>
        </div>
      `;
    });
  }
  listHtml += `</div>`;

  const pageHtml = renderPagination(paginated);
  return batchHtml + listHtml + pageHtml;
}

// ============================================================
// 8. 主渲染入口
// ============================================================

function render() {
  updateFilterSummary();
  const clearBtn = document.getElementById('am-search-clear');
  if (clearBtn) clearBtn.style.display = state.filterQuery ? 'inline' : 'none';
  const container = document.getElementById('am-results');
  if (!container) return;

  if (state.loading) {
    container.innerHTML = '<div style="padding:40px;text-align:center;color:var(--text-secondary);font-size:13px">加载中…</div>';
    return;
  }

  container.innerHTML = renderCards() + renderList();
}

// ============================================================
// 9. 操作逻辑（API 版）
// ============================================================

function updateLocalSession(id, changes) {
  const s = state.sessions.find(x => x.id === id);
  if (s) Object.assign(s, changes);
}

function removeLocalSession(id) {
  const idx = state.sessions.findIndex(x => x.id === id);
  if (idx !== -1) state.sessions.splice(idx, 1);
}

// 过滤
window.amFilterByStatus = function(status) {
  state.currentFilter = status;
  state.selectedIds.clear();
  state.allChecked = false;
  resetPage();
  render();
};

// 切换选中
window.amToggleItem = function(id, checked) {
  if (checked) state.selectedIds.add(id);
  else state.selectedIds.delete(id);
  state.allChecked = false;
  render();
};

// 全选
window.amToggleAll = function(checked) {
  state.allChecked = checked;
  state.selectedIds.clear();
  if (checked) getFilteredSessions().forEach(s => state.selectedIds.add(s.id));
  render();
};

// 查看笔记
window.amShowNotes = function(id) {
  const s = state.sessions.find(x => x.id === id);
  if (!s || !s.notes) return;
  showModal({
    title: '📝 知识笔记',
    body: `<div style="font-size:12px;line-height:1.6;white-space:pre-wrap;color:var(--text)">${escapeHtml(s.notes)}</div>`,
    buttons: [{ text: '关闭', primary: true }]
  });
};

// 归档弹窗
window.amShowArchiveModal = function(id) {
  const s = state.sessions.find(x => x.id === id);
  if (!s) return;
  state.pendingId = id;
  showModal({
    title: '✏️ 归档对话',
    subtitle: escapeHtml(s.title),
    body: `
      <label style="font-size:11px;color:var(--text-secondary);display:block;margin-bottom:4px">知识提炼笔记（可选）</label>
      <textarea id="am-notes-input" class="am-modal-textarea" placeholder="记录这篇对话中的关键知识点…"></textarea>
    `,
    buttons: [
      { text: '取消', onclick: 'closeAmModal()' },
      { text: '✅ 确认归档', primary: true, onclick: 'amDoArchive(state.pendingId); closeAmModal();' }
    ]
  });
  setTimeout(() => {
    const ta = document.getElementById('am-notes-input');
    if (ta) ta.focus();
  }, 100);
};

// 执行归档 → API
window.amDoArchive = async function(id) {
  const notes = (document.getElementById('am-notes-input') || {}).value || '';
  try {
    await deepseekUpdateStatus(id, 'archived', notes);
    updateLocalSession(id, { status: 'archived', notes });
    state.selectedIds.clear();
    state.allChecked = false;
    resetPage();
    render();
  } catch (e) {
    showModal({
      title: '❌ 归档失败',
      body: `<div style="font-size:12px;color:#d93025">${escapeHtml(e.message)}</div>`,
      buttons: [{ text: '关闭', primary: true }]
    });
  }
};

// 删除确认弹窗
window.amShowDeleteConfirm = function(id) {
  const s = state.sessions.find(x => x.id === id);
  if (!s) return;
  state.pendingId = id;
  showModal({
    title: '🗑️ 确认删除',
    body: `
      <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px">将以下对话移入回收站：</div>
      <div style="font-size:12px;font-weight:500;color:var(--text);padding:6px 10px;background:var(--bg);border-radius:6px">
        ${escapeHtml(s.title)}
      </div>
    `,
    buttons: [
      { text: '取消', onclick: 'closeAmModal()' },
      { text: '🗑️ 确认删除', danger: true, onclick: 'amDoDelete(state.pendingId); closeAmModal();' }
    ]
  });
};

// 执行删除 → API
window.amDoDelete = async function(id) {
  try {
    await deepseekUpdateStatus(id, 'deleted', '');
    updateLocalSession(id, { status: 'deleted', notes: '' });
    state.selectedIds.clear();
    state.allChecked = false;
    resetPage();
    render();
  } catch (e) {
    showModal({
      title: '❌ 删除失败',
      body: `<div style="font-size:12px;color:#d93025">${escapeHtml(e.message)}</div>`,
      buttons: [{ text: '关闭', primary: true }]
    });
  }
};

// 恢复 → API
window.amRestore = async function(id) {
  try {
    await deepseekUpdateStatus(id, 'raw', '');
    updateLocalSession(id, { status: 'raw' });
    state.selectedIds.clear();
    state.allChecked = false;
    resetPage();
    render();
  } catch (e) {
    showModal({
      title: '❌ 恢复失败',
      body: `<div style="font-size:12px;color:#d93025">${escapeHtml(e.message)}</div>`,
      buttons: [{ text: '关闭', primary: true }]
    });
  }
};

// 永久删除确认弹窗
window.amShowPermanentDeleteConfirm = function(id) {
  const s = state.sessions.find(x => x.id === id);
  if (!s) return;
  state.pendingId = id;
  showModal({
    title: '🔥 永久删除',
    body: `
      <div style="font-size:12px;color:#d93025;margin-bottom:8px">此操作不可恢复！</div>
      <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px">将从回收站彻底删除以下对话：</div>
      <div style="font-size:12px;font-weight:500;color:var(--text);padding:6px 10px;background:var(--bg);border-radius:6px">
        ${escapeHtml(s.title)}
      </div>
    `,
    buttons: [
      { text: '取消', onclick: 'closeAmModal()' },
      { text: '🔥 确认永久删除', danger: true, onclick: 'amDoPermanentDelete(state.pendingId); closeAmModal();' }
    ]
  });
};

// 执行永久删除 → API
window.amDoPermanentDelete = async function(id) {
  try {
    await deepseekPermanentDelete(id);
    removeLocalSession(id);
    state.selectedIds.clear();
    state.allChecked = false;
    resetPage();
    render();
  } catch (e) {
    showModal({
      title: '❌ 永久删除失败',
      body: `<div style="font-size:12px;color:#d93025">${escapeHtml(e.message)}</div>`,
      buttons: [{ text: '关闭', primary: true }]
    });
  }
};

// 批量操作：对每个选中 ID 调用 API，完成后整体刷新
async function batchApiCall(actionFn, titlePrefix) {
  const ids = [...state.selectedIds];
  const total = ids.length;
  let done = 0;
  let errors = 0;

  // 显示进度
  const container = document.getElementById('am-results');
  if (container) {
    container.innerHTML = `<div style="padding:40px;text-align:center;color:var(--text-secondary);font-size:13px">${titlePrefix}中… 0/${total}</div>`;
  }

  for (const id of ids) {
    try {
      await actionFn(id);
      done++;
    } catch {
      errors++;
    }
    if (container && (done + errors) % 5 === 0) {
      container.innerHTML = `<div style="padding:40px;text-align:center;color:var(--text-secondary);font-size:13px">${titlePrefix}中… ${done + errors}/${total}</div>`;
    }
  }

  state.selectedIds.clear();
  state.allChecked = false;
  resetPage();

  // 完成后重新加载数据
  await reloadAllSessions();
  render();

  if (errors > 0) {
    showModal({
      title: '⚠️ 部分操作失败',
      body: `<div style="font-size:12px;color:#d93025">${errors} / ${total} 操作失败，请重试</div>`,
      buttons: [{ text: '关闭', primary: true }]
    });
  }
}

// 批量归档
window.amBatchArchive = function() {
  if (state.selectedIds.size === 0) return;
  showModal({
    title: '📦 批量归档',
    body: `
      <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px">
        将 ${state.selectedIds.size} 条对话归档
      </div>
      <label style="font-size:11px;color:var(--text-secondary);display:block;margin-bottom:4px">统一笔记（可选，可为空）</label>
      <textarea id="am-notes-input" class="am-modal-textarea" placeholder="这批对话的共同知识点…"></textarea>
    `,
    buttons: [
      { text: '取消', onclick: 'closeAmModal()' },
      { text: '✅ 确认归档', primary: true, onclick: 'amDoBatchArchive(); closeAmModal();' }
    ]
  });
  setTimeout(() => {
    const ta = document.getElementById('am-notes-input');
    if (ta) ta.focus();
  }, 100);
};

window.amDoBatchArchive = function() {
  const notes = (document.getElementById('am-notes-input') || {}).value || '';
  batchApiCall(
    (id) => deepseekUpdateStatus(id, 'archived', notes),
    '归档'
  );
};

// 批量删除
window.amBatchDelete = function() {
  if (state.selectedIds.size === 0) return;
  showModal({
    title: '🗑️ 批量删除',
    body: `<div style="font-size:12px;color:var(--text-secondary)">确定要将 ${state.selectedIds.size} 条对话移入回收站？</div>`,
    buttons: [
      { text: '取消', onclick: 'closeAmModal()' },
      { text: '🗑️ 确认删除', danger: true, onclick: 'amDoBatchDelete(); closeAmModal();' }
    ]
  });
};

window.amDoBatchDelete = function() {
  batchApiCall(
    (id) => deepseekUpdateStatus(id, 'deleted', ''),
    '删除'
  );
};

// 批量恢复
window.amBatchRestore = function() {
  if (state.selectedIds.size === 0) return;
  batchApiCall(
    (id) => deepseekUpdateStatus(id, 'raw', ''),
    '恢复'
  );
};

// 批量永久删除
window.amBatchPermanentDelete = function() {
  if (state.selectedIds.size === 0) return;
  showModal({
    title: '🔥 批量永久删除',
    body: `
      <div style="font-size:12px;color:#d93025;margin-bottom:8px">此操作不可恢复！</div>
      <div style="font-size:12px;color:var(--text-secondary)">确定要从回收站永久删除 ${state.selectedIds.size} 条对话？</div>
    `,
    buttons: [
      { text: '取消', onclick: 'closeAmModal()' },
      { text: '🔥 确认永久删除', danger: true, onclick: 'amDoBatchPermanentDelete(); closeAmModal();' }
    ]
  });
};

window.amDoBatchPermanentDelete = function() {
  batchApiCall(
    (id) => deepseekPermanentDelete(id),
    '永久删除'
  );
};

// 重新加载所有会话
async function reloadAllSessions() {
  try {
    const data = await deepseekGetAllSessions();
    state.sessions = data.sessions || [];
  } catch (e) {
    console.error('Failed to reload sessions:', e);
    state.sessions = [];
  }
}

// 查看对话详情
window.amViewSession = async function(id) {
  const s = state.sessions.find(x => x.id === id);
  if (!s) return;
  const mainBody = document.getElementById('main-body');
  if (!mainBody) return;

  // 显示加载中
  mainBody.innerHTML = '<div class="loading" style="padding:40px;text-align:center">加载对话内容…</div>';
  document.getElementById('main-header').style.display = 'none';
  document.getElementById('copy-btn-wrap').style.display = 'none';

  try {
    const data = await deepseekGetContent(id);
    const contentHtml = renderDsMarkdown(data.content || '');

    mainBody.innerHTML = `
      <div class="ds-content" style="max-width:900px;margin:0 auto;padding:24px">
        <h2 style="font-size:18px;margin-bottom:8px">${escapeHtml(s.title)}</h2>
        <div style="font-size:12px;color:var(--text-secondary);margin-bottom:16px">
          📅 ${s.date} · 💬 ${s.message_count}条 · 🤖 ${escapeHtml(s.model)}
          <span class="am-item-status am-item-status-${s.status}" style="margin-left:8px">${getStatusDisplay(s.status)}</span>
        </div>
        <div style="font-size:11px;color:var(--text-secondary);margin-bottom:12px;display:flex;align-items:center;gap:6px;word-break:break-all">
          📂 <code style="font-size:11px;background:var(--bg);padding:2px 4px;border-radius:3px">${escapeHtml(data.abs_path || '')}</code>
          <button class="btn btn-ghost" style="padding:2px 6px;font-size:11px;flex-shrink:0" onclick="copyText('${escapeHtml(data.abs_path || '')}',this)">📋 复制路径</button>
        </div>
        ${s.notes ? `
          <div style="background:#fef9e7;border:1px solid #fdecc8;border-radius:8px;padding:12px;font-size:13px;line-height:1.6;margin-bottom:16px">
            <strong>📝 知识笔记</strong><br>
            ${escapeHtml(s.notes)}
          </div>
        ` : ''}
        <hr style="border:none;border-top:1px solid var(--border);margin:16px 0">
        ${contentHtml || '<div style="color:var(--text-secondary);text-align:center;padding:40px 0">（无对话内容）</div>'}
      </div>
    `;
    showContentSearch();
  } catch (e) {
    mainBody.innerHTML = `
      <div style="padding:40px;text-align:center;color:#d93025">
        ❌ 加载失败：${escapeHtml(e.message)}
      </div>
    `;
  }
};

// ============================================================
// 10. 弹窗系统
// ============================================================

function showModal(config) {
  const overlay = document.getElementById('am-modal-overlay');
  const modal = document.getElementById('am-modal');
  const body = document.getElementById('am-modal-body');
  if (!overlay || !modal || !body) return;

  let buttonsHtml = (config.buttons || []).map(b => {
    let cls = 'am-modal-btn';
    if (b.primary) cls += ' am-modal-btn-primary';
    if (b.danger) cls += ' am-modal-btn-danger';
    const clickHandler = (typeof b.onclick === 'string') ? b.onclick : (b.onclick ? b.onclick.name + '()' : '');
    return `<button class="${cls}" onclick="${escapeHtml(clickHandler)}">${escapeHtml(b.text)}</button>`;
  }).join('');

  body.innerHTML = `
    <div class="am-modal-title">${escapeHtml(config.title)}</div>
    ${config.subtitle ? `<div class="am-modal-sub">${config.subtitle}</div>` : ''}
    ${config.body || ''}
    <div class="am-modal-actions">${buttonsHtml}</div>
  `;

  overlay.style.display = 'block';
  modal.style.display = 'block';
}

window.closeAmModal = function() {
  const overlay = document.getElementById('am-modal-overlay');
  const modal = document.getElementById('am-modal');
  if (overlay) overlay.style.display = 'none';
  if (modal) modal.style.display = 'none';
};

// ============================================================
// 11. 初始化入口（API 版）
// ============================================================

window.loadArchiveManager = async function() {
  state.loading = true;
  state.sessions = [];
  state.currentFilter = 'raw';
  state.selectedIds.clear();
  state.allChecked = false;
  state.filterYear = '';
  state.filterMonth = '';

  const container = document.getElementById('am-results');
  if (container) {
    container.innerHTML = '<div style="padding:40px;text-align:center;color:var(--text-secondary);font-size:13px">⌛ 加载对话数据…</div>';
  }

  try {
    // 加载所有会话
    const data = await deepseekGetAllSessions();
    state.sessions = data.sessions || [];

    // 默认过滤掉 deleted_permanent
    state.sessions = state.sessions.filter(s => s.status !== 'deleted_permanent');

    // 默认选中当前月份
    const now = new Date();
    state.filterYear = String(now.getFullYear());
    state.filterMonth = String(now.getMonth() + 1).padStart(2, '0');
  } catch (e) {
    console.error('Failed to load archive manager:', e);
    state.sessions = [];
  }

  state.loading = false;

  // 初始化筛选区 DOM（只执行一次）
  initFilterArea();
  render();
};
