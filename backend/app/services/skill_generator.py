"""Skill 生成器

使用 LLM 根据需求描述自动生成 Skill 代码
"""

from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import ast
import re

from app.config import get_settings


# Skill 生成提示模板
SKILL_GENERATION_PROMPT = """
你是一个 Python 工具代码生成器。根据用户的需求描述，生成一个 Skill 工具代码。

要求：
1. 代码必须包含一个 `execute(input_data: dict) -> dict` 函数
2. 函数接收一个字典输入，返回一个字典输出
3. 代码必须是完整可执行的 Python 代码
4. 不要使用危险操作（文件系统、系统调用、网络监听）
5. 可以使用 requests/httpx 进行 HTTP 请求
6. 可以使用 numpy/pandas 进行数据处理
7. 输入输出格式必须清晰

需求描述：
{requirement}

请生成代码，格式如下：
```python
# Skill: {skill_name}
# Description: {description}

def execute(input_data: dict) -> dict:
    # 参数验证
    # ...

    # 核心逻辑
    # ...

    return dict(result=...)
```

请直接输出代码，不要添加任何解释。
"""


class SkillGenerator:
    """Skill 生成器"""

    def __init__(self):
        settings = get_settings()
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.3,
            api_key=settings.OPENAI_API_KEY,
        )

    async def generate(
        self,
        requirement: str,
        skill_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """生成 Skill

        Args:
            requirement: 需求描述
            skill_name: Skill 名称（可选，LLM 可自动生成）

        Returns:
            生成结果：{"code": str, "name": str, "description": str, "input_schema": dict}
        """
        # 构建 prompt
        prompt = SKILL_GENERATION_PROMPT.format(
            requirement=requirement,
            skill_name=skill_name or "auto_generated_skill",
            description=requirement,
        )

        # 调用 LLM
        messages = [
            SystemMessage(content="你是一个专业的 Python 工具代码生成器"),
            HumanMessage(content=prompt),
        ]

        response = await self.llm.ainvoke(messages)
        code_content = response.content

        # 提取代码块
        code = self._extract_code(code_content)

        # 验证代码
        validation = self._validate_generated_code(code)
        if not validation["valid"]:
            return {
                "success": False,
                "error": validation["error"],
                "code": code,
            }

        # 提取元信息
        name = skill_name or self._extract_skill_name(code)
        description = self._extract_description(code)
        input_schema = self._extract_input_schema(code)

        return {
            "success": True,
            "code": code,
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "generated_by_llm": True,
            "generation_prompt": requirement,
        }

    def _extract_code(self, content: str) -> str:
        """提取代码块"""
        # 提取 ```python ``` 之间的代码
        match = re.search(r"```python\s*(.*?)\s*```", content, re.DOTALL)
        if match:
            return match.group(1)
        # 没有 markdown 格式，直接返回
        return content.strip()

    def _validate_generated_code(self, code: str) -> Dict[str, Any]:
        """验证生成的代码"""
        # 语法验证
        try:
            ast.parse(code)
        except SyntaxError as e:
            return {"valid": False, "error": f"Syntax error: {e}"}

        # 必须包含 execute 函数
        tree = ast.parse(code)
        has_execute = False

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "execute":
                has_execute = True
                break

        if not has_execute:
            return {"valid": False, "error": "Missing execute function"}

        # 安全验证
        dangerous_modules = ["os", "subprocess", "sys", "socket"]
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in dangerous_modules:
                        return {"valid": False, "error": f"Dangerous import: {alias.name}"}

        return {"valid": True}

    def _extract_skill_name(self, code: str) -> str:
        """提取 Skill 名称"""
        match = re.search(r"# Skill: (\w+)", code)
        if match:
            return match.group(1).lower()
        return "generated_skill"

    def _extract_description(self, code: str) -> str:
        """提取描述"""
        match = re.search(r"# Description: (.+)", code)
        if match:
            return match.group(1)
        return "Auto-generated skill"

    def _extract_input_schema(self, code: str) -> Dict[str, Any]:
        """提取输入 schema（简化版）"""
        # 分析 execute 函数参数验证
        return {"type": "object", "properties": {}}


# 全局生成器实例
skill_generator = SkillGenerator()