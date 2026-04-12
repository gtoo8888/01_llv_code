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
