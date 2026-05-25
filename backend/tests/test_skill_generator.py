# backend/tests/test_skill_generator.py

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.skill_generator import SkillGenerator


def test_skill_generator_init():
    """测试生成器初始化"""
    generator = SkillGenerator()
    assert generator.llm is not None


def test_extract_code():
    """测试代码提取"""
    generator = SkillGenerator()

    content = """
Here is the code:
```python
def test():
    pass
```
"""

    code = generator._extract_code(content)
    assert "def test" in code


def test_extract_code_no_markdown():
    """测试无 markdown 格式的代码提取"""
    generator = SkillGenerator()

    content = "def execute(input_data): return {'result': 1}"
    code = generator._extract_code(content)
    assert "def execute" in code


def test_validate_generated_code_valid():
    """测试有效代码验证"""
    generator = SkillGenerator()

    valid_code = "def execute(input_data): return {'result': 1}"
    result = generator._validate_generated_code(valid_code)
    assert result["valid"] is True


def test_validate_generated_code_missing_execute():
    """测试缺少 execute 函数"""
    generator = SkillGenerator()

    invalid_code = "def other(): pass"
    result = generator._validate_generated_code(invalid_code)
    assert result["valid"] is False
    assert "Missing execute" in result["error"]


def test_validate_generated_code_dangerous_import():
    """测试危险导入"""
    generator = SkillGenerator()

    dangerous_code = "import os\n\ndef execute(input_data): return {'result': os.getcwd()}"
    result = generator._validate_generated_code(dangerous_code)
    assert result["valid"] is False
    assert "Dangerous import" in result["error"]


def test_validate_generated_code_syntax_error():
    """测试语法错误"""
    generator = SkillGenerator()

    invalid_code = "def execute(input_data) return {'result': 1}"
    result = generator._validate_generated_code(invalid_code)
    assert result["valid"] is False


def test_extract_skill_name():
    """测试提取 Skill 名称"""
    generator = SkillGenerator()

    code = "# Skill: calculator\n# Description: Calculate\n\ndef execute(input_data): return {}"
    name = generator._extract_skill_name(code)
    assert name == "calculator"


def test_extract_description():
    """测试提取描述"""
    generator = SkillGenerator()

    code = "# Skill: test\n# Description: Test skill\n\ndef execute(input_data): return {}"
    description = generator._extract_description(code)
    assert description == "Test skill"


@pytest.mark.asyncio
async def test_generate_skill_mock():
    """测试生成 Skill（Mock LLM）"""
    # 使用 patch 替换整个 ChatOpenAI
    mock_response = MagicMock()
    mock_response.content = """
```python
# Skill: calculator
# Description: Calculate math expressions

def execute(input_data: dict) -> dict:
    expression = input_data.get("expression", "0")
    result = eval(expression)
    return {"result": result}
```
"""

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch('app.services.skill_generator.ChatOpenAI', return_value=mock_llm):
        generator = SkillGenerator()
        result = await generator.generate("计算数学表达式")

        assert result["success"] is True
        assert "def execute" in result["code"]
        assert result["name"] == "calculator"