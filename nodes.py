import logging
import base64
import os
import re
import openai
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
try:
    from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
except ImportError:
    from moviepy import AudioFileClip, ImageClip, concatenate_videoclips
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

if __package__:
    from .state import VideoState
    from .config import PipelineConfig
else:
    from state import VideoState
    from config import PipelineConfig

logger = logging.getLogger(__name__)

# --- Helper Functions ---

def _get_llm(model="gpt-4o", temperature=0.7):
    # Disable internal retries to allow Graph control flow to handle errors immediately
    return ChatOpenAI(model=model, temperature=temperature, max_retries=0)

def _generate_script_content(topic: str, system_prompt: str, user_prompt_fmt: str = "Topic: {topic}") -> str:
    llm = _get_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt_fmt)
    ])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"topic": topic})

def _generate_audio_file(script: str, output_filename: str) -> str:
    client = OpenAI(max_retries=0)
    # Remove visual cues
    clean_script = re.sub(r'\[.*?\]', '', script).strip()
    
    os.makedirs("output", exist_ok=True)
    output_path = os.path.join("output", output_filename)

    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=clean_script[:4096]
    )
    response.stream_to_file(output_path)
    return output_path

def _generate_image_prompts(script: str, system_prompt: str) -> list[str]:
    llm = _get_llm()
    prompt_generator = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "Script: {script}")
    ])
    chain = prompt_generator | llm | StrOutputParser()
    prompts_text = chain.invoke({"script": script[:4000]})
    return [p.strip() for p in prompts_text.split('\n') if p.strip()][:3]

def _generate_images(prompts: list[str], size: str, output_prefix: str) -> list[str]:
    client = OpenAI(max_retries=0)
    os.makedirs("output", exist_ok=True)
    image_paths = []

    for i, img_prompt in enumerate(prompts):
        logger.info(f"Generating image {i+1} for {output_prefix}...")
        response = client.images.generate(
            model="dall-e-3",
            prompt=img_prompt,
            size=size,
            quality="standard",
            n=1,
            response_format="b64_json"
        )
        image_data = base64.b64decode(response.data[0].b64_json)
        file_path = os.path.join("output", f"{output_prefix}_{i}.png")
        with open(file_path, "wb") as f:
            f.write(image_data)
        image_paths.append(file_path)
    return image_paths

def _compose_video_file(voice_path: str, image_paths: list[str], output_filename: str, width: int, height: int, fps: int) -> str:
    audio_clip = AudioFileClip(voice_path)
    img_duration = audio_clip.duration / len(image_paths)
    
    clips = []
    for img_path in image_paths:
        clip = ImageClip(img_path).set_duration(img_duration)
        
        # Resize logic: fit height, then handle width (crop or pad)
        clip = clip.resize(height=height)
        
        if clip.w > width:
            # Crop center
            clip = clip.crop(x_center=clip.w / 2, width=width)
        elif clip.w < width:
            # Pad (Pillarbox)
            margin_left = int((width - clip.w) // 2)
            margin_right = int(width - clip.w - margin_left)
            clip = clip.margin(left=margin_left, right=margin_right, color=(0,0,0))
            
        clips.append(clip)
        
    final_clip = concatenate_videoclips(clips, method="compose")
    final_clip = final_clip.set_audio(audio_clip)
    
    os.makedirs("output", exist_ok=True)
    output_path = os.path.join("output", output_filename)
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=fps, logger=None)
    return output_path

def _handle_api_error(e: Exception, state: VideoState, node_name: str) -> VideoState:
    """Centralized error handling for API calls to provide more intelligent retry behavior."""
    logger.error(f"Error in {node_name}: {e}")
    
    # Check for non-retriable OpenAI errors
    if isinstance(e, openai.APIStatusError):
        # Quota errors or auth errors should not be retried
        if e.status_code == 429 and 'insufficient_quota' in str(e).lower():
            logger.warning("Non-retriable error (insufficient_quota). Bypassing retries to trigger fallback/end.")
            # Set retry_count to max to trigger fallback/end immediately
            return {"error": str(e), "retry_count": PipelineConfig.MAX_RETRIES} 
        if e.status_code in [401, 403]: # Unauthorized, Forbidden
            logger.warning(f"Non-retriable error (HTTP {e.status_code}). Bypassing retries to fallback/end.")
            return {"error": str(e), "retry_count": PipelineConfig.MAX_RETRIES}

    # For other errors, increment retry count normally
    return {"error": str(e), "retry_count": state.get("retry_count", 0) + 1}


def topic_planner(state: VideoState) -> VideoState:
    """Section 10.3: Validate or select the topic."""
    logger.info("--- Topic Planner ---")
    topic = state.get("topic") or "Default AI Topic"
    return {"topic": topic}

def content_type_router(state: VideoState) -> VideoState:
    """Section 12.1: Decide content type (short, long, both)."""
    logger.info("--- Content Type Router ---")
    topic = state.get("topic", "").lower()
    
    # Decision Rules
    if "both" in topic:
        c_type = "both"
    elif any(keyword in topic for keyword in ["trend", "promo", "short"]):
        c_type = "short"
    else:
        c_type = "long" # Default
    
    logger.info(f"Decision: {c_type}")
    return {"content_type": c_type}

# --- Long Form Pipeline Nodes ---

def script_generator(state: VideoState) -> VideoState:
    """Section 10.4: Generate long-form script."""
    logger.info("--- Script Generator (Long) ---")
    
    topic = state.get("topic")
    if not topic:
        return {"error": "No topic provided."}

    try:
        system_prompt = """You are a professional YouTube scriptwriter. Create an engaging 3-5 minute video script.

Structure:
1. Hook (0:00-0:30): Grab attention immediately.
2. Intro: Briefly explain the value proposition.
3. Main Body: Cover 3-4 key points in depth.
4. Conclusion & CTA: Summarize and ask to subscribe.

Format: Use [Visual] tags for visual cues and write the narration clearly."""
        
        script = _generate_script_content(topic, system_prompt)
        return {"script": script, "error": None, "retry_count": 0}
    except Exception as e:
        return _handle_api_error(e, state, "script_generator")

def script_generator_fallback(state: VideoState) -> VideoState:
    """Fallback logic if script generation fails repeatedly."""
    logger.info("--- Script Generator (Fallback) ---")
    topic = state.get("topic") or "Unknown Topic"
    # Simple template script to ensure pipeline continuity
    script = (
        f"Hello and welcome! Today we are discussing {topic}. "
        "This is a fascinating topic that affects many of us. "
        "We will be diving deeper into this in future videos. "
        "Thanks for watching and don't forget to subscribe!"
    )
    return {"script": script, "error": None, "retry_count": 0}

def voice_generator(state: VideoState) -> VideoState:
    """Section 10.5: TTS for long-form."""
    logger.info("--- Voice Generator (Long) ---")
    
    script = state.get("script")
    if not script:
        return {"error": "No script provided."}

    try:
        output_path = _generate_audio_file(script, "long_voice.mp3")
        return {"voice_path": output_path, "error": None, "retry_count": 0}
    except Exception as e:
        return _handle_api_error(e, state, "voice_generator")

def asset_generator(state: VideoState) -> VideoState:
    """Section 10.6: Visual assets for long-form."""
    logger.info("--- Asset Generator (Long) ---")
    
    script = state.get("script")
    if not script:
        return {"error": "No script provided."}

    try:
        system_prompt = """You are an AI visual director. 
Based on the provided video script, create exactly 3 distinct, detailed image generation prompts for DALL-E 3.
One for the beginning, one for the middle, and one for the end.
Return ONLY the 3 prompts, separated by newlines. Do not number them."""
        
        prompts = _generate_image_prompts(script, system_prompt)
        image_paths = _generate_images(prompts, "1024x1024", "image")
        return {"image_paths": image_paths, "error": None, "retry_count": 0}

    except Exception as e:
        return _handle_api_error(e, state, "asset_generator")

def video_composer(state: VideoState) -> VideoState:
    """Section 10.7: Compose long-form video."""
    logger.info("--- Video Composer (Long) ---")
    
    voice_path = state.get("voice_path")
    image_paths = state.get("image_paths")
    
    if not voice_path or not image_paths:
        return {"error": "Missing voice or images for video composition."}
        
    try:
        output_path = _compose_video_file(
            voice_path, image_paths, "final_video.mp4", width=1920, height=1080, fps=24
        )
        return {"video_path": output_path, "error": None, "retry_count": 0}
    except Exception as e:
        logger.error(f"Video composition failed: {e}")
        return {"error": str(e), "retry_count": state.get("retry_count", 0) + 1}

def metadata_generator(state: VideoState) -> VideoState:
    """Section 10.8: Generate metadata."""
    logger.info("--- Metadata Generator (Long) ---")
    
    topic = state.get("topic")
    script = state.get("script")
    
    if not topic or not script:
        return {"error": "Missing topic or script for metadata generation."}

    try:
        llm = _get_llm()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a YouTube SEO expert. Generate metadata for a video based on the script.
Return a valid JSON object with exactly these keys:
- "title": A catchy video title (max 100 chars).
- "description": A compelling video description (min 2 paragraphs).
- "tags": A list of 10-15 relevant tags."""),
            ("user", "Topic: {topic}\n\nScript Preview: {script_preview}")
        ])
        
        chain = prompt | llm | JsonOutputParser()
        result = chain.invoke({
            "topic": topic, 
            "script_preview": script[:2000]
        })
        
        return {
            "title": result.get("title"),
            "description": result.get("description"),
            "tags": result.get("tags"),
            "error": None,
            "retry_count": 0
        }
        
    except Exception as e:
        return _handle_api_error(e, state, "metadata_generator")

def thumbnail_generator(state: VideoState) -> VideoState:
    """Section 10.8.5: Generate thumbnail. (Specific to Long-form)"""
    logger.info("--- Thumbnail Generator ---")
    
    topic = state.get("topic")
    title = state.get("title") or topic
    
    if not topic:
        return {"error": "No topic provided for thumbnail."}

    try:
        # 1. Generate Prompt (Custom logic, keep explicit)
        llm = _get_llm()
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a YouTube thumbnail designer. Create a detailed prompt for DALL-E 3 to generate a high-CTR thumbnail. Focus on visual elements, high contrast, and emotion. Do not include the prompt for text overlays, just the visual scene."),
            ("user", "Topic: {topic}\nVideo Title: {title}")
        ])
        chain = prompt | llm | StrOutputParser()
        img_prompt = chain.invoke({"topic": topic, "title": title})

        # 2. Generate Image (16:9)
        client = OpenAI(max_retries=0)
        os.makedirs("output", exist_ok=True)
        
        response = client.images.generate(
            model="dall-e-3",
            prompt=img_prompt,
            size="1792x1024", # 16:9 aspect ratio
            quality="standard",
            n=1,
            response_format="b64_json"
        )
        
        image_data = base64.b64decode(response.data[0].b64_json)
        output_path = os.path.join("output", "thumbnail.png")
        with open(output_path, "wb") as f:
            f.write(image_data)
            
        return {"thumbnail_path": output_path, "error": None, "retry_count": 0}
    except Exception as e:
        return _handle_api_error(e, state, "thumbnail_generator")

def _get_youtube_service():
    """Helper to authenticate and return YouTube service."""
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None
    
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("client_secrets.json"):
                raise FileNotFoundError("client_secrets.json not found.")
                
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secrets.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
            
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)

def youtube_upload(state: VideoState) -> VideoState:
    """Section 10.9: Upload long-form video."""
    logger.info("--- YouTube Upload (Long) ---")
    
    video_path = state.get("video_path")
    title = state.get("title")
    description = state.get("description")
    tags = state.get("tags")
    thumbnail_path = state.get("thumbnail_path")
    
    if not video_path or not os.path.exists(video_path):
        return {"error": "Video path missing or file not found."}

    try:
        service = _get_youtube_service()
        
        body = {
            "snippet": {
                "title": title[:100] if title else "Untitled",
                "description": description or "",
                "tags": tags or [],
                "categoryId": "28" # Science & Technology
            },
            "status": {
                "privacyStatus": "private", # Default to private for safety
                "selfDeclaredMadeForKids": False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
        
        request = service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(f"Uploaded {int(status.progress() * 100)}%")
                
        video_id = response.get('id')
        logger.info(f"Upload Complete! Video ID: {video_id}")
        
        if video_id and thumbnail_path and os.path.exists(thumbnail_path):
            logger.info("Uploading thumbnail...")
            service.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            
        return {"upload_status": "success", "error": None, "retry_count": 0}
        
    except Exception as e:
        logger.error(f"YouTube upload failed: {e}")
        return {"error": str(e), "retry_count": state.get("retry_count", 0) + 1}

# --- Short Form Pipeline Nodes (Section 12) ---

def short_script_generator(state: VideoState) -> VideoState:
    """Section 12.3: Generate shorts script."""
    logger.info("--- Script Generator (Short) ---")
    
    topic = state.get("topic")
    if not topic:
        return {"error": "No topic provided."}

    try:
        system_prompt = """You are an expert YouTube Shorts scriptwriter. Create a high-energy, viral script under 60 seconds.

Structure:
1. Hook (0-3s): Stop the scroll immediately.
2. Value/Story (3-50s): Deliver the main point quickly and visually.
3. CTA (50-60s): Quick call to action (Subscribe/Like).

Format:
- Keep sentences short.
- Use [Visual] tags for visual cues.
- Total word count should be around 130-150 words for normal speaking pace."""

        script = _generate_script_content(topic, system_prompt)
        return {"short_script": script, "error": None, "retry_count": 0}
    except Exception as e:
        return _handle_api_error(e, state, "short_script_generator")

def short_voice_generator(state: VideoState) -> VideoState:
    """Implied by 12.4: TTS for shorts."""
    logger.info("--- Voice Generator (Short) ---")
    
    script = state.get("short_script")
    if not script:
        return {"error": "No short script provided."}

    try:
        output_path = _generate_audio_file(script, "short_voice.mp3")
        return {"short_voice_path": output_path, "error": None, "retry_count": 0}
    except Exception as e:
        return _handle_api_error(e, state, "short_voice_generator")

def short_asset_generator(state: VideoState) -> VideoState:
    """Implied by 12.4: Assets for shorts."""
    logger.info("--- Asset Generator (Short) ---")
    
    script = state.get("short_script")
    if not script:
        return {"error": "No short script provided."}

    try:
        system_prompt = """You are an AI visual director for YouTube Shorts. 
Based on the provided video script, create exactly 3 distinct, detailed image generation prompts for DALL-E 3.
The images will be generated in vertical format (9:16), so focus on central composition and verticality.
One for the beginning, one for the middle, and one for the end.
Return ONLY the 3 prompts, separated by newlines. Do not number them."""

        prompts = _generate_image_prompts(script, system_prompt)
        image_paths = _generate_images(prompts, "1024x1792", "short_image")
        return {"short_image_paths": image_paths, "error": None, "retry_count": 0}

    except Exception as e:
        return _handle_api_error(e, state, "short_asset_generator")

def short_video_composer(state: VideoState) -> VideoState:
    """Section 12.4: Compose shorts video (9:16)."""
    logger.info("--- Video Composer (Short) ---")
    
    voice_path = state.get("short_voice_path")
    image_paths = state.get("short_image_paths")
    
    if not voice_path or not image_paths:
        return {"error": "Missing voice or images for shorts composition."}
        
    try:
        output_path = _compose_video_file(
            voice_path, image_paths, "short_video.mp4", width=1080, height=1920, fps=30
        )
        return {"short_video_path": output_path, "error": None, "retry_count": 0}
    except Exception as e:
        logger.error(f"Short video composition failed: {e}")
        return {"error": str(e), "retry_count": state.get("retry_count", 0) + 1}

def short_metadata_generator(state: VideoState) -> VideoState:
    """Section 12.5: Shorts metadata."""
    logger.info("--- Metadata Generator (Short) ---")
    return {
        "short_title": f"{state['topic']} #Shorts",
        "short_tags": ["#Shorts", state['topic']]
    }

def short_youtube_upload(state: VideoState) -> VideoState:
    """Section 12.6: Upload shorts video."""
    logger.info("--- YouTube Upload (Short) ---")
    
    video_path = state.get("short_video_path")
    title = state.get("short_title")
    # Description isn't explicitly in short state, use generic
    description = f"Shorts video about {state.get('topic')} #Shorts"
    tags = state.get("short_tags")
    
    if not video_path or not os.path.exists(video_path):
        return {"error": "Short video path missing or file not found."}

    try:
        service = _get_youtube_service()
        
        body = {
            "snippet": {
                "title": title[:100] if title else "Untitled Short",
                "description": description,
                "tags": tags or [],
                "categoryId": "28" # Science & Technology
            },
            "status": {
                "privacyStatus": "private", # Default to private
                "selfDeclaredMadeForKids": False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
        
        request = service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(f"Uploaded Short {int(status.progress() * 100)}%")
                
        logger.info(f"Short Upload Complete! Video ID: {response.get('id')}")
        return {"short_upload_status": "success", "error": None, "retry_count": 0}
        
    except Exception as e:
        logger.error(f"YouTube short upload failed: {e}")
        return {"error": str(e), "retry_count": state.get("retry_count", 0) + 1}