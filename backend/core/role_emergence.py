"""
角色涌现引擎 (Role Emergence Engine)

核心设计理念：
1. LLM 自主规划 - 分析任务后自动推理需要什么角色
2. 能力无边界 - Agent 不被锁死在固定岗位
3. 动态生成 - 运行时创建，无需预定义
4. 技能赋能 - 根据任务动态分配技能

这是整个系统的"灵魂"所在
"""

import json
import uuid
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime

from core.models import (
    EmergentRole,
    SubagentConfig,
    TaskPlan,
    RelayStation,
    WorkMethodology,
    SkillAssignment,
)
from llm.provider import LLMProviderFactory, LLMMessage, LLMConfig


# 角色涌现的系统提示词 - 增强版，支持技能分配
ROLE_EMERGENCE_SYSTEM_PROMPT = """你是一个高级任务规划器，专门负责分析复杂任务并设计最优的多Agent协作方案。

你的核心能力是"角色涌现"——根据任务需求，自动创造最适合的专业角色，并为每个角色分配合适的技能。

## ⚠️ 重要约束

**角色数量限制**：创建的角色数量必须控制在 2-5 个之间！
- 简单任务：2-3 个角色
- 中等复杂任务：3-4 个角色  
- 复杂任务：4-5 个角色
- **绝对不要超过 5 个角色**！过多的角色会导致协调困难和效率降低。

## 可用技能列表

以下是系统中可用的技能，你需要根据每个角色的职责合理分配：

### 通用技能

1. **web_search** (网络搜索)
   - 能力：在互联网上搜索信息，获取最新数据和知识
   - 适用：需要获取实时信息、新闻、市场数据的角色

2. **data_analysis** (数据分析)
   - 能力：对结构化数据进行统计分析、趋势分析
   - 适用：需要处理数据、发现规律的角色

3. **code_execution** (代码执行)
   - 能力：执行 Python 代码进行计算和数据处理
   - 适用：需要精确计算、数据转换的角色

4. **document_summary** (文档摘要)
   - 能力：对长文本进行摘要和关键信息提取
   - 适用：需要处理大量文本、提取关键信息的角色

5. **reasoning** (推理分析)
   - 能力：进行深度逻辑推理、因果分析
   - 适用：需要复杂推理、问题解决的角色

### 影视制作专业技能

6. **director** (导演)
   - 能力：创意愿景制定、视觉风格定义、叙事节奏把控、场景调度设计、表演指导、团队协调、艺术质量监督
   - 适用：需要整体创意把控、艺术方向指导、团队协调的角色
   - 核心工作：定义项目视觉风格、设计场景和镜头语言、指导表演、审核创意产出

7. **screenwriter** (编剧)
   - 能力：故事概念开发、剧本撰写、角色塑造、对白创作、叙事结构设计、情节编排
   - 适用：需要创作故事、撰写剧本、设计角色对白的角色
   - 核心工作：开发故事概念、撰写剧本、创建角色、编写对白、设计故事结构

8. **visual_designer** (视觉设计师)
   - 能力：视觉风格定义、画面构图设计、色彩方案制定、光影氛围设计、动效概念设计、情绪板创建、美术指导
   - 适用：需要视觉设计、画面美学、色彩规划的角色
   - 核心工作：定义视觉风格、设计构图、创建色彩方案、规划光影、提供美术指导

## 你的工作流程

### 第一步：深度任务分析
1. 理解任务的本质和目标
2. 识别任务的关键维度和子领域
3. 分析任务的复杂度和依赖关系
4. 识别可能的挑战和边界情况

### 第二步：角色涌现与技能分配
基于任务分析，创造最适合的专业角色（**2-5个，不能超过5个**）。每个角色应该：
- 有明确的专业领域和独特视角
- 有清晰的工作目标和方法论
- 被分配合适的技能来完成任务
- 与其他角色形成互补而非重叠

角色设计原则：
1. **专业深度**：每个角色在其领域内应该是"专家级"的
2. **目标明确**：清晰定义工作目标和预期交付物
3. **方法论科学**：提供具体的工作方法和步骤
4. **技能适配**：根据工作需要分配合适的技能
5. **协作互补**：角色之间能够互相验证和补充
6. **精简高效**：宁可让单个角色承担更多职责，也不要创建过多角色

**重要**：对于涉及影视制作、内容创作、视频制作的任务，优先考虑使用 director、screenwriter、visual_designer 等专业技能！

### 第三步：任务分配与编排
1. 将任务分解为子任务，分配给各角色
2. 设计执行阶段和中继点
3. 定义各阶段的输入输出和质量标准

## 输出格式

你必须输出一个严格的 JSON 对象，格式如下：

```json
{
  "analysis": "对任务的深度分析，包括目标、挑战、关键点等",
  "roles": [
    {
      "name": "角色名称",
      "description": "角色的详细描述，包括其专业背景和独特价值",
      "capabilities": ["能力1", "能力2", "能力3"],
      "focus_areas": ["关注领域1", "关注领域2"],
      "expertise_level": "expert",
      "work_objective": "明确的工作目标，描述这个角色要达成什么",
      "deliverables": ["交付物1", "交付物2"],
      "methodology": {
        "approach": "总体工作方法/策略",
        "steps": ["步骤1", "步骤2", "步骤3"],
        "tools_and_frameworks": ["使用的理论框架1", "分析方法2"],
        "success_criteria": ["成功标准1", "成功标准2"],
        "quality_metrics": ["质量指标1", "质量指标2"]
      },
      "assigned_skills": [
        {
          "skill_name": "技能名称",
          "skill_display_name": "技能显示名",
          "reason": "为什么分配这个技能"
        }
      ],
      "system_prompt": "该角色的完整系统提示词，定义其人格、专业知识和工作方式",
      "relay_triggers": ["触发中继的条件1", "触发中继的条件2"],
      "task_segment": "分配给该角色的具体任务描述",
      "emergence_reasoning": "为什么需要涌现这个角色的推理"
    }
  ],
  "phases": [
    {
      "phase_number": 1,
      "name": "阶段名称",
      "description": "阶段描述",
      "participating_roles": ["角色名称1", "角色名称2"],
      "relay_strategy": "该阶段的中继策略",
      "expected_output": "该阶段的预期产出"
    }
  ],
  "estimated_duration_seconds": 300,
  "integration_strategy": "如何将各角色的输出整合成最终结果的策略"
}
```

## 示例

### 示例输入：为一个品牌创作30秒的短视频广告创意

### 示例输出（简化）：
```json
{
  "analysis": "这是一个短视频广告创作任务，需要从创意策划、内容编写、视觉设计等多个维度协作完成...",
  "roles": [
    {
      "name": "创意总监",
      "description": "资深广告创意人，负责整体创意方向把控和团队协调",
      "capabilities": ["创意策略制定", "视觉风格定义", "团队协调", "质量把控"],
      "focus_areas": ["品牌调性", "创意表达", "市场洞察"],
      "expertise_level": "master",
      "work_objective": "制定广告创意方向，确保创意与品牌调性一致，协调各角色产出",
      "deliverables": ["创意方向文档", "视觉风格指南", "最终创意审核"],
      "methodology": {
        "approach": "以品牌核心价值为出发点，结合目标受众特点设计创意",
        "steps": ["分析品牌调性", "确定创意方向", "定义视觉风格", "协调团队执行", "审核最终产出"],
        "tools_and_frameworks": ["品牌金字塔", "消费者洞察框架"],
        "success_criteria": ["创意与品牌一致", "视觉风格统一", "符合目标受众喜好"],
        "quality_metrics": ["创意独特性", "品牌契合度", "受众吸引力"]
      },
      "assigned_skills": [
        {
          "skill_name": "director",
          "skill_display_name": "导演",
          "reason": "用于整体创意把控、视觉风格定义和团队协调"
        },
        {
          "skill_name": "reasoning",
          "skill_display_name": "推理分析",
          "reason": "用于品牌分析和创意策略制定"
        }
      ],
      "system_prompt": "你是一位资深广告创意总监...",
      "relay_triggers": ["创意方向确定", "发现关键洞察"],
      "task_segment": "负责整体创意方向和团队协调",
      "emergence_reasoning": "广告创作需要有人统筹创意方向并协调各角色"
    },
    {
      "name": "内容策划",
      "description": "专业内容创作者，负责脚本和文案撰写",
      "capabilities": ["故事创作", "文案撰写", "脚本编写"],
      "work_objective": "创作引人入胜的广告脚本和文案",
      "assigned_skills": [
        {
          "skill_name": "screenwriter",
          "skill_display_name": "编剧",
          "reason": "用于脚本创作和故事构思"
        }
      ]
    },
    {
      "name": "视觉设计师",
      "description": "专业视觉设计师，负责画面风格和视觉元素设计",
      "capabilities": ["画面设计", "色彩规划", "视觉风格定义"],
      "work_objective": "设计广告的视觉风格和画面效果",
      "assigned_skills": [
        {
          "skill_name": "visual_designer",
          "skill_display_name": "视觉设计师",
          "reason": "用于视觉风格设计和画面规划"
        }
      ]
    }
  ],
  "phases": [...],
  "estimated_duration_seconds": 300,
  "integration_strategy": "创意总监统筹，内容和视觉相互配合，形成完整创意方案"
}
```

现在，请分析以下任务并设计最优的多Agent协作方案：
"""


class RoleEmergenceEngine:
    """角色涌现引擎"""
    
    def __init__(
        self,
        provider_type: str = "openai",
        model: Optional[str] = None
    ):
        self.provider = LLMProviderFactory.get_provider(provider_type)
        self.config = LLMProviderFactory.get_default_config(provider_type)
        if model:
            self.config.model = model
        self.config.temperature = 0.7  # 角色涌现需要一定的创造性
    
    async def analyze_and_emerge(
        self,
        task: str,
        context: Optional[str] = None
    ) -> TaskPlan:
        """
        分析任务并涌现角色
        
        Args:
            task: 用户任务描述
            context: 可选的上下文信息
            
        Returns:
            完整的任务规划
        """
        # 构建消息
        messages = [
            LLMMessage(role="system", content=ROLE_EMERGENCE_SYSTEM_PROMPT),
            LLMMessage(role="user", content=self._build_user_prompt(task, context))
        ]
        
        # 调用 LLM
        response = await self.provider.chat_complete(messages, self.config)
        
        # 解析响应
        plan = self._parse_response(task, response["content"])
        
        return plan
    
    async def analyze_and_emerge_stream(
        self,
        task: str,
        context: Optional[str] = None,
        previous_roles: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式分析任务并涌现角色
        
        逐步输出分析过程，提供更好的用户体验
        
        Args:
            task: 用户任务描述
            context: 可选的上下文信息（含用户记忆、追问上下文等）
            previous_roles: 上一轮的角色配置列表（追问场景下用于角色复用）
        """
        messages = [
            LLMMessage(role="system", content=ROLE_EMERGENCE_SYSTEM_PROMPT),
            LLMMessage(role="user", content=self._build_user_prompt(task, context, previous_roles))
        ]
        
        full_response = ""
        
        async for chunk in self.provider.chat(messages, self.config):
            full_response += chunk
            yield {"type": "chunk", "content": chunk}
        
        # 解析完整响应
        try:
            plan = self._parse_response(task, full_response)
            yield {"type": "plan", "plan": plan}
        except Exception as e:
            yield {"type": "error", "error": str(e)}
    
    def _build_user_prompt(
        self, 
        task: str, 
        context: Optional[str],
        previous_roles: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """构建用户提示"""
        prompt = f"## 任务\n{task}\n"
        
        if context:
            prompt += f"\n## 上下文信息\n{context}\n"
        
        # 追问场景：注入上一轮角色配置供引擎参考复用
        if previous_roles:
            prompt += "\n## 上一轮角色配置（参考复用）\n"
            prompt += "以下是上一轮任务使用的角色配置。请基于新任务的需求决定：\n"
            prompt += "- 如果新任务方向相似，可以**复用**这些角色（适当微调描述和任务分配）\n"
            prompt += "- 如果新任务方向变化较大，可以**替换或调整**部分角色\n"
            prompt += "- 优先复用已有角色，除非有明确理由需要新角色\n\n"
            for i, role in enumerate(previous_roles, 1):
                prompt += f"### 角色 {i}: {role.get('name', '未知')}\n"
                prompt += f"- 描述: {role.get('description', '')}\n"
                prompt += f"- 能力: {', '.join(role.get('capabilities', []))}\n"
                prompt += f"- 关注领域: {', '.join(role.get('focus_areas', []))}\n"
                prompt += f"- 上轮任务分段: {role.get('task_segment', '')}\n\n"
        
        prompt += "\n请分析这个任务，并设计最优的多Agent协作方案。输出严格的 JSON 格式。"
        
        return prompt
    
    def _parse_response(self, original_task: str, response: str) -> TaskPlan:
        """解析 LLM 响应为 TaskPlan"""
        # 调试：打印原始响应
        print(f"[RoleEmergence] Raw response length: {len(response) if response else 0}")
        print(f"[RoleEmergence] Raw response (first 1000 chars): {response[:1000] if response else 'EMPTY'}")
        
        # 尝试提取 JSON
        json_str = self._extract_json(response)
        
        print(f"[RoleEmergence] Extracted JSON length: {len(json_str) if json_str else 0}")
        
        if not json_str:
            raise ValueError(f"无法从响应中提取 JSON:\n{response[:500]}")
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败: {e}\nJSON 字符串: {json_str[:500]}")
        
        # 验证必要字段
        if not isinstance(data, dict):
            raise ValueError(f"响应不是有效的 JSON 对象: {type(data)}")
        
        roles_data = data.get("roles", [])
        if not roles_data:
            raise ValueError(f"响应中没有 roles 字段或为空。响应 keys: {list(data.keys())}")
        
        # 限制角色数量不超过 5 个
        MAX_ROLES = 5
        if len(roles_data) > MAX_ROLES:
            print(f"[RoleEmergence] Warning: Too many roles ({len(roles_data)}), truncating to {MAX_ROLES}")
            roles_data = roles_data[:MAX_ROLES]
        
        # 构建 EmergentRoles
        emergent_roles = []
        subagent_configs = []
        
        for idx, role_data in enumerate(roles_data):
            try:
                # 验证必要字段
                if not isinstance(role_data, dict):
                    raise ValueError(f"角色 {idx} 不是有效的对象: {type(role_data)}")
                if "name" not in role_data:
                    raise ValueError(f"角色 {idx} 缺少 name 字段")
                if "description" not in role_data:
                    role_data["description"] = role_data.get("name", "未知角色")
                
                # 解析方法论
                methodology = None
                if "methodology" in role_data and isinstance(role_data["methodology"], dict):
                    method_data = role_data["methodology"]
                    methodology = WorkMethodology(
                        approach=method_data.get("approach", ""),
                        steps=method_data.get("steps", []),
                        tools_and_frameworks=method_data.get("tools_and_frameworks", []),
                        success_criteria=method_data.get("success_criteria", []),
                        quality_metrics=method_data.get("quality_metrics", [])
                    )
                
                # 解析技能分配
                assigned_skills = []
                if "assigned_skills" in role_data and isinstance(role_data["assigned_skills"], list):
                    for skill_data in role_data["assigned_skills"]:
                        if isinstance(skill_data, dict) and "skill_name" in skill_data:
                            assigned_skills.append(SkillAssignment(
                                skill_name=skill_data["skill_name"],
                                skill_display_name=skill_data.get("skill_display_name", skill_data["skill_name"]),
                                reason=skill_data.get("reason", "")
                            ))
                
                # 如果没有分配技能，根据角色类型默认分配
                if not assigned_skills:
                    assigned_skills = self._suggest_default_skills(role_data)
                
                role = EmergentRole(
                    name=role_data["name"],
                    description=role_data.get("description", ""),
                    capabilities=role_data.get("capabilities", []),
                    focus_areas=role_data.get("focus_areas", []),
                    expertise_level=role_data.get("expertise_level", "expert"),
                    work_objective=role_data.get("work_objective", f"完成{role_data['name']}相关的分析任务"),
                    deliverables=role_data.get("deliverables", []),
                    methodology=methodology,
                    assigned_skills=assigned_skills,
                    system_prompt=role_data.get("system_prompt", f"你是{role_data['name']}，负责相关领域的分析工作。"),
                    relay_triggers=role_data.get("relay_triggers", []),
                    emergence_reasoning=role_data.get("emergence_reasoning", "")
                )
                emergent_roles.append(role)
                
                # 为每个角色创建 Subagent 配置
                config = SubagentConfig(
                    role=role,
                    task_segment=role_data.get("task_segment", f"执行{role_data['name']}相关的分析任务"),
                    priority=5,
                    relay_enabled=True,
                )
                subagent_configs.append(config)
            except Exception as e:
                raise ValueError(f"解析角色 {idx} 失败: {e}\n角色数据: {role_data}")
        
        # 构建中继站
        relay_stations = []
        phases_data = data.get("phases", [])
        if phases_data:
            for phase_data in phases_data:
                if isinstance(phase_data, dict):
                    station = RelayStation(
                        name=f"阶段{phase_data.get('phase_number', 1)}中继站",
                        phase=phase_data.get("phase_number", 1),
                        participating_agents=[],  # 稍后填充
                    )
                    relay_stations.append(station)
        
        # 如果没有中继站，创建一个默认的
        if not relay_stations:
            relay_stations.append(RelayStation(
                name="默认中继站",
                phase=1,
                participating_agents=[],
            ))
        
        # 构建 TaskPlan
        plan = TaskPlan(
            original_task=original_task,
            analysis=data.get("analysis", "任务分析中..."),
            emergent_roles=emergent_roles,
            subagent_configs=subagent_configs,
            relay_stations=relay_stations,
            estimated_duration=data.get("estimated_duration_seconds", 300),
            phases=phases_data if phases_data else [{"phase_number": 1, "name": "执行阶段"}],
        )
        
        return plan
    
    def _suggest_default_skills(self, role_data: Dict[str, Any]) -> List[SkillAssignment]:
        """根据角色特征建议默认技能"""
        skills = []
        name_lower = role_data.get("name", "").lower()
        desc_lower = role_data.get("description", "").lower()
        combined = name_lower + " " + desc_lower
        
        # === 影视制作专业技能匹配 ===
        
        # 导演技能匹配
        director_keywords = [
            "导演", "总监", "director", "创意", "把控", "统筹", "协调",
            "指导", "监督", "愿景", "vision", "creative director"
        ]
        if any(kw in combined for kw in director_keywords):
            skills.append(SkillAssignment(
                skill_name="director",
                skill_display_name="导演",
                reason="用于创意把控、视觉风格定义和团队协调"
            ))
        
        # 编剧技能匹配
        screenwriter_keywords = [
            "编剧", "策划", "脚本", "文案", "故事", "剧本", 
            "screenwriter", "writer", "copywriter", "story", "script",
            "内容", "创作", "叙事", "narrative"
        ]
        if any(kw in combined for kw in screenwriter_keywords):
            skills.append(SkillAssignment(
                skill_name="screenwriter",
                skill_display_name="编剧",
                reason="用于故事创作、脚本撰写和内容策划"
            ))
        
        # 视觉设计师技能匹配
        visual_designer_keywords = [
            "视觉", "设计", "美术", "画面", "色彩", "构图",
            "visual", "designer", "art", "aesthetic", "graphic",
            "摄影", "灯光", "光影", "风格"
        ]
        if any(kw in combined for kw in visual_designer_keywords):
            skills.append(SkillAssignment(
                skill_name="visual_designer",
                skill_display_name="视觉设计师",
                reason="用于视觉风格设计、画面构图和美术指导"
            ))
        
        # === 通用技能匹配 ===
        
        # 基于角色名称和描述推断技能
        if any(kw in combined for kw in ["分析", "研究", "评估", "analysis", "研判", "解读"]):
            skills.append(SkillAssignment(
                skill_name="reasoning",
                skill_display_name="推理分析",
                reason="用于深度分析和推理"
            ))
        
        if any(kw in combined for kw in ["数据", "统计", "指标", "data", "metrics"]):
            skills.append(SkillAssignment(
                skill_name="data_analysis",
                skill_display_name="数据分析",
                reason="用于数据处理和分析"
            ))
        
        if any(kw in combined for kw in ["搜索", "调研", "信息", "search", "research", "资料"]):
            skills.append(SkillAssignment(
                skill_name="web_search",
                skill_display_name="网络搜索",
                reason="用于信息检索"
            ))
        
        if any(kw in combined for kw in ["文档", "报告", "摘要", "document", "summary", "整理"]):
            skills.append(SkillAssignment(
                skill_name="document_summary",
                skill_display_name="文档摘要",
                reason="用于文档处理"
            ))
        
        # 如果没有匹配到，至少给一个推理技能
        if not skills:
            skills.append(SkillAssignment(
                skill_name="reasoning",
                skill_display_name="推理分析",
                reason="通用分析能力"
            ))
        
        return skills
    
    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON"""
        import re
        
        if not text or not text.strip():
            return ""
        
        # 方法1: 查找 ```json ... ``` 块
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if json_match:
            extracted = json_match.group(1).strip()
            if extracted:
                return extracted
        
        # 方法2: 查找 ``` ... ``` 块（不带语言标签）
        code_match = re.search(r'```\s*([\s\S]*?)\s*```', text)
        if code_match:
            extracted = code_match.group(1).strip()
            if extracted.startswith('{'):
                return extracted
        
        # 方法3: 查找 { ... } 块（最外层的大括号）
        brace_count = 0
        start_idx = -1
        
        for i, char in enumerate(text):
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    return text[start_idx:i+1]
        
        # 方法4: 如果文本本身看起来像 JSON，直接返回
        stripped = text.strip()
        if stripped.startswith('{') and stripped.endswith('}'):
            return stripped
        
        return ""


class RoleEmergenceValidator:
    """角色涌现验证器 - 验证涌现的角色是否合理"""
    
    MAX_ROLES = 5  # 最大角色数量限制
    
    @staticmethod
    def validate_roles(roles: List[EmergentRole]) -> Dict[str, Any]:
        """验证角色列表"""
        issues = []
        
        # 检查角色数量
        if len(roles) < 2:
            issues.append("角色数量过少，可能无法充分覆盖任务")
        if len(roles) > RoleEmergenceValidator.MAX_ROLES:
            issues.append(f"角色数量过多（{len(roles)} > {RoleEmergenceValidator.MAX_ROLES}），需要精简")
        
        # 检查角色重叠
        all_capabilities = []
        for role in roles:
            for cap in role.capabilities:
                if cap in all_capabilities:
                    issues.append(f"能力 '{cap}' 在多个角色中重复")
                all_capabilities.append(cap)
        
        # 检查 system_prompt 长度
        for role in roles:
            if len(role.system_prompt) < 100:
                issues.append(f"角色 '{role.name}' 的 system_prompt 过短，可能不够详细")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "role_count": len(roles),
            "total_capabilities": len(all_capabilities)
        }
