"""Pydantic schemas for connection management."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ConnectionCreate(BaseModel):
    """Schema for creating a new database connection."""

    name: str = Field(..., min_length=1, max_length=255, description="Connection display name")
    db_type: str = Field(..., description="Database type: mysql, postgresql, oracle")
    host: str = Field(..., min_length=1, max_length=255, description="Database host address")
    port: int = Field(..., gt=0, le=65535, description="Database port")
    username: str = Field(..., min_length=1, max_length=255, description="Database username")
    password: str = Field(..., description="Database password (will be encrypted)")
    database_name: str = Field(..., min_length=1, max_length=255, description="Database name")
    extra_params: Optional[dict] = Field(default=None, description="Extra connection parameters")
    group_name: str = Field(default="default", description="Connection group name")
    tags: list[str] = Field(default_factory=list, description="Tags for organizing connections")
    pool_size: int = Field(default=5, ge=1, le=50, description="Connection pool size")
    # 安全修复：服务端只读模式，启用后该连接强制只允许 SELECT 查询
    read_only: bool = Field(default=False, description="Server-side read-only mode for this connection")


class ConnectionUpdate(BaseModel):
    """Schema for updating an existing connection. All fields optional."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    db_type: Optional[str] = Field(default=None)
    host: Optional[str] = Field(default=None, min_length=1, max_length=255)
    port: Optional[int] = Field(default=None, gt=0, le=65535)
    username: Optional[str] = Field(default=None, min_length=1, max_length=255)
    password: Optional[str] = Field(default=None)
    database_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    extra_params: Optional[dict] = Field(default=None)
    group_name: Optional[str] = Field(default=None)
    tags: Optional[list[str]] = Field(default=None)
    pool_size: Optional[int] = Field(default=None, ge=1, le=50)
    # 安全修复：服务端只读模式
    read_only: Optional[bool] = Field(default=None, description="Server-side read-only mode")


class ConnectionResponse(BaseModel):
    """Schema for connection response (excludes password)."""

    id: int
    name: str
    db_type: str
    host: str
    port: int
    username: str
    database_name: str
    group_name: str
    tags: list[str]
    pool_size: int
    # 安全修复：返回只读模式状态
    read_only: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConnectionTestRequest(BaseModel):
    """Schema for testing a connection without saving."""

    name: str = Field(..., min_length=1, max_length=255)
    db_type: str = Field(..., description="Database type: mysql, postgresql, oracle")
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., gt=0, le=65535)
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(...)
    database_name: str = Field(..., min_length=1, max_length=255)
    extra_params: Optional[dict] = Field(default=None)
    group_name: str = Field(default="default")
    tags: list[str] = Field(default_factory=list)


class ConnectionTestResponse(BaseModel):
    """Schema for connection test result."""

    status: str = Field(..., description="Connection status: success or error")
    message: str = Field(..., description="Human-readable status message")
