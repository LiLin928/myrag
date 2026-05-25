"""Metadata Pydantic Schema"""

import re
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional


# 校验规则
FIELD_NAME_PATTERN = r'^[a-zA-Z][a-zA-Z0-9_]*$'
MAX_FIELD_NAME_LENGTH = 50
MAX_FIELD_VALUE_LENGTH = 500
MAX_METADATA_FIELDS = 20


class MetadataResponse(BaseModel):
    """元数据响应（含继承和自有）"""
    inherited: Dict[str, str] = Field(default_factory=dict, description="从文档继承的元数据（只读）")
    own: Dict[str, str] = Field(default_factory=dict, description="自有元数据（可编辑）")
    merged: Dict[str, str] = Field(default_factory=dict, description="合并后的元数据")


class MetadataUpdate(BaseModel):
    """元数据更新请求"""
    metadata: Dict[str, str] = Field(..., description="元数据键值对")

    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v: Dict[str, str]) -> Dict[str, str]:
        if len(v) > MAX_METADATA_FIELDS:
            raise ValueError(f"元数据字段不能超过 {MAX_METADATA_FIELDS} 个")

        for name, value in v.items():
            if len(name) > MAX_FIELD_NAME_LENGTH:
                raise ValueError(f"字段名 '{name}' 超过最大长度 {MAX_FIELD_NAME_LENGTH}")
            if not re.match(FIELD_NAME_PATTERN, name):
                raise ValueError(f"字段名 '{name}' 格式错误，仅支持英文开头的字母数字下划线")
            if len(value) > MAX_FIELD_VALUE_LENGTH:
                raise ValueError(f"字段值 '{name}' 超过最大长度 {MAX_FIELD_VALUE_LENGTH}")

        return v


class MetadataPatch(BaseModel):
    """元数据增量更新请求"""
    name: str = Field(..., description="字段名")
    value: str = Field(..., description="字段值")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if len(v) > MAX_FIELD_NAME_LENGTH:
            raise ValueError(f"字段名超过最大长度 {MAX_FIELD_NAME_LENGTH}")
        if not re.match(FIELD_NAME_PATTERN, v):
            raise ValueError("字段名格式错误，仅支持英文开头的字母数字下划线")
        return v

    @field_validator('value')
    @classmethod
    def validate_value(cls, v: str) -> str:
        if len(v) > MAX_FIELD_VALUE_LENGTH:
            raise ValueError(f"字段值超过最大长度 {MAX_FIELD_VALUE_LENGTH}")
        return v


class MetadataFieldDefinition(BaseModel):
    """元数据字段定义"""
    name: str
    display_name: str
    readonly: bool = False


class MetadataFieldsResponse(BaseModel):
    """元数据字段定义列表响应"""
    fields: List[MetadataFieldDefinition]


# 系统预定义字段
SYSTEM_METADATA_FIELDS = [
    {"name": "filename", "display_name": "文件名", "readonly": True},
    {"name": "file_type", "display_name": "文件类型", "readonly": True},
    {"name": "file_size", "display_name": "文件大小", "readonly": True},
    {"name": "page_count", "display_name": "页数", "readonly": True},
    {"name": "created_date", "display_name": "创建日期", "readonly": True},
    {"name": "author", "display_name": "作者", "readonly": False},
    {"name": "source", "display_name": "来源", "readonly": False},
    {"name": "version", "display_name": "版本", "readonly": False},
]