"""
SmartFood Platform — Authentication & Session Management Module
Handles password hashing via bcrypt, user login, signup validation,
and role-based session states in Streamlit.
"""

from typing import Optional, Dict, Any
import bcrypt
import streamlit as st


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with salt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def init_session() -> None:
    """Initializes Streamlit authentication session state if not already set."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user" not in st.session_state:
        st.session_state["user"] = None


def login_user(user_data: Dict[str, Any]) -> None:
    """Sets session state for an authenticated user."""
    st.session_state["authenticated"] = True
    st.session_state["user"] = {
        "id": int(user_data["id"]),
        "email": str(user_data["email"]),
        "name": str(user_data["name"]),
        "org_name": str(user_data["org_name"]),
        "role": str(user_data["role"]),
        "phone": str(user_data.get("phone", "")),
        "address": str(user_data.get("address", "")),
        "city": str(user_data.get("city", "Bangalore")),
        "capacity": int(user_data.get("capacity", 100)),
        "fssai_no": str(user_data.get("fssai_no") or ""),
    }


def logout_user() -> None:
    """Clears authentication session state."""
    st.session_state["authenticated"] = False
    st.session_state["user"] = None


def get_current_user() -> Optional[Dict[str, Any]]:
    """Returns the currently logged-in user dictionary, or None."""
    init_session()
    if st.session_state.get("authenticated", False):
        return st.session_state.get("user")
    return None


def is_authenticated() -> bool:
    """Checks if a user is currently logged in."""
    init_session()
    return st.session_state.get("authenticated", False)


def has_role(role: str) -> bool:
    """Checks if the logged-in user has the specified role."""
    user = get_current_user()
    if not user:
        return False
    if role == "canteen_or_restro":
        return user["role"] in ["canteen", "restaurant"]
    return user["role"] == role
