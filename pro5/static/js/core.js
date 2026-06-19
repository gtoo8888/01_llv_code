// index.html 逻辑：会话列表 SPA

function formatDate(isoString) {
  if (!isoString) return '-';
  const d = new Date(isoString);
  if (isNaN(d)) return isoString;
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function formatTime(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  if (isNaN(d)) return isoString;
  const pad = n => String(n).padStart(2, '0');
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// 点击会话
async function selectSession(sessionKey) {
  // 局部更新选中样式
  const prevActive = document.querySelector('.conv-item.active');
  if (prevActive) prevActive.classList.remove('active');
  const newActive = document.querySelector(`.conv-item[data-key="${sessionKey.replace(/"/g, '&quot;')}"]`);
  if (newActive) newActive.classList.add('active');

  const mainBody = document.getElementById('main-body');
  mainBody.textContent = '';
  const loadingEl = document.createElement('div');
  loadingEl.className = 'loading';
  loadingEl.style.cssText = 'padding:40px';
  loadingEl.textContent = '加载中';
  mainBody.appendChild(loadingEl);

  try {
    const data = await getSessionMessages(sessionKey);
    renderConversation(data);
  } catch (e) {
    mainBody.textContent = '';
    const err = document.createElement('div');
    err.className = 'empty-main';
    err.textContent = '加载失败：' + e.message;
    mainBody.appendChild(err);
  }
}

// 渲染会话消息
function renderConversation(data) {
  const { session_key, channel, messages } = data;

  document.getElementById('h-key').textContent = session_key;
  document.getElementById('h-channel').textContent = channel;
  document.getElementById('h-count').textContent = messages.length;
  document.getElementById('main-header').style.display = 'flex';
  document.getElementById('copy-btn-wrap').style.display = 'none';

  const mainBody = document.getElementById('main-body');

  if (!messages || messages.length === 0) {
    mainBody.innerHTML = '<div class="empty-main">该会话暂无消息</div>';
    return;
  }

  const html = `
    <div class="message-list">
      ${messages.map(m => buildMessageHtml(m)).join('')}
    </div>
  `;

  mainBody.innerHTML = html;
}

function buildMessageHtml(msg) {
  const roleLabelMap = {
    user: '👤 User',
    assistant: '🤖 Assistant',
    system: '⚙️ System',
    tool: '🔧 Tool',
    toolResult: '🔧 Tool Result' 
  };
  const roleClass = msg.is_system ? 'msg-system' : `msg-${msg.role}`;
  const roleLabel = roleLabelMap[msg.role] || msg.role;
  const timeStr = formatTime(msg.timestamp);
  const content = msg.content || '';
  const escapedContent = escapeHtml(content);
  const toolCallsHtml = renderToolCalls(msg.tool_calls);

  if (msg.role === 'toolResult') {
    return `
      <div class="msg ${roleClass}">
        <div class="msg-role">
          ${timeStr ? `<span class="msg-time">${timeStr}</span>` : ''}
          ${roleLabel}
        </div>
        <div class="toolresult-container">
          <button class="toolresult-expand-btn" 
                  onclick="var contentDiv = this.nextElementSibling; 
                           if(contentDiv.style.display === 'none'){ 
                             contentDiv.style.display = 'block'; 
                             this.textContent = '收起'; 
                           } else { 
                             contentDiv.style.display = 'none'; 
                             this.textContent = '展开'; 
                           }">展开</button>
          <div class="msg-content" style="display:none;">${escapedContent || '<em>（无内容）</em>'}</div>
        </div>
        ${toolCallsHtml}
      </div>
    `;
  }

  return `
    <div class="msg ${roleClass}">
      <div class="msg-role">
        ${timeStr ? `<span class="msg-time">${timeStr}</span>` : ''}
        ${roleLabel}
      </div>
      <div class="msg-content">${escapedContent || '<em>（无内容）</em>'}</div>
      ${toolCallsHtml}
    </div>
  `;
}


function renderToolCalls(toolCalls) {
  if (!toolCalls || toolCalls.length === 0) return '';

  return `
    <div class="tool-calls">
      ${toolCalls.map(tc => `
        <div class="tool-call">
          <div class="tool-call-header" onclick="toggleEl(this)">
            <span>🔧 ${escapeHtml(tc.name)}</span>
            <span class="toggle-btn">参数 ▼</span>
          </div>
          <div class="tool-args">${escapeHtml(JSON.stringify(tc.arguments, null, 2))}</div>
          ${tc.result ? `
            <div class="tool-call-header" onclick="toggleEl(this)" style="margin-top:6px">
              <span>📥 结果</span>
              <span class="toggle-btn">结果 ▼</span>
            </div>
            <div class="tool-result">${escapeHtml(tc.result)}</div>
          ` : ''}
        </div>
      `).join('')}
    </div>
  `;
}

function toggleEl(headerEl) {
  const next = headerEl.nextElementSibling;
  const btn = headerEl.querySelector('.toggle-btn');
  if (!next || !btn) return;
  const visible = next.classList.toggle('visible');
  btn.textContent = visible
    ? (next.classList.contains('tool-args') ? '参数 ▲' : '结果 ▲')
    : (next.classList.contains('tool-args') ? '参数 ▼' : '结果 ▼');
}

// 渲染左侧会话列表
function renderSessionList(sessions) {
  const list = document.getElementById('conv-list');

  if (!sessions || sessions.length === 0) {
    list.innerHTML = '<div style="padding:20px;color:var(--text-secondary);font-size:13px;text-align:center">暂无会话记录</div>';
    return;
  }

  list.innerHTML = sessions.map(s => `
    <div class="conv-item" data-key="${encodeURIComponent(s.session_key)}"
         onclick="selectSession('${encodeURIComponent(s.session_key).replace(/'/g, "\\'")}')">
      <div class="conv-item-time">📅 ${formatDate(s.start_time)}</div>
      <div class="conv-item-meta">💬 ${s.message_count}条 · 📡 ${s.channel}</div>
    </div>
  `).join('');
}

async function loadSessions() {
  const list = document.getElementById('conv-list');
  list.innerHTML = '<div class="loading" style="padding:20px">加载中</div>';

  try {
    const data = await getSessions();
    renderSessionList(data.sessions);
  } catch (e) {
    list.innerHTML = `<div style="padding:20px;color:#d93025;font-size:13px">加载失败：${e.message}</div>`;
  }
}

// ============================================================
// Tab 切换
// ============================================================

// DeepSeek 当前状态
const dsState = { year: '', month: '', sessions: [], sessionId: '' };

// DeepSeek 当前显示的原始内容（供复制用）
let dsRawContent = '';

// ============================================================
// API 缓存
// ============================================================

let dsStructureCache = null;       // deepseekGetStructure() 缓存
const dsDatesCache = new Map();    // deepseekGetDates(year,month) 缓存，key="YYYY-MM"，存 Promise

function clearDsCache() {
  dsStructureCache = null;
  dsDatesCache.clear();
  if (document.getElementById('ds-year-nav')) loadDsStructure();
}

function switchTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));

  if (tab === 'stats') {
    document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
    document.getElementById('main-header').style.display = 'none';
    document.getElementById('copy-btn-wrap').style.display = 'none';
    hideContentSearch();
    document.getElementById('main-body').innerHTML = '<div class="loading" style="padding:40px;text-align:center">加载统计数据...</div>';
    deepseekGetStats().then(data => renderStatsDashboard(data)).catch(e => {
      document.getElementById('main-body').innerHTML = `<div class="empty-main">加载失败：${e.message}</div>`;
    });
    return;
  }

  hideContentSearch();
  document.querySelectorAll('.tab-content').forEach(c => c.style.display = c.id === `tab-${tab}` ? 'flex' : 'none');

  if (tab === 'deepseek') {
    // 默认重置为浏览视图，清理管理视图的右侧
    switchDsSubTab('browse');
  }
}

// ============================================================
// DeepSeek 子 Tab 切换
// ============================================================

function switchDsSubTab(subtab) {
  document.querySelectorAll('.ds-sub-tab-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.subtab === subtab)
  );

  // 显示/隐藏子视图
  document.getElementById('ds-browse-view').style.display = subtab === 'browse' ? 'flex' : 'none';
  document.getElementById('ds-manage-view').style.display = subtab === 'manage' ? 'flex' : 'none';

  if (subtab === 'browse') {
    // 恢复浏览视图，清空右侧
    document.getElementById('main-header').style.display = 'none';
    document.getElementById('copy-btn-wrap').style.display = 'none';
    hideContentSearch();
    document.getElementById('main-body').innerHTML = '<div class="empty-main">← 选择一条对话查看详情</div>';
    loadDsStructure();
  } else {
    // 切换到管理视图
    document.getElementById('main-header').style.display = 'none';
    document.getElementById('copy-btn-wrap').style.display = 'none';
    hideContentSearch();
    document.getElementById('main-body').innerHTML = '<div class="empty-main">← 选择一条对话查看详情</div>';
    loadArchiveManager();
  }
}

// ═══════════════════════════════════════════════
// 右侧正文搜索（仅搜索 main-body 内部）
// ═══════════════════════════════════════════════

// 搜索状态
const _csState = { matches: [], currentIdx: -1, query: '' };

function showContentSearch() {
  const bar = document.getElementById('content-search-bar');
  if (bar) {
    bar.style.display = 'flex';
    const input = document.getElementById('content-search-input');
    if (input) { input.value = ''; input.focus(); }
  }
  _csState.matches = [];
  _csState.currentIdx = -1;
  _csState.query = '';
  updateCsNavButtons();
}

function hideContentSearch() {
  const bar = document.getElementById('content-search-bar');
  if (bar) bar.style.display = 'none';
  clearCsHighlights();
}

function clearCsHighlights() {
  const body = document.getElementById('main-body');
  if (!body) return;
  // 解除所有高亮标记，合并回原文
  const marks = body.querySelectorAll('.cs-highlight');
  marks.forEach(m => {
    const text = document.createTextNode(m.textContent);
    m.parentNode.replaceChild(text, m);
  });
  // 合并相邻文本节点
  body.normalize();
  _csState.matches = [];
  _csState.currentIdx = -1;
  updateCsNavButtons();
}

function updateCsNavButtons() {
  const prev = document.getElementById('cs-prev');
  const next = document.getElementById('cs-next');
  const count = document.getElementById('content-search-count');
  if (prev) prev.disabled = _csState.matches.length === 0;
  if (next) next.disabled = _csState.matches.length === 0;
  if (count) {
    if (_csState.matches.length > 0) {
      count.textContent = `${_csState.currentIdx + 1} / ${_csState.matches.length}`;
    } else {
      count.textContent = _csState.query ? '0 个结果' : '';
    }
  }
}

function scrollToMatch(el) {
  if (!el) return;
  const body = document.getElementById('main-body');
  if (!body) return;
  const bodyRect = body.getBoundingClientRect();
  const elRect = el.getBoundingClientRect();
  const offset = elRect.top - bodyRect.top - body.scrollTop - 60;
  body.scrollBy({ top: offset, behavior: 'smooth' });
}

function doContentSearch() {
  const input = document.getElementById('content-search-input');
  const q = (input ? input.value.trim() : '').toLowerCase();
  if (!q) { clearCsHighlights(); return; }

  clearCsHighlights();

  const body = document.getElementById('main-body');
  if (!body) return;

  _csState.query = q;
  const matches = [];

  // 收集所有文本节点（先收集再处理，避免 TreeWalker 被 DOM 修改干扰）
  const textNodes = [];
  const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT, null, false);
  let n;
  while (n = walker.nextNode()) textNodes.push(n);

  for (const tn of textNodes) {
    const text = tn.textContent;
    const lower = text.toLowerCase();
    if (lower.indexOf(q) === -1) continue;

    const parent = tn.parentNode;
    const parts = [];
    let remaining = text;
    let pos = 0;

    while (true) {
      const idx = remaining.toLowerCase().indexOf(q);
      if (idx === -1) {
        parts.push(document.createTextNode(remaining));
        break;
      }

      if (idx > 0) {
        parts.push(document.createTextNode(remaining.slice(0, idx)));
      }

      const mark = document.createElement('span');
      mark.className = 'cs-highlight';
      mark.textContent = remaining.slice(idx, idx + q.length);
      parts.push(mark);
      matches.push(mark);

      remaining = remaining.slice(idx + q.length);
    }

    // 用处理后的节点替换原文本节点
    const frag = document.createDocumentFragment();
    for (const p of parts) frag.appendChild(p);
    parent.replaceChild(frag, tn);
  }

  // 合并相邻文本节点
  body.normalize();

  _csState.matches = matches;
  if (matches.length > 0) {
    _csState.currentIdx = 0;
    matches[0].classList.add('cs-current');
    scrollToMatch(matches[0]);
  } else {
    _csState.currentIdx = -1;
  }
  updateCsNavButtons();
}

function contentSearchPrev() {
  const m = _csState.matches;
  if (m.length === 0) return;
  m[_csState.currentIdx].classList.remove('cs-current');
  _csState.currentIdx = (_csState.currentIdx - 1 + m.length) % m.length;
  m[_csState.currentIdx].classList.add('cs-current');
  scrollToMatch(m[_csState.currentIdx]);
  updateCsNavButtons();
}

function contentSearchNext() {
  const m = _csState.matches;
  if (m.length === 0) return;
  m[_csState.currentIdx].classList.remove('cs-current');
  _csState.currentIdx = (_csState.currentIdx + 1) % m.length;
  m[_csState.currentIdx].classList.add('cs-current');
  scrollToMatch(m[_csState.currentIdx]);
  updateCsNavButtons();
}

function contentSearchKeydown(e) {
  const input = document.getElementById('content-search-input');
  const q = (input ? input.value.trim() : '').toLowerCase();

  if (e.key === 'Enter') {
    if (e.shiftKey) {
      // Shift+Enter → 上一个
      e.preventDefault();
      contentSearchPrev();
    } else {
      // Enter → 首次搜索或下一个
      e.preventDefault();
      if (!_csState.query || q !== _csState.query || _csState.matches.length === 0) {
        doContentSearch();
      } else {
        contentSearchNext();
      }
    }
  }
}

// ═══════════════════════════════════════════════
// 侧栏时钟
// ═══════════════════════════════════════════════

const DAY_NAMES = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];

function updateClock() {
  const el = document.getElementById('sidebar-clock');
  if (!el) return;
  const now = new Date();
  const pad = n => String(n).padStart(2, '0');
  const y = now.getFullYear();
  const mo = pad(now.getMonth() + 1);
  const d = pad(now.getDate());
  const h = pad(now.getHours());
  const mi = pad(now.getMinutes());
  const s = pad(now.getSeconds());
  const day = DAY_NAMES[now.getDay()];
  el.innerHTML = `<span class="clock-date">${y}-${mo}-${d}</span> <span class="clock-time">${h}:${mi}:${s}</span> <span class="clock-day">${day}</span>`;
}

// 立即更新一次，然后每秒更新
updateClock();
setInterval(updateClock, 1000);

