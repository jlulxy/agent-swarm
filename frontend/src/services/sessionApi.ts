/**
 * Session API 服务
 * 
 * 提供与后端 Session 相关的 API 调用
 */

import { getAuthHeader } from '../auth/api';

export interface SessionData {
  session_id: string;
  task: string;
  status: string;
  provider: string;
  model?: string;
  mode?: string;  // emergent(涌现模式) / direct(普通模式)
  plan?: any;
  final_report?: string;
  error?: string;
  created_at: string;
  updated_at?: string;
  last_active_at: string;
  has_agent?: boolean;
  is_active_in_memory?: boolean;
  metadata?: Record<string, any>;
}

export interface SessionListResponse {
  success: boolean;
  message: string;
  data: {
    sessions: SessionData[];
    total: number;
    limit: number;
    offset: number;
    stats: {
      active_sessions: number;
      active_agents: number;
      max_sessions: number;
      timeout_minutes: number;
      has_repository: boolean;
      db_total_sessions?: number;
      db_active_sessions?: number;
      db_completed_sessions?: number;
    };
  };
}

export interface SessionDetailResponse {
  success: boolean;
  message: string;
  data: SessionData;
}

export interface AgentData {
  agent_id: string;
  session_id: string;
  name: string;
  role_name: string;
  role_description: string;
  capabilities: string[];
  task_segment: string;
  status: string;
  progress: number;
  current_step: string;
  iterations: number;
  thinking: string;
  work_objective?: string;
  deliverables: string[];
  methodology?: string;
  created_at: string;
  updated_at: string;
}

export interface RelayMessageData {
  message_id: string;
  station_id: string;
  session_id: string;
  relay_type: string;
  source_agent_id: string;
  source_agent_name: string;
  target_agent_ids: string[];
  content: string;
  importance: number;
  viewed_by: string[];
  acknowledged_by: string[];
  timestamp: string;
}

export interface InterventionData {
  intervention_id: string;
  session_id: string;
  intervention_type: string;
  scope: string;
  target_agent_id?: string;
  target_agent_ids: string[];
  payload?: any;
  reason: string;
  priority: number;
  timestamp: string;
}

const API_BASE = '/api';

/**
 * 获取会话列表
 */
export async function fetchSessions(options?: {
  status?: string;
  source?: 'memory' | 'db';
  limit?: number;
  offset?: number;
}): Promise<SessionListResponse> {
  const params = new URLSearchParams();
  
  if (options?.status) params.append('status', options.status);
  if (options?.source) params.append('source', options.source);
  if (options?.limit) params.append('limit', options.limit.toString());
  if (options?.offset) params.append('offset', options.offset.toString());
  
  const response = await fetch(`${API_BASE}/sessions?${params.toString()}`, {
    headers: { ...getAuthHeader() },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch sessions: ${response.status}`);
  }
  
  return response.json();
}

/**
 * 获取单个会话详情
 */
export async function fetchSessionDetail(sessionId: string): Promise<SessionDetailResponse> {
  const response = await fetch(`${API_BASE}/session/${sessionId}`, {
    headers: { ...getAuthHeader() },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch session: ${response.status}`);
  }
  
  return response.json();
}

/**
 * 获取会话的 Agent 列表
 */
export async function fetchSessionAgents(sessionId: string): Promise<{
  success: boolean;
  message: string;
  data: { agents: AgentData[] };
}> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/agents`, {
    headers: { ...getAuthHeader() },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch agents: ${response.status}`);
  }
  
  return response.json();
}

/**
 * 获取会话的中继消息历史
 */
export async function fetchSessionRelayHistory(
  sessionId: string,
  limit: number = 100
): Promise<{
  success: boolean;
  message: string;
  data: { messages: RelayMessageData[] };
}> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/relay-history?limit=${limit}`, {
    headers: { ...getAuthHeader() },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch relay history: ${response.status}`);
  }
  
  return response.json();
}

/**
 * 获取会话的干预历史
 */
export async function fetchSessionInterventions(
  sessionId: string,
  limit: number = 50
): Promise<{
  success: boolean;
  message: string;
  data: { interventions: InterventionData[] };
}> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/interventions?limit=${limit}`, {
    headers: { ...getAuthHeader() },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch interventions: ${response.status}`);
  }
  
  return response.json();
}

/**
 * 关闭会话
 */
export async function closeSession(sessionId: string): Promise<{
  success: boolean;
  message: string;
}> {
  const response = await fetch(`${API_BASE}/session/${sessionId}`, {
    method: 'DELETE',
    headers: { ...getAuthHeader() },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to close session: ${response.status}`);
  }
  
  return response.json();
}

/**
 * 获取统计信息
 */
export async function fetchStats(): Promise<{
  success: boolean;
  message: string;
  data: {
    active_sessions: number;
    active_agents: number;
    max_sessions: number;
    timeout_minutes: number;
    has_repository: boolean;
    db_total_sessions?: number;
    db_active_sessions?: number;
    db_completed_sessions?: number;
  };
}> {
  const response = await fetch(`${API_BASE}/stats`, {
    headers: { ...getAuthHeader() },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch stats: ${response.status}`);
  }
  
  return response.json();
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<{
  status: string;
  service: string;
  version: string;
  session_manager_stats: any;
}> {
  const response = await fetch(`${API_BASE}/health`, {
    headers: { ...getAuthHeader() },
  });
  
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  
  return response.json();
}

/**
 * 获取会话的实时状态（仅适用于内存中活跃的会话）
 * 
 * 用于切换到运行中的会话时恢复完整状态
 */
export async function fetchSessionLiveState(sessionId: string): Promise<{
  success: boolean;
  message: string;
  data: {
    is_live: boolean;
    session_id: string;
    task?: string;
    status?: string;
    plan?: any;
    agents: Array<{
      agent_id: string;
      name: string;
      role_name: string;
      role_description: string;
      capabilities: string[];
      task_segment: string;
      status: string;
      progress: number;
      current_step: string;
      iterations: number;
      thinking: string;
      work_objective?: string;
      deliverables: string[];
      methodology?: string;
    }>;
    relay_stations: Array<{
      station_id: string;
      name: string;
      phase: number;
      participating_agents: string[];
      is_active: boolean;
      messages: Array<{
        message_id: string;
        station_id: string;
        source_agent_id: string;
        source_agent_name: string;
        target_agent_ids: string[];
        relay_type: string;
        content: string;
        importance: number;
        timestamp: string;
        viewed_by: string[];
        acknowledged_by: string[];
      }>;
    }>;
    // 消息历史（Master Agent 的任务分析、思考过程等）
    messages?: Array<{
      message_id: string;
      session_id: string;
      role: string;
      content: string;
      timestamp: string;
    }>;
    total_messages: number;
  };
}> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/live-state`, {
    headers: { ...getAuthHeader() },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch live state: ${response.status}`);
  }
  
  return response.json();
}

/**
 * 检查会话是否还在运行中（轻量级检查）
 * 
 * 用于决定是否使用 SSE 订阅还是直接加载快照
 * 
 * 关键：必须检查会话是否有活跃的 Agent 实例（has_agent），
 * 而不只是订阅者数量，因为订阅者端点总是返回 200
 */
export async function checkSessionIsLive(sessionId: string): Promise<{
  success: boolean;
  is_live: boolean;
  has_agent?: boolean;
  subscriber_count?: number;
}> {
  try {
    // 首先获取会话详情，检查是否有活跃的 Agent
    const detailResponse = await fetch(`${API_BASE}/session/${sessionId}`, {
      headers: { ...getAuthHeader() },
    });
    
    if (!detailResponse.ok) {
      // 会话不存在
      if (detailResponse.status === 404) {
        return { success: true, is_live: false };
      }
      throw new Error(`Failed to check session status: ${detailResponse.status}`);
    }
    
    const detailData = await detailResponse.json();
    
    // 关键判断：会话必须满足以下条件才算 "live"
    // 1. 状态为 active
    // 2. has_agent 为 true（内存中有 Agent 实例）
    const hasActiveAgent = detailData.data?.has_agent === true;
    const statusIsActive = detailData.data?.status === 'active';
    const isLive = hasActiveAgent && statusIsActive;
    
    // 获取订阅者数量（可选）
    let subscriberCount = 0;
    try {
      const subResponse = await fetch(`${API_BASE}/session/${sessionId}/subscribers`, {
        headers: { ...getAuthHeader() },
      });
      if (subResponse.ok) {
        const subData = await subResponse.json();
        subscriberCount = subData.data?.subscriber_count ?? 0;
      }
    } catch {
      // 忽略订阅者查询错误
    }
    
    return {
      success: true,
      is_live: isLive,
      has_agent: hasActiveAgent,
      subscriber_count: subscriberCount,
    };
  } catch (err) {
    console.error('[sessionApi] checkSessionIsLive error:', err);
    return { success: false, is_live: false };
  }
}
