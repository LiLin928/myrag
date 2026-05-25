# app/agents/nl2sql_agent.py
"""NL2SQL Agent - 自然语言转 SQL 查询"""

from typing import Dict, Any, Optional


class NL2SQLAgent:
    """NL2SQL Agent - 自然语言转 SQL 查询

    工具集（通过 SQLDatabaseToolkit）：
    - sql_schema: 获取数据库 schema
    - sql_query: 执行 SQL 查询
    - sql_query_checker: 检查 SQL 正确性

    重要规则：只执行 SELECT 查询
    """

    DANGEROUS_KEYWORDS = ["DELETE", "DROP", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE"]

    def __init__(self, db_uri: Optional[str] = None):
        """初始化 NL2SQL Agent

        Args:
            db_uri: 数据库连接 URI（可选）
        """
        self.db_uri = db_uri
        self._agent = None  # LangChain Agent 实例（延迟初始化）
        self._db = None  # SQLDatabase 实例（延迟初始化）

    def _validate_sql_safe(self, sql: str) -> bool:
        """验证 SQL 是否安全（只允许 SELECT）

        Args:
            sql: SQL 语句

        Returns:
            是否安全
        """
        sql_upper = sql.upper()
        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword in sql_upper:
                return False
        return True

    def _format_query_result(self, result: Dict[str, Any]) -> str:
        """格式化查询结果

        Args:
            result: Agent 执行结果

        Returns:
            格式化的查询结果字符串
        """
        if "messages" in result:
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                return last_message.content
        return str(result)

    async def _agent_invoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """调用 LangChain Agent（模拟实现）

        Args:
            input_data: 输入数据

        Returns:
            Agent 执行结果
        """
        # 实际实现需要 create_react_agent + SQLDatabaseToolkit
        return {"messages": [type("obj", (), {"content": "查询执行成功"})()]}

    async def query(self, question: str, db_config: Optional[Dict[str, Any]] = None) -> str:
        """执行自然语言查询

        Args:
            question: 自然语言问题
            db_config: 数据库配置（可选）

        Returns:
            查询结果
        """
        # 使用传入配置或默认 URI
        uri = db_config.get("uri") if db_config else self.db_uri

        if not uri:
            return "未配置数据库连接"

        result = await self._agent_invoke({"input": question})
        return self._format_query_result(result)