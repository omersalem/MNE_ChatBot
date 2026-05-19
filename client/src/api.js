const API_BASE = '';

let adminToken = localStorage.getItem('admin_token') || '';

export function setAdminToken(token) {
  adminToken = token;
  if (token) {
    localStorage.setItem('admin_token', token);
  } else {
    localStorage.removeItem('admin_token');
  }
}

export function getAdminToken() {
  return adminToken;
}

async function request(method, path, body = null) {
  const headers = { 'Content-Type': 'application/json' };
  if (adminToken) {
    headers['X-Admin-Token'] = adminToken;
  }

  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Request failed');
  return data;
}

export const api = {
  // Auth
  login: (password) => request('POST', '/api/auth/login', { password }),
  logout: () => request('POST', '/api/auth/logout'),
  checkAuth: () => request('GET', '/api/auth/check'),

  // Config
  getConfig: () => request('GET', '/api/config'),
  setProvider: (provider) => request('POST', '/api/config/provider', { provider }),
  setModel: (model) => request('POST', '/api/config/model', { model }),
  getModels: (provider) => request('GET', `/api/config/models/${provider}`),

  // API Keys
  getApiKeys: () => request('GET', '/api/config/api-keys'),
  saveApiKey: (provider, apiKey) => request('POST', '/api/config/api-keys', { provider, api_key: apiKey }),

  // Chat
  getSuggestedQuestions: () => request('GET', '/api/suggested-questions'),
  getGroups: () => request('GET', '/api/groups'),

  // Admin
  getDocuments: () => request('GET', '/admin/api/documents'),
  getStats: () => request('GET', '/admin/api/stats'),
  getHealth: () => request('GET', '/admin/api/health'),
  reindexAll: () => request('POST', '/admin/api/reindex-all'),
  reindexDocument: (filename) => request('POST', `/admin/api/documents/${encodeURIComponent(filename)}/reindex`),
  deleteDocument: (filename) => request('DELETE', `/admin/api/documents/${encodeURIComponent(filename)}`),
  getGroupsAdmin: () => request('GET', '/admin/api/groups'),
  createGroup: (payload) => request('POST', '/admin/api/groups', payload),
  updateGroup: (groupId, payload) => request('PUT', `/admin/api/groups/${encodeURIComponent(groupId)}`, payload),
  deleteGroup: (groupId) => request('DELETE', `/admin/api/groups/${encodeURIComponent(groupId)}`),
  getGroupDocuments: () => request('GET', '/admin/api/groups/documents'),
};
