import pytest
from unittest.mock import patch, MagicMock, mock_open
from nodes import (
    topic_planner,
    content_type_router,
    script_generator,
    voice_generator,
    asset_generator,
    video_composer,
    metadata_generator,
    thumbnail_generator,
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

def test_topic_planner_empty_string():
    """Test that empty string topic triggers default."""
    assert topic_planner({"topic": ""})["topic"] == "Default AI Topic"

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

def test_content_type_router_precedence():
    """Test that 'both' keyword takes precedence over 'short' keyword."""
    # Topic contains both "both" and "short"
    state = {"topic": "Create both short and long videos"}
    assert content_type_router(state)["content_type"] == "both"

# --- Long Form Nodes ---

def test_script_generator():
    """Test script generator handles missing topic."""
    result = script_generator({"topic": "Test"})
    assert "script" in result
    assert "Test" in result["script"]

@patch("nodes.ChatPromptTemplate")
@patch("nodes.ChatOpenAI")
@patch("nodes.StrOutputParser")
def test_script_generator_success(mock_parser, mock_chat, mock_prompt):
    """Test script generator success path with mocks."""
    # Mock chain: prompt | llm | parser
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "Generated Long Script"
    
    mock_prompt_instance = mock_prompt.from_messages.return_value
    mock_intermediate = MagicMock()
    mock_prompt_instance.__or__.return_value = mock_intermediate
    mock_intermediate.__or__.return_value = mock_chain
    
    result = script_generator({"topic": "AI"})
    assert result["script"] == "Generated Long Script"
    assert result["error"] is None

def test_voice_generator():
    assert "error" in voice_generator({})

@patch("nodes.OpenAI")
@patch("nodes.os.makedirs")
@patch("nodes.os.path.join", return_value="output/long_voice.mp3")
def test_voice_generator_success(mock_join, mock_makedirs, mock_openai):
    """Test voice generator success path."""
    mock_client = mock_openai.return_value
    mock_response = MagicMock()
    mock_client.audio.speech.create.return_value = mock_response
    
    state = {"script": "Some script"}
    result = voice_generator(state)
    
    assert result["voice_path"] == "output/long_voice.mp3"
    assert result["error"] is None
    mock_response.stream_to_file.assert_called_once()

def test_asset_generator():
    result = asset_generator({})
    assert "error" in result

@patch("nodes.ChatPromptTemplate")
@patch("nodes.ChatOpenAI")
@patch("nodes.OpenAI")
@patch("nodes.base64.b64decode", return_value=b"fake_image_data")
@patch("builtins.open", new_callable=mock_open)
@patch("nodes.os.makedirs")
def test_asset_generator_success(mock_makedirs, mock_file, mock_b64, mock_openai, mock_chat, mock_prompt):
    """Test asset generator success path."""
    # Mock Prompt Generation Chain
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "Prompt 1\nPrompt 2\nPrompt 3"
    
    mock_prompt_instance = mock_prompt.from_messages.return_value
    mock_intermediate = MagicMock()
    mock_prompt_instance.__or__.return_value = mock_intermediate
    mock_intermediate.__or__.return_value = mock_chain
    
    # Mock Image Generation
    mock_client = mock_openai.return_value
    mock_img_response = MagicMock()
    mock_img_data = MagicMock()
    mock_img_data.b64_json = "fake_b64_json"
    mock_img_response.data = [mock_img_data]
    mock_client.images.generate.return_value = mock_img_response
    
    state = {"script": "Script"}
    result = asset_generator(state)
    
    assert len(result["image_paths"]) == 3
    assert result["error"] is None
    assert mock_client.images.generate.call_count == 3

def test_video_composer():
    assert "error" in video_composer({})

def test_metadata_generator():
    # Expect error because script is missing
    assert "error" in metadata_generator({"topic": "Test"})

@patch("nodes.ChatPromptTemplate")
@patch("nodes.ChatOpenAI")
@patch("nodes.JsonOutputParser")
def test_metadata_generator_success(mock_parser, mock_chat, mock_prompt):
    """Test metadata generator success path."""
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = {
        "title": "Test Title",
        "description": "Test Desc",
        "tags": ["tag1", "tag2"]
    }
    
    mock_prompt_instance = mock_prompt.from_messages.return_value
    mock_intermediate = MagicMock()
    mock_prompt_instance.__or__.return_value = mock_intermediate
    mock_intermediate.__or__.return_value = mock_chain
    
    state = {"topic": "AI", "script": "Script"}
    result = metadata_generator(state)
    
    assert result["title"] == "Test Title"
    assert result["tags"] == ["tag1", "tag2"]
    assert result["error"] is None

def test_thumbnail_generator():
    assert "error" in thumbnail_generator({})

@patch("nodes.ChatPromptTemplate")
@patch("nodes.ChatOpenAI")
@patch("nodes.OpenAI")
@patch("nodes.base64.b64decode", return_value=b"fake_thumb_data")
@patch("builtins.open", new_callable=mock_open)
@patch("nodes.os.makedirs")
def test_thumbnail_generator_success(mock_makedirs, mock_file, mock_b64, mock_openai, mock_chat, mock_prompt):
    """Test thumbnail generator success path."""
    # Mock Prompt Chain
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "Thumbnail Prompt"
    
    mock_prompt_instance = mock_prompt.from_messages.return_value
    mock_intermediate = MagicMock()
    mock_prompt_instance.__or__.return_value = mock_intermediate
    mock_intermediate.__or__.return_value = mock_chain
    
    # Mock Image Gen
    mock_client = mock_openai.return_value
    mock_img_response = MagicMock()
    mock_img_data = MagicMock()
    mock_img_data.b64_json = "fake_b64"
    mock_img_response.data = [mock_img_data]
    mock_client.images.generate.return_value = mock_img_response
    
    state = {"topic": "AI", "title": "AI Video"}
    result = thumbnail_generator(state)
    
    assert result["thumbnail_path"] == "output/thumbnail.png"
    assert result["error"] is None

def test_youtube_upload():
    assert "error" in youtube_upload({})

@patch("nodes.os.path.exists")
def test_youtube_upload_missing_file(mock_exists):
    """Test upload fails if file does not exist."""
    mock_exists.return_value = False
    state = {
        "video_path": "non_existent.mp4",
        "title": "Title",
        "description": "Desc",
        "tags": []
    }
    result = youtube_upload(state)
    assert "error" in result
    assert "Video path missing or file not found" in result["error"]

# --- Short Form Nodes ---

def test_short_script_generator():
    result = short_script_generator({"topic": "Test"})
    assert "short_script" in result
    assert "Test" in result["short_script"]

@patch("nodes.ChatPromptTemplate")
@patch("nodes.ChatOpenAI")
@patch("nodes.StrOutputParser")
def test_short_script_generator_success(mock_parser, mock_chat, mock_prompt):
    """Test short script generator success path."""
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "Generated Short Script"
    
    mock_prompt_instance = mock_prompt.from_messages.return_value
    mock_intermediate = MagicMock()
    mock_prompt_instance.__or__.return_value = mock_intermediate
    mock_intermediate.__or__.return_value = mock_chain
    
    result = short_script_generator({"topic": "Shorts"})
    assert result["short_script"] == "Generated Short Script"
    assert result["error"] is None

def test_short_voice_generator():
    assert "error" in short_voice_generator({})

@patch("nodes.OpenAI")
@patch("nodes.os.makedirs")
@patch("nodes.os.path.join", return_value="output/short_voice.mp3")
def test_short_voice_generator_success(mock_join, mock_makedirs, mock_openai):
    """Test short voice generator success path."""
    mock_client = mock_openai.return_value
    mock_response = MagicMock()
    mock_client.audio.speech.create.return_value = mock_response
    
    state = {"short_script": "Short script"}
    result = short_voice_generator(state)
    
    assert result["short_voice_path"] == "output/short_voice.mp3"
    assert result["error"] is None

def test_short_asset_generator():
    result = short_asset_generator({})
    assert "error" in result

def test_short_video_composer():
    assert "error" in short_video_composer({})

def test_short_metadata_generator():
    result = short_metadata_generator({"topic": "Test"})
    assert result["short_title"] == "Test #Shorts"
    assert "#Shorts" in result["short_tags"]

def test_short_youtube_upload():
    assert "error" in short_youtube_upload({})