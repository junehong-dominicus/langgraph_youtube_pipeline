import logging
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the LangGraph YouTube Pipeline")
    parser.add_argument("--topic", type=str, help="The topic for the video", default="The Future of AI")
    args = parser.parse_args()

    try:
        from langgraph_youtube_pipeline.graph import app
    except ImportError as e:
        logger.error(f"Failed to import application: {e}")
        logger.error("Ensure directory is named 'langgraph_youtube_pipeline' and run with 'python -m langgraph_youtube_pipeline.main'")
        sys.exit(1)

    logger.info(f">>> Running Pipeline for Topic: {args.topic}")
    initial_state = {"topic": args.topic, "retry_count": 0}
    
    final_state = app.invoke(initial_state)
    
    print("\n" + "="*50)
    print("PIPELINE EXECUTION COMPLETE")
    print("="*50)
    
    if final_state.get("error"):
        logger.error(f"Pipeline failed with error: {final_state['error']}")
    
    if final_state.get("video_path"):
        print(f"Long Video: {final_state['video_path']}")
        if final_state.get("thumbnail_path"):
            print(f"Thumbnail: {final_state['thumbnail_path']}")
        print(f"Upload Status: {final_state.get('upload_status')}")
        
    if final_state.get("short_video_path"):
        print(f"Short Video: {final_state['short_video_path']}")
        print(f"Short Upload Status: {final_state.get('short_upload_status')}")
    
    print("="*50 + "\n")