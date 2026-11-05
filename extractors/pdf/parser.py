import base64
import io
import pymupdf

from langchain_core.messages import HumanMessage
from PIL import Image


def image_to_base64_opened(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def pdf_to_base64_messages(pdf_path: str) -> list[HumanMessage]:
    """將 PDF 所有頁面轉換為 Base64 圖像訊息列表。"""

    #stream（二進位資料）
    #pdf_doc = pymupdf.open(stream=data, filetype="pdf")
    pdf_doc = pymupdf.open(pdf_path)

    messages = []

    for page_number, page in enumerate(pdf_doc):
        pixmap = page.get_pixmap(dpi=200)
        image_bytes = pixmap.tobytes("jpeg")
        image = Image.open(io.BytesIO(image_bytes))
        image_str = image_to_base64_opened(image)
        messages.append(
            HumanMessage(content=[{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_str}"}}]))

    return messages