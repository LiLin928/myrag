"""Master Agent - 任务分发中心"""

from typing import Literal, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.agents.agent_registry import AgentRegistry


class TaskDispatchInput(BaseModel):
    """任务分发输入 Schema"""

    task_type: Literal["document_review", "data_analysis", "nl2sql", "general_chat"] = Field(
        description="任务类型"
    )
    task_description: str = Field(description="任务描述")
    context: Dict[str, Any] = Field(default_factory=dict, description="任务上下文")


class MasterAgent:
    """主控 Agent - 任务分发与编排

    根据用户任务描述判断任务类型，分发到对应的专门 Agent。
    """

    TASK_TYPE_KEYWORDS = {
        "document_review": ["审核", "校验", "检查", "发票", "合同", "文档"],
        "data_analysis": ["分析", "统计", "图表", "可视化", "报告", "数据"],
        "nl2sql": ["查询", "多少", "对比", "数据库", "报表"],
    }

    def __init__(self, registry: AgentRegistry):
        """初始化 Master Agent

        Args:
            registry: Agent 注册中心实例
        """
        self.registry = registry

    def classify_task(self, task_description: str) -> str:
        """分类任务类型

        Args:
            task_description: 任务描述

        Returns:
            任务类型: document_review / data_analysis / nl2sql / general_chat
        """
        for task_type, keywords in self.TASK_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in task_description:
                    return task_type
        return "general_chat"

    async def dispatch_to_document_review(self, input: TaskDispatchInput) -> str:
        """分发到文档审核 Agent

        Args:
            input: 任务分发输入

        Returns:
            审核结果
        """
        agent = self.registry.get("document_review")
        if agent is None:
            return "文档审核 Agent 未注册"

        document_id = input.context.get("document_id")
        rules = input.context.get("rules", [])
        return await agent.review(document_id, rules)

    async def dispatch_to_data_analysis(self, input: TaskDispatchInput) -> str:
        """分发到数据分析 Agent

        Args:
            input: 任务分发输入

        Returns:
            分析结果
        """
        agent = self.registry.get("data_analysis")
        if agent is None:
            return "数据分析 Agent 未注册"

        return await agent.analyze(input.task_description, input.context)

    async def dispatch_to_nl2sql(self, input: TaskDispatchInput) -> str:
        """分发到 NL2SQL Agent

        Args:
            input: 任务分发输入

        Returns:
            查询结果
        """
        agent = self.registry.get("nl2sql")
        if agent is None:
            return "NL2SQL Agent 未注册"

        db_config = input.context.get("db_config")
        return await agent.query(input.task_description, db_config)

    async def process(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> str:
        """处理任务 - 自动分类并分发

        Args:
            task_description: 任务描述
            context: 任务上下文

        Returns:
            处理结果
        """
        task_type = self.classify_task(task_description)

        if task_type == "general_chat":
            return f"通用对话: {task_description}"

        dispatch_input = TaskDispatchInput(
            task_type=task_type,
            task_description=task_description,
            context=context or {}
        )

        dispatch_methods = {
            "document_review": self.dispatch_to_document_review,
            "data_analysis": self.dispatch_to_data_analysis,
            "nl2sql": self.dispatch_to_nl2sql,
        }

        return await dispatch_methods[task_type](dispatch_input)