"""
Explorer router.

Re-exports the full explorer router from the business module,
providing endpoints for browsing remote database structure.
"""

from app.explorer.router import router

__all__ = ["router"]
