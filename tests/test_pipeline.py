import pytest
from langgraph_youtube_pipeline.graph import app

# --- Integration Tests: Graph Execution ---

def test_pipeline_execution_long():
    """Test full execution of the long-form pipeline."""
    initial_state = {"topic": "Long Form Test", "retry_count": 0}
    final_state = app.invoke(initial_state)
    
    assert final_state["content_type"] == "long"
    assert final_state["upload_status"] == "success"
    # Ensure short form artifacts are not present
    assert "short_upload_status" not in final_state or final_state["short_upload_status"] is None

def test_pipeline_execution_both():
    """Test full execution of both pipelines in parallel."""
    initial_state = {"topic": "Both Forms Test (both)", "retry_count": 0}
    final_state = app.invoke(initial_state)
    
    assert final_state["content_type"] == "both"
    assert final_state["upload_status"] == "success"
    assert final_state["short_upload_status"] == "success"