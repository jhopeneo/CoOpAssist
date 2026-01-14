"""
LDAP/Active Directory authentication for QmanAssist.
Provides secure authentication against Windows domain controllers.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger
import ssl

from ldap3 import Server, Connection, Tls, SAFE_SYNC, ALL, SUBTREE
from ldap3.core.exceptions import (
    LDAPBindError,
    LDAPException,
    LDAPSocketOpenError,
    LDAPInvalidCredentialsResult,
)

from config.settings import get_settings


class LDAPAuthenticator:
    """Handles LDAP/AD authentication and group membership checks."""

    def __init__(self):
        """Initialize LDAP authenticator with settings."""
        self.settings = get_settings()

        if not self.settings.auth_enabled:
            logger.info("Authentication is disabled")
            return

        if not self.settings.ldap_server:
            raise ValueError("LDAP_SERVER must be configured when AUTH_ENABLED=true")

        logger.info(
            f"LDAP Authenticator initialized: server={self.settings.ldap_server}, "
            f"port={self.settings.ldap_port}, ssl={self.settings.ldap_use_ssl}"
        )

    def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user against LDAP/AD.

        Args:
            username: Username (without domain)
            password: User password

        Returns:
            Dictionary with authentication result:
            {
                "success": bool,
                "username": str,
                "display_name": str,
                "email": str,
                "groups": list,
                "error": str (if failed)
            }
        """
        if not username or not password:
            return {"success": False, "error": "Username and password are required"}

        # Clean username (remove domain if provided)
        username = username.split("@")[0].split("\\")[-1].strip()

        logger.info(f"Attempting LDAP authentication for user: {username}")

        try:
            # Build user DN based on domain
            if self.settings.ldap_domain:
                # Try domain\username format first
                user_dn = f"{self.settings.ldap_domain}\\{username}"
            else:
                # Fall back to UPN format if base DN is provided
                if self.settings.ldap_base_dn:
                    domain_suffix = self._dn_to_domain(self.settings.ldap_base_dn)
                    user_dn = f"{username}@{domain_suffix}"
                else:
                    user_dn = username

            # Create TLS configuration if using SSL
            tls_configuration = None
            if self.settings.ldap_use_ssl:
                tls_configuration = Tls(
                    validate=ssl.CERT_NONE,  # In production, use CERT_REQUIRED with proper certs
                    version=ssl.PROTOCOL_TLSv1_2,
                )

            # Connect to LDAP server
            server = Server(
                self.settings.ldap_server,
                port=self.settings.ldap_port,
                use_ssl=self.settings.ldap_use_ssl,
                tls=tls_configuration,
                get_info=ALL,
                connect_timeout=self.settings.ldap_timeout,
            )

            # Attempt to bind with user credentials
            connection = Connection(
                server,
                user=user_dn,
                password=password,
                client_strategy=SAFE_SYNC,
                auto_bind=True,
                raise_exceptions=True,
            )

            logger.info(f"User {username} authenticated successfully")

            # Get user details
            user_info = self._get_user_info(connection, username)

            # Check group membership if required
            if self.settings.ldap_require_group and self.settings.ldap_allowed_groups:
                if not self._check_group_membership(connection, user_info.get("dn")):
                    connection.unbind()
                    logger.warning(f"User {username} not in allowed groups")
                    return {
                        "success": False,
                        "error": "Access denied: User not in authorized group",
                    }

            connection.unbind()

            return {
                "success": True,
                "username": username,
                "display_name": user_info.get("display_name", username),
                "email": user_info.get("email", ""),
                "groups": user_info.get("groups", []),
                "authenticated_at": datetime.now().isoformat(),
            }

        except LDAPInvalidCredentialsResult:
            logger.warning(f"Invalid credentials for user: {username}")
            return {"success": False, "error": "Invalid username or password"}

        except LDAPBindError as e:
            logger.error(f"LDAP bind error for user {username}: {e}")
            return {"success": False, "error": "Authentication failed"}

        except LDAPSocketOpenError as e:
            logger.error(f"Cannot connect to LDAP server: {e}")
            return {
                "success": False,
                "error": f"Cannot connect to authentication server: {self.settings.ldap_server}",
            }

        except LDAPException as e:
            logger.error(f"LDAP error during authentication: {e}")
            return {"success": False, "error": "Authentication service error"}

        except Exception as e:
            logger.exception(f"Unexpected error during authentication: {e}")
            return {"success": False, "error": "Authentication failed"}

    def _get_user_info(
        self, connection: Connection, username: str
    ) -> Dict[str, Any]:
        """Retrieve user information from LDAP.

        Args:
            connection: Active LDAP connection
            username: Username to look up

        Returns:
            Dictionary with user details
        """
        if not self.settings.ldap_base_dn:
            return {"display_name": username, "email": "", "groups": []}

        try:
            # Search for user
            search_filter = self.settings.ldap_user_search_filter.format(
                username=username
            )

            connection.search(
                search_base=self.settings.ldap_base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=["displayName", "mail", "memberOf", "distinguishedName"],
            )

            if not connection.entries:
                logger.warning(f"User {username} not found in directory")
                return {"display_name": username, "email": "", "groups": []}

            entry = connection.entries[0]

            # Extract user details
            display_name = str(entry.displayName) if entry.displayName else username
            email = str(entry.mail) if entry.mail else ""
            dn = str(entry.distinguishedName) if entry.distinguishedName else ""

            # Extract group names from memberOf
            groups = []
            if entry.memberOf:
                for group_dn in entry.memberOf:
                    # Extract CN from group DN (e.g., "CN=QualityTeam,OU=..." -> "QualityTeam")
                    cn_part = str(group_dn).split(",")[0]
                    if cn_part.startswith("CN="):
                        groups.append(cn_part[3:])

            logger.debug(
                f"User info retrieved: {username} ({display_name}), groups: {groups}"
            )

            return {
                "display_name": display_name,
                "email": email,
                "groups": groups,
                "dn": dn,
            }

        except Exception as e:
            logger.error(f"Error retrieving user info: {e}")
            return {"display_name": username, "email": "", "groups": []}

    def _check_group_membership(
        self, connection: Connection, user_dn: Optional[str]
    ) -> bool:
        """Check if user is member of allowed groups.

        Args:
            connection: Active LDAP connection
            user_dn: User's distinguished name

        Returns:
            True if user is in an allowed group, False otherwise
        """
        if not self.settings.ldap_allowed_groups or not user_dn:
            return True

        allowed_groups = [
            g.strip()
            for g in self.settings.ldap_allowed_groups.split(",")
            if g.strip()
        ]

        if not allowed_groups:
            return True

        try:
            # Search for user's group memberships
            search_filter = self.settings.ldap_group_search_filter.format(
                user_dn=user_dn
            )

            connection.search(
                search_base=self.settings.ldap_base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=["cn"],
            )

            user_groups = [str(entry.cn) for entry in connection.entries if entry.cn]

            # Check if user is in any allowed group
            for group in allowed_groups:
                if group in user_groups:
                    logger.info(f"User authorized via group: {group}")
                    return True

            logger.warning(
                f"User not in allowed groups. User groups: {user_groups}, "
                f"Allowed: {allowed_groups}"
            )
            return False

        except Exception as e:
            logger.error(f"Error checking group membership: {e}")
            return False

    def _dn_to_domain(self, dn: str) -> str:
        """Convert DN to domain name (e.g., DC=neocon,DC=local -> neocon.local).

        Args:
            dn: Distinguished name

        Returns:
            Domain name
        """
        parts = [p.split("=")[1] for p in dn.split(",") if p.startswith("DC=")]
        return ".".join(parts)


class SessionManager:
    """Manages user sessions in Streamlit."""

    @staticmethod
    def is_authenticated(session_state: Any) -> bool:
        """Check if user is authenticated.

        Args:
            session_state: Streamlit session state

        Returns:
            True if authenticated and session is valid
        """
        settings = get_settings()

        if not settings.auth_enabled:
            return True  # No auth required

        if not hasattr(session_state, "authenticated") or not session_state.authenticated:
            return False

        # Check session timeout
        if hasattr(session_state, "authenticated_at"):
            auth_time = datetime.fromisoformat(session_state.authenticated_at)
            timeout = timedelta(minutes=settings.session_timeout_minutes)

            if datetime.now() - auth_time > timeout:
                logger.info("Session expired")
                return False

        return True

    @staticmethod
    def login(session_state: Any, auth_result: Dict[str, Any]) -> None:
        """Store authentication information in session.

        Args:
            session_state: Streamlit session state
            auth_result: Authentication result dictionary
        """
        session_state.authenticated = True
        session_state.username = auth_result.get("username", "")
        session_state.display_name = auth_result.get("display_name", "")
        session_state.email = auth_result.get("email", "")
        session_state.groups = auth_result.get("groups", [])
        session_state.authenticated_at = auth_result.get(
            "authenticated_at", datetime.now().isoformat()
        )

        logger.info(f"User {session_state.username} logged in")

    @staticmethod
    def logout(session_state: Any) -> None:
        """Clear authentication information from session.

        Args:
            session_state: Streamlit session state
        """
        username = getattr(session_state, "username", "unknown")

        session_state.authenticated = False
        session_state.username = None
        session_state.display_name = None
        session_state.email = None
        session_state.groups = []
        session_state.authenticated_at = None

        logger.info(f"User {username} logged out")


# Convenience functions
def authenticate_user(username: str, password: str) -> Dict[str, Any]:
    """Authenticate user against LDAP.

    Args:
        username: Username
        password: Password

    Returns:
        Authentication result dictionary
    """
    authenticator = LDAPAuthenticator()
    return authenticator.authenticate(username, password)


def is_auth_enabled() -> bool:
    """Check if authentication is enabled.

    Returns:
        True if authentication is enabled
    """
    settings = get_settings()
    return settings.auth_enabled
