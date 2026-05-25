from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, BaseModel
from app.models.associations import user_model_configs
import uuid


class User(BaseModel):
    """用户表"""
    __tablename__ = 'users'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    avatar_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # 关联
    bound_model_configs = relationship('ModelConfig', secondary=user_model_configs, back_populates='users', lazy='selectin')

    def __repr__(self):
        return f"<User {self.username}>"