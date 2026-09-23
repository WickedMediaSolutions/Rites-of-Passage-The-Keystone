r"""
Evennia settings file.

The available options are found in the default settings file found
here:

https://www.evennia.com/docs/latest/Setup/Settings-Default.html

Remember:

Don't copy more from the default file than you actually intend to
change; this will make sure that you don't overload upstream updates
unnecessarily.

When changing a setting requiring a file system path (like
path/to/actual/file.py), use GAME_DIR and EVENNIA_DIR to reference
your game folder and the Evennia library folders respectively. Python
paths (path.to.module) should be given relative to the game's root
folder (typeclasses.foo) whereas paths within the Evennia library
needs to be given explicitly (evennia.foo).

If you want to share your game dir, including its settings, you can
put secret game- or server-specific settings in secret_settings.py.

"""

# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *

######################################################################
# Evennia base server config
######################################################################

# This is the name of your game. Make it catchy!
SERVERNAME = "Rites of Passage"


######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")


# ============================================================
# NEW WORLD PORT CONFIGURATION
# ============================================================

TELNET_PORTS = [4010]

WEBSERVER_PORTS = [(4011, 8011)]

WEBSOCKET_CLIENT_PORT = 4012

AMP_PORT = 4026


# ============================================================
# FACTION STARTING ROOMS
# ============================================================
#
# Maps faction identifiers ("good", "evil") to room world IDs.
# Set each value to the room_id string once the faction-specific
# starting rooms are built.
#
# None = not yet configured → character creation will display a
# builder-facing message instead of placing the character.

FACTION_STARTING_ROOMS: dict[str, str | None] = {
    "good": "#885",
    "evil": "#928",
}


# ============================================================
# ROP PHASE 3 — PORTAL AUTH SETTINGS
# ============================================================

# Enable new account registration through the portal
NEW_ACCOUNT_REGISTRATION_ENABLED = True

# Where logged-in players should land
LOGIN_REDIRECT_URL = "/dashboard/"

# Where to send users after logout
LOGOUT_REDIRECT_URL = "/"

# ============================================================
# ROP PHASE 3b — CSRF / PRODUCTION SECURITY
# ============================================================
#
# Root cause of registration CSRF 403:
# Django 4.0+ requires CSRF_TRUSTED_ORIGINS for HTTPS requests.
# Evennia's settings_default.py does not set this. Without it,
# the CsrfViewMiddleware rejects ALL HTTPS-origin POST requests
# because the Origin/Referer header doesn't match any trusted origin.
#
# Additionally, when behind a reverse-proxy that terminates SSL,
# SECURE_PROXY_SSL_HEADER tells Django the original request was
# HTTPS so cookies and redirects use the correct scheme.

# Trusted origins for CSRF validation (minimum production origin only)
CSRF_TRUSTED_ORIGINS = [
    "https://ritesrpg.com",
]

# Handle reverse-proxy SSL termination (nginx, HAProxy, etc.)
# The header below is the industry-standard convention.
# Remove or adjust if your proxy uses a different header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Secure cookies for HTTPS deployment
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# ============================================================
# ROP PHASE 10 — PRODUCTION INTEGRATION FIXES
# ============================================================

import os

# 1. Statics — clear obsolete STATICFILES_DIRS pointing at nonexistent
#    web/static/.  Evennia's web server serves static files from
#    STATIC_ROOT (server/.static/) directly, and the AppDirectoriesFinder
#    handles per-app static directories.
STATICFILES_DIRS = [os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "web", "static"))]

# 2. Ensure production template configuration gives the project
#    web/templates/ directory precedence over Evennia defaults.
#    Matches the test_settings.py pattern for deterministic ordering.
_templates_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "web", "templates")
)
if TEMPLATES and len(TEMPLATES) > 0 and "DIRS" in TEMPLATES[0]:
    dirs = list(TEMPLATES[0]["DIRS"])
    if _templates_dir in dirs:
        dirs.remove(_templates_dir)
    dirs.insert(0, _templates_dir)
    TEMPLATES[0]["DIRS"] = dirs

# 3. Install the ROP website app so models (Ban, AuditLog, ReservedName)
#    and their migration are discoverable.
if "web.website" not in INSTALLED_APPS:
    INSTALLED_APPS = list(INSTALLED_APPS) + ["web.website"]

WEBSOCKET_CLIENT_URL = "wss://ritesrpg.com/ws/"
