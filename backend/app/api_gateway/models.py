"""Pydantic schemas for the API Gateway module."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ParamDefinition(BaseModel):
    """Definition of a single API parameter."""

    name: str = Field(..., description="Parameter name matching :param in SQL template")
    type: str = Field(default="string", description="Parameter type: string, int, float, bool")
    required: bool = Field(default=False, description="Whether the parameter is required")
    default: Optional[str] = Field(default=None, description="Default value if not provided")


class ApiCreate(BaseModel):
    """Schema for creating an API definition."""

    name: str = Field(..., min_length=1, max_length=255, description="API display name")
    method: str = Field(default="GET", description="HTTP method: GET, POST")
    url_path: str = Field(..., min_length=1, description="URL path for the API (e.g., /users/search)")
    sql_template: str = Field(..., description="SQL template with :param placeholders")
    params_definition: list[ParamDefinition] = Field(default_factory=list, description="Parameter definitions")
    connection_id: int = Field(..., description="Database connection ID")
    result_limit: int = Field(default=1000, ge=1, le=50000, description="Maximum rows to return")
    cache_seconds: int = Field(default=0, ge=0, description="Response cache duration in seconds")
    auth_type: str = Field(default="none", description="Auth type: none, token")


class ApiUpdate(BaseModel):
    """Schema for updating an API definition. All fields optional."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    method: Optional[str] = Field(default=None)
    url_path: Optional[str] = Field(default=None, min_length=1)
    sql_template: Optional[str] = Field(default=None)
    params_definition: Optional[list[ParamDefinition]] = Field(default=None)
    connection_id: Optional[int] = Field(default=None)
    result_limit: Optional[int] = Field(default=None, ge=1, le=50000)
    cache_seconds: Optional[int] = Field(default=None, ge=0)
    auth_type: Optional[str] = Field(default=None)


class ApiResponse(BaseModel):
    """Full API definition response (token is masked for security)."""

    id: int
    name: str
    method: str
    url_path: str
    sql_template: str
    params_definition: list[dict]
    connection_id: int
    result_limit: int
    cache_seconds: int
    auth_type: str
    # 安全修复：令牌字段已脱敏，仅显示最后 4 位（如 ****abcd）
    token: Optional[str] = Field(default=None, description="Masked token (last 4 chars only)")
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApiTokenResponse(BaseModel):
    """API token reveal response - full token returned for authorized requests only."""

    api_id: int
    name: str
    auth_type: str
    token: Optional[str] = Field(default=None, description="Full authentication token")


class ApiCallRequest(BaseModel):
    """Request body for calling a dynamic API."""

    params: dict = Field(default_factory=dict, description="Parameter values for the SQL template")


class ApiCallResponse(BaseModel):
    """Response from a dynamic API call."""

    data: list[dict]
    total: int
    duration_ms: int


class ExtractParamsRequest(BaseModel):
    """Request to extract parameter names from a SQL template."""

    sql: str = Field(..., description="SQL template with :param_name patterns")


class ToggleEnabledRequest(BaseModel):
    """Request to toggle API enabled/disabled state."""

    is_enabled: bool
