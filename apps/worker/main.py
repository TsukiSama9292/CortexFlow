import asyncio
import socket
import sys
from loguru import logger
from cortexflow.core.db import Database
from cortexflow.core.pipeline import Pipeline
from cortexflow.core.schema import PipelineInput

async def worker_loop():
    worker_id = f"worker-{socket.gethostname()}"
    db = Database()
    logger.info(f"CortexFlow Worker {worker_id} started. Polling for tasks...")

    while True:
        try:
            # 1. 嘗試獲取下一個任務
            task = await db.get_next_task(worker_id)
            
            if not task:
                # 無任務時休息
                await asyncio.sleep(5)
                continue

            task_id = task["id"]
            topic = task["topic"]
            input_data = task["input_data"]
            
            logger.info(f"[{worker_id}] Processing task {task_id}: {topic}")

            # 2. 執行 Pipeline
            try:
                inp = PipelineInput(**input_data)
                pipeline = Pipeline(inp)
                pipeline.db = db # 注入同一個 DB 客戶端
                
                result = await pipeline.run()
                
                # 3. 標記任務完成
                await db.update_task(
                    task_id, 
                    status="completed", 
                    result_data=result.model_dump(mode="json")
                )
                logger.info(f"[{worker_id}] Task {task_id} completed.")
                
            except Exception as e:
                logger.exception(f"[{worker_id}] Task {task_id} failed: {e}")
                await db.update_task(
                    task_id, 
                    status="failed", 
                    error_message=str(e)
                )

        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")
        sys.exit(0)
