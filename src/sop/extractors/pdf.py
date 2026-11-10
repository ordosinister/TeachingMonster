import io
import logging

import pymupdf
from langchain_core.messages import HumanMessage
from PIL import Image

from src.sop.extractors import image_to_base64_opened


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sop_writers.extractors.pdf")


def pdf_data_extraction(pdf_path):

    pdf_doc = pymupdf.open(pdf_path)
    results = []
    messages = []

    try:
        for page_number, page in enumerate(pdf_doc, start=1):

            logger.info(f"Extract page {page_number}")

            # 1. PDF 頁面轉 JPEG
            pixmap = page.get_pixmap(
                dpi=200,
                colorspace=pymupdf.csRGB,
                alpha=False,
            )

            image_bytes = pixmap.tobytes("jpeg")

            # 2. 將 Binary 包裝成 OpenAI SDK 可接受的檔案
            image_file = (
                f"page_{page_number}.jpg",
                image_bytes,
                "image/jpeg",
            )

            image = Image.open(io.BytesIO(image_bytes))
            image_str = image_to_base64_opened(image)
            messages.append(
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": f"Page: {page_number}"
                        },
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_str}"}}]))
            results.append(image_file)

        return results, messages

    finally:
        pdf_doc.close()