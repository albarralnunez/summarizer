from dask.distributed import Client
import logging
from contextlib import asynccontextmanager
import asyncio
import os

logger = logging.getLogger(__name__)


class DaskClientError(Exception):
    """Exception raised for Dask client-related errors"""

    pass


class DaskClientInitError(DaskClientError):
    """Raised when the Dask client fails to initialize"""

    pass


async def get_dask_client():
    """
    Async context manager that provides a Dask client.
    Ensures proper initialization and cleanup of Dask client.
    """
    client = None
    try:
        # Create client in the current event loop
        loop = asyncio.get_event_loop()
        client = await loop.run_in_executor(
            None, lambda: Client(processes=True, n_workers=2, threads_per_worker=2)
        )
        logger.info("Dask client initialized successfully")
        yield client
    finally:
        if client:
            await cleanup_dask_client(client)


async def cleanup_dask_client(client: Client):
    """Helper function to cleanup Dask client"""
    if client:
        try:
            # Run close in executor to avoid event loop issues
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, client.close)
            logger.info("Dask client closed")
        except Exception as e:
            logger.error(f"Error closing Dask client: {str(e)}")
