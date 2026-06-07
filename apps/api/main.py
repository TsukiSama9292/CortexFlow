from fastapi import FastAPI
from cortexflow.core.pipeline import Pipeline

app = FastAPI(title="CortexFlow API")

@app.get("/")
async def root():
    return {"message": "CortexFlow API is running"}

@app.post("/pipeline/run")
async def run_pipeline(topic: str):
    # Placeholder for starting a pipeline task
    return {"status": "accepted", "topic": topic}
