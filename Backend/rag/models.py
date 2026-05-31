from pydantic import BaseModel
from typing import Optional


class VideoMeta(BaseModel):
    video_id: str
    video_title: str
    creator: str
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    engagement_rate: Optional[float] = None
    upload_date: Optional[str] = None
    duration: Optional[float] = None
    hashtags: Optional[list[str]] = None
    source: Optional[str] = None  # "youtube" or "instagram"