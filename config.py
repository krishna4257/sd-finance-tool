"""
Application configuration module.

This module centralizes environment‐dependent configuration values so they
can be modified in a single place. Sensitive values such as the secret
key or database locations should not be hard coded in the main
application logic. Instead, they are read from environment variables
with sensible fallbacks for local development.

Attributes
----------
BASE_DIR : str
    The absolute path to the directory containing this file. Used as
    the default base for relative paths.
SQLITE_FOLDER : str
    Directory containing all village SQLite databases. Defaults to a
    ``databases`` folder within the project. Can be overridden via
    the ``SQLITE_FOLDER`` environment variable.
SECRET_KEY : str
    Flask's secret key. Defaults to ``development-secret-key`` for
    development; should be overridden in production via the
    ``SECRET_KEY`` environment variable.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Allow the location of the database directory to be configured via an
# environment variable. If not provided, default to a ``databases``
# directory adjacent to this module. This makes the application more
# portable and avoids hard coding absolute paths.
SQLITE_FOLDER = os.environ.get(
    "SQLITE_FOLDER",
    os.path.join(BASE_DIR, "databases"),
)

# Flask requires a secret key to sign session cookies. In
# development we provide a default, but in production it should be
# overridden via the environment for security.
SECRET_KEY = os.environ.get("SECRET_KEY", "development-secret-key")

RUN_MODE = os.environ.get("RUN_MODE", "cloud")  # default cloud
