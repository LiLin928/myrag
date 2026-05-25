"""Skill 业务服务

管理 Skill 的创建、执行、版本管理
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid

from app.models.skill import Skill, SkillStatus
from app.services.skill_generator import skill_generator
from app.workflow.sandbox.code_executor import get_code_executor


class SkillService:
    """Skill 业务服务"""

    async def create_skill(
        self,
        db: AsyncSession,
        internal_name: str,
        code: str,
        description: str = None,
        user_id: str = None,
        input_schema: Dict = None,
        output_schema: Dict = None,
        display_name: str = None,
        is_public: bool = False,
        entry_command: str = "python main.py",
    ) -> Skill:
        """创建 Skill

        Args:
            db: 数据库会话
            internal_name: Skill 内部名称（唯一标识符）
            code: Python 代码
            description: 描述
            user_id: 用户 ID
            input_schema: 输入 schema
            output_schema: 输出 schema
            display_name: 显示名称
            is_public: 是否公开
            entry_command: 入口命令

        Returns:
            Skill 实例
        """
        # 验证代码（如果非空）
        if code and code.strip():
            code_executor = get_code_executor()
            validation = await code_executor.validate_code(code)
            if not validation["valid"]:
                raise ValueError(f"Invalid code: {validation['error']}")

        # 创建 Skill
        skill = Skill(
            internal_name=internal_name,
            display_name=display_name or internal_name,
            code=code,
            description=description,
            user_id=uuid.UUID(user_id) if user_id else None,
            input_schema=input_schema,
            output_schema=output_schema,
            is_public=is_public,
            entry_command=entry_command,
            status=SkillStatus.DRAFT,
        )

        db.add(skill)
        await db.commit()
        await db.refresh(skill)

        return skill

    async def generate_skill_with_llm(
        self,
        db: AsyncSession,
        requirements: str,
        user_id: str,
        skill_name: str = None,
    ) -> Skill:
        """使用 LLM 生成 Skill

        Args:
            db: 数据库会话
            requirements: 需求描述
            user_id: 用户 ID
            skill_name: Skill 名称（可选）

        Returns:
            Skill 实例
        """
        # 生成代码
        result = await skill_generator.generate(requirements, skill_name)

        if not result["success"]:
            raise ValueError(f"Generation failed: {result['error']}")

        # 创建 Skill
        skill = Skill(
            internal_name=result["name"],
            display_name=result.get("display_name", result["name"]),
            code=result["code"],
            description=result["description"],
            user_id=uuid.UUID(user_id),
            input_schema=result["input_schema"],
            generated_by_llm=True,
            generation_prompt=requirements,
            status=SkillStatus.DRAFT,
        )

        db.add(skill)
        await db.commit()
        await db.refresh(skill)

        return skill

    async def execute_skill(
        self,
        db: AsyncSession,
        skill_name: str,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行 Skill

        Args:
            db: 数据库会话
            skill_name: Skill 内部名称
            input_data: 输入数据

        Returns:
            执行结果
        """
        # 获取 Skill
        result = await db.execute(
            select(Skill).where(Skill.internal_name == skill_name, Skill.enabled == True)
        )
        skill = result.scalar_one_or_none()

        if not skill:
            raise ValueError(f"Skill '{skill_name}' not found or disabled")

        # 包装代码执行
        import json
        wrapped_code = f'''
import json

input_data = json.loads('{json.dumps(input_data)}')

{skill.code}

result = execute(input_data)
print(json.dumps({"success": True, "result": result}))
'''

        # 执行代码
        code_executor = get_code_executor()
        execution_result = await code_executor.execute(wrapped_code, timeout=30)

        # 更新统计
        skill.execution_count += 1
        skill.last_executed_at = datetime.utcnow()
        await db.commit()

        return execution_result

    async def create_new_version(
        self,
        db: AsyncSession,
        skill_id: str,
        new_code: str,
        user_id: str,
    ) -> Skill:
        """创建新版本

        Args:
            db: 数据库会话
            skill_id: 原 Skill ID
            new_code: 新代码
            user_id: 用户 ID

        Returns:
            新版本 Skill
        """
        # 获取原 Skill
        skill_uuid = uuid.UUID(skill_id)
        result = await db.execute(select(Skill).where(Skill.id == skill_uuid))
        original = result.scalar_one_or_none()

        if not original:
            raise ValueError("Original skill not found")

        # 增加版本号
        version_parts = original.version.split(".")
        new_minor = int(version_parts[-1]) + 1
        new_version = f"{version_parts[0]}.{new_minor}"

        # 创建新版本
        new_skill = Skill(
            internal_name=original.internal_name,
            display_name=original.display_name,
            code=new_code,
            description=original.description,
            user_id=uuid.UUID(user_id),
            input_schema=original.input_schema,
            output_schema=original.output_schema,
            version=new_version,
            previous_version_id=original.id,
            is_public=original.is_public,
            entry_command=original.entry_command,
            status=SkillStatus.DRAFT,
        )

        db.add(new_skill)
        await db.commit()
        await db.refresh(new_skill)

        return new_skill

    async def list_skills(
        self,
        db: AsyncSession,
        user_id: str = None,
        status: SkillStatus = None,
    ) -> List[Skill]:
        """列出 Skills"""
        query = select(Skill)

        if user_id:
            query = query.where(Skill.user_id == user_id)

        if status:
            query = query.where(Skill.status == status)

        result = await db.execute(query)
        return result.scalars().all()

    async def get_skill_by_name(
        self,
        db: AsyncSession,
        name: str,
    ) -> Optional[Skill]:
        """按内部名称获取 Skill"""
        result = await db.execute(
            select(Skill).where(Skill.internal_name == name)
        )
        return result.scalar_one_or_none()


# 全局服务实例
skill_service = SkillService()