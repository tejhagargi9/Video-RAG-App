from fastapi import APIRouter, HTTPException
from apify_client import ApifyClient
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")

if not APIFY_TOKEN:
    logger.warning(
        "APIFY_TOKEN environment variable is not set. "
        "Instagram transcript functionality will not work."
    )
    APIFY_TOKEN = "dummy_token_for_initialization_only"

client = ApifyClient(APIFY_TOKEN)


def compute_engagement_rate(
    likes: int | None,
    comments: int | None,
    views: int | None,
) -> float | None:
    likes = likes or 0
    comments = comments or 0
    if not views or views == 0:
        return None
    return round(((likes + comments) / views) * 100, 2)


@router.get("/instagram-transcript/{video_path:path}")
async def get_instagram_transcript(video_path: str):
    logger.info(f"Starting Instagram transcript fetch for: {video_path}")

    if APIFY_TOKEN == "dummy_token_for_initialization_only":
        raise HTTPException(
            status_code=500,
            detail=(
                "Instagram transcript functionality is not configured. "
                "Please set the APIFY_TOKEN environment variable."
            ),
        )

    try:
        run_input = {"videoUrl": video_path}
        logger.info(f"Calling Apify actor with input: {run_input}")

        run = client.actor("apple_yang/instagram-transcripts-scraper").call(
            run_input=run_input
        )

        # run is an apify_client._models.Run object — use snake_case attributes
        logger.info(f"Run status: {run.status}")
        logger.info(f"Run id: {run.id}")

        # FIX: use run.default_dataset_id (snake_case attribute), NOT run["defaultDatasetId"]
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
        items = list(client.dataset(dataset_id).iterate_items())
        logger.info(f"Got {len(items)} items from dataset")

        if not items:
            raise HTTPException(
                status_code=404,
                detail="No transcript data found for the given Instagram URL.",
            )

        data = items[0]
        logger.info(f"First item keys: {list(data.keys())}")

        # Metadata
        like_count    = data.get("likeCount")    or 0
        comment_count = data.get("commentCount") or 0

        # View count: use real value if available, else fall back to like_count as proxy
        view_count = (
            data.get("viewCount")
            or data.get("playCount")
            or like_count
            or None
        )

        if not data.get("viewCount") and not data.get("playCount"):
            logger.warning(
                "viewCount not returned by Apify actor — "
                "using likeCount as temporary view proxy for engagement rate"
            )

        engagement_rate = compute_engagement_rate(like_count, comment_count, view_count)

        logger.info(
            f"Instagram Metadata | "
            f"Username: {data.get('userName')} | "
            f"Likes: {like_count} | "
            f"Comments: {comment_count} | "
            f"Views (proxy): {view_count} | "
            f"Engagement Rate: {f'{engagement_rate}%' if engagement_rate is not None else 'N/A'}"
        )

        # Transcript
        transcript_text = data.get("text", "")
        segments        = data.get("segments", [])

        if segments:
            logger.info(f"Returning transcript with {len(segments)} segments")
            for idx, seg in enumerate(segments[:50]):
                logger.info(
                    f"  {idx + 1}. [{seg.get('start', 0):.2f}s – {seg.get('end', 0):.2f}s] "
                    f"{seg.get('text', '').strip()}"
                )
        elif transcript_text:
            logger.info("No timestamped segments — returning full text only")
        else:
            logger.warning("No transcript text or segments found in actor output")

        return {
            "video_url": video_path,
            "metadata": {
                "title":           data.get("title"),
                "username":        data.get("userName"),
                "full_name":       data.get("userFullName"),
                "user_id":         data.get("userPk"),
                "post_id":         data.get("id"),
                "shortcode":       data.get("code"),
                "duration":        data.get("duration"),
                "created_at":      data.get("createTime"),
                "likes":           like_count,
                "comments":        comment_count,
                "views":           view_count,
                "engagement_rate": engagement_rate,
                "thumbnail":       data.get("img"),
                "video_url":       data.get("videoUrl"),
                "audio_url":       data.get("audioUrl"),
                "avatar_url":      data.get("avatarUri"),
            },
            "transcript": {
                "text":     transcript_text,
                "segments": segments,
            },
            "dataset_id": dataset_id,
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(f"Unhandled exception in get_instagram_transcript: {e}")
        err = str(e)
        if any(k in err for k in ["x402", "PAYMENT-SIGNATURE", "Apify token", "401"]):
            raise HTTPException(
                status_code=500,
                detail="Invalid or missing Apify API token. Please check APIFY_TOKEN.",
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch Instagram transcript: {err}",
        )