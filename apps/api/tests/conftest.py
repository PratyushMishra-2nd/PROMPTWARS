"""Shared pytest fixtures."""
import os
# Set a dummy key so config doesn't warn during tests
os.environ.setdefault("GEMINI_API_KEY", "test-dummy-key")
