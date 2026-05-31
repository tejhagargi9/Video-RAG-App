from fastapi import APIRouter, HTTPException
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
import re
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube_service = build("youtube", "v3", developerKey=YOUTUBE_API_KEY) if YOUTUBE_API_KEY else None

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

def get_video_metadata(video_id: str) -> dict:
    """Fetch video metadata using YouTube Data API."""
    if not youtube_service:
        logger.warning("YouTube API key not configured, skipping metadata fetch")
        return None
    
    try:
        request = youtube_service.videos().list(
            part="snippet,contentDetails,statistics",
            id=video_id
        )
        response = request.execute()
        
        if response.get("items"):
            item = response["items"][0]
            view_count = int(item["statistics"].get("viewCount", 0))
            like_count = int(item["statistics"].get("likeCount", 0))
            comment_count = int(item["statistics"].get("commentCount", 0))
            
            engagement_rate = ((like_count + comment_count) / view_count * 100) if view_count > 0 else 0
            
            metadata = {
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"],
                "channel_title": item["snippet"]["channelTitle"],
                "published_at": item["snippet"]["publishedAt"],
                "tags": item["snippet"].get("tags", []),
                "duration": item["contentDetails"]["duration"],
                "view_count": view_count,
                "like_count": like_count,
                "comment_count": comment_count,
                "engagement_rate": round(engagement_rate, 2)
            }
            logger.info(f"Video metadata - Title: {metadata['title']}, Channel: {metadata['channel_title']}")
            logger.info(f"Published: {metadata['published_at']}, Views: {metadata['view_count']}")
            logger.info(f"Engagement Rate: {metadata['engagement_rate']}% (Likes: {like_count}, Comments: {comment_count})")
            return metadata
        return None
    except Exception as e:
        logger.error(f"Error fetching video metadata: {str(e)}")
        return None

@router.get("/transcript/{video_path:path}")
async def get_transcript(video_path: str):
    logger.info(f"Starting transcript fetch for: {video_path}")
    try:
        # Extract video ID from the path (which could be a full URL or just ID)
        logger.info(f"Extracting video ID from path")
        video_id = extract_video_id(video_path)
        logger.info(f"Extracted video ID: {video_id}")

        # Fetch video metadata
        logger.info(f"Fetching video metadata for video_id: {video_id}")
        metadata = get_video_metadata(video_id)

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

        response = {
            "video_id": video_id,
            "transcript": raw_data,
            "language": fetched_transcript.language,
            "language_code": fetched_transcript.language_code,
            "is_generated": fetched_transcript.is_generated
        }
        if metadata:
            response["metadata"] = metadata
        return response
    except ValueError as e:
        logger.error(f"ValueError: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching transcript: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch transcript: {str(e)}")