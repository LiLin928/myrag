# tests/agent/test_human_approval.py

import pytest
from unittest.mock import MagicMock, patch


class TestHumanApproval:
    """人工审批中间件测试"""

    def test_sensitive_tools_list(self):
        """测试敏感工具列表"""
        from app.agent.middleware.human_approval import SENSITIVE_TOOLS

        assert "execute_python" in SENSITIVE_TOOLS
        assert "http_request" in SENSITIVE_TOOLS
        assert len(SENSITIVE_TOOLS) == 2

    def test_human_approval_middleware_interrupt_on_config(self):
        """测试 interrupt_on 配置"""
        from app.agent.middleware.human_approval import human_approval_middleware

        # human_approval_middleware 应有 interrupt_on 属性
        assert hasattr(human_approval_middleware, "interrupt_on")

        # 检查所有敏感工具都在 interrupt_on 中
        interrupt_on = human_approval_middleware.interrupt_on
        assert "execute_python" in interrupt_on
        assert "http_request" in interrupt_on

    def test_human_approval_middleware_allowed_decisions(self):
        """测试允许的决策类型"""
        from app.agent.middleware.human_approval import human_approval_middleware

        interrupt_on = human_approval_middleware.interrupt_on

        # 检查每个工具的 allowed_decisions
        for tool_name, config in interrupt_on.items():
            assert "allowed_decisions" in config
            assert "approve" in config["allowed_decisions"]
            assert "edit" in config["allowed_decisions"]
            assert "reject" in config["allowed_decisions"]

    def test_human_approval_middleware_description_callable(self):
        """测试描述生成函数"""
        from app.agent.middleware.human_approval import human_approval_middleware

        interrupt_on = human_approval_middleware.interrupt_on

        # 检查每个工具都有 description 函数
        for tool_name, config in interrupt_on.items():
            assert "description" in config
            desc_func = config["description"]

            # 测试调用描述函数
            result = desc_func(tool_name, {"arg1": "value1"}, {})
            assert tool_name in result or "审批" in result