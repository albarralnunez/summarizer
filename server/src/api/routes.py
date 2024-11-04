from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Query
from typing import Optional, List, Literal
from src.api.models import SummaryOutput
from src.services.summarizer import summarize_text
from src.services.dask_summarizer import summarize_text_dask
from src.services.file_processor import process_input
from src.utils.dask_client import get_dask_client, cleanup_dask_client
from dask.distributed import Client
import time
import logging
from src.services.dask_summarizer import (
    SummarizationError,
    EmptyInputError,
    ProcessingError,
)
from src.utils.dask_client import DaskClientError
from src.config.dask_config import get_dask_settings, DaskSettings
import aiohttp
import asyncio
from pydantic import BaseModel
from src.services.dask_processor import process_with_dask


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/summarize",
    response_model=SummaryOutput,
    summary="Summarize File or Text",
    description="Summarize content using selected algorithm and processor",
)
async def summarize_file(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    num_sentences: int = Form(..., gt=0),
    early_termination_factor: float = Form(2.0, ge=1.0, le=10.0),
    algorithm: Literal["default", "dask"] = Form("default"),
    processor: Literal["default", "dask"] = Form("default"),
    client: Optional[Client] = Depends(get_dask_client),
):
    start_time = time.time()
    logger.debug(
        f"Starting summarization request - algorithm: {algorithm}, processor: {processor}"
    )

    try:
        # Get sentence iterator from appropriate processor
        if processor == "dask":
            logger.debug("Using Dask processor for text processing")
            sentence_iterator = process_with_dask(file, text)
        else:
            logger.debug("Using default processor for text processing")
            sentence_iterator = process_input(file, text)

        # Process with appropriate summarizer
        if algorithm == "dask":
            logger.debug("Starting Dask summarization")
            summary = await summarize_text_dask(
                sentence_iterator, num_sentences, early_termination_factor, client
            )
        else:
            logger.debug("Starting default summarization")
            summary = await summarize_text(
                sentence_iterator, num_sentences, early_termination_factor
            )

        processing_time = time.time() - start_time
        return SummaryOutput(
            summary=summary,
            method=algorithm,
            processor=processor,
            backend_processing_time=processing_time,
        )
    except ValueError as e:
        # Handle all ValueError exceptions with 400 status
        raise HTTPException(status_code=400, detail=str(e))
    except (EmptyInputError, ProcessingError) as e:
        # Convert specific errors to ValueError
        raise HTTPException(status_code=400, detail=str(e))
    except DaskClientError as e:
        # Handle Dask client specific errors
        raise HTTPException(status_code=503, detail=f"Dask cluster error: {str(e)}")
    finally:
        if (algorithm == "dask" or processor == "dask") and client:
            logger.debug("Cleaning up Dask client")
            await cleanup_dask_client(client)


@router.get("/", summary="Root Endpoint", description="Returns a welcome message")
async def root():
    return {"message": "Welcome to the File Summarizer API"}


@router.get("/health")
async def health_check(settings: DaskSettings = Depends(get_dask_settings)):
    """Check API and Dask cluster health"""
    health_status = {
        "status": "healthy",
        "api": "healthy",
        "dask": {"status": "healthy"},
    }

    dashboard_url = f"http://{settings.scheduler_host}:{settings.dashboard_port}/health"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(dashboard_url) as response:
                if response.status != 200:
                    health_status["dask"] = {
                        "status": "unhealthy",
                        "detail": f"Scheduler dashboard returned status {response.status}",
                    }
                    health_status["status"] = "degraded"
        except aiohttp.ClientError as e:
            health_status["dask"] = {
                "status": "unhealthy",
                "detail": f"Failed to connect to dashboard: {str(e)}",
            }
            health_status["status"] = "degraded"
            return health_status

    try:
        client = Client(settings.scheduler_address)
        workers = len(client.scheduler_info()["workers"])
        client.close()
        health_status["dask"].update(
            {"workers": workers, "scheduler": settings.scheduler_address}
        )
    except (OSError, TimeoutError) as e:
        health_status["dask"] = {
            "status": "unhealthy",
            "detail": f"Failed to connect to Dask cluster: {str(e)}",
        }
        health_status["status"] = "degraded"
    except ValueError as e:
        health_status["dask"] = {
            "status": "unhealthy",
            "detail": f"Invalid scheduler address: {str(e)}",
        }
        health_status["status"] = "degraded"

    return health_status
