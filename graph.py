from typing import Literal, List
from langgraph.graph import StateGraph, END
import logging

if __package__:
    from .state import VideoState
    from .config import PipelineConfig
    from .nodes import *
else:
    from state import VideoState
    from config import PipelineConfig
    from nodes import *

logger = logging.getLogger(__name__)

def route_content_type(state: VideoState) -> List[str]:
    """
    Determines which pipeline branch(es) to execute based on content_type.
    Returns a list of node names to execute next.
    """
    c_type = state.get("content_type", PipelineConfig.DEFAULT_CONTENT_TYPE)
    
    # Return routes from config, defaulting to 'long' if unknown type
    return PipelineConfig.CONTENT_ROUTES.get(
        c_type, 
        PipelineConfig.CONTENT_ROUTES[PipelineConfig.DEFAULT_CONTENT_TYPE]
    )

def should_retry(state: VideoState) -> Literal["retry", "fallback", "next"]:
    """
    Section 11.1: Retry logic based on error state.
    """
    # Check if error exists
    if state.get("error"):
        # Check if we haven't exceeded max retries configured in config
        if state.get("retry_count", 0) < PipelineConfig.MAX_RETRIES:
            return "retry"
        return "fallback"
    return "next"

def should_retry_or_end(state: VideoState) -> Literal["retry", "end", "next"]:
    """
    Retry logic for nodes without a fallback. Ends the graph on failure.
    """
    if state.get("error"):
        if state.get("retry_count", 0) < PipelineConfig.MAX_RETRIES:
            # Clear error before retry, but keep retry_count
            state["error"] = None
            return "retry"
        # After max retries, log and end this branch
        logger.error("Node failed after multiple retries. Ending branch.")
        return "end"
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

workflow.add_conditional_edges(
    "voice_generator",
    should_retry_or_end,
    {"retry": "voice_generator", "end": END, "next": "asset_generator"}
)

workflow.add_conditional_edges(
    "asset_generator",
    should_retry_or_end,
    {"retry": "asset_generator", "end": END, "next": "video_composer"}
)

workflow.add_edge("video_composer", "metadata_generator")

workflow.add_conditional_edges(
    "metadata_generator",
    should_retry_or_end,
    {"retry": "metadata_generator", "end": END, "next": "thumbnail_generator"}
)

workflow.add_conditional_edges(
    "thumbnail_generator",
    should_retry_or_end,
    {"retry": "thumbnail_generator", "end": END, "next": "youtube_upload"}
)

workflow.add_conditional_edges(
    "youtube_upload",
    should_retry_or_end,
    {"retry": "youtube_upload", "end": END, "next": END}
)

# Short Form Pipeline Flow
workflow.add_conditional_edges(
    "short_script_generator",
    should_retry_or_end,
    {"retry": "short_script_generator", "end": END, "next": "short_voice_generator"}
)
workflow.add_conditional_edges(
    "short_voice_generator",
    should_retry_or_end,
    {"retry": "short_voice_generator", "end": END, "next": "short_asset_generator"}
)
workflow.add_conditional_edges(
    "short_asset_generator",
    should_retry_or_end,
    {"retry": "short_asset_generator", "end": END, "next": "short_video_composer"}
)
workflow.add_edge("short_video_composer", "short_metadata_generator")
workflow.add_edge("short_metadata_generator", "short_youtube_upload")
workflow.add_conditional_edges(
    "short_youtube_upload",
    should_retry_or_end,
    {"retry": "short_youtube_upload", "end": END, "next": END}
)

app = workflow.compile()