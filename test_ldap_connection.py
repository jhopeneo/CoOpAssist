#!/usr/bin/env python3
"""
Test LDAP/AD connection and configuration.
Use this script to verify your LDAP settings before deploying.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import get_settings
from src.core.auth import LDAPAuthenticator
from loguru import logger


def test_ldap_connection():
    """Test LDAP connection and configuration."""
    settings = get_settings()

    print("=" * 70)
    print("LDAP/AD Connection Test")
    print("=" * 70)
    print()

    # Check if auth is enabled
    if not settings.auth_enabled:
        print("❌ Authentication is DISABLED")
        print()
        print("To enable authentication, set AUTH_ENABLED=true in your .env file")
        print("Then configure the other LDAP settings.")
        return False

    print("✅ Authentication is ENABLED")
    print()

    # Display configuration
    print("Configuration:")
    print(f"  Server: {settings.ldap_server or 'NOT SET'}")
    print(f"  Port: {settings.ldap_port}")
    print(f"  Use SSL: {settings.ldap_use_ssl}")
    print(f"  Domain: {settings.ldap_domain or 'NOT SET'}")
    print(f"  Base DN: {settings.ldap_base_dn or 'NOT SET'}")
    print(f"  Allowed Groups: {settings.ldap_allowed_groups or 'ANY (no restrictions)'}")
    print(f"  Require Group: {settings.ldap_require_group}")
    print()

    # Check required settings
    if not settings.ldap_server:
        print("❌ LDAP_SERVER is not configured")
        return False

    if not settings.ldap_domain and not settings.ldap_base_dn:
        print("❌ Either LDAP_DOMAIN or LDAP_BASE_DN must be configured")
        return False

    print("✅ All required settings are configured")
    print()

    # Test connection
    print("-" * 70)
    print("Testing LDAP Connection...")
    print("-" * 70)
    print()

    try:
        # Try to initialize authenticator (tests connection)
        authenticator = LDAPAuthenticator()
        print("✅ LDAP Authenticator initialized successfully")
        print()

        # Prompt for test credentials
        print("Enter test credentials to verify authentication:")
        print("(Your password will not be stored or logged)")
        print()

        username = input("Username (without domain): ").strip()
        if not username:
            print("❌ No username provided, skipping authentication test")
            return True

        import getpass

        password = getpass.getpass("Password: ")
        if not password:
            print("❌ No password provided, skipping authentication test")
            return True

        print()
        print("Attempting authentication...")
        print()

        result = authenticator.authenticate(username, password)

        if result["success"]:
            print("🎉 Authentication SUCCESSFUL!")
            print()
            print("User Details:")
            print(f"  Username: {result.get('username')}")
            print(f"  Display Name: {result.get('display_name')}")
            print(f"  Email: {result.get('email', 'N/A')}")

            groups = result.get("groups", [])
            if groups:
                print(f"  Groups ({len(groups)}):")
                for group in groups[:10]:
                    print(f"    - {group}")
                if len(groups) > 10:
                    print(f"    ... and {len(groups) - 10} more")
            else:
                print("  Groups: None found")

            print()
            print("✅ LDAP configuration is working correctly!")
            return True
        else:
            print("❌ Authentication FAILED")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            print()
            print("Possible causes:")
            print("  - Incorrect credentials")
            print("  - User not in allowed groups (if LDAP_REQUIRE_GROUP=true)")
            print("  - Domain controller not reachable")
            print("  - LDAP settings incorrect")
            return False

    except Exception as e:
        print(f"❌ Error during LDAP test: {e}")
        logger.exception("Full error details:")
        print()
        print("Possible causes:")
        print("  - Cannot connect to domain controller")
        print("  - Firewall blocking LDAP port")
        print("  - LDAP_SERVER hostname not resolvable")
        print("  - SSL certificate issues")
        return False


def main():
    """Main entry point."""
    print()
    success = test_ldap_connection()
    print()
    print("=" * 70)

    if success:
        print("✅ LDAP configuration test PASSED")
        print()
        print("Your QmanAssist instance is ready to use LDAP authentication!")
        print("Users can now log in with their domain credentials.")
    else:
        print("❌ LDAP configuration test FAILED")
        print()
        print("Please review the errors above and check:")
        print("  1. Your .env file configuration")
        print("  2. Network connectivity to domain controller")
        print("  3. LDAP/AD settings match your domain")
        print()
        print("See docs/LDAP_AUTHENTICATION_SETUP.md for detailed help.")

    print("=" * 70)
    print()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
