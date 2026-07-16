"""
Audit logs router.

Re-exports the audit log router from the audit package,
providing a paginated endpoint for querying audit trail entries.
"""

from app.audit.router import router

__all__ = ["router"]
