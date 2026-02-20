# 贡献指南

感谢你对 Agent Hive 的关注！欢迎任何形式的贡献。

## 如何贡献

### 报告 Bug

1. 在 [Issues](../../issues) 中搜索是否已有相同问题
2. 如果没有，创建新 Issue，请包含：
   - 问题描述
   - 复现步骤
   - 期望行为 vs 实际行为
   - 环境信息（OS、Python 版本、Node 版本）

### 提交功能建议

在 Issues 中创建 Feature Request，描述：
- 你想解决的问题
- 建议的解决方案
- 可能的替代方案

### 提交代码

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m "feat: add your feature"`
4. 推送到 Fork：`git push origin feature/your-feature`
5. 创建 Pull Request

## 开发环境搭建

```bash
# 克隆仓库
git clone <repo-url>
cd agent-hive

# 后端
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 前端
cd ../frontend
npm install
```

## 代码规范

### 后端 (Python)

- 遵循 PEP 8
- 使用 type hints
- 函数和类添加 docstring

### 前端 (TypeScript/React)

- 使用 TypeScript 严格模式
- 组件使用函数式组件 + Hooks
- 使用 Tailwind CSS 编写样式

### Commit Message 规范

采用 [Conventional Commits](https://www.conventionalcommits.org/)：

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `refactor:` 代码重构
- `chore:` 构建/工具变更

## 项目结构

```
├── backend/          # FastAPI 后端
│   ├── api/          # API 路由
│   ├── core/         # 核心 Agent 逻辑
│   ├── llm/          # LLM 提供者
│   ├── memory/       # 记忆系统
│   ├── skills/       # 技能系统
│   └── auth/         # 认证模块
├── frontend/         # React 前端
│   └── src/
│       ├── components/  # UI 组件
│       ├── store/       # Zustand 状态管理
│       └── services/    # API 调用
└── start.sh          # 一键启动脚本
```

## 行为准则

请保持友善和尊重。我们致力于维护一个开放、包容的社区环境。
