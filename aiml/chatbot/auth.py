"""
Role-Based Authorization Module for CMS AI Assistant.
Provides flexible role checks for AI Assistant access control.
"""

from functools import wraps
import os
from flask import session, jsonify

# Configuration flag for role restriction.
# Set RESTRICT_ASSISTANT_ROLES = True to restrict assistant access to Super Admin (ORD) and Admin roles only.
RESTRICT_ASSISTANT_ROLES = os.getenv("RESTRICT_ASSISTANT_ROLES", "false").lower() in ("true", "1", "yes")

# List of allowed roles when restriction is enabled
ALLOWED_ROLES = {"ORD", "Admin"}

def is_role_authorized(role: str) -> bool:
    """
    Check if a given user role is authorized to use the AI Assistant.
    If RESTRICT_ASSISTANT_ROLES is False, all authenticated users are allowed.
    If RESTRICT_ASSISTANT_ROLES is True, only roles in ALLOWED_ROLES are allowed.
    """
    if not RESTRICT_ASSISTANT_ROLES:
        return True
    if not role:
        return False
    return role.strip() in ALLOWED_ROLES


def require_chatbot_access(f):
    """
    Flask route decorator to enforce AI Assistant access permissions.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_role = session.get("role")
        if not is_role_authorized(user_role):
            return jsonify({
                "success": False,
                "message": f"Access denied. AI Assistant is restricted to Super Admin and Admin roles."
            }), 403
        return f(*args, **kwargs)
    return decorated_function
