"""Image generation entry point (async, concurrent)."""
import asyncio
import base64
import logging
import os

from openai import AsyncOpenAI, APIConnectionError

logger = logging.getLogger("image_generator")


_RATIO_SIZE_MAP = {
    "16:9": "1792x1008",
    "4:3": "1600x1200",
    "1:1": "1024x1024",
}

_MAX_RETRIES = 3


async def _generate_one_image(
    client,
    image_prompt,
    image_type,
    image_ratio,
    output_path,
    visual_guidance,
    max_retries=_MAX_RETRIES,
):
    """Generate a single image and save to disk."""
    if image_type == "None" or not image_prompt.strip():
        logger.info("Skipping image generation (type=%s)", image_type)
        return None

    size = _RATIO_SIZE_MAP.get(image_ratio, "1024x1024")
    # Prepend visual_guidance to enforce consistency across the deck
    full_prompt = f"{visual_guidance}\n\n{image_prompt}"

    for attempt in range(max_retries + 1):
        try:
            logger.info("Generating image (attempt %d/%d): %s...",
                         attempt + 1, max_retries + 1, full_prompt[:80])
            result = await client.images.generate(
                model="gpt-image-2.5-sunburst",
                prompt=full_prompt,
                size=size,
                n=1
            )
            image_b64 = result.data[0].b64_json
            image_bytes = base64.b64decode(image_b64)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as fh:
                fh.write(image_bytes)
            logger.info("Image saved to %s", output_path)
            return output_path

        except APIConnectionError:
            logger.warning("API connection error, retrying in 5s...")
            await asyncio.sleep(5)
        except Exception as exc:
            logger.error("Image generation failed: %s", exc)
            if attempt == max_retries:
                raise
            await asyncio.sleep(2)

    return None


async def generate_images(
    image_prompts,
    layouts,
    output_dir,
    visual_guidance,
    semaphore_limit=4,
    max_retries=_MAX_RETRIES,
):
    """Generate images for all slides with asyncio.Semaphore."""
    client = AsyncOpenAI()
    semaphore = asyncio.Semaphore(semaphore_limit)
    os.makedirs(output_dir, exist_ok=True)

    async def _invoke(idx, ip, layout):
        async with semaphore:
            output_path = os.path.join(output_dir, f"slide_{idx + 1:02d}_image.png")
            return await _generate_one_image(
                client=client,
                image_prompt=ip.image_prompt,
                image_type=ip.image_type,
                image_ratio=layout.image_ratio,
                output_path=output_path,
                visual_guidance=visual_guidance,
                max_retries=max_retries,
            )

    tasks = [
        _invoke(idx, ip, layout)
        for idx, (ip, layout) in enumerate(zip(image_prompts, layouts))
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    output_paths = []
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("Slide %d image generation failed: %s", idx + 1, result)
            output_paths.append(None)
        else:
            output_paths.append(result)

    logger.info("Image generation complete: %d/%d succeeded",
                 sum(1 for r in output_paths if r), len(output_paths))
    return output_paths