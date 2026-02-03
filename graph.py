from typing import Literal, List
from langgraph.graph import StateGraph, END
try:
    from state import VideoState
    from nodes import *
except ImportError:
    from .state import VideoState
    from .nodes import *

def route_content_type(state: VideoState) -> List[str]:
    """
    Determines which pipeline branch(es) to execute based on content_type.
    Returns a list of node names to execute next.
    """
    c_type = state.get("content_type", "long")
    if c_type == "short":
        return ["short_script_generator"]
    elif c_type == "long":
        return ["script_generator"]
    elif c_type == "both":
        # Parallel execution of both pipelines
        return ["script_generator", "short_script_generator"]
    return ["script_generator"]

def should_retry(state: VideoState) -> Literal["retry", "fallback", "next"]:
    """
    Section 11.1: Retry logic based on error state.
    """
    # Check if error exists
    if state.get("error"):
        # Check if we haven't exceeded max retries (e.g., 2)
        if state.get("retry_count", 0) < 2:
            return "retry"
        return "fallback"
    return "next"


# Initialize Graph
workflow = StateGraph(VideoState)

# --- Add Nodes ---
workflow.add_node("topic_planner", topic_planner)
workflow.add_node("content_type_router", content_type_router)

# Long Form Nodes
workflow.add_node("script_generator", script_generator)
workflow.add_node("script_generator_fallback", script_generator_fallback)
workflow.add_node("voice_generator", voice_generator)
workflow.add_node("asset_generator", asset_generator)
workflow.add_node("video_composer", video_composer)
workflow.add_node("metadata_generator", metadata_generator)
workflow.add_node("thumbnail_generator", thumbnail_generator)
workflow.add_node("youtube_upload", youtube_upload)

# Short Form Nodes
workflow.add_node("short_script_generator", short_script_generator)
workflow.add_node("short_voice_generator", short_voice_generator)
workflow.add_node("short_asset_generator", short_asset_generator)
workflow.add_node("short_video_composer", short_video_composer)
workflow.add_node("short_metadata_generator", short_metadata_generator)
workflow.add_node("short_youtube_upload", short_youtube_upload)

# --- Define Edges ---

# Entry
workflow.set_entry_point("topic_planner")
workflow.add_edge("topic_planner", "content_type_router")

# Branching Logic (Section 12.7)
workflow.add_conditional_edges(
    "content_type_router",
    route_content_type,
    ["script_generator", "short_script_generator"]
)

# Long Form Pipeline Flow
# Implements Section 11.1 Retry Logic for Script Generator
workflow.add_conditional_edges(
    "script_generator",
    should_retry,
    {"retry": "script_generator", "fallback": "script_generator_fallback", "next": "voice_generator"}
)

workflow.add_edge("script_generator_fallback", "voice_generator")
workflow.add_edge("voice_generator", "asset_generator")
workflow.add_edge("asset_generator", "video_composer")
workflow.add_edge("video_composer", "metadata_generator")
workflow.add_edge("metadata_generator", "thumbnail_generator")
workflow.add_edge("thumbnail_generator", "youtube_upload")
workflow.add_edge("youtube_upload", END)

# Short Form Pipeline Flow
workflow.add_edge("short_script_generator", "short_voice_generator")
workflow.add_edge("short_voice_generator", "short_asset_generator")
workflow.add_edge("short_asset_generator", "short_video_composer")
workflow.add_edge("short_video_composer", "short_metadata_generator")
workflow.add_edge("short_metadata_generator", "short_youtube_upload")
workflow.add_edge("short_youtube_upload", END)

app = workflow.compile()