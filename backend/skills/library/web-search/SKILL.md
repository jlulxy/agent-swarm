---
name: web-search
description: Search the internet for real-time information using DuckDuckGo. Returns actual search results with titles, URLs, and snippets. Use when you need current data, latest updates, or information beyond training data cutoff.
version: "2.1.0"
author: system
category: search
tags:
  - search
  - internet
  - information
  - real-time
  - duckduckgo
trigger_keywords:
  - 搜索
  - 查找
  - search
  - find
  - look up
  - latest
  - 最新
  - 查询
  - 网上搜
  - google
  - 百度
requires_packages:
  - ddgs
display_name: 网络搜索
icon: 🔍
---

# Web Search 网络搜索

在互联网上搜索实时信息，使用 DuckDuckGo 搜索引擎获取真实的搜索结果。适用于需要最新数据、时事动态或超出训练数据范围的查询。

## 核心能力

本技能提供**真实的网络搜索能力**，通过 DuckDuckGo 搜索引擎：
- 返回真实的搜索结果（标题、URL、摘要）
- 支持通用搜索和新闻搜索
- 支持区域和时间范围过滤
- 无需 API Key，免费可用

## Scripts 可用脚本

本技能在 `scripts/` 目录下提供以下可执行脚本：

### search.py - 网络搜索脚本

**路径**: `scripts/search.py`

**功能**: 执行 DuckDuckGo 网络搜索，支持通用搜索、新闻搜索和即时答案。

**使用方法**:

```bash
# 基础网页搜索
python scripts/search.py --query "Python 异步编程最佳实践" --max-results 5

# 新闻搜索
python scripts/search.py --query "AI 最新进展" --type news --max-results 10

# 限定时间范围（最近一周）
python scripts/search.py --query "React 19 新特性" --time-range w

# 指定区域（中国）
python scripts/search.py --query "大模型最新进展" --region cn-zh

# 输出 Markdown 格式
python scripts/search.py --query "Rust 教程" --format markdown
```

**参数说明**:

| 参数 | 缩写 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| --query | -q | ✅ | - | 搜索关键词 |
| --type | -t | ❌ | web | 搜索类型: web(网页), news(新闻), instant(即时答案) |
| --max-results | -n | ❌ | 5 | 返回结果数量 (最大20) |
| --region | -r | ❌ | wt-wt | 搜索区域 (wt-wt:全球, cn-zh:中国, us-en:美国) |
| --time-range | - | ❌ | - | 时间范围: d(天), w(周), m(月), y(年) |
| --format | -f | ❌ | json | 输出格式: json, markdown |
| --timeout | - | ❌ | 30 | 搜索超时时间（秒） |

**输出格式** (JSON):

```json
{
  "success": true,
  "query": "Python asyncio",
  "type": "web",
  "count": 5,
  "results": [
    {
      "title": "Python asyncio documentation",
      "url": "https://docs.python.org/3/library/asyncio.html",
      "snippet": "asyncio is a library to write concurrent code...",
      "source": "duckduckgo"
    }
  ]
}
```

## Workflow

1. **分析搜索意图**: 理解用户的查询需求
   - 识别核心搜索关键词
   - 判断搜索类型（通用/新闻）
   - 确定时间范围要求（最新/历史）
   - 判断是否需要特定区域结果

2. **构建搜索查询**: 优化搜索关键词
   - 使用精准的搜索词组
   - 添加必要的限定词
   - 对于中文查询，考虑同时搜索英文关键词
   - 避免使用过长或过于复杂的查询

3. **执行搜索**: 运行 search.py 脚本
   ```bash
   # 根据需求选择合适的参数
   python scripts/search.py --query "<优化后的关键词>" --type <web|news> --max-results <数量>
   ```

4. **解析结果**: 处理搜索返回的 JSON
   - 提取每个结果的标题、URL、摘要
   - 识别最相关的结果
   - 过滤低质量或不相关内容

5. **整合呈现**: 组织和总结搜索结果
   - 提取关键信息和要点
   - **必须标注信息来源和链接**
   - 多个来源时进行信息整合
   - 对矛盾信息进行说明

## Examples 使用示例

### 示例 1: 技术调研

用户问："帮我搜索 2024 年最流行的 Python Web 框架"

执行:
```bash
python scripts/search.py --query "best Python web framework 2024 comparison" --max-results 8 --time-range y
```

### 示例 2: 新闻查询

用户问："最近 AI 行业有什么重大新闻"

执行:
```bash
python scripts/search.py --query "AI artificial intelligence breakthrough" --type news --max-results 10
```

### 示例 3: 学术搜索

用户问："搜索 Transformer 架构的最新优化研究"

执行:
```bash
python scripts/search.py --query "Transformer architecture optimization 2024 paper" --max-results 10 --time-range m
```

## Response Format 响应格式

搜索结果应按以下格式呈现：

```markdown
## 搜索结果

### 1. [结果标题](URL)
> 结果摘要内容...

### 2. [结果标题](URL)
> 结果摘要内容...

---

### 信息整合

基于以上搜索结果，总结关键信息...
```

## Guidelines 指导原则

- **优先使用精准关键词**: 避免过长的查询语句
- **合理设置结果数量**: 通常 5-10 个结果足够，复杂问题可增加到 15-20
- **善用时间过滤**: 对于技术类查询，使用 `--time-range` 获取最新信息
- **交叉验证**: 对于重要信息，建议从多个结果中验证
- **标注来源**: 使用搜索结果时必须标注出处和链接
- **处理搜索失败**: 如果搜索失败，尝试调整关键词或简化查询

## Error Handling 错误处理

脚本会返回 JSON 格式的错误信息：

```json
{
  "success": false,
  "error": "错误描述",
  "error_code": "SEARCH_ERROR|MISSING_DEPENDENCY|UNKNOWN_ERROR",
  "query": "原始查询"
}
```

| 错误类型 | error_code | 处理方式 |
|----------|------------|----------|
| 网络超时 | SEARCH_ERROR | 重试搜索，或提示用户稍后重试 |
| 缺少依赖 | MISSING_DEPENDENCY | 运行 `pip install ddgs` 安装依赖 |
| 无结果 | - | 调整关键词，尝试更宽泛的查询 |

## Safety Checks 安全检查

- 验证搜索结果来源的可信度
- 注意区分事实与观点
- 对于敏感话题保持中立客观
- 不传播未经验证的信息
- 标注信息的时效性

## Success Criteria 成功标准

- ✅ 搜索结果与查询意图高度相关
- ✅ 返回真实可访问的 URL 链接
- ✅ 信息来源可靠且可追溯
- ✅ 结果呈现清晰有条理
- ✅ 时效性要求得到满足
