"""
Connections router.

Re-exports the full connections router from the business module,
providing CRUD endpoints for managing database connection configurations.
"""

from app.connections.router import router

__all__ = ["router"]
