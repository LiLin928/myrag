"""工作流进度追踪器

追踪工作流执行进度，通过 WebSocket 实时推送并记录到数据库
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.middleware.websocket import manager
from app.workflow.models.workflow_execution_log import WorkflowExecutionLog, LogEventType
from app.workflow.models.execution import WorkflowExecution, ExecutionStatus


class WorkflowProgressTracker:
    """工作流进度追踪器"""

    def __init__(
        self,
        execution_id: str,
        workflow_id: str,
        user_id: str,
        db: AsyncSession,
        node_names: Dict[str, str] = None,
        node_types: Dict[str, str] = None,
    ):
        self.execution_id = execution_id
        self.workflow_id = workflow_id
        self.user_id = user_id
        self.db = db
        self.node_names = node_names or {}
        self.node_types = node_types or {}

        # 追踪节点开始时间
        self._node_start_times: Dict[str, datetime] = {}
        # 总节点数（用于计算进度）
        self._total_nodes: int = 0
        self._completed_nodes: int = 0

    def set_total_nodes(self, total: int):
        """设置总节点数"""
        self._total_nodes = total

    async def send_event(self, event_type: str, data: Dict[str, Any]):
        """发送 WebSocket 事件"""
        event = {
            "type": event_type,
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            **data
        }
        await manager.send_progress(self.user_id, event)

    async def log_and_send(
        self,
        node_id: str,
        event_type: LogEventType,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        progress_percent: Optional[int] = None,
        progress_message: Optional[str] = None,
    ):
        """记录日志并发送 WebSocket 事件"""
        # 创建日志记录
        log = WorkflowExecutionLog(
            execution_id=self.execution_id,
            node_id=node_id,
            node_name=self.node_names.get(node_id, node_id),
            node_type=self.node_types.get(node_id),
            event_type=event_type,
            input_data=input_data,
            output_data=output_data,
            error_message=error_message,
            duration_ms=duration_ms,
            progress_percent=progress_percent,
            progress_message=progress_message,
        )

        self.db.add(log)
        await self.db.commit()

        # 发送 WebSocket 事件
        ws_event_type = f"node_{event_type.value}"
        await self.send_event(ws_event_type, {
            "node_id": node_id,
            "node_name": self.node_names.get(node_id, node_id),
            "node_type": self.node_types.get(node_id),
            "input_data": input_data,
            "output_data": output_data,
            "error_message": error_message,
            "duration_ms": duration_ms,
            "progress_percent": progress_percent,
            "progress_message": progress_message,
        })

    async def on_execution_start(self, total_nodes: int):
        """执行开始"""
        self.set_total_nodes(total_nodes)

        # 更新执行状态
        result = await self.db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == self.execution_id)
        )
        execution = result.scalar_one_or_none()
        if execution:
            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.utcnow()
            await self.db.commit()

        await self.send_event("execution_start", {
            "total_nodes": total_nodes,
        })

    async def on_node_start(self, node_id: str, input_data: Optional[Dict[str, Any]] = None):
        """节点开始执行"""
        self._node_start_times[node_id] = datetime.utcnow()

        await self.log_and_send(
            node_id=node_id,
            event_type=LogEventType.START,
            input_data=input_data,
        )

    async def on_node_progress(
        self,
        node_id: str,
        progress_percent: int,
        message: Optional[str] = None,
    ):
        """节点执行进度更新（用于长时间节点）"""
        await self.log_and_send(
            node_id=node_id,
            event_type=LogEventType.PROGRESS,
            progress_percent=progress_percent,
            progress_message=message,
        )

    async def on_node_complete(
        self,
        node_id: str,
        output_data: Optional[Dict[str, Any]] = None,
    ):
        """节点执行完成"""
        start_time = self._node_start_times.pop(node_id, None)
        duration_ms = None
        if start_time:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        self._completed_nodes += 1

        await self.log_and_send(
            node_id=node_id,
            event_type=LogEventType.COMPLETE,
            output_data=output_data,
            duration_ms=duration_ms,
        )

        # 发送整体进度
        overall_progress = int((self._completed_nodes / self._total_nodes) * 100) if self._total_nodes > 0 else 0
        await self.send_event("execution_progress", {
            "completed_nodes": self._completed_nodes,
            "total_nodes": self._total_nodes,
            "progress_percent": overall_progress,
        })

    async def on_node_error(self, node_id: str, error_message: str):
        """节点执行错误"""
        start_time = self._node_start_times.pop(node_id, None)
        duration_ms = None
        if start_time:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # 更新执行状态
        result = await self.db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == self.execution_id)
        )
        execution = result.scalar_one_or_none()
        if execution:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = error_message
            execution.error_node = node_id
            await self.db.commit()

        await self.log_and_send(
            node_id=node_id,
            event_type=LogEventType.ERROR,
            error_message=error_message,
            duration_ms=duration_ms,
        )

        await self.send_event("execution_error", {
            "node_id": node_id,
            "error_message": error_message,
        })

    async def on_execution_complete(self, final_output: Optional[Dict[str, Any]] = None):
        """执行完成"""
        total_duration_ms = 0

        # 计算总耗时
        result = await self.db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == self.execution_id)
        )
        execution = result.scalar_one_or_none()
        if execution and execution.started_at:
            total_duration_ms = int((datetime.utcnow() - execution.started_at).total_seconds() * 1000)
            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.node_outputs = final_output
            await self.db.commit()

        await self.send_event("execution_complete", {
            "final_output": final_output,
            "total_duration_ms": total_duration_ms,
            "completed_nodes": self._completed_nodes,
        })

    async def on_execution_interrupted(self, node_id: str, reason: str):
        """执行中断（人工节点等待）"""
        # 更新执行状态
        result = await self.db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == self.execution_id)
        )
        execution = result.scalar_one_or_none()
        if execution:
            execution.status = ExecutionStatus.PAUSED
            execution.current_node = node_id
            await self.db.commit()

        await self.send_event("execution_interrupted", {
            "node_id": node_id,
            "node_name": self.node_names.get(node_id, node_id),
            "reason": reason,
        })