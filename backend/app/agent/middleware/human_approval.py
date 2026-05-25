# app/agent/middleware/human_approval.py

"""Human-in-the-Loop 中间件

使用 HumanInTheLoopMiddleware，拦截敏感工具调用：
- execute_python: 代码执行
- http_request: 外部 HTTP 请求
"""

from langchain.agents.middleware import HumanInTheLoopMiddleware

# 敏感工具列表（需要人工审批）
SENSITIVE_TOOLS = ["execute_python", "http_request"]

human_approval_middleware = HumanInTheLoopMiddleware(
    interrupt_on={
        tool_name: {
            "allowed_decisions": ["approve", "edit", "reject"],
            "description": lambda name, tool_input, state:
                f"⚠️ 工具 '{name}' 需人工审批\n参数: {tool_input}"
        }
        for tool_name in SENSITIVE_TOOLS
    },
    description_prefix="⚠️ 敏感操作需要人工审批"
)