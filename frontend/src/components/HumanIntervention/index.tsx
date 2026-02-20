/**
 * 人工干预接口组件
 * 
 * 允许用户暂停、调整、重启某个 Agent
 */

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Settings,
  Pause,
  Play,
  Square,
  Syringe,
  AlertTriangle,
  Send,
} from 'lucide-react';
import { useStore } from '../../store';
import { useAgui } from '../../hooks/useAgui';
import { AgentStatus } from '../../types/agui';
import { cn } from '../../utils/cn';

export function HumanIntervention() {
  const { agents, sessionId, status } = useStore();
  const { intervene } = useAgui();
  
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [injectText, setInjectText] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const agentList = Object.values(agents);
  const selectedAgent = selectedAgentId ? agents[selectedAgentId] : null;

  // 【会话隔离】当会话切换时，清除选中的 Agent
  // 因为不同会话的 Agent 是独立的
  useEffect(() => {
    // 如果当前选中的 Agent 不在新会话的 agents 列表中，清除选择
    if (selectedAgentId && !agents[selectedAgentId]) {
      console.log(`[HumanIntervention] Clearing selected agent ${selectedAgentId} - not in current session`);
      setSelectedAgentId(null);
    }
  }, [sessionId, agents, selectedAgentId]);

  const handleIntervention = async (type: 'pause' | 'resume' | 'cancel') => {
    if (!sessionId) return;
    setIsLoading(true);
    try {
      await intervene(sessionId, type, selectedAgentId || undefined);
    } finally {
      setIsLoading(false);
    }
  };

  const handleInject = async () => {
    if (!sessionId || !selectedAgentId || !injectText.trim()) return;
    setIsLoading(true);
    try {
      await intervene(sessionId, 'inject', selectedAgentId, {
        information: injectText.trim(),
      });
      setInjectText('');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePauseAll = async () => {
    if (!sessionId) return;
    setIsLoading(true);
    try {
      await intervene(sessionId, 'pause');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResumeAll = async () => {
    if (!sessionId) return;
    setIsLoading(true);
    try {
      await intervene(sessionId, 'resume');
    } finally {
      setIsLoading(false);
    }
  };

  const isTaskActive = status === AgentStatus.RUNNING || status === AgentStatus.PLANNING;

  return (
    <div className="h-full flex flex-col">
      {/* 头部 */}
      <div className="flex-shrink-0 p-4 border-b border-dark-700">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Settings className="w-5 h-5 text-purple-400" />
          人工干预
        </h2>
      </div>

      {/* 内容 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* 全局控制 */}
        <div className="p-4 rounded-xl bg-dark-800/50 border border-dark-700">
          <h3 className="text-sm font-medium text-white mb-3">全局控制</h3>
          <div className="flex gap-2">
            <button
              onClick={handlePauseAll}
              disabled={!isTaskActive || isLoading}
              className={cn(
                'flex-1 py-2 px-3 rounded-lg text-sm font-medium',
                'flex items-center justify-center gap-2 transition-colors',
                isTaskActive
                  ? 'bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30'
                  : 'bg-dark-700 text-dark-500 cursor-not-allowed'
              )}
            >
              <Pause className="w-4 h-4" />
              全部暂停
            </button>
            <button
              onClick={handleResumeAll}
              disabled={!isTaskActive || isLoading}
              className={cn(
                'flex-1 py-2 px-3 rounded-lg text-sm font-medium',
                'flex items-center justify-center gap-2 transition-colors',
                isTaskActive
                  ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
                  : 'bg-dark-700 text-dark-500 cursor-not-allowed'
              )}
            >
              <Play className="w-4 h-4" />
              全部继续
            </button>
          </div>
        </div>

        {/* 选择 Agent */}
        <div className="p-4 rounded-xl bg-dark-800/50 border border-dark-700">
          <h3 className="text-sm font-medium text-white mb-3">选择 Agent</h3>
          {agentList.length === 0 ? (
            <p className="text-sm text-dark-400">暂无 Agent</p>
          ) : (
            <div className="space-y-2">
              {agentList.map((agent) => (
                <button
                  key={agent.id}
                  onClick={() => setSelectedAgentId(
                    selectedAgentId === agent.id ? null : agent.id
                  )}
                  className={cn(
                    'w-full p-3 rounded-lg text-left transition-colors',
                    'flex items-center justify-between',
                    selectedAgentId === agent.id
                      ? 'bg-primary-500/20 border border-primary-500/50'
                      : 'bg-dark-700/50 border border-transparent hover:bg-dark-700'
                  )}
                >
                  <div>
                    <p className="text-sm font-medium text-white">{agent.name}</p>
                    <p className="text-xs text-dark-400">{agent.status}</p>
                  </div>
                  <div className={cn(
                    'w-2 h-2 rounded-full',
                    agent.status === AgentStatus.RUNNING && 'bg-green-500',
                    agent.status === AgentStatus.PAUSED && 'bg-yellow-500',
                    agent.status === AgentStatus.COMPLETED && 'bg-cyan-500',
                    agent.status === AgentStatus.FAILED && 'bg-red-500',
                  )} />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Agent 控制 */}
        {selectedAgent && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 rounded-xl bg-dark-800/50 border border-dark-700"
          >
            <h3 className="text-sm font-medium text-white mb-3">
              控制 {selectedAgent.name}
            </h3>
            
            <div className="space-y-3">
              {/* 操作按钮 */}
              <div className="flex gap-2">
                {selectedAgent.status === AgentStatus.RUNNING ? (
                  <button
                    onClick={() => handleIntervention('pause')}
                    disabled={isLoading}
                    className="flex-1 py-2 px-3 rounded-lg bg-yellow-500/20 text-yellow-400 
                               hover:bg-yellow-500/30 text-sm font-medium transition-colors
                               flex items-center justify-center gap-2"
                  >
                    <Pause className="w-4 h-4" />
                    暂停
                  </button>
                ) : selectedAgent.status === AgentStatus.PAUSED ? (
                  <button
                    onClick={() => handleIntervention('resume')}
                    disabled={isLoading}
                    className="flex-1 py-2 px-3 rounded-lg bg-green-500/20 text-green-400 
                               hover:bg-green-500/30 text-sm font-medium transition-colors
                               flex items-center justify-center gap-2"
                  >
                    <Play className="w-4 h-4" />
                    继续
                  </button>
                ) : null}
                
                <button
                  onClick={() => handleIntervention('cancel')}
                  disabled={
                    isLoading ||
                    selectedAgent.status === AgentStatus.COMPLETED ||
                    selectedAgent.status === AgentStatus.CANCELLED
                  }
                  className="py-2 px-3 rounded-lg bg-red-500/20 text-red-400 
                             hover:bg-red-500/30 text-sm font-medium transition-colors
                             flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  <Square className="w-4 h-4" />
                  取消
                </button>
              </div>

              {/* 注入信息 */}
              <div>
                <label className="flex items-center gap-2 text-sm text-dark-300 mb-2">
                  <Syringe className="w-4 h-4" />
                  注入信息
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={injectText}
                    onChange={(e) => setInjectText(e.target.value)}
                    placeholder="输入要注入的信息..."
                    className="flex-1 px-3 py-2 rounded-lg bg-dark-900 border border-dark-600
                               text-sm text-white placeholder-dark-500
                               focus:outline-none focus:border-primary-500"
                  />
                  <button
                    onClick={handleInject}
                    disabled={isLoading || !injectText.trim()}
                    className="px-3 py-2 rounded-lg bg-primary-500 text-white
                               hover:bg-primary-600 transition-colors disabled:opacity-50
                               flex items-center justify-center"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* 警告 */}
        <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/30">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-yellow-400">注意</p>
              <p className="text-xs text-yellow-400/80 mt-1">
                人工干预可能会影响 Agent 的执行结果。请谨慎操作。
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
