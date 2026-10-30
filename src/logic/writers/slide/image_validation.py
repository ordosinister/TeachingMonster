"""Mathematics image quality validation via vision-model captioning.

Uses the image_caption model from model_orchestration to inspect generated
slide images and detect serious flaws (coordinate misalignment, equation
mismatches, etc.) that would confuse students.
"""

import asyncio
import path
import base64 as b64
import logging
import os

from PIL import Image
from langchain_core.messages import HumanMessage

from model_orchestration import get_model_config

logger = logging.getLogger("Image Validation")

VALIDATION_PROMPT = """你是一位數學和物理教育專家。請仔細檢查這張教學投影片中的圖表是否有嚴重瑕疵。

投影片內容：
{slide_content}

重點檢查項目：
- 座標軸上的數值與圖形位置是否對應正確
- 函數圖形是否與標註的方程式一致
- 數據點、標註值、向量分量等數值是否準確
- 幾何圖形的比例和位置關係是否合理
- 任何會誤導學生、造成學習困惑的錯誤

如果發現嚴重錯誤，請回答「有瑕疵」，簡短說明問題所在，並具體指出應如何修正（例如：調整某個數值、移動某個標註、修正某條曲線的形狀、更改某個標籤文字等）。
如果圖像準確無誤，請回答「無瑕疵」。
"""


def validate_math_images(image_types: list, script: dict, output_dir: str, env: str) -> list:
    """Validate all non-None math slide images and return list of flawed slide numbers.

    Args:
        image_types: List of (slide_number, type_name) tuples from process_concurrent.
        script: The full slide script dict with slide content.
        output_dir: Directory containing the generated slide images.
        env: Environment key ("DEV" or "PROD") for model selection.

    Returns:
        List of slide numbers flagged as flawed.
    """
    non_none_slides = [
        (sn, tn) for sn, tn in image_types
        if tn is not None and not isinstance(sn, Exception)
    ]

    async def _caption_one(slide_number, type_name, caption_model):
        image_path = os.path.join(output_dir, f"slide_{slide_number}_image.png")
        if not os.path.isfile(image_path):
            return None

        # Find the slide content for context
        slide_content = ""
        for s in script["slides"]:
            if s["slide_number"] == slide_number:
                slide_content = ",".join(s["slide_content"])
                break

        # Encode image to base64
        with Image.open(image_path) as img:
            buffered = path.BytesIO()
            img.save(buffered, format="JPEG")
            image_str = b64.b64encode(buffered.getvalue()).decode("utf-8")

        validation_prompt = VALIDATION_PROMPT.format(slide_content=slide_content)
        message = HumanMessage(content=[
            {"type": "text", "text": validation_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_str}"}}
        ])

        try:
            response = await caption_model.ainvoke([message])
            result_text = response.content.strip()
            logger.info(f"Slide {slide_number} caption result: {result_text[:120]}...")

            if "有瑕疵" in result_text and "無瑕疵" not in result_text.split("有瑕疵")[0]:
                logger.warning(f"Slide {slide_number} flagged as flawed: {result_text}")
                return slide_number, result_text, type_name
        except Exception as e:
            logger.error(f"Slide {slide_number} caption failed: {e}")
        return None

    async def _caption_all():
        caption_model = get_model_config(env)["image_caption"]
        tasks = [_caption_one(sn, tn, caption_model) for sn, tn in non_none_slides]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if r is not None and not isinstance(r, Exception)]

    return asyncio.run(_caption_all())
