import pytest
from graph import app

def test_pipeline_execution_long(default_state):
    """Test full execution of the long-form pipeline."""
    state = default_state.copy()
    state["topic"] = "Long Form Test"
    
    final_state = app.invoke(state)
    
    assert final_state["content_type"] == "long"
    assert final_state["upload_status"] == "success"
    # Ensure short form artifacts are not present
    assert final_state.get("short_upload_status") is None

def test_pipeline_execution_short(default_state):
    """Test full execution of the short-form pipeline."""
    state = default_state.copy()
    state["topic"] = "Short Form Test #Shorts"
    
    final_state = app.invoke(state)
    
    assert final_state["content_type"] == "short"
    assert final_state["short_upload_status"] == "success"
    # Ensure long form artifacts are not present
    assert final_state.get("upload_status") is None

def test_pipeline_execution_both(default_state):
    """Test full execution of both pipelines in parallel."""
    state = default_state.copy()
    state["topic"] = "Both Forms Test (both)"
    
    final_state = app.invoke(state)
    
    assert final_state["content_type"] == "both"
    assert final_state["upload_status"] == "success"
    assert final_state["short_upload_status"] == "success"