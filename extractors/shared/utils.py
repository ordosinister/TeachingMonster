import base64
import io
from pathlib import Path
from collections.abc import Iterable
from typing import Any, cast, Union

import pymupdf
from langchain_core.messages import HumanMessage
from PIL import Image


def image_to_base64(image_path):
    """
    這樣做的必要性在於：
    1. API 通常以文本（JSON）形式傳輸數據，而非原始二進制數據
    2. Base64 允許僅使用可打印的 ASCII 字符來表示二進制數據
    3. 它能夠將圖像直接嵌入 JSON 有效負載或 HTML/CSS 中

    處理過程：
        1. 打開圖像文件
        2. 將其保存到內存緩衝區（BytesIO）
        3. 將緩衝區內容編碼為 Base64
        4. 解碼為 UTF-8 字符串以進行傳輸

    注意：Base64 編碼會使文件大小增加約 33%，因此對於大型圖像而言，
    其效率低於直接文件上傳方法。

    Args:
        image_path (str): 圖像文件的路徑

    Returns:
        str: 圖像的 Base64 編碼字符串表示形式

    """

    with Image.open(image_path) as image:
        # Save the Image to a Buffer
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")

        # Encode the Image to Base64

        image_str = base64.b64encode(buffered.getvalue())

    return image_str.decode('utf-8')


def pdf_to_base64_messages(pdf_path: Union[Path, bytes]) -> list[HumanMessage]:
    """將 PDF 所有頁面轉換為 Base64 圖像訊息列表。"""
    messages = []
    if isinstance(pdf_path, Path):
        doc = pymupdf.open(pdf_path)
    elif isinstance(pdf_path, bytes):
        doc = pymupdf.open(stream=pdf_path, filetype="pdf")
    else:
        raise TypeError("Provided filepath is neither a Path object nor a bytes")

    for page_number, page in enumerate(cast(Iterable[Any], doc)):
        pixmap = page.get_pixmap(dpi=200)
        image_bytes = pixmap.tobytes("jpeg")
        image_str = base64.b64encode(image_bytes).decode("utf-8")
        messages.append(
            HumanMessage(
                content=[
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_str}"},
                    }
                ]
            )
        )
    return messages