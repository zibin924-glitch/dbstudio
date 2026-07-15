"""
API Gateway router.

Re-exports the full API gateway router from the business module,
providing endpoints for publishing and executing SQL-based REST APIs.
"""

from app.api_gateway.router import router, dynamic_router

__all__ = ["router", "dynamic_router"]
