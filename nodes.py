import logging
import base64
import os
import re
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
try:
    from state import VideoState
except ImportError:
    from .state import VideoState

logger = logging.getLogger(__name__)

# --- Core Logic Nodes ---

def topic_planner(state: VideoState) -> VideoState:
    """Section 10.3: Validate or select the topic."""
    logger.info("--- Topic Planner ---")
    # Ensure a topic exists, fallback to default if empty or None
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
        # Initialize LLM
        llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a professional YouTube scriptwriter. Create an engaging 3-5 minute video script.

Structure:
1. Hook (0:00-0:30): Grab attention immediately.
2. Intro: Briefly explain the value proposition.
3. Main Body: Cover 3-4 key points in depth.
4. Conclusion & CTA: Summarize and ask to subscribe.

Format: Use [Visual] tags for visual cues and write the narration clearly."""),
            ("user", "Topic: {topic}")
        ])

        chain = prompt | llm | StrOutputParser()
        script = chain.invoke({"topic": topic})
        
        return {"script": script, "error": None}
    except Exception as e:
        logger.error(f"Script generation failed: {e}")
        return {"error": str(e), "retry_count": state.get("retry_count", 0) + 1}

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
    return {"script": script, "error": None}

def voice_generator(state: VideoState) -> VideoState:
    """Section 10.5: TTS for long-form."""
    logger.info("--- Voice Generator (Long) ---")
    
    script = state.get("script")
    if not script:
        return {"error": "No script provided."}

    try:
        client = OpenAI()
        
        # Remove visual cues like [Visual: ...] for TTS
        clean_script = re.sub(r'\[.*?\]', '', script).strip()
        
        # Ensure output directory exists
        os.makedirs("output", exist_ok=True)
        output_path = os.path.join("output", "long_voice.mp3")

        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=clean_script[:4096]  # Limit for single request
        )
        
        response.stream_to_file(output_path)
        
        return {"voice_path": output_path, "error": None}
    except Exception as e:
        logger.error(f"Voice generation failed: {e}")
        return {"error": str(e)}

def asset_generator(state: VideoState) -> VideoState:
    """Section 10.6: Visual assets for long-form."""
    logger.info("--- Asset Generator (Long) ---")
    
    script = state.get("script")
    if not script:
        return {"error": "No script provided."}

    image_paths = []
    
    try:
        # 1. Generate Image Prompts using LLM
        llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        prompt_generator = ChatPromptTemplate.from_messages([
            ("system", """You are an AI visual director. 
Based on the provided video script, create exactly 3 distinct, detailed image generation prompts for DALL-E 3.
One for the beginning, one for the middle, and one for the end.
Return ONLY the 3 prompts, separated by newlines. Do not number them."""),
            ("user", "Script: {script}")
        ])
        
        chain = prompt_generator | llm | StrOutputParser()
        prompts_text = chain.invoke({"script": script[:4000]})
        prompts = [p.strip() for p in prompts_text.split('\n') if p.strip()][:3]

        client = OpenAI()
        os.makedirs("output", exist_ok=True)

        # 2. Generate Images
        for i, img_prompt in enumerate(prompts):
            logger.info(f"Generating image {i+1}: {img_prompt[:50]}...")
            response = client.images.generate(
                model="dall-e-3",
                prompt=img_prompt,
                size="1024x1024",
                quality="standard",
                n=1,
                response_format="b64_json"
            )
            
            image_data = base64.b64decode(response.data[0].b64_json)
            file_path = os.path.join("output", f"image_{i}.png")
            
            with open(file_path, "wb") as f:
                f.write(image_data)
            
            image_paths.append(file_path)
            
        return {"image_paths": image_paths, "error": None}

    except Exception as e:
        logger.error(f"Asset generation failed: {e}")
        return {"error": str(e)}

def video_composer(state: VideoState) -> VideoState:
    """Section 10.7: Compose long-form video."""
    logger.info("--- Video Composer (Long) ---")
    
    voice_path = state.get("voice_path")
    image_paths = state.get("image_paths")
    
    if not voice_path or not image_paths:
        return {"error": "Missing voice or images for video composition."}
        
    try:
        audio_clip = AudioFileClip(voice_path)
        # Calculate duration per image
        img_duration = audio_clip.duration / len(image_paths)
        
        clips = []
        for img_path in image_paths:
            clip = ImageClip(img_path).set_duration(img_duration).resize(height=1080)
            # Center on 1920x1080 canvas
            margin_left = (1920 - clip.w) // 2
            margin_right = 1920 - clip.w - margin_left
            clip = clip.margin(left=margin_left, right=margin_right, color=(0,0,0))
            clips.append(clip)
            
        final_clip = concatenate_videoclips(clips, method="compose")
        final_clip = final_clip.set_audio(audio_clip)
        
        os.makedirs("output", exist_ok=True)
        output_path = os.path.join("output", "final_video.mp4")
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24, logger=None)
        
        return {"video_path": output_path, "error": None}
    except Exception as e:
        logger.error(f"Video composition failed: {e}")
        return {"error": str(e)}

def metadata_generator(state: VideoState) -> VideoState:
    """Section 10.8: Generate metadata."""
    logger.info("--- Metadata Generator (Long) ---")
    
    topic = state.get("topic")
    script = state.get("script")
    
    if not topic or not script:
        return {"error": "Missing topic or script for metadata generation."}

    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        
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
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Metadata generation failed: {e}")
        return {"error": str(e)}

def thumbnail_generator(state: VideoState) -> VideoState:
    """Section 10.8.5: Generate thumbnail."""
    logger.info("--- Thumbnail Generator ---")
    
    topic = state.get("topic")
    title = state.get("title") or topic
    
    if not topic:
        return {"error": "No topic provided for thumbnail."}

    try:
        # 1. Generate Prompt
        llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a YouTube thumbnail designer. Create a detailed prompt for DALL-E 3 to generate a high-CTR thumbnail. Focus on visual elements, high contrast, and emotion. Do not include the prompt for text overlays, just the visual scene."),
            ("user", "Topic: {topic}\nVideo Title: {title}")
        ])
        chain = prompt | llm | StrOutputParser()
        img_prompt = chain.invoke({"topic": topic, "title": title})

        # 2. Generate Image
        client = OpenAI()
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
            
        return {"thumbnail_path": output_path, "error": None}
    except Exception as e:
        logger.error(f"Thumbnail generation failed: {e}")
        return {"error": str(e)}

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
            
        return {"upload_status": "success", "error": None}
        
    except Exception as e:
        logger.error(f"YouTube upload failed: {e}")
        return {"error": str(e)}

# --- Short Form Pipeline Nodes (Section 12) ---

def short_script_generator(state: VideoState) -> VideoState:
    """Section 12.3: Generate shorts script."""
    logger.info("--- Script Generator (Short) ---")
    
    topic = state.get("topic")
    if not topic:
        return {"error": "No topic provided."}

    try:
        # Initialize LLM
        llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert YouTube Shorts scriptwriter. Create a high-energy, viral script under 60 seconds.

Structure:
1. Hook (0-3s): Stop the scroll immediately.
2. Value/Story (3-50s): Deliver the main point quickly and visually.
3. CTA (50-60s): Quick call to action (Subscribe/Like).

Format:
- Keep sentences short.
- Use [Visual] tags for visual cues.
- Total word count should be around 130-150 words for normal speaking pace."""),
            ("user", "Topic: {topic}")
        ])

        chain = prompt | llm | StrOutputParser()
        script = chain.invoke({"topic": topic})
        
        return {"short_script": script, "error": None}
    except Exception as e:
        logger.error(f"Short script generation failed: {e}")
        return {"error": str(e)}

def short_voice_generator(state: VideoState) -> VideoState:
    """Implied by 12.4: TTS for shorts."""
    logger.info("--- Voice Generator (Short) ---")
    
    script = state.get("short_script")
    if not script:
        return {"error": "No short script provided."}

    try:
        client = OpenAI()
        
        # Remove visual cues like [Visual: ...] for TTS
        clean_script = re.sub(r'\[.*?\]', '', script).strip()
        
        # Ensure output directory exists
        os.makedirs("output", exist_ok=True)
        output_path = os.path.join("output", "short_voice.mp3")

        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=clean_script[:4096]
        )
        
        response.stream_to_file(output_path)
        
        return {"short_voice_path": output_path, "error": None}
    except Exception as e:
        logger.error(f"Short voice generation failed: {e}")
        return {"error": str(e)}

def short_asset_generator(state: VideoState) -> VideoState:
    """Implied by 12.4: Assets for shorts."""
    logger.info("--- Asset Generator (Short) ---")
    
    script = state.get("short_script")
    if not script:
        return {"error": "No short script provided."}

    image_paths = []
    
    try:
        # 1. Generate Image Prompts using LLM
        llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        prompt_generator = ChatPromptTemplate.from_messages([
            ("system", """You are an AI visual director for YouTube Shorts. 
Based on the provided video script, create exactly 3 distinct, detailed image generation prompts for DALL-E 3.
The images will be generated in vertical format (9:16), so focus on central composition and verticality.
One for the beginning, one for the middle, and one for the end.
Return ONLY the 3 prompts, separated by newlines. Do not number them."""),
            ("user", "Script: {script}")
        ])
        
        chain = prompt_generator | llm | StrOutputParser()
        prompts_text = chain.invoke({"script": script[:4000]})
        prompts = [p.strip() for p in prompts_text.split('\n') if p.strip()][:3]

        client = OpenAI()
        os.makedirs("output", exist_ok=True)

        # 2. Generate Images
        for i, img_prompt in enumerate(prompts):
            logger.info(f"Generating short image {i+1}: {img_prompt[:50]}...")
            response = client.images.generate(
                model="dall-e-3",
                prompt=img_prompt,
                size="1024x1792",  # Vertical for Shorts
                quality="standard",
                n=1,
                response_format="b64_json"
            )
            
            image_data = base64.b64decode(response.data[0].b64_json)
            file_path = os.path.join("output", f"short_image_{i}.png")
            
            with open(file_path, "wb") as f:
                f.write(image_data)
            
            image_paths.append(file_path)
            
        return {"short_image_paths": image_paths, "error": None}

    except Exception as e:
        logger.error(f"Short asset generation failed: {e}")
        return {"error": str(e)}

def short_video_composer(state: VideoState) -> VideoState:
    """Section 12.4: Compose shorts video (9:16)."""
    logger.info("--- Video Composer (Short) ---")
    
    voice_path = state.get("short_voice_path")
    image_paths = state.get("short_image_paths")
    
    if not voice_path or not image_paths:
        return {"error": "Missing voice or images for shorts composition."}
        
    try:
        audio_clip = AudioFileClip(voice_path)
        # Calculate duration per image
        img_duration = audio_clip.duration / len(image_paths)
        
        clips = []
        for img_path in image_paths:
            clip = ImageClip(img_path).set_duration(img_duration)
            
            # Resize to fill 1080x1920 (Vertical)
            # Strategy: Resize height to 1920, then center crop width to 1080
            clip = clip.resize(height=1920)
            
            if clip.w > 1080:
                clip = clip.crop(x_center=clip.w / 2, width=1080)
            elif clip.w < 1080:
                # Fallback: pad if somehow narrower
                margin_left = int((1080 - clip.w) // 2)
                margin_right = int(1080 - clip.w - margin_left)
                clip = clip.margin(left=margin_left, right=margin_right, color=(0,0,0))
                
            clips.append(clip)
            
        final_clip = concatenate_videoclips(clips, method="compose")
        final_clip = final_clip.set_audio(audio_clip)
        
        os.makedirs("output", exist_ok=True)
        output_path = os.path.join("output", "short_video.mp4")
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=30, logger=None)
        
        return {"short_video_path": output_path, "error": None}
    except Exception as e:
        logger.error(f"Short video composition failed: {e}")
        return {"error": str(e)}

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
        return {"short_upload_status": "success", "error": None}
        
    except Exception as e:
        logger.error(f"YouTube short upload failed: {e}")
        return {"error": str(e)}