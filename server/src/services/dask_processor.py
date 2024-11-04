from fastapi import HTTPException, UploadFile
from typing import Optional, List, AsyncIterator
import dask.bag as db
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
import io
from ..utils.text_processing import split_into_sentences
import tempfile
import os
from dask.distributed import progress, wait
import logging
import asyncio
import concurrent.futures
import numpy as np
import dask.config
import chardet
import re

logger = logging.getLogger(__name__)


async def decode_chunk(chunk: bytes) -> str:
    """Decode a chunk of bytes to string with encoding detection"""
    try:
        # First try UTF-8
        return chunk.decode("utf-8")
    except UnicodeDecodeError:
        try:
            # Detect encoding
            detection = chardet.detect(chunk)
            encoding = detection["encoding"] or "latin-1"
            logger.debug(
                f"Detected encoding: {encoding} with confidence: {detection['confidence']}"
            )
            return chunk.decode(encoding)
        except Exception as e:
            logger.warning(f"Failed to decode with detected encoding: {str(e)}")
            # Fallback to latin-1 (which always works but might not be correct)
            return chunk.decode("latin-1")


async def process_with_dask(
    file: Optional[UploadFile],
    text: Optional[str],
    chunk_size: int = 1024 * 1024,  # 1MB chunks
    batch_size: int = 1000,  # Process sentences in batches
) -> AsyncIterator[str]:
    """Optimized Dask processing with batching and robust encoding handling"""
    logger.debug("Initializing Dask processing")

    if file is None and text is None:
        raise HTTPException(
            status_code=400, detail="Either file or text must be provided"
        )
    if file is not None and text is not None:
        raise HTTPException(
            status_code=400, detail="Please provide either a file or text, not both"
        )

    try:
        text_content = ""
        if file:
            file_extension = file.filename.lower().split(".")[-1]
            if file_extension not in ["txt", "md", "epub"]:
                raise HTTPException(
                    status_code=400,
                    detail="Only .txt, .md, and .epub files are supported",
                )

            content = await file.read()
            if file_extension in ["txt", "md"]:
                detection = chardet.detect(content)
                encoding = detection["encoding"] or "utf-8"
                logger.debug(f"Detected file encoding: {encoding}")

                try:
                    text_content = content.decode(encoding)
                except UnicodeDecodeError:
                    text_content = content.decode("latin-1")

            elif file_extension == "epub":
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".epub"
                ) as tmp_file:
                    try:
                        tmp_file.write(content)
                        tmp_file.flush()

                        try:
                            book = epub.read_epub(tmp_file.name)
                        except ebooklib.epub.EpubException as e:
                            raise HTTPException(
                                status_code=400, detail=f"Invalid EPUB file: {str(e)}"
                            )

                        # Extract text from all document items
                        text_contents = []
                        for item in book.get_items():
                            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                                soup = BeautifulSoup(item.get_content(), "html.parser")
                                text_contents.append(soup.get_text())

                        text_content = " ".join(text_contents)
                    finally:
                        try:
                            os.unlink(tmp_file.name)
                        except Exception:
                            pass
        else:
            text_content = text

        # Process text content in chunks
        chunks = [
            chunk
            for chunk in [
                text_content[i : i + chunk_size]
                for i in range(0, len(text_content), chunk_size)
            ]
            if chunk.strip()
        ]

        if not chunks:
            raise HTTPException(status_code=400, detail="No valid text content found")

        # Create Dask bag and process sentences
        bag = db.from_sequence(chunks, npartitions=min(len(chunks), 8))
        sentences = (
            bag.map(split_into_sentences)
            .flatten()
            .filter(lambda x: bool(x and x.strip()))
            .map(lambda x: x.strip())
            .repartition(npartitions=dask.config.get("num-workers", 4))
        )

        try:
            computed_sentences = sentences.compute()
            if not computed_sentences:
                raise HTTPException(status_code=400, detail="No valid sentences found")

            logger.info(f"Processing {len(computed_sentences)} sentences")

            # Yield sentences in batches
            for i in range(0, len(computed_sentences), batch_size):
                batch = computed_sentences[i : i + batch_size]
                for sentence in batch:
                    if sentence and isinstance(sentence, str):
                        yield sentence.strip()

        except Exception as e:
            logger.error(f"Error processing sentences: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.exception("Error in Dask processing")
        raise HTTPException(status_code=500, detail=str(e))


def process_data(client, data):
    future = client.submit(some_function, data)
    progress(future)
    return future.result()


def monitor_tasks(futures):
    """Monitor task status with enhanced logging"""
    logger.info("Monitoring task status")

    done, not_done = wait(futures, timeout=10)
    logger.info(f"Tasks completed: {len(done)}")
    logger.info(f"Tasks pending: {len(not_done)}")

    for i, future in enumerate(futures):
        logger.info(f"Task {i + 1}:")
        logger.info(f"  Status: {future.status}")
        if future.status == "error":
            logger.error(f"  Error: {future.exception()}")
        elif future.status == "finished":
            logger.info("  Completed successfully")


def check_cluster_status(client):
    """Monitor cluster status with enhanced logging"""
    logger.debug("Retrieving detailed cluster status")

    scheduler_info = client.scheduler_info()
    workers_info = scheduler_info["workers"]

    logger.debug("Cluster Overview:")
    logger.debug("Total Workers: %d", len(workers_info))
    logger.debug("Total Memory: %s", scheduler_info.get("memory"))
    logger.debug("Total Cores: %s", scheduler_info.get("workers_ncores"))

    for worker_id, info in workers_info.items():
        logger.debug("Worker %s:", worker_id)
        logger.debug(
            "  Memory: %s/%s (used/total)", info.get("memory"), info.get("memory_limit")
        )
        logger.debug("  CPU: %s", info.get("cpu"))
        logger.debug("  Status: %s", info.get("status"))
        logger.debug(
            "  Tasks: executing=%d, in_memory=%d, ready=%d",
            info.get("executing", 0),
            info.get("in_memory", 0),
            info.get("ready", 0),
        )
