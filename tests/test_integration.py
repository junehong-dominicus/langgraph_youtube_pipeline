import pytest
import sys
import os
from dotenv import load_dotenv

# Ensure parent directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from graph import app

load_dotenv()

has_google_creds = os.path.exists("token.json") or os.path.exists("client_secrets.json")
requires_creds = pytest.mark.skipif(
    not (os.environ.get("OPENAI_API_KEY") and has_google_creds),
    reason="OpenAI API Key or Google Credentials missing"
)

@requires_creds
def test_pipeline_execution_long(default_state):
    """Test full execution of the long-form pipeline."""
    state = default_state.copy()
    state["topic"] = "Long Form Test"
    
    final_state = app.invoke(state)
    
    assert final_state["content_type"] == "long"
    assert final_state["upload_status"] == "success"
    # Ensure short form artifacts are not present
    assert final_state.get("short_upload_status") is None

@requires_creds
def test_pipeline_execution_short(default_state):
    """Test full execution of the short-form pipeline."""
    state = default_state.copy()
    state["topic"] = "Short Form Test #Shorts"
    
    final_state = app.invoke(state)
    
    assert final_state["content_type"] == "short"
    assert final_state["short_upload_status"] == "success"
    # Ensure long form artifacts are not present
    assert final_state.get("upload_status") is None

@requires_creds
def test_pipeline_execution_both(default_state):
    """Test full execution of both pipelines in parallel."""
    state = default_state.copy()
    state["topic"] = "Both Forms Test (both)"
    
    final_state = app.invoke(state)
    
    assert final_state["content_type"] == "both"
    assert final_state["upload_status"] == "success"
    assert final_state["short_upload_status"] == "success"