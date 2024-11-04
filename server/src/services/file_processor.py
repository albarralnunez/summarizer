from fastapi import HTTPException, UploadFile
from typing import Optional, AsyncIterator
import re
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import tempfile
import os
from src.utils.text_processing import yield_sentences
import logging

logger = logging.getLogger(__name__)


async def process_input(
    file: Optional[UploadFile], text: Optional[str]
) -> AsyncIterator[str]:

    if file is None and text is None:
        raise HTTPException(
            status_code=400, detail="Either file or text must be provided"
        )
    if file is not None and text is not None:
        raise HTTPException(
            status_code=400, detail="Please provide either a file or text, not both"
        )

    if file:
        file_extension = file.filename.lower().split(".")[-1]
        if file_extension not in ["txt", "md", "epub"]:
            raise HTTPException(
                status_code=400, detail="Only .txt, .md, and .epub files are supported"
            )

        if file_extension in ["txt", "md"]:
            chunk_size = 1024 * 1024  # 1 MB chunks
            buffer = ""

            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break

                buffer += chunk.decode("utf-8")
                sentences = re.split(r"(?<=[.!?])\s+", buffer)

                for sentence in sentences[:-1]:
                    if sentence.strip():
                        yield sentence

                buffer = sentences[-1]

            if buffer.strip():
                yield buffer.strip()
        elif file_extension == "epub":
            content = await file.read()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name

            try:
                try:
                    book = epub.read_epub(temp_file_path)
                except ebooklib.epub.EpubException as e:
                    raise HTTPException(
                        status_code=400, detail=f"Invalid EPUB file: {str(e)}"
                    )

                documents = []
                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        soup = BeautifulSoup(item.get_content(), "html.parser")

                        for element in soup(["script", "style"]):
                            element.decompose()

                        text = soup.get_text(separator=" ", strip=True)
                        if text.strip():
                            documents.append(text)

                full_text = " ".join(documents)

                async for sentence in yield_sentences(full_text):
                    yield sentence
            finally:
                os.unlink(temp_file_path)
    else:
        async for sentence in yield_sentences(text):
            yield sentence
