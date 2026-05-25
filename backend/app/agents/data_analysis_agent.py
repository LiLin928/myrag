"""DataAnalysis Agent - 数据分析智能体"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class AnalysisResult(BaseModel):
    """分析结果 Schema"""

    summary: str = Field(description="分析摘要")
    insights: List[str] = Field(default_factory=list, description="洞察列表")
    recommendations: List[str] = Field(default_factory=list, description="建议列表")


class DataAnalysisAgent:
    """数据分析 Agent

    负责执行数据分析任务，包括：
    - 数据统计分析
    - 趋势分析
    - 图表生成建议
    - 分析报告生成
    """

    def __init__(self, llm_service: Optional[Any] = None):
        """初始化数据分析 Agent

        Args:
            llm_service: LLM 服务实例（可选）
        """
        self.llm_service = llm_service

    def _build_prompt(self, task_description: str, context: Dict[str, Any]) -> str:
        """构建分析提示词

        Args:
            task_description: 任务描述
            context: 任务上下文

        Returns:
            构建的提示词
        """
        prompt_parts = [
            "你是一名专业的数据分析师。请根据以下信息进行分析：",
            "",
            f"任务描述：{task_description}",
        ]

        if context:
            prompt_parts.append("")
            prompt_parts.append("上下文信息：")
            for key, value in context.items():
                if isinstance(value, list):
                    prompt_parts.append(f"- {key}: {', '.join(str(v) for v in value)}")
                else:
                    prompt_parts.append(f"- {key}: {value}")

        prompt_parts.append("")
        prompt_parts.append("请提供详细的分析结果，包括：")
        prompt_parts.append("1. 数据概要")
        prompt_parts.append("2. 关键洞察")
        prompt_parts.append("3. 分析建议")

        return "\n".join(prompt_parts)

    async def analyze(self, task_description: str, context: Dict[str, Any]) -> str:
        """执行数据分析

        Args:
            task_description: 任务描述
            context: 任务上下文

        Returns:
            分析结果
        """
        if self.llm_service is None:
            return "需要配置 LLM 服务才能执行数据分析"

        prompt = self._build_prompt(task_description, context)
        result = await self.llm_service.chat(prompt)

        return result