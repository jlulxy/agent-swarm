/**
 * 登录/注册页面
 *
 * Cyberpunk 深色主题 + 毛玻璃效果
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Eye, EyeOff, Sparkles, LogIn, UserPlus, Loader2 } from 'lucide-react';
import { useAuth } from './AuthProvider';

type TabMode = 'login' | 'register';

export function LoginPage() {
  const { login, register } = useAuth();

  const [mode, setMode] = useState<TabMode>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!username.trim() || !password.trim()) {
      setError('请填写用户名和密码');
      return;
    }

    if (mode === 'register' && password.length < 6) {
      setError('密码长度至少为 6 位');
      return;
    }

    setIsSubmitting(true);
    try {
      if (mode === 'login') {
        await login(username.trim(), password);
      } else {
        await register(username.trim(), password, displayName.trim() || undefined);
      }
    } catch (err: any) {
      setError(err.message || '操作失败，请重试');
    } finally {
      setIsSubmitting(false);
    }
  };

  const switchMode = (newMode: TabMode) => {
    setMode(newMode);
    setError('');
  };

  return (
    <div className="min-h-screen bg-[#0F172A] flex items-center justify-center relative overflow-hidden">
      {/* 背景装饰 */}
      <div className="absolute inset-0 pointer-events-none">
        {/* 网格纹理 */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `
              linear-gradient(rgba(99, 102, 241, 0.5) 1px, transparent 1px),
              linear-gradient(90deg, rgba(99, 102, 241, 0.5) 1px, transparent 1px)
            `,
            backgroundSize: '60px 60px',
          }}
        />
        {/* 光晕 */}
        <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] rounded-full bg-[#6366F1]/10 blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] rounded-full bg-[#8B5CF6]/8 blur-[100px]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px] rounded-full bg-[#A78BFA]/5 blur-[80px]" />
      </div>

      {/* 登录卡片 */}
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="relative z-10 w-full max-w-md mx-4"
      >
        {/* 品牌区域 */}
        <div className="flex flex-col items-center mb-8">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
            className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#6366F1] to-[#8B5CF6] flex items-center justify-center mb-4 shadow-lg shadow-[#6366F1]/30"
          >
            <Sparkles className="w-8 h-8 text-white" />
          </motion.div>
          <h1 className="text-2xl font-bold text-[#F8FAFC] tracking-tight">
            Agent Swarm
          </h1>
          <p className="text-sm text-[#64748B] mt-1">角色涌现 × 3D编排 × AG-UI</p>
        </div>

        {/* 卡片主体 */}
        <div
          className="rounded-2xl border border-white/[0.08] overflow-hidden"
          style={{
            background: 'rgba(30, 41, 59, 0.6)',
            backdropFilter: 'blur(24px)',
            boxShadow: '0 0 40px rgba(99, 102, 241, 0.08), 0 25px 50px -12px rgba(0, 0, 0, 0.5)',
          }}
        >
          {/* Tab 切换 */}
          <div className="flex border-b border-white/[0.06]">
            {[
              { key: 'login' as TabMode, label: '登录', icon: LogIn },
              { key: 'register' as TabMode, label: '注册', icon: UserPlus },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = mode === tab.key;
              return (
                <button
                  key={tab.key}
                  onClick={() => switchMode(tab.key)}
                  className={`
                    flex-1 py-4 px-4 text-sm font-medium transition-all duration-200
                    flex items-center justify-center gap-2 relative cursor-pointer
                    ${isActive
                      ? 'text-[#A78BFA]'
                      : 'text-[#64748B] hover:text-[#94A3B8]'
                    }
                  `}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                  {isActive && (
                    <motion.div
                      layoutId="tab-indicator"
                      className="absolute bottom-0 left-0 right-0 h-[2px] bg-gradient-to-r from-[#6366F1] to-[#8B5CF6]"
                    />
                  )}
                </button>
              );
            })}
          </div>

          {/* 表单 */}
          <form onSubmit={handleSubmit} className="p-6 space-y-5">
            <AnimatePresence mode="wait">
              <motion.div
                key={mode}
                initial={{ opacity: 0, x: mode === 'login' ? -10 : 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: mode === 'login' ? 10 : -10 }}
                transition={{ duration: 0.2 }}
                className="space-y-4"
              >
                {/* 用户名 */}
                <div className="space-y-1.5">
                  <label className="block text-xs font-medium text-[#94A3B8] uppercase tracking-wider">
                    用户名
                  </label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="输入用户名"
                    autoComplete="username"
                    className="
                      w-full px-4 py-3 rounded-xl text-sm text-[#F8FAFC]
                      bg-[#0F172A]/60 border border-white/[0.08]
                      outline-none transition-all duration-200
                      placeholder:text-[#475569]
                      focus:border-[#6366F1]/50 focus:ring-1 focus:ring-[#6366F1]/20
                      focus:shadow-[0_0_20px_rgba(99,102,241,0.1)]
                    "
                  />
                </div>

                {/* 密码 */}
                <div className="space-y-1.5">
                  <label className="block text-xs font-medium text-[#94A3B8] uppercase tracking-wider">
                    密码
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder={mode === 'register' ? '至少 6 位字符' : '输入密码'}
                      autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                      className="
                        w-full px-4 py-3 pr-12 rounded-xl text-sm text-[#F8FAFC]
                        bg-[#0F172A]/60 border border-white/[0.08]
                        outline-none transition-all duration-200
                        placeholder:text-[#475569]
                        focus:border-[#6366F1]/50 focus:ring-1 focus:ring-[#6366F1]/20
                        focus:shadow-[0_0_20px_rgba(99,102,241,0.1)]
                      "
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-[#475569] hover:text-[#94A3B8] transition-colors cursor-pointer"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* 显示名（仅注册） */}
                {mode === 'register' && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="space-y-1.5 overflow-hidden"
                  >
                    <label className="block text-xs font-medium text-[#94A3B8] uppercase tracking-wider">
                      显示名称 <span className="text-[#475569]">(可选)</span>
                    </label>
                    <input
                      type="text"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      placeholder="你希望被怎么称呼"
                      className="
                        w-full px-4 py-3 rounded-xl text-sm text-[#F8FAFC]
                        bg-[#0F172A]/60 border border-white/[0.08]
                        outline-none transition-all duration-200
                        placeholder:text-[#475569]
                        focus:border-[#6366F1]/50 focus:ring-1 focus:ring-[#6366F1]/20
                        focus:shadow-[0_0_20px_rgba(99,102,241,0.1)]
                      "
                    />
                  </motion.div>
                )}
              </motion.div>
            </AnimatePresence>

            {/* 错误提示 */}
            <AnimatePresence>
              {error && (
                <motion.p
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -5 }}
                  className="text-sm text-[#EF4444] bg-[#EF4444]/10 px-4 py-2.5 rounded-lg border border-[#EF4444]/20"
                >
                  {error}
                </motion.p>
              )}
            </AnimatePresence>

            {/* 提交按钮 */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="
                w-full py-3 rounded-xl text-sm font-semibold text-white
                bg-gradient-to-r from-[#6366F1] to-[#8B5CF6]
                hover:from-[#5558E6] hover:to-[#7C4FE8]
                active:from-[#4F52D9] active:to-[#7043DB]
                transition-all duration-200
                disabled:opacity-50 disabled:cursor-not-allowed
                shadow-lg shadow-[#6366F1]/20
                hover:shadow-xl hover:shadow-[#6366F1]/30
                hover:scale-[1.01] active:scale-[0.99]
                cursor-pointer
                flex items-center justify-center gap-2
              "
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {mode === 'login' ? '登录中...' : '注册中...'}
                </>
              ) : (
                mode === 'login' ? '登录' : '创建账户'
              )}
            </button>
          </form>
        </div>

        {/* 底部 */}
        <p className="text-center text-[#475569] text-xs mt-6">
          Powered by AG-UI Protocol
        </p>
      </motion.div>
    </div>
  );
}
