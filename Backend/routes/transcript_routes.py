from fastapi import APIRouter, HTTPException
from youtube_transcript_api import YouTubeTranscriptApi
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

def extract_video_id(url: str) -> str:
    """
    Extract video ID from various YouTube URL formats.
    Supports:
    - http://youtube.com/watch?v=VIDEO_ID
    - https://www.youtube.com/watch?v=VIDEO_ID
    - http://youtu.be/VIDEO_ID
    - https://www.youtu.be/VIDEO_ID
    - http://youtube.com/shorts/VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    """
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)([^&\n?#]+)',
        r'youtube\.com\/embed\/([^&\n?#]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # If no match found, assume the input is already a video ID
    # But validate it looks like a video ID (11 chars, alphanumeric and -_)
    if re.match(r'^[A-Za-z0-9_-]{11}$', url):
        return url
        
    raise ValueError("Could not extract video ID from URL")

@router.get("/transcript/{video_path:path}")
async def get_transcript(video_path: str):
    logger.info(f"Starting transcript fetch for: {video_path}")
    try:
        # Extract video ID from the path (which could be a full URL or just ID)
        logger.info(f"Extracting video ID from path")
        video_id = extract_video_id(video_path)
        logger.info(f"Extracted video ID: {video_id}")
        
        # Fetch transcript
        logger.info(f"Starting transcript API fetch for video_id: {video_id}")
        ytt_api = YouTubeTranscriptApi()
        fetched_transcript = ytt_api.fetch(video_id)
        logger.info(f"Transcript fetch complete, got {len(fetched_transcript)} snippets")
        
        # Convert to raw data format as requested
        raw_data = fetched_transcript.to_raw_data()
        
        logger.info(f"Returning transcript with {len(raw_data)} entries")
        # Log transcript snippets to backend console
        if len(raw_data) <= 50:  # Limit logging to avoid excessive output
            logger.info("Transcript snippets:")
            for i, snippet in enumerate(raw_data):
                logger.info(f"  {i+1}. {snippet.get('text', '')}")
        else:
            logger.info(f"Transcript too long to display fully ({len(raw_data)} snippets). Showing first 5:")
            for i, snippet in enumerate(raw_data[:5]):
                logger.info(f"  {i+1}. {snippet.get('text', '')}")
        
        return {
            "video_id": video_id,
            "transcript": raw_data,
            "language": fetched_transcript.language,
            "language_code": fetched_transcript.language_code,
            "is_generated": fetched_transcript.is_generated
        }
    except ValueError as e:
        logger.error(f"ValueError: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching transcript: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch transcript: {str(e)}")