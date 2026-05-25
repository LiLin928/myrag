"""关联表定义

定义多对多关系：
- 用户-模型配置
"""

from sqlalchemy import Table, Column, String, Boolean, ForeignKey, DateTime
from datetime import datetime

from app.models.base import Base


# 用户-模型配置关联表
user_model_configs = Table(
    'user_model_configs',
    Base.metadata,
    Column('user_id', String(36), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('model_config_id', String(36), ForeignKey('model_configs.id', ondelete='CASCADE'), primary_key=True),
    Column('is_default', Boolean, default=False),
    Column('created_at', DateTime, default=datetime.utcnow),
)