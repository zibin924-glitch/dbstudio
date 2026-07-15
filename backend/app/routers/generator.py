"""
Generator router.

Re-exports the full generator router from the business module,
providing endpoints for documentation and code generation.
"""

from app.generator.router import router

__all__ = ["router"]
