"""元数据字段定义 API"""

from fastapi import APIRouter, Query
from typing import Optional

from app.schemas.metadata import MetadataFieldsResponse, MetadataFieldDefinition, SYSTEM_METADATA_FIELDS

router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.get("/fields", response_model=MetadataFieldsResponse)
async def get_metadata_fields(
    type: Optional[str] = Query(None, description="类型过滤: document/chunk"),
):
    """获取系统预定义元数据字段

    Args:
        type: 类型过滤（可选）

    Returns:
        字段定义列表
    """
    # 目前文档和分块共用预定义字段
    fields = [
        MetadataFieldDefinition(**field)
        for field in SYSTEM_METADATA_FIELDS
    ]

    # type 过滤暂时忽略，返回所有字段
    return MetadataFieldsResponse(fields=fields)