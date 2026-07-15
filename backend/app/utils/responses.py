"""
Standard response schemas and pagination helpers for the DBStudio API.

Every endpoint should return one of these envelopes so that front-end code
can handle success, error, and pagination uniformly.

Examples::

    # Success with data
    return SuccessResponse(data={"id": 1, "name": "prod-mysql"})

    # Error
    raise HTTPException(status_code=400, detail=ErrorResponse(code=40001, message="Bad SQL").model_dump())

    # Paginated list
    return PaginatedResponse(items=[...], total=123, page=1, page_size=50)
"""

from typing import Any

from fastapi import Query
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────────────
# Envelope responses
# ──────────────────────────────────────────────────────────────────────────────

class SuccessResponse(BaseModel):
    """
    Generic success envelope.

    ``code == 0`` always indicates success.  ``data`` carries the
    endpoint-specific payload (object, list, or null).
    """

    code: int = Field(default=0, description="0 means success")
    message: str = Field(default="success", description="Human-readable status")
    data: Any = Field(default=None, description="Endpoint-specific response payload")


class ErrorResponse(BaseModel):
    """
    Error envelope returned (or raised) when a request cannot be fulfilled.

    ``code`` is an application-level error number (distinct from the HTTP
    status code) that the front end can switch on.
    """

    code: int = Field(default=500, description="Application-level error code")
    message: str = Field(..., description="Human-readable error description")
    detail: Any = Field(
        default=None,
        description="Optional structured context (validation errors, stack traces in debug mode, etc.)",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Pagination
# ──────────────────────────────────────────────────────────────────────────────

class PaginationParams(BaseModel):
    """
    Query-parameter model for paginated list endpoints.

    Inject into a route handler via ``Depends()``::

        from fastapi import Depends

        @router.get("/items")
        async def list_items(pagination: PaginationParams = Depends()):
            offset = (pagination.page - 1) * pagination.page_size
            ...
    """

    page: int = Field(
        default=1,
        ge=1,
        description="1-based page number",
    )
    page_size: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Number of items per page (max 500)",
    )


class PaginatedResponse(BaseModel):
    """
    Paginated list envelope.

    Returned by any endpoint that serves a slice of a larger collection.
    ``total`` is the full count across all pages so the client can render
    a pager without a second request.
    """

    items: list = Field(default_factory=list, description="Items in the current page")
    total: int = Field(..., ge=0, description="Total number of items across all pages")
    page: int = Field(..., ge=1, description="Current 1-based page number")
    page_size: int = Field(..., ge=1, description="Items per page used for this response")
