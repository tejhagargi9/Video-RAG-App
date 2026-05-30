from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from fastapi import FastAPI
from routes.transcript_routes import router as transcript_router
from routes.instagram_routes import router as instagram_router

app = FastAPI()

app.include_router(transcript_router)
app.include_router(instagram_router)

@app.get("/")
def root():
    return {"message": "Hello FastAPI"}