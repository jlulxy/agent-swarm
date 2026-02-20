/**
 * 认证相关 API 调用封装
 */

const API_BASE = '/api/auth';

export interface AuthUser {
  user_id: string;
  username: string;
  display_name: string;
  created_at: string;
}

export interface AuthResponse {
  token: string;
  user: AuthUser;
}

export type UserResponse = AuthUser;

/**
 * 获取存储的 Token
 */
export function getStoredToken(): string | null {
  return localStorage.getItem('eac_token');
}

/**
 * 存储 Token
 */
export function storeToken(token: string): void {
  localStorage.setItem('eac_token', token);
}

/**
 * 清除 Token
 */
export function clearToken(): void {
  localStorage.removeItem('eac_token');
}

/**
 * 获取 Authorization Header
 */
export function getAuthHeader(): Record<string, string> {
  const token = getStoredToken();
  if (token) {
    return { 'Authorization': `Bearer ${token}` };
  }
  return {};
}

/**
 * 用户登录
 */
export async function login(username: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || data.message || '登录失败');
  }

  return data;
}

/**
 * 用户注册
 */
export async function register(
  username: string,
  password: string,
  displayName?: string
): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username,
      password,
      display_name: displayName || username,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || data.message || '注册失败');
  }

  return data;
}

/**
 * 获取当前用户信息
 */
export async function getMe(token: string): Promise<UserResponse> {
  const response = await fetch(`${API_BASE}/me`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || data.message || '获取用户信息失败');
  }

  return data;
}

/**
 * 更新用户信息
 */
export async function updateMe(
  token: string,
  updates: { display_name?: string }
): Promise<UserResponse> {
  const response = await fetch(`${API_BASE}/me`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(updates),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || data.message || '更新用户信息失败');
  }

  return data;
}
