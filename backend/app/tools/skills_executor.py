"""Skills 执行器

Skills 是动态创建的工具代码，可以在沙箱中执行。
支持：
- 手动创建 Skill
- LLM 自动生成 Skill
- 验证 Skill 代码安全性
- 执行 Skill 并返回结果
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import ast
import json
import uuid
from datetime import datetime

from app.workflow.sandbox.code_executor import get_code_executor


class SkillDefinition(BaseModel):
    """Skill 定义"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Skill ID")
    name: str = Field(..., description="Skill 名称")
    description: str = Field(..., description="Skill 描述")
    code: str = Field(..., description="Skill 代码（包含 execute 函数）")
    input_schema: Dict[str, str] = Field(default_factory=dict, description="输入参数 Schema")
    output_schema: Dict[str, str] = Field(default_factory=dict, description="输出参数 Schema")
    author: Optional[str] = Field(None, description="创建者")
    created_at: Optional[str] = Field(default_factory=lambda: datetime.now().isoformat(), description="创建时间")
    enabled: bool = Field(True, description="是否启用")

    def validate_code(self) -> bool:
        """验证代码语法

        Returns:
            是否有效
        """
        try:
            ast.parse(self.code)
            return True
        except SyntaxError:
            return False

    def validate_security(self) -> Dict[str, Any]:
        """验证代码安全性

        检查是否包含危险操作：
        - 文件系统操作（os、shutil）
        - 系统调用（subprocess、sys）
        - 网络监听（socket）
        - 进程操作（multiprocessing）

        Returns:
            验证结果
        """
        dangerous_modules = [
            "os", "shutil", "subprocess", "sys", "socket",
            "multiprocessing", "threading", "pickle",
        ]

        dangerous_functions = [
            "eval", "exec", "compile", "open",
        ]

        # 解析 AST
        try:
            tree = ast.parse(self.code)
        except SyntaxError:
            return {"safe": False, "error": "Syntax error"}

        warnings = []

        # 检查导入
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in dangerous_modules:
                        warnings.append(f"Dangerous import: {alias.name}")

            if isinstance(node, ast.ImportFrom):
                if node.module in dangerous_modules:
                    warnings.append(f"Dangerous import from: {node.module}")

            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in dangerous_functions:
                        warnings.append(f"Dangerous function call: {node.func.id}")

        return {
            "safe": len(warnings) == 0,
            "warnings": warnings,
        }


class SkillsExecutor:
    """Skills 执行器"""

    def __init__(self):
        self.registry: Dict[str, SkillDefinition] = {}
        self.executor = get_code_executor()

    def register_skill(self, skill: SkillDefinition):
        """注册 Skill

        Args:
            skill: Skill 定义
        """
        # 验证代码
        if not skill.validate_code():
            raise ValueError(f"Skill '{skill.name}' has invalid syntax")

        self.registry[skill.id] = skill

    def unregister_skill(self, skill_id: str):
        """注销 Skill"""
        if skill_id in self.registry:
            del self.registry[skill_id]

    def get_skill(self, skill_id: str) -> Optional[SkillDefinition]:
        """获取 Skill"""
        return self.registry.get(skill_id)

    def get_skill_by_name(self, name: str) -> Optional[SkillDefinition]:
        """按名称获取 Skill"""
        for skill in self.registry.values():
            if skill.name == name:
                return skill
        return None

    def list_skills(self) -> List[Dict[str, Any]]:
        """列出所有 Skills"""
        return [
            {
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "input_schema": skill.input_schema,
                "output_schema": skill.output_schema,
                "enabled": skill.enabled,
                "author": skill.author,
            }
            for skill in self.registry.values()
        ]

    async def execute_skill(
        self,
        skill_id: str,
        input_data: Dict[str, Any],
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """执行 Skill

        Args:
            skill_id: Skill ID
            input_data: 输入数据
            timeout: 执行超时

        Returns:
            执行结果
        """
        skill = self.get_skill(skill_id)
        if not skill:
            return {
                "success": False,
                "error": f"Skill '{skill_id}' not found",
            }

        if not skill.enabled:
            return {
                "success": False,
                "error": f"Skill '{skill_id}' is disabled",
            }

        # 包装 Skill 执行
        wrapped_code = f'''
import json

skill_input = json.loads('{json.dumps(input_data)}')

{skill.code}

result = execute(skill_input)
print(json.dumps({"success": True, "return_value": result}))
'''

        # 执行
        result = await self.executor.execute(wrapped_code, timeout)
        return result

    async def generate_skill_with_llm(
        self,
        requirement: str,
        llm_model: Any = None,
    ) -> SkillDefinition:
        """使用 LLM 生成 Skill

        Args:
            requirement: Skill 需求描述
            llm_model: LLM 模型（可选）

        Returns:
            生成的 SkillDefinition
        """
        # TODO: 实现 LLM 生成逻辑
        # 使用 LangChain 调用 LLM

        # 当前返回占位 Skill
        return SkillDefinition(
            name="generated_skill",
            description=f"Generated from: {requirement}",
            code="def execute(input): return {'result': 'placeholder'}",
            input_schema={},
            output_schema={},
        )

    def export_skills(self) -> Dict[str, Any]:
        """导出所有 Skills

        Returns:
            Skills 导出数据
        """
        return {
            skill.id: {
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "code": skill.code,
                "input_schema": skill.input_schema,
                "output_schema": skill.output_schema,
            }
            for skill in self.registry.values()
        }

    def import_skills(self, data: Dict[str, Any]):
        """导入 Skills

        Args:
            data: Skills 导入数据
        """
        for skill_id, skill_data in data.items():
            skill = SkillDefinition(**skill_data)
            self.register_skill(skill)


# 全局 Skills 执行器实例（延迟初始化）
_skills_executor: Optional[SkillsExecutor] = None


def get_skills_executor() -> SkillsExecutor:
    """获取 Skills 执行器实例（延迟初始化）"""
    global _skills_executor
    if _skills_executor is None:
        _skills_executor = SkillsExecutor()
    return _skills_executor