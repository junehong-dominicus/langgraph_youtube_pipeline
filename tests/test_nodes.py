import pytest
from nodes import (
    topic_planner,
    content_type_router,
    script_generator,
    voice_generator,
    asset_generator,
    video_composer,
    metadata_generator,
    youtube_upload,
    short_script_generator,
    short_voice_generator,
    short_asset_generator,
    short_video_composer,
    short_metadata_generator,
    short_youtube_upload
)

# --- Core Logic Nodes ---

def test_topic_planner_defaults():
    """Test that topic planner provides a default if missing."""
    assert topic_planner({"topic": None})["topic"] == "Default AI Topic"
    assert topic_planner({})["topic"] == "Default AI Topic"

def test_topic_planner_preserves_topic():
    """Test that topic planner keeps existing topic."""
    assert topic_planner({"topic": "Custom Topic"})["topic"] == "Custom Topic"

def test_content_type_router_logic():
    """Test routing logic based on keywords."""
    # Long form default
    assert content_type_router({"topic": "History of Math"})["content_type"] == "long"
    
    # Short form keywords (case insensitive)
    assert content_type_router({"topic": "Math trends"})["content_type"] == "short"
    assert content_type_router({"topic": "Math Promo"})["content_type"] == "short"
    assert content_type_router({"topic": "Math #Short"})["content_type"] == "short"
    
    # Both
    assert content_type_router({"topic": "Math (Both)"})["content_type"] == "both"

# --- Long Form Nodes ---

def test_script_generator():
    result = script_generator({"topic": "Test"})
    assert "script" in result
    assert "Test" in result["script"]

def test_voice_generator():
    assert voice_generator({})["voice_path"] == "output/long_voice.mp3"

def test_asset_generator():
    result = asset_generator({})
    assert result["image_paths"] == ["img1.png", "img2.png", "img3.png"]

def test_video_composer():
    assert video_composer({})["video_path"] == "output/final_video.mp4"

def test_metadata_generator():
    result = metadata_generator({"topic": "Test"})
    assert result["title"] == "Deep Dive: Test"
    assert "Test" in result["tags"]

def test_youtube_upload():
    assert youtube_upload({})["upload_status"] == "success"

# --- Short Form Nodes ---

def test_short_script_generator():
    result = short_script_generator({"topic": "Test"})
    assert "short_script" in result
    assert "Test" in result["short_script"]

def test_short_voice_generator():
    assert short_voice_generator({})["short_voice_path"] == "output/short_voice.mp3"

def test_short_asset_generator():
    result = short_asset_generator({})
    assert result["short_image_paths"] == ["s_img1.png", "s_img2.png"]

def test_short_video_composer():
    assert short_video_composer({})["short_video_path"] == "output/short_video.mp4"

def test_short_metadata_generator():
    result = short_metadata_generator({"topic": "Test"})
    assert result["short_title"] == "Test #Shorts"
    assert "#Shorts" in result["short_tags"]

def test_short_youtube_upload():
    assert short_youtube_upload({})["short_upload_status"] == "success"