# backend/tests/workflow/test_skills_executor.py

import pytest
from app.tools.skills_executor import SkillsExecutor, SkillDefinition, get_skills_executor


def test_skill_definition():
    """测试 Skill 定义"""
    skill = SkillDefinition(
        name="test_skill",
        description="Test skill",
        code="def execute(input): return {'result': input['value'] * 2}",
        input_schema={"value": "int"},
        output_schema={"result": "int"},
    )

    assert skill.name == "test_skill"
    assert skill.validate_code() is True


def test_skill_definition_invalid():
    """测试无效 Skill"""
    skill = SkillDefinition(
        name="invalid_skill",
        description="Invalid skill",
        code="def execute(",  # 语法错误
        input_schema={},
        output_schema={},
    )

    assert skill.validate_code() is False


def test_skill_security_check():
    """测试安全检查"""
    # 安全代码
    safe_skill = SkillDefinition(
        name="safe_skill",
        description="Safe skill",
        code="def execute(input): return {'result': input['value']}",
        input_schema={},
        output_schema={},
    )

    result = safe_skill.validate_security()
    assert result["safe"] is True

    # 危险代码（包含 os 导入）
    dangerous_skill = SkillDefinition(
        name="dangerous_skill",
        description="Dangerous skill",
        code="import os\n\ndef execute(input): return {'result': os.getcwd()}",
        input_schema={},
        output_schema={},
    )

    result = dangerous_skill.validate_security()
    assert result["safe"] is False
    assert len(result["warnings"]) > 0


def test_skills_executor_init():
    """测试 Skills 执行器初始化"""
    executor = SkillsExecutor()
    assert executor is not None
    assert executor.registry is not None


def test_register_skill():
    """测试注册 Skill"""
    executor = SkillsExecutor()

    skill = SkillDefinition(
        name="double",
        description="Double input value",
        code="def execute(input): return {'result': input['value'] * 2}",
        input_schema={"value": "int"},
        output_schema={"result": "int"},
    )

    executor.register_skill(skill)

    assert skill.id in executor.registry


def test_list_skills():
    """测试列出 Skills"""
    executor = SkillsExecutor()

    skill1 = SkillDefinition(name="skill1", description="Test 1", code="def execute(input): return {}", input_schema={}, output_schema={})
    skill2 = SkillDefinition(name="skill2", description="Test 2", code="def execute(input): return {}", input_schema={}, output_schema={})

    executor.register_skill(skill1)
    executor.register_skill(skill2)

    skills = executor.list_skills()

    assert len(skills) == 2


def test_get_skill_by_name():
    """测试按名称获取 Skill"""
    executor = SkillsExecutor()

    skill = SkillDefinition(
        name="test_skill",
        description="Test",
        code="def execute(input): return {}",
        input_schema={},
        output_schema={},
    )

    executor.register_skill(skill)

    found = executor.get_skill_by_name("test_skill")
    assert found is not None
    assert found.name == "test_skill"


def test_get_skills_executor():
    """测试获取 Skills 执行器实例"""
    executor = get_skills_executor()
    assert executor is not None
    assert isinstance(executor, SkillsExecutor)