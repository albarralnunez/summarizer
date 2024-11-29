from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import Optional, Literal
from src.api.models import SummaryOutput, ProfilingData, FunctionProfile
from src.services.summarizer import summarize_text
from src.services.dask_summarizer import (
    summarize_text_dask,
    EmptyInputError,
    ProcessingError,
)
from src.services.file_processor import process_input
from src.utils.dask_client import get_dask_client, cleanup_dask_client, DaskClientError
from src.config.dask_config import get_dask_settings, DaskSettings
from dask.distributed import Client
import time
import logging
import cProfile
import pstats
import io
import tracemalloc
import psutil
import os
from functools import wraps
import aiohttp
from src.utils.text_processing import calculate_text_statistics

router = APIRouter()
logger = logging.getLogger(__name__)


def profile_endpoint(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not kwargs.get("enable_profiling"):
            return await func(*args, **kwargs)

        tracemalloc.start()
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss / 1024 / 1024
        snapshot1 = tracemalloc.take_snapshot()

        pr = cProfile.Profile()
        pr.enable()
        result = await func(*args, **kwargs)
        pr.disable()

        snapshot2 = tracemalloc.take_snapshot()
        top_stats = snapshot2.compare_to(snapshot1, "lineno")
        end_memory = process.memory_info().rss / 1024 / 1024

        memory_stats = [
            {
                "file": str(stat.traceback[0]),
                "line": stat.traceback[0].lineno,
                "size": stat.size / 1024 / 1024,
                "count": stat.count,
            }
            for stat in top_stats[:10]
        ]

        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
        ps.print_stats()

        profiling_data = ProfilingData(
            functions=get_function_profiles(ps),
            memory_usage=end_memory - start_memory,
            memory_peak=peak / 1024 / 1024,
            memory_details=memory_stats,
        )

        if isinstance(result, SummaryOutput):
            result.profiling_data = profiling_data

        return result

    return wrapper


def get_function_profiles(ps):
    function_profiles = []
    total_service_time = sum(
        total_time * calls
        for (filename, _, _), (calls, _, total_time, _, _) in ps.stats.items()
        if "src/services" in str(filename)
    )

    for (filename, line_no, func_name), (
        calls,
        _,
        total_time,
        cumulative_time,
        _,
    ) in ps.stats.items():
        if "src/services" in str(filename) and "wrapper" not in str(func_name):
            total_exec_time = total_time * calls
            function_profiles.append(
                FunctionProfile(
                    function_name=f"{func_name} ({filename}:{line_no})",
                    total_time=total_time,
                    total_exec_time=total_exec_time,
                    percentage=(
                        (total_exec_time / total_service_time) * 100
                        if total_service_time > 0
                        else 0
                    ),
                    calls=calls,
                    memory_per_call=0,
                )
            )

    return sorted(function_profiles, key=lambda x: x.total_exec_time, reverse=True)


@router.post("/summarize", response_model=SummaryOutput)
@profile_endpoint
async def summarize_file(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    num_sentences: int = Form(..., gt=0),
    early_termination_factor: float = Form(2.0, ge=1.0, le=10.0),
    algorithm: Literal["default", "dask", "simple", "sklearn"] = Form("default"),
    processor: Literal["default", "dask"] = Form("default"),
    language: Literal["english", "spanish"] = Form("english"),
    compute_statistics: bool = Form(True),
    enable_profiling: bool = Form(False),
    client: Optional[Client] = Depends(get_dask_client),
):
    start_time = time.time()

    try:
        sentence_iterator = (
            await process_with_dask(file, text)
            if processor == "dask"
            else process_input(file, text)
        )

        # Get both summary and statistics in one pass if enabled
        summary_sentences, text_stats = (
            await summarize_text_dask(
                sentence_iterator,
                num_sentences,
                early_termination_factor,
                client,
                language=language,
                compute_statistics=compute_statistics,
            )
            if algorithm == "dask"
            else await summarize_text(
                sentence_iterator,
                num_sentences,
                early_termination_factor=early_termination_factor,
                algorithm=algorithm,
                language=language,
                compute_statistics=compute_statistics,
            )
        )

        return SummaryOutput(
            summary=summary_sentences,
            method=algorithm,
            processor=processor,
            backend_processing_time=time.time() - start_time,
            compute_statistics=compute_statistics,
            profiling_data=None,
            text_statistics=text_stats,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (EmptyInputError, ProcessingError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DaskClientError as e:
        raise HTTPException(status_code=503, detail=f"Dask cluster error: {str(e)}")
    finally:
        if (algorithm == "dask" or processor == "dask") and client:
            await cleanup_dask_client(client)


@router.get("/health")
async def health_check(settings: DaskSettings = Depends(get_dask_settings)):
    """Check API and Dask cluster health"""
    health_status = {
        "status": "healthy",
        "api": "healthy",
        "dask": {"status": "healthy"},
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{settings.scheduler_host}:{settings.dashboard_port}/health"
            ) as response:
                if response.status != 200:
                    health_status["dask"]["status"] = "unhealthy"
                    health_status["status"] = "degraded"
                    return health_status

        client = Client(settings.scheduler_address)
        workers = len(client.scheduler_info()["workers"])
        client.close()
        health_status["dask"].update(
            {"workers": workers, "scheduler": settings.scheduler_address}
        )

    except Exception as e:
        health_status.update(
            {"status": "degraded", "dask": {"status": "unhealthy", "detail": str(e)}}
        )

    return health_status
