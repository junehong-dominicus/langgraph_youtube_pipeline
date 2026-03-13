import logging
import sys
import argparse
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the LangGraph YouTube Pipeline")
    parser.add_argument("--topic", type=str, help="The topic for the video", default="The Future of AI")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        from langgraph_youtube_pipeline.graph import app
    except ImportError:
        try:
            from graph import app
        except ImportError as e:
            logger.error(f"Failed to import application: {e}")
            sys.exit(1)

    logger.info(f">>> Running Pipeline for Topic: {args.topic}")
    initial_state = {"topic": args.topic, "retry_count": 0}
    
    final_state = app.invoke(initial_state)
    
    print("\n" + "="*50)
    print("PIPELINE EXECUTION COMPLETE")
    print("="*50)
    
    err = final_state.get("error")
    if err:
        logger.error(f"Pipeline encountered error: {err}")
    
    # Long Form Results
    if final_state.get("video_path") and os.path.exists(final_state["video_path"]):
        print(f"✅ Long Video: {final_state['video_path']}")
        if final_state.get("thumbnail_path"):
            print(f"🖼️ Thumbnail: {final_state['thumbnail_path']}")
        print(f"🚀 Upload Status: {final_state.get('upload_status')}")
        
    # Short Form Results
    if final_state.get("short_video_path") and os.path.exists(final_state["short_video_path"]):
        print(f"✅ Short Video: {final_state['short_video_path']}")
        print(f"🚀 Upload Status: {final_state.get('short_upload_status')}")
    
    print("="*50 + "\n")