from typing import TypedDict, Optional, List, Literal, Annotated
import operator

def replace_reducer(a, b):
    return b

class VideoState(TypedDict):
    # Inputs
    topic: str
    
    # Control Flow
    content_type: Literal["short", "long", "both"]
    retry_count: int
    
    # Long-form Artifacts
    script: Optional[str]
    voice_path: Optional[str]
    image_paths: Optional[List[str]]
    video_path: Optional[str]
    title: Optional[str]
    description: Optional[str]
    tags: Optional[List[str]]
    upload_status: Optional[str]
    
    # Short-form Artifacts
    short_script: Optional[str]
    short_voice_path: Optional[str]
    short_image_paths: Optional[List[str]]
    short_video_path: Optional[str]
    short_title: Optional[str]
    short_tags: Optional[List[str]]
    short_upload_status: Optional[str]
    
    # Common
    error: Annotated[Optional[str], replace_reducer]