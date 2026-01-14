"""
Login interface component for QmanAssist.
Provides user authentication via LDAP/Active Directory.
"""

import streamlit as st
from loguru import logger

from src.core.auth import authenticate_user, SessionManager
from config.settings import get_settings


def render_login_page():
    """Render the login page."""
    settings = get_settings()

    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("## 🔐 QmanAssist Login")
        st.markdown("---")

        # Show LDAP server info (helpful for debugging)
        if settings.ldap_server:
            st.info(
                f"**Authentication Server:** {settings.ldap_server}\n\n"
                f"**Domain:** {settings.ldap_domain or 'N/A'}"
            )

        # Login form
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input(
                "Username",
                placeholder="Enter your domain username",
                help="Enter your username without the domain (e.g., 'jsmith', not 'NEOCON\\jsmith')",
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
            )

            st.markdown("")  # Spacing

            col_login, col_help = st.columns([1, 1])

            with col_login:
                submit = st.form_submit_button(
                    "🔓 Login",
                    use_container_width=True,
                    type="primary",
                )

            with col_help:
                if st.form_submit_button("❓ Help", use_container_width=True):
                    st.session_state.show_help = True

        # Handle login
        if submit:
            if not username or not password:
                st.error("⚠️ Please enter both username and password")
            else:
                with st.spinner("Authenticating..."):
                    result = authenticate_user(username, password)

                    if result["success"]:
                        # Store authentication in session
                        SessionManager.login(st.session_state, result)

                        st.success(
                            f"✅ Welcome, {result.get('display_name', username)}!"
                        )

                        # Show groups if available
                        if result.get("groups"):
                            groups_str = ", ".join(result["groups"][:5])
                            if len(result["groups"]) > 5:
                                groups_str += f" (+{len(result['groups']) - 5} more)"
                            st.info(f"**Groups:** {groups_str}")

                        # Rerun to show main app
                        st.rerun()
                    else:
                        error_msg = result.get("error", "Authentication failed")
                        st.error(f"❌ {error_msg}")
                        logger.warning(
                            f"Failed login attempt for user: {username} - {error_msg}"
                        )

        # Show help dialog
        if getattr(st.session_state, "show_help", False):
            st.markdown("---")
            st.markdown("### 📖 Login Help")

            st.markdown(
                """
                **How to login:**
                1. Enter your **domain username** (without domain prefix)
                   - ✅ Correct: `jsmith`
                   - ❌ Wrong: `NEOCON\\jsmith` or `jsmith@neocon.local`

                2. Enter your **domain password**

                3. Click **Login**

                **Troubleshooting:**
                - Ensure you're on the company network or VPN
                - Use the same credentials you use for Windows login
                - Contact IT if you continue to have issues

                **Security:**
                - All authentication is encrypted using LDAPS
                - Sessions expire after 8 hours of inactivity
                - Your password is never stored
                """
            )

            if st.button("Close Help"):
                st.session_state.show_help = False
                st.rerun()

        # Footer
        st.markdown("---")
        st.markdown(
            f"""
            <div style='text-align: center; color: gray; font-size: 0.8em;'>
                <p>🔒 Secure authentication via {settings.ldap_server}</p>
                <p>QmanAssist - Quality Documentation Assistant</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_user_info():
    """Render user information and logout button in sidebar."""
    if not SessionManager.is_authenticated(st.session_state):
        return

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 👤 User Info")

    # User details
    display_name = getattr(st.session_state, "display_name", "Unknown")
    username = getattr(st.session_state, "username", "")
    email = getattr(st.session_state, "email", "")

    st.sidebar.markdown(f"**{display_name}**")
    if username:
        st.sidebar.markdown(f"`{username}`")
    if email:
        st.sidebar.markdown(f"📧 {email}")

    # Show groups in expander
    groups = getattr(st.session_state, "groups", [])
    if groups:
        with st.sidebar.expander("👥 Groups", expanded=False):
            for group in groups[:10]:  # Show first 10 groups
                st.markdown(f"- {group}")
            if len(groups) > 10:
                st.markdown(f"*...and {len(groups) - 10} more*")

    # Logout button
    st.sidebar.markdown("")  # Spacing
    if st.sidebar.button("🚪 Logout", use_container_width=True, type="secondary"):
        SessionManager.logout(st.session_state)
        st.rerun()


def require_authentication():
    """Require authentication to access the app.

    This function should be called at the start of main app pages.
    If not authenticated, it shows the login page and stops execution.

    Returns:
        True if authenticated, does not return if not authenticated
    """
    settings = get_settings()

    # Skip authentication if disabled
    if not settings.auth_enabled:
        return True

    # Check if user is authenticated
    if not SessionManager.is_authenticated(st.session_state):
        render_login_page()
        st.stop()  # Stop execution if not authenticated

    return True
