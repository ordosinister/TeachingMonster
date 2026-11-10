"""Slide layout generation entry point (two-stage, concurrent)."""
import asyncio
import logging

from langchain_core.exceptions import OutputParserException

from src.pipeline.slide_layout.models import SlideImagePrompt, SlideLayout
from src.pipeline.slide_layout.pipeline import create_image_prompt_pipeline, create_slide_layout_pipeline

logger = logging.getLogger("slide_layout")


async def _generate_image_prompts(model, slides, visual_guidance, anti_patterns, semaphore_limit) -> list[SlideImagePrompt]:
    """Stage A: generate image prompts for all slides concurrently."""
    pipeline = create_image_prompt_pipeline(model)
    semaphore = asyncio.Semaphore(semaphore_limit)

    async def _invoke(slide_number, slide_title, slide_content, speaker_notes, persona, visual_guidance, anti_patterns):
        async with semaphore:
            return await asyncio.to_thread(
                pipeline.invoke,
                {
                    "slide_number": str(slide_number),
                    "slide_title": slide_title,
                    "slide_content": "\n".join(slide_content),
                    "speaker_notes": speaker_notes,
                    "persona": persona,
                    "visual_guidance": visual_guidance,
                    "anti_patterns": anti_patterns,
                },
            )

    tasks = [
        _invoke(
            idx + 1,
            slide.slide_title if hasattr(slide, "slide_title") else "",
            slide.slide_content,
            slide.speaker_notes,
            "",  # persona can be injected by caller if needed
            visual_guidance,
            anti_patterns,
        )
        for idx, slide in enumerate(slides)
    ]
    results = await asyncio.gather(*tasks)
    logger.info("Stage A complete: %d image prompts generated", len(results))
    return results


async def _generate_layouts(model, slides, image_prompts, visual_guidance, semaphore_limit) -> list[SlideLayout]:
    """Stage B: generate HTML layouts for all slides concurrently."""
    pipeline = create_slide_layout_pipeline(model)
    semaphore = asyncio.Semaphore(semaphore_limit)

    async def _invoke(slide_number, slide_content, image_prompt, image_type, visual_guidance):
        async with semaphore:
            return await asyncio.to_thread(
                pipeline.invoke,
                {
                    "slide_number": str(slide_number),
                    "slide_content": "\n".join(slide_content),
                    "image_prompt": image_prompt,
                    "image_type": image_type,
                    "visual_guidance": visual_guidance,
                },
            )

    tasks = [
        _invoke(
            idx + 1,
            slide.slide_content,
            ip.image_prompt,
            ip.image_type,
            visual_guidance,
        )
        for idx, (slide, ip) in enumerate(zip(slides, image_prompts))
    ]
    results = await asyncio.gather(*tasks)
    logger.info("Stage B complete: %d layouts generated", len(results))
    return results


async def generate_slide_layouts_two_stage(
    model,
    slides,
    visual_guidance,
    anti_patterns="",
    semaphore_limit=4,
) -> tuple[list[SlideImagePrompt], list[SlideLayout]]:
    """Run two-stage layout generation: image prompts -> HTML layouts."""
    image_prompts = await _generate_image_prompts(model, slides, visual_guidance, anti_patterns, semaphore_limit)
    layouts = await _generate_layouts(model, slides, image_prompts, visual_guidance, semaphore_limit)
    return image_prompts, layouts