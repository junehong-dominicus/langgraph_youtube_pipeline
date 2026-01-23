import sys
import os
import pytest

# Ensure the project root is in the python path so imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@pytest.fixture
def default_state():
    """Returns a default valid state for testing."""
    return {
        "topic": "Test Topic",
        "content_type": "long",
        "retry_count": 0,
        "error": None
    }