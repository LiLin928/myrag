"""MultiAgentService - 多 Agent 协作服务层"""

from typing import Dict, Any, List, Optional

from app.agents.agent_registry import AgentRegistry
from app.agents.master_agent import MasterAgent
from app.agents.data_analysis_agent import DataAnalysisAgent
from app.agents.nl2sql_agent import NL2SQLAgent
from app.agents.document_review_agent import DocumentReviewAgent


class MultiAgentService:
    """多 Agent 协作服务

    负责管理所有 Agent 的生命周期和任务分发：
    - initialize: 初始化所有 Agent（注册到 AgentRegistry）
    - process_task: 处理任务（通过 Master Agent 分发）
    - dispatch_to_agent: 直接分发到特定 Agent
    - get_agent_status: 获取所有 Agent 状态
    - get_available_agents: 获取可用 Agent 列表
    """

    def __init__(self, llm_service: Optional[Any] = None, db_uri: Optional[str] = None):
        """初始化 MultiAgentService

        Args:
            llm_service: LLM 服务实例（可选）
            db_uri: 数据库连接 URI（可选）
        """
        self.registry = AgentRegistry()
        self.llm_service = llm_service
        self.db_uri = db_uri
        self._initialized = False

    def initialize(self) -> None:
        """初始化所有 Agent 并注册到 AgentRegistry"""
        if self._initialized:
            return

        # 创建并注册 Master Agent
        master_agent = MasterAgent(self.registry)
        self.registry.register("master", master_agent)

        # 创建并注册 DataAnalysis Agent
        data_analysis_agent = DataAnalysisAgent(llm_service=self.llm_service)
        self.registry.register("data_analysis", data_analysis_agent)

        # 创建并注册 NL2SQL Agent
        nl2sql_agent = NL2SQLAgent(db_uri=self.db_uri)
        self.registry.register("nl2sql", nl2sql_agent)

        # 创建并注册 DocumentReview Agent
        document_review_agent = DocumentReviewAgent()
        self.registry.register("document_review", document_review_agent)

        self._initialized = True

    async def process_task(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """处理任务 - 通过 Master Agent 分发

        Args:
            task_description: 任务描述
            context: 任务上下文

        Returns:
            处理结果
        """
        if not self._initialized:
            self.initialize()

        master_agent = self.registry.get("master")
        if master_agent is None:
            return "Master Agent 未初始化"

        return await master_agent.process(task_description, context)

    async def dispatch_to_agent(
        self,
        agent_name: str,
        **kwargs
    ) -> str:
        """直接分发到特定 Agent

        Args:
            agent_name: Agent 名称
            **kwargs: Agent 特定参数

        Returns:
            Agent 执行结果
        """
        if not self._initialized:
            self.initialize()

        agent = self.registry.get(agent_name)
        if agent is None:
            return f"Agent '{agent_name}' 未注册"

        # 根据不同 Agent 类型调用对应方法
        if agent_name == "document_review":
            document_id = kwargs.get("document_id")
            rules = kwargs.get("rules")
            return await agent.review(document_id, rules)

        elif agent_name == "data_analysis":
            task_description = kwargs.get("task_description", "")
            context = kwargs.get("context", {})
            return await agent.analyze(task_description, context)

        elif agent_name == "nl2sql":
            question = kwargs.get("question", "")
            db_config = kwargs.get("db_config")
            return await agent.query(question, db_config)

        elif agent_name == "master":
            task_description = kwargs.get("task_description", "")
            context = kwargs.get("context")
            return await agent.process(task_description, context)

        else:
            return f"未知的 Agent 类型: {agent_name}"

    def get_agent_status(self) -> Dict[str, Any]:
        """获取所有 Agent 状态

        Returns:
            Agent 状态字典，包含 total 和 agents 字段
        """
        if not self._initialized:
            self.initialize()

        agents = {}
        for agent_name in self.registry.list_agents():
            agent = self.registry.get(agent_name)
            agents[agent_name] = {
                "registered": True,
                "status": "ready",
                "type": type(agent).__name__
            }

        return {
            "total": len(agents),
            "agents": agents
        }

    def get_available_agents(self) -> List[str]:
        """获取可用 Agent 列表

        Returns:
            Agent 名称列表
        """
        if not self._initialized:
            self.initialize()

        return self.registry.list_agents()


# 全局服务实例
multi_agent_service = MultiAgentService()