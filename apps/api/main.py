import socket
from fastapi import FastAPI, BackgroundTasks
from cortexflow.core.db import Database
from cortexflow.core.schema import PipelineInput

app = FastAPI(title="CortexFlow API")
db = Database()

@app.get("/health")
async def health():
    """健康檢查端點。"""
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {
        "message": "CortexFlow API is running",
        "worker_node": socket.gethostname()
    }

@app.post("/pipeline/run")
async def run_pipeline(topic: str):
    """將主題加入任務佇列，異步執行。"""
    inp = PipelineInput(topic=topic)
    task_id = await db.enqueue_task(topic, inp.model_dump(mode="json"))
    return {
        "status": "queued",
        "task_id": task_id,
        "topic": topic
    }

@app.get("/pipeline/status/{task_id}")
async def get_task_status(task_id: int):
    """查詢任務執行狀態。"""
    # 這裡可以實作查詢 Task 狀態的邏輯
    return {"task_id": task_id, "status": "TODO"}
