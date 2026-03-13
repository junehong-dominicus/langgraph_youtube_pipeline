from typing import Dict, List

class PipelineConfig:
    """
    Central configuration for the YouTube Pipeline Graph.
    Controls retry logic, branching paths, and default behaviors.
    """
    
    # Retry Configuration
    # Number of times to retry a node before falling back
    MAX_RETRIES: int = 2
    
    # Content Routing Logic
    # Maps the 'content_type' state to the list of initial nodes to execute
    CONTENT_ROUTES: Dict[str, List[str]] = {
        "short": ["short_script_generator"],
        "long": ["script_generator"],
        "both": ["script_generator", "short_script_generator"]
    }
    
    # Default behavior if content_type is missing or invalid
    DEFAULT_CONTENT_TYPE: str = "long"