import pytest
from langgraph_youtube_pipeline.graph import route_content_type, should_retry, app

def test_app_compilation():
    """Test that the app is compiled and ready for execution."""
    assert app is not None
    # Verify it has the invoke method (basic check for a compiled graph)
    assert hasattr(app, "invoke")

# --- Routing Logic Tests ---

def test_route_content_type_long():
    """Test routing for long-form content."""
    state = {"content_type": "long"}
    result = route_content_type(state)
    assert result == ["script_generator"]

def test_route_content_type_short():
    """Test routing for short-form content."""
    state = {"content_type": "short"}
    result = route_content_type(state)
    assert result == ["short_script_generator"]

def test_route_content_type_both():
    """Test routing for both content types (parallel execution)."""
    state = {"content_type": "both"}
    result = route_content_type(state)
    # Check that both entry points are returned
    assert "script_generator" in result
    assert "short_script_generator" in result
    assert len(result) == 2

def test_route_content_type_default():
    """Test default routing when content_type is missing."""
    state = {}
    # Should default to long form
    result = route_content_type(state)
    assert result == ["script_generator"]

# --- Retry Logic Tests ---

def test_should_retry_logic_no_error():
    """Test retry logic when there is no error."""
    state = {"error": None, "retry_count": 0}
    assert should_retry(state) == "next"

def test_should_retry_logic_retry():
    """Test retry logic when error exists and retry count is under limit."""
    assert should_retry({"error": "Error", "retry_count": 0}) == "retry"
    assert should_retry({"error": "Error", "retry_count": 1}) == "retry"

def test_should_retry_logic_max_retries():
    """Test retry logic when max retries reached."""
    # Limit is < 2, so 2 should fail/proceed to next
    assert should_retry({"error": "Error", "retry_count": 2}) == "next"
    assert should_retry({"error": "Error", "retry_count": 3}) == "next"