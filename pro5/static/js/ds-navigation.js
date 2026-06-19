// DeepSeek — 年份/月份导航

async function loadDsStructure() {
  const yearNav = document.getElementById('ds-year-nav');
  const monthNav = document.getElementById('ds-month-nav');

  try {
    if (!dsStructureCache) {
      dsStructureCache = await deepseekGetStructure();
    }
    const data = dsStructureCache;
    const years = Object.keys(data.years || {}).sort().reverse();

    if (years.length === 0) {
      yearNav.innerHTML = '<div style="padding:10px;color:var(--text-secondary);font-size:12px">暂无归档数据</div>';
      return;
    }

    yearNav.innerHTML = years.map(y =>
      `<button class="ds-nav-btn${dsState.year === y ? ' active' : ''}" onclick="selectDsYear('${y}')">${y}</button>`
    ).join('');

    if (dsState.year && data.years[dsState.year]) {
      renderDsMonths(data.years[dsState.year]);
    } else {
      monthNav.style.display = 'none';
    }
  } catch (e) {
    yearNav.innerHTML = `<div style="padding:10px;color:#d93025;font-size:12px">加载失败：${e.message}</div>`;
  }
}

function selectDsYear(year) {
  dsState.year = year;
  dsState.month = '';
  dsState.sessions = [];
  dsState.sessionId = '';

  document.querySelectorAll('#ds-year-nav .ds-nav-btn').forEach(b =>
    b.classList.toggle('active', b.textContent === year)
  );

  document.getElementById('ds-session-list').textContent = '';
  const hint = document.createElement('div');
  hint.style.cssText = 'padding:20px;color:var(--text-secondary);font-size:13px;text-align:center';
  hint.textContent = '选择月份查看对话';
  document.getElementById('ds-session-list').appendChild(hint);

  document.getElementById('main-body').textContent = '';
  const empty = document.createElement('div');
  empty.className = 'empty-main';
  empty.textContent = '← 选择一条对话查看详情';
  document.getElementById('main-body').appendChild(empty);
  document.getElementById('main-header').style.display = 'none';

  // 直接从缓存读取，不再请求
  if (dsStructureCache && dsStructureCache.years && dsStructureCache.years[year]) {
    renderDsMonths(dsStructureCache.years[year]);
  }
}

function renderDsMonths(months) {
  const monthNav = document.getElementById('ds-month-nav');
  monthNav.style.display = 'flex';
  monthNav.innerHTML = months.map(m => {
    const active = dsState.month === m;
    const num = m.slice(0, 2);  // "01_January" → "01"
    return `<button class="ds-nav-btn ds-month-btn${active ? ' active' : ''}" onclick="selectDsMonth('${dsState.year}', '${m}')">${num}月</button>`;
  }).join('');
}

// ============================================================
// DeepSeek — 对话列表
// ============================================================

async function selectDsMonth(year, month) {
  dsState.month = month;
  dsState.sessionId = '';

  document.querySelectorAll('#ds-month-nav .ds-nav-btn').forEach(b =>
    b.classList.toggle('active', b.textContent === month.slice(0, 2) + '月')
  );

  const list = document.getElementById('ds-session-list');
  list.textContent = '';
  const loadingEl = document.createElement('div');
  loadingEl.className = 'loading';
  loadingEl.style.cssText = 'padding:20px';
  loadingEl.textContent = '加载中';
  list.appendChild(loadingEl);

  document.getElementById('main-body').textContent = '';
  const emptyMsg = document.createElement('div');
  emptyMsg.className = 'empty-main';
  emptyMsg.textContent = '← 选择一条对话查看详情';
  document.getElementById('main-body').appendChild(emptyMsg);
  document.getElementById('main-header').style.display = 'none';
  document.getElementById('copy-btn-wrap').style.display = 'none';

  try {
    const data = await deepseekGetSessions(year, month);
    dsState.sessions = data.sessions || [];

    if (dsState.sessions.length === 0) {
      list.textContent = '';
      const empty = document.createElement('div');
      empty.style.cssText = 'padding:20px;color:var(--text-secondary);font-size:13px;text-align:center';
      empty.textContent = '该月暂无对话';
      list.appendChild(empty);
      return;
    }

    renderDsSessionList(list, dsState.sessions);
  } catch (e) {
    list.textContent = '';
    const err = document.createElement('div');
    err.style.cssText = 'padding:20px;color:#d93025;font-size:13px';
    err.textContent = '加载失败：' + e.message;
    list.appendChild(err);
  }
}

// ============================================================
// DeepSeek — 查看单条对话
// ============================================================

async function selectDsSession(sessionId) {
  dsState.sessionId = sessionId;

  // 局部更新选中样式：用 dataset 查，不走全量 querySelectorAll
  const prevActive = document.querySelector('.ds-session-item.active');
  if (prevActive) prevActive.classList.remove('active');
  const newActive = document.querySelector(`.ds-session-item[data-id="${sessionId}"]`);
  if (newActive) newActive.classList.add('active');

  const mainBody = document.getElementById('main-body');
  mainBody.textContent = '';
  const loadingEl = document.createElement('div');
  loadingEl.className = 'loading';
  loadingEl.style.cssText = 'padding:40px';
  loadingEl.textContent = '加载中';
  mainBody.appendChild(loadingEl);

  try {
    const data = await deepseekGetContent(sessionId);
    renderDsContent(data);
  } catch (e) {
    mainBody.textContent = '';
    const err = document.createElement('div');
    err.className = 'empty-main';
    err.textContent = '加载失败：' + e.message;
    mainBody.appendChild(err);
  }
}

// ============================================================
// DeepSeek — Markdown 渲染
// ============================================================

function renderDsContent(data) {
  const { content } = data;
  dsRawContent = content || '';

  document.getElementById('h-key').textContent = data.filename || '';
  document.getElementById('h-channel').textContent = 'DeepSeek';
  document.getElementById('h-count').textContent = '';
  document.getElementById('main-header').style.display = 'flex';
  document.getElementById('copy-btn-wrap').style.display = 'inline';

  const mainBody = document.getElementById('main-body');

  if (!content) {
    mainBody.innerHTML = '<div class="empty-main">无内容</div>';
    return;
  }

  const html = renderDsMarkdown(content);
  mainBody.innerHTML = `<div class="ds-content">${html}</div>`;
}

function copyDsContent() {
  if (!dsRawContent) {
    return;
  }
  const btn = document.getElementById('copy-btn');
  const orig = btn.textContent;

  try {
    // 直接使用 textarea 方案，兼容 HTTP 环境
    const ta = document.createElement('textarea');
    ta.value = dsRawContent;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    ta.style.top = '-9999px';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    ta.setSelectionRange(0, dsRawContent.length);
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);

    if (ok) {
      btn.textContent = '✅ 已复制';
    } else {
      btn.textContent = '❌ 复制失败';
    }
  } catch (e) {
    btn.textContent = '❌ 复制失败';
  }
  setTimeout(() => { btn.textContent = orig; }, 1500);
}

function renderDsMarkdown(text) {
  // 1. 转义 HTML
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // 2. 代码块 (```) — 必须在其他转换之前
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const langClass = lang ? ` class="lang-${escapeHtml(lang)}"` : '';
    return `<pre${langClass}><code>${code.trim()}</code></pre>`;
  });

  // 3. 行内代码 (`code`)
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // 4. 图片
  html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" style="max-width:100%">');

  // 5. 链接
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  // 6. 分割线
  html = html.replace(/^---$/gm, '<hr>');

  // 7. 表格
  html = html.replace(/^\|(.+)\|$/gm, (line) => {
    return '<tr>' + line.slice(1, -1).split('|').map(c => `<td>${c.trim()}</td>`).join('') + '</tr>';
  });

  // 8. 加粗
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

  // 9. 斜体
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // 10. 标题 (h1-h4)
  html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // 11. 块引用
  html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');

  // 12. 段落：双换行分割
  const blocks = html.split(/\n{2,}/);
  html = blocks.map(block => {
    block = block.trim();
    if (!block) return '';
    // 已经是块级元素
    if (/^<\//.test(block) || /^<(h[1-4]|pre|blockquote|hr|table|ul|ol|li|tr|img)/.test(block)) {
      return block;
    }
    return `<p>${block}</p>`;
  }).join('\n');

  // 13. 修复嵌套的 <p>（块引用、pre 里面不要包 p）
  html = html.replace(/<blockquote><p>/g, '<blockquote>');
  html = html.replace(/<\/p><\/blockquote>/g, '</blockquote>');
  html = html.replace(/<pre><p>/g, '<pre>');
  html = html.replace(/<\/p><\/pre>/g, '</pre>');

  // 14. 单行换行转 <br>
  html = html.replace(/\n/g, '<br>');

  return html;
}


// ============================================================
// DeepSeek — 搜索
// ============================================================

let dsSearchMode = 'title';

function dsSetMode(mode) {
  dsSearchMode = mode;
  document.querySelectorAll('.ds-mode-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.mode === mode);
  });
  // 聚焦搜索框方便直接输入
  document.getElementById('ds-search-input').focus();
}

function dsSearchKeydown(e) {
  if (e.key === 'Enter') {
    dsSearch();
  }
}

async function dsSearch() {
  const input = document.getElementById('ds-search-input');
  const q = input.value.trim();
  const status = document.getElementById('ds-search-status');

  if (!q) {
    status.textContent = '请输入关键词';
    status.style.display = 'block';
    return;
  }

  status.style.display = 'none';

  const list = document.getElementById('ds-session-list');
  list.innerHTML = '<div class="loading" style="padding:20px">搜索中</div>';

  try {
    const data = await deepseekSearch(q, dsSearchMode);
    renderDsSearchResults(data);
  } catch (e) {
    list.innerHTML = `<div style="padding:20px;color:#d93025;font-size:13px">搜索失败：${e.message}</div>`;
  }
}

function renderDsSearchResults(data) {
  const list = document.getElementById('ds-session-list');
  const { results, count, mode } = data;

  // 隐藏年月导航显示搜索结果
  document.getElementById('ds-year-nav').style.display = 'none';
  document.getElementById('ds-month-nav').style.display = 'none';

  if (count === 0) {
    list.innerHTML = `
      <div style="padding:16px;text-align:center">
        <div style="font-size:13px;color:var(--text-secondary);margin-bottom:8px">未找到匹配的对话</div>
        <button class="ds-nav-btn" onclick="dsClearSearch()">← 返回浏览</button>
      </div>
    `;
    return;
  }

  const header = `
    <div style="padding:8px 4px 6px;font-size:12px;color:var(--text-secondary);display:flex;justify-content:space-between">
      <span>🔍 找到 ${count} 条结果${mode === 'full' ? '（全文搜索）' : ''}</span>
      <button class="ds-nav-btn" style="padding:2px 8px;font-size:11px" onclick="dsClearSearch()">← 返回浏览</button>
    </div>
  `;

  const items = results.map(s =>
    `<div class="ds-session-item" data-id="${escapeHtml(s.id)}" onclick="selectDsSession('${escapeHtml(s.id)}')">
      <div class="ds-session-title">
        <span>${escapeHtml(s.title)}</span>
        ${s.message_count ? `<span class="ds-session-msg-count">${s.message_count}条</span>` : ''}
      </div>
      <div class="ds-session-meta">
        <span>📅 ${s.date}</span>
        ${s.model ? `<span>🤖 ${escapeHtml(s.model)}</span>` : ''}
      </div>
      ${s.snippet ? `<div class="ds-snippet">${escapeHtml(s.snippet)}</div>` : ''}
    </div>`
  ).join('');

  list.innerHTML = header + items;
}

function dsClearSearch() {
  document.getElementById('ds-search-input').value = '';
  document.getElementById('ds-search-status').style.display = 'none';

  // 恢复年月导航
  document.getElementById('ds-year-nav').style.display = 'flex';
  // 重新加载结构
  loadDsStructure();
  // 清空结果恢复默认提示
  document.getElementById('ds-session-list').innerHTML =
    '<div style="padding:20px;color:var(--text-secondary);font-size:13px;text-align:center">← 选择年月查看对话</div>';
  document.getElementById('main-body').innerHTML =
    '<div class="empty-main">← 选择一条对话查看详情</div>';
  document.getElementById('main-header').style.display = 'none';
  document.getElementById('copy-btn-wrap').style.display = 'none';
}

