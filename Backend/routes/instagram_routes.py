from fastapi import APIRouter, HTTPException
from apify_client import ApifyClient
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize ApifyClient with token from environment variable
# For security, we should load the token from environment variables
# In a real app, you would set APIFY_TOKEN in your .env file
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
if not APIFY_TOKEN:
    logger.warning("APIFY_TOKEN environment variable is not set. Instagram transcript functionality will not work.")
    # Set to a dummy value to prevent client initialization errors, but it will fail at runtime
    APIFY_TOKEN = "dummy_token_for_initialization_only"
client = ApifyClient(APIFY_TOKEN)

@router.get("/instagram-transcript/{video_path:path}")
async def get_instagram_transcript(video_path: str):
    logger.info(f"Starting Instagram transcript fetch for: {video_path}")
    try:
        # Check if API token is properly configured
        if APIFY_TOKEN == "dummy_token_for_initialization_only":
            logger.error("APIFY_TOKEN environment variable is not set. Please set it to use Instagram transcript functionality.")
            raise HTTPException(
                status_code=500, 
                detail="Instagram transcript functionality is not configured. Please set the APIFY_TOKEN environment variable."
            )
        
        # Prepare the Actor input
        run_input = { "videoUrl": video_path }

        # Run the Actor and wait for it to finish
        run = client.actor("apple_yang/instagram-transcripts-scraper").call(run_input=run_input)

        # Fetch and print Actor results from the run's dataset (if there are any)
        logger.info(f"💾 Check your data here: https://console.apify.com/storage/datasets/{run['defaultDatasetId']}")
        
        # Collect items from the dataset
        items = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            items.append(item)
            logger.info(f"Instagram transcript item: {item}")

        if not items:
            logger.warning("No transcript items found for the given Instagram URL.")
            raise HTTPException(status_code=404, detail="No transcript found for the given Instagram URL.")

        # Assuming the first item contains the transcript data
        # Adjust this based on the actual structure of the actor's output
        transcript_data = items[0]  # or however you want to structure the response

        # Log the transcript snippets (if they are in a specific format)
        # For example, if the item has a 'transcript' field that is a list of snippets
        if isinstance(transcript_data, dict) and 'transcript' in transcript_data:
            snippets = transcript_data['transcript']
            if isinstance(snippets, list):
                logger.info(f"Returning Instagram transcript with {len(snippets)} snippets")
                # Log snippets to backend console (limit to 50 for brevity)
                if len(snippets) <= 50:
                    logger.info("Instagram transcript snippets:")
                    for i, snippet in enumerate(snippets):
                        logger.info(f"  {i+1}. {snippet}")
                else:
                    logger.info(f"Instagram transcript too long to display fully ({len(snippets)} snippets). Showing first 5:")
                    for i, snippet in enumerate(snippets[:5]):
                        logger.info(f"  {i+1}. {snippet}")
            else:
                logger.info("Instagram transcript data is not a list of snippets.")
        else:
            logger.info("Instagram transcript data format not as expected for snippet logging.")

        return {
            "video_url": video_path,
            "transcript": transcript_data,
            "dataset_id": run["defaultDatasetId"]
        }
    except Exception as e:
        logger.error(f"Error fetching Instagram transcript: {str(e)}")
        # Provide more specific error messages for common issues
        if "x402 payment header missing" in str(e) or "PAYMENT-SIGNATURE" in str(e) or "Apify token" in str(e):
            raise HTTPException(
                status_code=500, 
                detail="Invalid or missing Apify API token. Please check your APIFY_TOKEN environment variable."
            )
        raise HTTPException(status_code=500, detail=f"Failed to fetch Instagram transcript: {str(e)}")