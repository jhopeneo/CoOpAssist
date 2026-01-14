# LDAP/Active Directory Authentication Setup Guide

This guide explains how to configure QmanAssist to authenticate users against your Windows Active Directory domain controller.

## Overview

QmanAssist supports secure LDAP/AD authentication with the following features:
- **LDAPS (LDAP over SSL)** for encrypted authentication
- **Group-based access control** to restrict access to specific AD groups
- **Session management** with configurable timeout
- **User profile display** showing name, email, and group memberships
- **Flexible configuration** via environment variables

## Prerequisites

1. **Windows Domain Controller** accessible from the Docker host
2. **Network connectivity** between Docker container and domain controller (port 636 for LDAPS)
3. **Domain user credentials** for testing
4. (Optional) **Service account** for advanced group lookups

## Quick Start Configuration

### Step 1: Edit `.env` File

Copy and edit the `.env` file in your QmanAssist directory:

```bash
# Enable authentication
AUTH_ENABLED=true

# Domain Controller Configuration
LDAP_SERVER=dc.neocon.local          # Your DC hostname or IP
LDAP_PORT=636                         # 636 for LDAPS, 389 for LDAP
LDAP_USE_SSL=true                     # Always use SSL in production
LDAP_DOMAIN=NEOCON                    # Your AD domain name
LDAP_BASE_DN=DC=neocon,DC=local      # Base DN for user searches
```

### Step 2: Rebuild Docker Container

```bash
docker compose down
docker compose up --build -d
```

### Step 3: Test Login

1. Navigate to `http://localhost:8501`
2. You should see a login page
3. Enter your domain credentials (username without domain prefix)
4. Click **Login**

## Configuration Options

### Basic Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTH_ENABLED` | Yes | `false` | Enable/disable authentication |
| `LDAP_SERVER` | Yes | - | Domain controller hostname or IP |
| `LDAP_PORT` | No | `636` | LDAP port (389 or 636) |
| `LDAP_USE_SSL` | No | `true` | Use LDAPS for encryption |
| `LDAP_DOMAIN` | Yes | - | AD domain name (e.g., NEOCON) |
| `LDAP_BASE_DN` | Yes | - | Base DN (e.g., DC=neocon,DC=local) |

### Advanced Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LDAP_BIND_USER` | No | - | Service account DN for group lookups |
| `LDAP_BIND_PASSWORD` | No | - | Service account password |
| `LDAP_ALLOWED_GROUPS` | No | - | Comma-separated list of allowed AD groups |
| `LDAP_REQUIRE_GROUP` | No | `false` | Require group membership |
| `LDAP_TIMEOUT` | No | `10` | Connection timeout in seconds |
| `SESSION_TIMEOUT_MINUTES` | No | `480` | Session timeout (8 hours default) |

### Search Filter Settings (Advanced)

These control how users and groups are searched in AD. Use defaults unless you have custom requirements:

| Variable | Default | Description |
|----------|---------|-------------|
| `LDAP_USER_SEARCH_FILTER` | `(sAMAccountName={username})` | How to find users |
| `LDAP_GROUP_SEARCH_FILTER` | `(member={user_dn})` | How to find group memberships |

## Configuration Examples

### Example 1: Basic Setup (No Group Restrictions)

Allow any domain user to log in:

```bash
AUTH_ENABLED=true
LDAP_SERVER=dc.neocon.local
LDAP_PORT=636
LDAP_USE_SSL=true
LDAP_DOMAIN=NEOCON
LDAP_BASE_DN=DC=neocon,DC=local
```

### Example 2: Restrict to Specific Groups

Only allow members of QualityTeam or Admins groups:

```bash
AUTH_ENABLED=true
LDAP_SERVER=dc.neocon.local
LDAP_PORT=636
LDAP_USE_SSL=true
LDAP_DOMAIN=NEOCON
LDAP_BASE_DN=DC=neocon,DC=local
LDAP_ALLOWED_GROUPS=QualityTeam,Admins
LDAP_REQUIRE_GROUP=true
```

### Example 3: Using IP Address

If DNS resolution doesn't work, use the DC IP address:

```bash
AUTH_ENABLED=true
LDAP_SERVER=192.168.95.10
LDAP_PORT=636
LDAP_USE_SSL=true
LDAP_DOMAIN=NEOCON
LDAP_BASE_DN=DC=neocon,DC=local
```

### Example 4: Non-SSL (Testing Only - NOT RECOMMENDED)

For testing in isolated environments only:

```bash
AUTH_ENABLED=true
LDAP_SERVER=dc.neocon.local
LDAP_PORT=389
LDAP_USE_SSL=false
LDAP_DOMAIN=NEOCON
LDAP_BASE_DN=DC=neocon,DC=local
```

**⚠️ WARNING:** Never use non-SSL LDAP in production! Passwords will be sent in clear text.

## How to Find Your Settings

### Finding Your Domain Controller

**Option 1: On a domain-joined Windows machine**
```cmd
echo %LOGONSERVER%
```
This shows your DC name (remove the `\\` prefix)

**Option 2: Using nslookup**
```cmd
nslookup -type=SRV _ldap._tcp.dc._msdcs.yourdomain.local
```

**Option 3: Check DNS**
Your domain controller is typically named `dc.yourdomain.local`

### Finding Your Base DN

Convert your domain name to DN format:
- Domain: `neocon.local` → Base DN: `DC=neocon,DC=local`
- Domain: `company.com` → Base DN: `DC=company,DC=com`
- Domain: `sub.company.com` → Base DN: `DC=sub,DC=company,DC=com`

### Finding AD Group Names

**Option 1: Active Directory Users and Computers**
1. Open `dsa.msc` on a domain controller or admin workstation
2. Navigate to your groups OU
3. Right-click a group → Properties
4. Use the **CN (Common Name)** value

**Option 2: PowerShell**
```powershell
Get-ADGroup -Filter "Name -like '*Quality*'" | Select Name
```

## Troubleshooting

### Issue: "Cannot connect to authentication server"

**Causes:**
- Domain controller hostname not resolvable
- Firewall blocking port 636
- Docker container can't reach DC network

**Solutions:**
1. Try using DC IP address instead of hostname
2. Verify port 636 is open: `telnet dc.neocon.local 636`
3. Add DC to docker-compose.yml extra_hosts (already configured)
4. Check if DC is on same network/VPN

### Issue: "Invalid username or password"

**Causes:**
- Wrong credentials
- Username format incorrect
- Account locked/disabled
- Domain name wrong

**Solutions:**
1. Verify credentials work on a Windows machine
2. Enter username WITHOUT domain prefix (just `jsmith`, not `NEOCON\\jsmith`)
3. Check LDAP_DOMAIN matches your actual domain
4. Verify account is enabled in AD

### Issue: "Access denied: User not in authorized group"

**Causes:**
- User not member of allowed groups
- Group name misspelled
- Group membership not updated

**Solutions:**
1. Verify user is in the group using AD Users and Computers
2. Check LDAP_ALLOWED_GROUPS spelling matches AD exactly
3. User may need to log off/on Windows for group changes to apply

### Issue: "Session expired"

**Cause:**
- Session timeout reached (default 8 hours)

**Solution:**
- Increase SESSION_TIMEOUT_MINUTES if needed
- User just needs to log in again

### Testing LDAP Connectivity

**From Docker Container:**
```bash
# Enter container
docker exec -it qmanassist bash

# Test LDAPS connection
python -c "
import ldap3
server = ldap3.Server('dc.neocon.local', port=636, use_ssl=True)
print('Connected!' if server else 'Failed')
"
```

## Security Best Practices

### ✅ Recommended

1. **Always use LDAPS (port 636)** - encrypts authentication traffic
2. **Use group-based access control** - limit who can access the system
3. **Set appropriate session timeouts** - balance security and convenience
4. **Monitor authentication logs** - check for unauthorized access attempts
5. **Use service accounts sparingly** - only if you need advanced group lookups

### ❌ Not Recommended

1. **Don't use plain LDAP (port 389)** in production - passwords sent in clear text
2. **Don't store .env file in version control** - contains sensitive settings
3. **Don't disable SSL certificate validation** in production
4. **Don't use overly permissive group settings** - be specific about who can access

## User Experience

### Login Flow

1. User navigates to QmanAssist URL
2. Sees professional login page with:
   - Domain controller information
   - Username and password fields
   - Help button for instructions
3. Enters domain credentials
4. System authenticates against AD
5. If successful:
   - User sees welcome message
   - Groups displayed
   - Redirected to chat interface
6. If failed:
   - Clear error message
   - User can try again

### Logged-In Experience

- **Sidebar shows user info:**
  - Display name
  - Username
  - Email address
  - AD group memberships
- **Logout button available**
- **Session persists until:**
  - User logs out
  - Browser closes
  - Session timeout reached

## Architecture Details

### Authentication Flow

```
User → Streamlit UI → auth.py → Domain Controller
                               ← User DN + Attributes
         ← Success/Failure
```

### Components

1. **`src/core/auth.py`**
   - `LDAPAuthenticator` class handles all LDAP operations
   - `SessionManager` class manages Streamlit session state
   - Supports both simple bind (user credentials) and service account binding

2. **`src/ui/components/login.py`**
   - Login page UI
   - User info sidebar widget
   - Session validation

3. **`config/settings.py`**
   - All LDAP configuration loaded from environment variables
   - Type-safe configuration with Pydantic

### Security Features

- **Encrypted communication** via LDAPS
- **No password storage** - passwords never logged or stored
- **Session tokens** - unique per browser session
- **Timeout enforcement** - automatic logout after inactivity
- **Group-based authorization** - optional access control
- **Audit logging** - all authentication attempts logged

## Support and Maintenance

### Monitoring Authentication

Check Docker logs for authentication events:

```bash
# View recent authentication logs
docker logs qmanassist | grep -i "auth"

# Follow logs in real-time
docker logs -f qmanassist | grep -i "ldap\|auth"
```

### Updating Configuration

After changing `.env` settings:

```bash
# Restart container to apply changes
docker compose restart

# Or rebuild if you changed code
docker compose down
docker compose up --build -d
```

### Disabling Authentication

To temporarily disable authentication:

```bash
# In .env file
AUTH_ENABLED=false

# Restart
docker compose restart
```

## Need Help?

If you encounter issues:

1. Check Docker logs: `docker logs qmanassist`
2. Verify connectivity to domain controller
3. Test credentials on a Windows machine first
4. Review this guide's troubleshooting section
5. Contact your IT administrator for AD-specific questions

## Example .env File

Here's a complete example `.env` file with LDAP configured:

```bash
# LLM Configuration
OPENAI_API_KEY=sk-your-key-here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o

# Authentication
AUTH_ENABLED=true
LDAP_SERVER=dc.neocon.local
LDAP_PORT=636
LDAP_USE_SSL=true
LDAP_DOMAIN=NEOCON
LDAP_BASE_DN=DC=neocon,DC=local
LDAP_ALLOWED_GROUPS=QualityTeam,Engineers
LDAP_REQUIRE_GROUP=true
SESSION_TIMEOUT_MINUTES=480

# Other settings...
QMANUALS_PATH=Q:\
CHROMA_DB_PATH=./data/chroma_db
```

Save this as `.env` in your QmanAssist directory, then restart the container.
