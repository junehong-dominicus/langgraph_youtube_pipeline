import pytest
from state import replace_reducer, VideoState

def test_replace_reducer():
    """Test the reducer used for error updates."""
    # Test replacing an existing value
    assert replace_reducer("old_error", "new_error") == "new_error"
    # Test replacing None
    assert replace_reducer(None, "new_error") == "new_error"
    # Test replacing with None
    assert replace_reducer("old_error", None) is None

def test_video_state_definition():
    """Test that VideoState is defined correctly and accepts expected keys."""
    # Verify we can instantiate a dict matching the TypedDict structure
    state: VideoState = {
        "topic": "Test Topic",
        "content_type": "long",
        "retry_count": 0,
        "script": "Some script",
        "voice_path": None,
        "image_paths": [],
        "video_path": None,
        "title": None,
        "description": None,
        "tags": [],
        "upload_status": None,
        "short_script": None,
        "short_voice_path": None,
        "short_image_paths": None,
        "short_video_path": None,
        "short_title": None,
        "short_tags": None,
        "short_upload_status": None,
        "error": None
    }
    assert state["topic"] == "Test Topic"
    assert state["content_type"] == "long"