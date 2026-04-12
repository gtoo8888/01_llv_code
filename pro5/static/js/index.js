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
  document.querySelectorAll('.conv-item').forEach(el => {
    el.classList.toggle('active', el.dataset.key === sessionKey);
  });

  const mainBody = document.getElementById('main-body');
  mainBody.innerHTML = '<div class="loading" style="padding:40px">加载中</div>';

  try {
    const data = await getSessionMessages(sessionKey);
    renderConversation(data);
  } catch (e) {
    mainBody.innerHTML = `<div class="empty-main">加载失败：${e.message}</div>`;
  }
}

// 渲染会话消息
function renderConversation(data) {
  const { session_key, channel, messages } = data;

  document.getElementById('h-key').textContent = session_key;
  document.getElementById('h-channel').textContent = channel;
  document.getElementById('h-count').textContent = messages.length;
  document.getElementById('main-header').style.display = 'flex';

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

function toggleExpand(btn) {
  const contentEl = btn.previousElementSibling;
  const isExpanded = contentEl.classList.contains('expanded');
  if (isExpanded) {
    const raw = contentEl.dataset.raw;
    const short = raw.slice(0, 400) + '\n...';
    contentEl.textContent = short;
    contentEl.classList.remove('expanded');
    btn.textContent = '展开 ▼';
  } else {
    contentEl.textContent = contentEl.dataset.raw;
    contentEl.classList.add('expanded');
    btn.textContent = '收起 ▲';
  }
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

// 初始化
loadSessions();
