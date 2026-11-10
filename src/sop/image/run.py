import asyncio
import base64
import logging
import os
from textwrap import dedent

from openai import AsyncOpenAI, APIConnectionError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Image Extraction")


async def img2img_process(client, image_file, semaphore, output_filename, prompt):

    QUALITY = "medium"

    async with semaphore:
        while True:
            try:
                result = await client.images.edit(
                    model="gpt-image-2.5-sunburst",
                    image=image_file,
                    prompt=prompt,
                    quality=QUALITY,
                    size="1792x1008",
                )
                break
            except APIConnectionError:
                logger.info(f"API Connection Error, Sleep for 5 seconds")
                await asyncio.sleep(5)
            except Exception as e:
                logger.info(f"{e}, Sleep for 5 seconds")
                await asyncio.sleep(5)


        # 4. Base64 -> Binary
        image_base64 = result.data[0].b64_json
        output_bytes = base64.b64decode(image_base64)

        with open(output_filename, "wb") as f:
            f.write(output_bytes)


async def process_concurrent(client, image_files, output_dir: str, prompt: str, max_concurrent=4):

    semaphore = asyncio.Semaphore(max_concurrent)

    tasks = []

    for slide_number, image_file in enumerate(image_files,start=1):

        output_filename = os.path.join(output_dir, f"slide_{slide_number}_image.png")

        if os.path.isfile(output_filename):
            continue

        task = img2img_process(client=client, image_file=image_file, semaphore=semaphore,
                               output_filename=output_filename, prompt=prompt)
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results


def main(img2img_inputs, source_dir):

    PROMPT = dedent("""
    Transform the provided document page into a clean, professional enterprise training slide.

    Instructions:
    - Preserve all text content from the original page exactly; do not omit, summarize, or rephrase.
    - Reorganize the layout into a clear visual hierarchy: prominent title, well-structured body text, and any tables or charts rendered cleanly.
    - Apply a unified enterprise visual style: flat diagrammatic aesthetic, muted professional color palette (navy, slate, soft teal accents), ample white space, and readable sans-serif typography.
    - Enhance tables and charts for clarity: add subtle grid lines, aligned headers, and distinct data rows without excessive decoration.
    - Use bullet points or numbered lists where the original presents sequential or grouped information.
    - Maintain a consistent 16:9 widescreen composition.
    - Remove any background noise, scan artifacts, or informal markings from the source page.
    - Ensure the final image looks polished, legible, and suitable for a corporate training presentation.
    """)

    output_dir = os.path.join(source_dir, "image")

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    client = AsyncOpenAI()

    asyncio.run(process_concurrent(client=client, image_files=img2img_inputs, output_dir=output_dir, max_concurrent=4, prompt=PROMPT))