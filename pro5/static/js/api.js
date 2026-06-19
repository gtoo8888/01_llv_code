// API 调用封装
const BASE = '/api';

async function apiGet(path) {
  const res = await fetch(BASE + path);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// 获取会话列表
async function getSessions() {
  return apiGet('/sessions');
}

// 获取某会话的消息
async function getSessionMessages(sessionKey) {
  return apiGet(`/sessions/${encodeURIComponent(sessionKey)}/messages`);
}

// ═══════════════════════════════════════════════
// DeepSeek API
// ═══════════════════════════════════════════════

async function deepseekGetStructure() {
  return apiGet('/deepseek/structure');
}

async function deepseekGetSessions(year, month) {
  return apiGet(`/deepseek/sessions?year=${encodeURIComponent(year)}&month=${encodeURIComponent(month)}`);
}

async function deepseekGetContent(sessionId) {
  return apiGet(`/deepseek/sessions/${encodeURIComponent(sessionId)}`);
}

async function deepseekSearch(q, mode) {
  return apiGet(`/deepseek/search?q=${encodeURIComponent(q)}&mode=${encodeURIComponent(mode)}`);
}

async function deepseekGetSessionsByDate(date) {
  return apiGet(`/deepseek/sessions-by-date?date=${encodeURIComponent(date)}`);
}

async function deepseekGetDates(year, month) {
  return apiGet(`/deepseek/dates?year=${encodeURIComponent(year)}&month=${encodeURIComponent(month)}`);
}

async function deepseekGetStats() {
  return apiGet('/deepseek/stats');
}
