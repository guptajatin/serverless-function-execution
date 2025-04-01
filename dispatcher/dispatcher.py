from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import redis
import json
import requests
from threading import Thread
from pydantic import BaseModel
import uuid
from typing import Any, Optional
import time
import psutil

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

r = redis.Redis(host="redis", port=6379, decode_responses=True)

LANG_WORKER_URLS = {
    "python": "http://python-worker:8000/execute",
    "js": "http://js-worker:8000/execute"
}

# Constants for queue names
RESULTS_QUEUE = "job_results"

class JobRequest(BaseModel):
    lang: str
    code: str
    input: Optional[Any] = None

class JobResponse(BaseModel):
    job_id: str
    result: Optional[Any] = None
    error: Optional[str] = None
    status: str
    executionTime: Optional[float] = None
    memoryUsage: Optional[int] = None
    language: Optional[str] = None
    printed: Optional[str] = None

@app.post("/execute")
async def execute(job: JobRequest):
    if job.lang not in LANG_WORKER_URLS:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {job.lang}")
    
    job_id = str(uuid.uuid4())
    job_data = {
        "job_id": job_id,
        "code": job.code,
        "input": job.input
    }
    
    # Store job in Redis
    r.rpush(f"{job.lang}_jobs", json.dumps(job_data))
    
    # Wait for result in the shared results queue (with timeout)
    start_time = time.time()
    process = psutil.Process()
    initial_memory = process.memory_info().rss
    
    while time.time() - start_time < 30:  # 30 second timeout
        # Check for new results
        result = r.blpop(RESULTS_QUEUE, timeout=1)
        if result:
            result_data = json.loads(result[1])
            if result_data.get("job_id") == job_id:
                execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                memory_used = process.memory_info().rss - initial_memory
                
                return JobResponse(
                    job_id=job_id,
                    result=result_data.get("result"),
                    error=result_data.get("error"),
                    status="completed" if not result_data.get("error") else "error",
                    executionTime=execution_time,
                    memoryUsage=memory_used,
                    language=job.lang,
                    printed=result_data.get("printed")
                )
    
    execution_time = (time.time() - start_time) * 1000
    memory_used = process.memory_info().rss - initial_memory
    
    return JobResponse(
        job_id=job_id,
        error="Job timed out",
        status="timeout",
        executionTime=execution_time,
        memoryUsage=memory_used,
        language=job.lang
    )

def process_job(language):
    queue_name = f"{language}_jobs"
    while True:
        _, job_data = r.blpop(queue_name)
        job = json.loads(job_data)
        try:
            res = requests.post(LANG_WORKER_URLS[language], json=job)
            result = res.json()
            
            # Push to shared results queue with job_id
            response_data = {
                "job_id": job["job_id"],
                "result": result.get("result"),
                "error": result.get("error"),
                "printed": result.get("printed")
            }
            
            r.rpush(RESULTS_QUEUE, json.dumps(response_data))
            print(f"[{language.upper()} Worker] Output for job {job['job_id']}: {result}")
        except Exception as e:
            error_msg = str(e)
            # Push error to shared results queue
            r.rpush(RESULTS_QUEUE, json.dumps({
                "job_id": job["job_id"],
                "error": error_msg
            }))
            print(f"[{language.upper()} Worker] Error processing job {job['job_id']}: {error_msg}")

# Start worker threads for each language
for lang in LANG_WORKER_URLS:
    Thread(target=process_job, args=(lang,), daemon=True).start()

if __name__ == "__main__":
    # Start FastAPI server
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)