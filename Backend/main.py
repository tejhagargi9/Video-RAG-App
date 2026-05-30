from fastapi import FastAPI
from routes.transcript_routes import router as transcript_router

app = FastAPI()

# Include the transcript router
app.include_router(transcript_router)

@app.get("/")
def root():
    return {"message": "Hello FastAPI"}