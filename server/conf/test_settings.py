"""Test settings — inherits from main settings but forces in-memory DB,
ensures `web` importability, and installs the ROP `website` app."""

import sys
import os

# Ensure `newworld/` is on sys.path so that `web` (newworld/web)
# can be imported as a top-level package by Evennia's ROOT_URLCONF.
_project_parent = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _project_parent not in sys.path:
    sys.path.insert(0, _project_parent)

from newworld.server.conf.settings import *  # noqa: E402, F403

# Override database to in-memory SQLite so tests never touch
# the Evennia db3 file under /root/rop.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Ensure the ROP website app (Ban, ReservedName, AuditLog models)
# is installed so its tables are created during test setup.
if "web.website" not in INSTALLED_APPS:  # noqa: F821
    INSTALLED_APPS = list(INSTALLED_APPS) + ["web.website"]  # noqa: F821

# Add ROP custom template directories to the search path.
_templates_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "web", "templates")
)
if TEMPLATES and len(TEMPLATES) > 0 and "DIRS" in TEMPLATES[0]:  # noqa: F821
    dirs = list(TEMPLATES[0]["DIRS"])  # noqa: F821
    if _templates_dir in dirs:
        dirs.remove(_templates_dir)
    dirs.insert(0, _templates_dir)
    TEMPLATES[0]["DIRS"] = dirs  # noqa: F821
