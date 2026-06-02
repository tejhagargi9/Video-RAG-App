from fastapi import APIRouter, HTTPException
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from apify_client import ApifyClient
import re
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube_service = build("youtube", "v3", developerKey=YOUTUBE_API_KEY) if YOUTUBE_API_KEY else None

# Apify client for YouTube transcript scraper actor
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
if not APIFY_TOKEN:
    logger.warning(
        "APIFY_TOKEN environment variable is not set. "
        "YouTube transcript Apify functionality will not work."
    )
    APIFY_TOKEN = "dummy_token_for_initialization_only"

apify_client = ApifyClient(APIFY_TOKEN)

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


@router.get("/youtube-transcript-apify/{video_path:path}")
async def get_youtube_transcript_apify(video_path: str):
    logger.info(f"Starting YouTube transcript fetch via Apify actor for: {video_path}")

    if APIFY_TOKEN == "dummy_token_for_initialization_only":
        raise HTTPException(
            status_code=500,
            detail=(
                "YouTube transcript Apify functionality is not configured. "
                "Please set the APIFY_TOKEN environment variable."
            ),
        )

    try:
        # The actor expects a YouTube URL. We'll assume video_path is a valid YouTube URL.
        # If it's just a video ID, we can convert it to a URL.
        if not video_path.startswith("http"):
            video_path = f"https://www.youtube.com/watch?v={video_path}"

        run_input = {"videoUrl": video_path}
        logger.info(f"Calling Apify actor with input: {run_input}")

        run = apify_client.actor("pintostudio/youtube-transcript-scraper").call(
            run_input=run_input
        )

        # run is an apify_client._models.Run object — use snake_case attributes
        logger.info(f"Run status: {run.status}")
        logger.info(f"Run id: {run.id}")

        dataset_id = run.default_dataset_id
        logger.info(f"Dataset ID: {dataset_id}")

        if not dataset_id:
            raise HTTPException(
                status_code=500,
                detail="Apify actor did not return a dataset ID.",
            )

        logger.info(
            f"Dataset URL: https://console.apify.com/storage/datasets/{dataset_id}"
        )

        logger.info("Fetching items from dataset...")
        items = list(apify_client.dataset(dataset_id).iterate_items())
        logger.info(f"Got {len(items)} items from dataset")

        if not items:
            raise HTTPException(
                status_code=404,
                detail="No transcript data found for the given YouTube URL.",
            )

        # Assuming the first item contains the transcript data
        data = items[0]
        logger.info(f"First item keys: {list(data.keys())}")

        # Extract transcript and metadata based on the actor's output format.
        # We need to inspect the actual output, but for now, we assume common fields.
        # Let's log a sample of the data to understand the structure (in production, we would adjust).
        # For now, we'll try to map to a similar structure as the existing transcript endpoint.

        # The actor might return:
        #   - text: full transcript text
        #   - segments: array of {text, start, duration} or similar
        #   - language, etc.

        transcript_text = data.get("transcript", "") or data.get("text", "")
        segments = data.get("segments", [])

        # If segments are not in the expected format, we might need to adapt.
        # For safety, we'll return the raw data as well.

        # We'll also try to extract video ID from the URL for consistency with the other endpoint.
        # But note: the actor might not return the video ID. We can extract it from the input URL.
        try:
            video_id = extract_video_id(video_path)
        except ValueError:
            video_id = None
        except Exception:
            video_id = None

        # Prepare response similar to the existing transcript endpoint but using Apify data.
        response = {
            "video_id": video_id,
            "transcript": {
                "text": transcript_text,
                "segments": segments,
            },
            "dataset_id": dataset_id,
            # We don't have language info from the actor? We can add if available.
            "language": data.get("language"),
            "language_code": data.get("languageCode"),
            "is_generated": data.get("isGenerated"),
        }

        # If we have metadata from the actor, we can include it.
        # The actor might return metadata such as title, view count, etc.
        # We'll check for common fields and add them under a metadata key.
        metadata_fields = ["title", "description", "channelTitle", "publishedAt", "tags", "duration", "viewCount", "likeCount", "commentCount"]
        metadata = {}
        for field in metadata_fields:
            if field in data:
                # Convert to snake_case for consistency with the other endpoint?
                # We'll keep the original field name for now, but note that the other endpoint uses snake_case.
                # We'll map camelCase to snake_case for known fields.
                snake_case_field = field
                if field == "channelTitle":
                    snake_case_field = "channel_title"
                elif field == "publishedAt":
                    snake_case_field = "published_at"
                elif field == "viewCount":
                    snake_case_field = "view_count"
                elif field == "likeCount":
                    snake_case_field = "like_count"
                elif field == "commentCount":
                    snake_case_field = "comment_count"
                metadata[snake_case_field] = data[field]

        if metadata:
            response["metadata"] = metadata

        logger.info(f"Returning YouTube transcript Apify result for video_id: {video_id}")
        return response

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(f"Unhandled exception in get_youtube_transcript_apify: {e}")
        err = str(e)
        if any(k in err for k in ["x402", "PAYMENT-SIGNATURE", "Apify token", "401"]):
            raise HTTPException(
                status_code=500,
                detail="Invalid or missing Apify API token. Please check APIFY_TOKEN.",
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch YouTube transcript via Apify: {err}",
        )