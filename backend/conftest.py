"""
pytest conftest - sets test environment variables before any imports.
"""
import os

# Set test environment before app imports
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault(
    "SECRET_KEY",
    "test-secret-key-for-pytest-only-not-for-production-use-this-is-32chars"
)
