"""
Skills - 技能注册表

负责：
1. 技能注册和注销
2. 技能查询和过滤
3. 意图匹配和技能推荐
4. 支持热更新
"""

import logging
from typing import Dict, List, Optional, Set
from pathlib import Path
from datetime import datetime

from .models import Skill, SkillTriggerType, SkillResourceType
from .loader import SkillLoader, SkillParseError

logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    技能注册表
    
    特性：
    1. 支持 SKILL.md 格式的技能
    2. 意图匹配 - 根据用户输入自动推荐技能
    3. 渐进式加载 - 按需加载资源内容
    4. 热更新 - 支持运行时重载技能
    """
    
    _instance: Optional['SkillRegistry'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 技能存储
        self._skills: Dict[str, Skill] = {}
        
        # 索引
        self._category_index: Dict[str, Set[str]] = {}
        self._tag_index: Dict[str, Set[str]] = {}
        self._trigger_index: Dict[str, Set[str]] = {}  # 关键词 -> 技能名
        
        # 加载器
        self._loader = SkillLoader()
        
        # 状态
        self._initialized = True
        self._last_update = datetime.now()
    
    def register(self, skill: Skill) -> bool:
        """
        注册技能
        
        Args:
            skill: Skill 对象
            
        Returns:
            是否注册成功
        """
        try:
            name = skill.name
            
            if name in self._skills:
                logger.warning(f"技能 '{name}' 已存在，将被覆盖")
                self._remove_from_indexes(name)
            
            # 存储技能
            self._skills[name] = skill
            
            # 更新索引
            self._update_indexes(skill)
            
            self._last_update = datetime.now()
            logger.info(f"注册技能: {skill.display_name} ({name})")
            return True
            
        except Exception as e:
            logger.error(f"注册技能失败: {e}")
            return False
    
    def register_from_path(self, skill_path: str | Path) -> Optional[Skill]:
        """
        从路径加载并注册技能
        
        Args:
            skill_path: 技能目录路径
            
        Returns:
            注册成功返回 Skill，否则返回 None
        """
        try:
            skill = self._loader.load_skill(skill_path)
            if self.register(skill):
                return skill
        except SkillParseError as e:
            logger.error(f"加载技能失败: {e}")
        return None
    
    def register_all_from_directory(self, skills_dir: str | Path) -> int:
        """
        从目录批量注册技能
        
        Args:
            skills_dir: 技能库目录
            
        Returns:
            成功注册的数量
        """
        skills = self._loader.load_all_skills(skills_dir)
        success_count = 0
        
        for skill in skills:
            if self.register(skill):
                success_count += 1
        
        logger.info(f"批量注册完成: {success_count}/{len(skills)} 个技能")
        return success_count
    
    def _update_indexes(self, skill: Skill):
        """更新索引"""
        name = skill.name
        
        # 分类索引
        if skill.metadata.category:
            category = skill.metadata.category
            if category not in self._category_index:
                self._category_index[category] = set()
            self._category_index[category].add(name)
        
        # 标签索引
        for tag in skill.metadata.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(name)
        
        # 触发关键词索引
        for keyword in skill.metadata.trigger_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower not in self._trigger_index:
                self._trigger_index[keyword_lower] = set()
            self._trigger_index[keyword_lower].add(name)
    
    def _remove_from_indexes(self, name: str):
        """从索引中移除"""
        skill = self._skills.get(name)
        if not skill:
            return
        
        # 从分类索引移除
        if skill.metadata.category:
            self._category_index.get(skill.metadata.category, set()).discard(name)
        
        # 从标签索引移除
        for tag in skill.metadata.tags:
            self._tag_index.get(tag, set()).discard(name)
        
        # 从触发索引移除
        for keyword in skill.metadata.trigger_keywords:
            self._trigger_index.get(keyword.lower(), set()).discard(name)
    
    def unregister(self, name: str) -> bool:
        """注销技能"""
        if name not in self._skills:
            return False
        
        self._remove_from_indexes(name)
        del self._skills[name]
        
        self._last_update = datetime.now()
        logger.info(f"注销技能: {name}")
        return True
    
    def get(self, name: str) -> Optional[Skill]:
        """获取技能"""
        return self._skills.get(name)
    
    def get_all(self) -> Dict[str, Skill]:
        """获取所有技能"""
        return self._skills.copy()
    
    def has(self, name: str) -> bool:
        """检查技能是否存在"""
        return name in self._skills
    
    def count(self) -> int:
        """获取技能数量"""
        return len(self._skills)
    
    def list_names(self) -> List[str]:
        """列出所有技能名称"""
        return list(self._skills.keys())
    
    # === 查询方法 ===
    
    def get_by_category(self, category: str) -> List[Skill]:
        """按分类获取技能"""
        names = self._category_index.get(category, set())
        return [self._skills[n] for n in names if n in self._skills]
    
    def get_by_tag(self, tag: str) -> List[Skill]:
        """按标签获取技能"""
        names = self._tag_index.get(tag, set())
        return [self._skills[n] for n in names if n in self._skills]
    
    def get_by_names(self, names: List[str]) -> List[Skill]:
        """按名称列表获取技能"""
        return [self._skills[n] for n in names if n in self._skills]
    
    def search(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        trigger_type: Optional[SkillTriggerType] = None
    ) -> List[Skill]:
        """
        搜索技能
        
        Args:
            query: 搜索关键词
            category: 分类过滤
            tags: 标签过滤
            trigger_type: 触发类型过滤
            
        Returns:
            匹配的技能列表
        """
        results = list(self._skills.values())
        
        # 分类过滤
        if category:
            category_names = self._category_index.get(category, set())
            results = [s for s in results if s.name in category_names]
        
        # 标签过滤
        if tags:
            tag_names = set()
            for tag in tags:
                tag_names.update(self._tag_index.get(tag, set()))
            results = [s for s in results if s.name in tag_names]
        
        # 触发类型过滤
        if trigger_type:
            results = [s for s in results if s.metadata.trigger_type == trigger_type]
        
        # 关键词搜索
        if query:
            query_lower = query.lower()
            results = [
                s for s in results
                if query_lower in s.name.lower()
                or query_lower in s.description.lower()
                or query_lower in s.display_name.lower()
                or any(query_lower in t.lower() for t in s.metadata.tags)
            ]
        
        return results
    
    # === 意图匹配 ===
    
    def match_intent(
        self,
        user_input: str,
        top_k: int = 3,
        min_score: float = 0.3
    ) -> List[tuple[Skill, float]]:
        """
        根据用户输入匹配技能
        
        使用简单的关键词匹配算法：
        1. 精确匹配触发关键词
        2. 模糊匹配技能名称和描述
        
        Args:
            user_input: 用户输入
            top_k: 返回 top K 个结果
            min_score: 最小匹配分数
            
        Returns:
            [(skill, score), ...] 列表，按分数降序
        """
        input_lower = user_input.lower()
        input_words = set(input_lower.split())
        
        scores: List[tuple[Skill, float]] = []
        
        for skill in self._skills.values():
            score = 0.0
            
            # 1. 触发关键词匹配（权重高）
            for keyword in skill.metadata.trigger_keywords:
                if keyword.lower() in input_lower:
                    score += 0.5
                    break
            
            # 2. 技能名匹配
            name_words = set(skill.name.replace('-', ' ').split())
            name_overlap = len(input_words & name_words) / max(len(name_words), 1)
            score += name_overlap * 0.3
            
            # 3. 描述匹配
            desc_words = set(skill.description.lower().split())
            desc_overlap = len(input_words & desc_words) / max(len(desc_words), 1)
            score += desc_overlap * 0.2
            
            # 4. 标签匹配
            for tag in skill.metadata.tags:
                if tag.lower() in input_lower:
                    score += 0.1
            
            if score >= min_score:
                scores.append((skill, score))
        
        # 按分数降序排序
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[:top_k]
    
    def get_always_active_skills(self) -> List[Skill]:
        """获取始终激活的技能"""
        return [
            s for s in self._skills.values()
            if s.metadata.trigger_type == SkillTriggerType.ALWAYS
        ]
    
    # === 系统提示生成 ===
    
    def get_system_prompt_for_skills(
        self,
        skill_names: Optional[List[str]] = None,
        include_resources: bool = False
    ) -> str:
        """
        生成技能的系统提示内容
        
        Args:
            skill_names: 指定技能名，None 表示所有
            include_resources: 是否包含资源内容
            
        Returns:
            系统提示文本
        """
        if skill_names:
            skills = self.get_by_names(skill_names)
        else:
            skills = list(self._skills.values())
        
        if not skills:
            return ""
        
        parts = ["\n## 可用技能\n"]
        
        for skill in skills:
            parts.append(skill.to_system_prompt(include_resources=include_resources))
            parts.append("\n---\n")
        
        return "\n".join(parts)
    
    def get_tool_definitions(
        self,
        skill_names: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        获取技能的 Tool 定义（用于 Function Calling）
        
        Args:
            skill_names: 指定技能名，None 表示所有
            
        Returns:
            OpenAI Tool 格式列表
        """
        if skill_names:
            skills = self.get_by_names(skill_names)
        else:
            skills = list(self._skills.values())
        
        return [skill.to_tool_definition() for skill in skills]
    
    # === 资源加载 ===
    
    def load_skill_resources(
        self,
        skill_name: str,
        resource_types: Optional[List[SkillResourceType]] = None
    ) -> Dict[str, str]:
        """
        加载技能的资源内容
        
        渐进式披露：按需加载资源
        
        Args:
            skill_name: 技能名
            resource_types: 要加载的资源类型，None 表示全部
            
        Returns:
            {资源名: 内容} 字典
        """
        skill = self.get(skill_name)
        if not skill or not skill.skill_path:
            return {}
        
        base_path = Path(skill.skill_path)
        loaded = {}
        
        for resource in skill.resources:
            if resource_types and resource.resource_type not in resource_types:
                continue
            
            content = resource.load_content(base_path)
            if content:
                loaded[resource.name] = content
        
        return loaded
    
    # === 热更新 ===
    
    def reload_skill(self, name: str) -> Optional[Skill]:
        """
        热更新：重新加载技能
        
        Args:
            name: 技能名
            
        Returns:
            更新后的技能，失败返回 None
        """
        skill = self.get(name)
        if not skill or not skill.skill_path:
            return None
        
        try:
            new_skill = self._loader.load_skill(skill.skill_path)
            self.register(new_skill)
            return new_skill
        except SkillParseError as e:
            logger.error(f"重载技能失败: {e}")
            return None
    
    def clear(self):
        """清空所有技能"""
        self._skills.clear()
        self._category_index.clear()
        self._tag_index.clear()
        self._trigger_index.clear()
        self._loader.clear_cache()


# 全局注册表实例
_global_registry: Optional[SkillRegistry] = None


def get_global_registry() -> SkillRegistry:
    """获取全局技能注册表"""
    global _global_registry
    if _global_registry is None:
        _global_registry = SkillRegistry()
    return _global_registry
