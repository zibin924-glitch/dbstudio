"""
Query router.

Re-exports the full query router from the business module,
providing endpoints for the SQL query console.
"""

from app.query.router import router

__all__ = ["router"]
