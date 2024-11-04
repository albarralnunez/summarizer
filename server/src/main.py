from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router
from src.utils.logging_config import setup_logging
import time
import logging
from src.services.dask_summarizer import (
    SummarizationError,
    EmptyInputError,
    ProcessingError,
)
from src.utils.dask_client import DaskClientError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

app = FastAPI(
    title="File Summarizer API",
    description="An API that preforms extractive summarization on uploaded text files.",
    version="0.0.1",
)

setup_logging()
logger = logging.getLogger(__name__)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    log_dict = {
        "request_method": request.method,
        "request_url": request.url.path,
        "request_query": str(request.query_params),
        "remote_ip": request.client.host,
        "response_status": response.status_code,
        "process_time": f"{process_time:.4f}s",
    }
    logging.info(f"Request processed: {log_dict}")
    return response


app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8888)
