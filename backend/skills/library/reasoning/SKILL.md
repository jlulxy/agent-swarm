---
name: reasoning
description: Perform deep logical reasoning, analysis, and problem-solving. Use when facing complex problems that require step-by-step thinking, causal analysis, or multi-factor evaluation.
version: "1.0.0"
author: system
category: analysis
tags:
  - reasoning
  - logic
  - analysis
  - problem-solving
  - thinking
trigger_keywords:
  - 分析
  - 推理
  - 思考
  - analyze
  - reason
  - think
  - 为什么
  - why
  - how
display_name: 推理分析
icon: 🧠
---

# Reasoning & Analysis

进行深度逻辑推理、分析和问题解决。适用于需要逐步思考、因果分析或多因素评估的复杂问题。

## Workflow

1. **问题理解**: 深入理解问题的本质
   - 明确问题边界和约束
   - 识别关键变量和因素
   - 理清已知条件和未知目标

2. **信息收集**: 收集相关背景信息
   - 整理现有数据和事实
   - 识别信息缺口
   - 确定假设前提

3. **分解分析**: 将复杂问题分解为子问题
   - 使用结构化思维框架
   - 建立因果关系图
   - 识别关键决策点

4. **逻辑推导**: 进行系统性推理
   - 演绎推理：从一般到特殊
   - 归纳推理：从特殊到一般
   - 类比推理：借鉴相似案例

5. **验证结论**: 检验推理过程和结论
   - 检查逻辑一致性
   - 考虑反例和边界情况
   - 评估结论的可靠性

6. **综合呈现**: 清晰表达推理过程和结论
   - 结构化展示思路
   - 标明关键假设
   - 提供置信度评估

## Reasoning Frameworks

### 结构化分析框架

| 框架 | 适用场景 | 核心步骤 |
|------|----------|----------|
| MECE | 问题分解 | 相互独立、完全穷尽 |
| 5W2H | 问题定义 | What/Why/Who/When/Where/How/How much |
| 金字塔原理 | 论证表达 | 结论先行、以下统上 |
| 费米估算 | 数量估计 | 分解、假设、计算 |

### 思维模式

- **第一性原理**: 回归基本事实，从根本出发
- **逆向思维**: 从结果反推原因
- **系统思维**: 考虑整体和各部分的相互作用
- **批判性思维**: 质疑假设，寻找漏洞

## Guidelines

- 明确区分事实、观点和假设
- 对不确定性保持敏感，给出置信度
- 考虑多种可能性，避免确认偏误
- 推理过程要透明可追溯
- 承认认知局限，标注不确定之处

## Examples

```
用户: 为什么这个系统的响应时间突然变慢了？

推理过程:
1. 定义问题：响应时间从 X ms 增加到 Y ms
2. 收集信息：
   - 最近是否有代码变更？
   - 流量是否有变化？
   - 依赖服务状态如何？
3. 假设排查：
   - H1: 代码变更引入性能问题
   - H2: 流量激增导致资源不足
   - H3: 依赖服务响应变慢
4. 验证假设：逐一排查，定位根因
5. 得出结论：基于证据确定最可能的原因
```

## Safety Checks

- 避免过度简化复杂问题
- 警惕认知偏误（确认偏误、锚定效应等）
- 对于重大决策，建议多方验证
- 承认推理的局限性

## Success Criteria

- 推理过程逻辑清晰、步骤完整
- 结论有充分的论据支持
- 考虑了主要的替代解释
- 不确定性得到恰当标注
- 可以被他人理解和验证
