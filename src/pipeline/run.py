"""src_v2 orchestrator: slide content + visual style + two-stage layout + validation + image gen + audio gen + embed + cache + save."""

import hashlib
import json
import logging
import os
from typing import Any

from model_orchestration import get_model_config
from src.blueprint.run import main as generate_slide_content
from src.blueprint.structured_output import LessonBlueprint
from src.pipeline.audio_generator.run import generate_audios, build_instructions
from src.pipeline.renderer.run import render_video
from src.pipeline.image_generator.run import generate_images
from src.pipeline.image_generator.visual_style import generate_visual_style, VisualStyle
from src.pipeline.slide_layout.models import SlideImagePrompt, SlideLayout
from src.pipeline.slide_layout.run import generate_slide_layouts_two_stage
from src.pipeline.validator.html_validator import validate_all

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("src_v2")


class _CacheManager:
    """Simple JSON cache manager per pipeline run."""

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _path(self, stage_name: str) -> str:
        return os.path.join(self.cache_dir, f"{stage_name}.json")

    def exists(self, stage_name: str) -> bool:
        return os.path.isfile(self._path(stage_name))

    def save(self, stage_name: str, data: Any) -> None:
        path = self._path(stage_name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Cache saved: %s", path)

    def load(self, stage_name: str) -> Any:
        path = self._path(stage_name)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


def _compute_cache_key(user_input: str, persona: str) -> str:
    raw = f"{user_input}::{persona}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


async def run_pipeline(
    user_input,
    request_id,
    env="DEV",
    layout_semaphore=4,
    image_semaphore=4,
    output_dir=None,
    persona="",
):
    """Run the full src_v2 pipeline with caching, audio generation, and image embedding."""
    model = get_model_config(env)["main"]
    cache_key = _compute_cache_key(user_input, persona)

    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), "data", request_id, cache_key)
    cache = _CacheManager(output_dir)

    # Stage 1: content blueprint
    logger.info("=== Stage 1: Slide Content Generation ===")
    if cache.exists("stage_1_blueprint"):
        logger.info("CACHE HIT: stage_1_blueprint")
        blueprint_data = cache.load("stage_1_blueprint")
        blueprint = LessonBlueprint.model_validate(blueprint_data)
    else:
        _ = generate_slide_content(course_requirement=user_input, request_id=request_id,
                                   cache_key=cache_key, persona=persona)

        with open(os.path.join(output_dir, "blueprint.json"), "r", encoding="utf-8") as f:
            blueprint = LessonBlueprint.model_validate_json(f.read())

        cache.save("stage_1_blueprint", blueprint.model_dump())
    logger.info("Generated %d slides", len(blueprint.slides))

    # Stage 2: unified visual style
    logger.info("=== Stage 2: Unified Visual Style Generation ===")
    if cache.exists("stage_2_visual_style"):
        logger.info("CACHE HIT: stage_2_visual_style")
        vs_data = cache.load("stage_2_visual_style")
        visual_style = VisualStyle.model_validate(vs_data)
    else:
        slides_content = "\n\n".join(
            f"Slide {i+1}: {s.slide_title}\n" + "\n".join(s.slide_content)
            for i, s in enumerate(blueprint.slides)
        )
        visual_style = generate_visual_style(
            model=model,
            course_requirement=user_input,
            persona=persona,
            slides_content=slides_content,
        )
        cache.save("stage_2_visual_style", visual_style.model_dump())
    logger.info(
        "Visual style: %s | %s",
        visual_style.style_category,
        visual_style.tone_descriptor,
    )

    # Stage 3: two-stage layout (image prompts -> HTML layouts)
    logger.info("=== Stage 3: Two-Stage Layout Generation ===")
    if cache.exists("stage_3a_image_prompts") and cache.exists("stage_3b_layouts"):
        logger.info("CACHE HIT: stage_3a_image_prompts + stage_3b_layouts")
        ip_data = cache.load("stage_3a_image_prompts")
        layout_data = cache.load("stage_3b_layouts")
        image_prompts = [SlideImagePrompt.model_validate(d) for d in ip_data]
        layouts = [SlideLayout.model_validate(d) for d in layout_data]
    else:
        image_prompts, layouts = await generate_slide_layouts_two_stage(
            model=model,
            slides=blueprint.slides,
            visual_guidance=visual_style.visual_guidance,
            anti_patterns=visual_style.anti_patterns,
            semaphore_limit=layout_semaphore,
        )
        cache.save("stage_3a_image_prompts", [ip.model_dump() for ip in image_prompts])
        cache.save("stage_3b_layouts", [lo.model_dump() for lo in layouts])
    logger.info(
        "Generated %d image prompts + %d layouts", len(image_prompts), len(layouts)
    )

    # Stage 4: validate all HTML
    logger.info("=== Stage 4: HTML Validation ===")
    if cache.exists("stage_4_validation"):
        logger.info("CACHE HIT: stage_4_validation")
        validation = cache.load("stage_4_validation")
    else:
        validation = validate_all(layouts)
        cache.save("stage_4_validation", validation)
    if validation["all_passed"]:
        logger.info("All %d layouts passed validation", len(layouts))
    else:
        logger.warning("Some layouts failed validation")
        for slide, result in validation["details"].items():
            if not result["passed"]:
                logger.warning("  %s: %s", slide, result)

    # Stage 5: generate images
    logger.info("=== Stage 5: Image Generation ===")
    if cache.exists("stage_5_image_paths"):
        logger.info("CACHE HIT: stage_5_image_paths")
        image_paths = cache.load("stage_5_image_paths")
    else:
        image_dir = os.path.join(output_dir, "images")
        image_paths = await generate_images(
            image_prompts=image_prompts,
            layouts=layouts,
            output_dir=image_dir,
            visual_guidance=visual_style.visual_guidance,
            semaphore_limit=image_semaphore,
        )
        cache.save("stage_5_image_paths", image_paths)
    logger.info("Images saved")

    # Stage 6: generate audio (TTS)
    logger.info("=== Stage 6: Audio Generation ===")
    if cache.exists("stage_6_audio"):
        logger.info("CACHE HIT: stage_6_audio")
        audio_cache = cache.load("stage_6_audio")
        audio_paths = audio_cache["paths"]
        audio_durations = audio_cache["durations"]
    else:
        audio_dir = os.path.join(output_dir, "audio")
        instructions = build_instructions(visual_style.tone_descriptor)
        audio_paths, audio_durations = await generate_audios(
            slides=[s.model_dump() for s in blueprint.slides],
            output_dir=audio_dir,
            instructions=instructions,
            semaphore_limit=4,
        )
        cache.save(
            "stage_6_audio", {"paths": audio_paths, "durations": audio_durations}
        )
    logger.info(
        "Audio generation complete: %d/%d succeeded",
        sum(1 for p in audio_paths if p),
        len(audio_paths),
    )

    # Stage 7: embed images + audio, render video via Playwright
    logger.info("=== Stage 7: Render Video (images + audio + Playwright) ===")
    if cache.exists("stage_7_rendered_video"):
        logger.info("CACHE HIT: stage_7_rendered_video")
        render_result = cache.load("stage_7_rendered_video")
    else:
        render_result = await render_video(
            layouts=layouts,
            image_paths=image_paths,
            audio_paths=audio_paths,
            audio_durations=audio_durations,
            output_dir=output_dir,
        )
        cache.save("stage_7_rendered_video", render_result)
    html_paths = render_result["slide_html_paths"]
    player_path = render_result.get("player_path")
    final_video_path = render_result.get("final_video_path")
    logger.info(
        "Generated %d HTML slides, player: %s, video: %s",
        len(html_paths),
        player_path,
        final_video_path,
    )

    # Stage 8: save results to JSON
    logger.info("=== Stage 8: Save Results ===")
    os.makedirs(output_dir, exist_ok=True)

    output_data = {
        "user_input": user_input,
        "persona": persona,
        "cache_key": cache_key,
        "visual_style": visual_style.model_dump(),
        "blueprint": [slide.model_dump() for slide in blueprint.slides],
        "image_prompts": [ip.model_dump() for ip in image_prompts],
        "layouts": [layout.model_dump() for layout in layouts],
        "validation": validation,
        "image_paths": image_paths,
        "audio_paths": audio_paths,
        "audio_durations": audio_durations,
        "html_paths": html_paths,
        "player_path": player_path,
        "final_video_path": final_video_path,
    }

    output_path = os.path.join(output_dir, "result.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    logger.info("Results saved to %s", output_path)

    return output_data


if __name__ == "__main__":
    import asyncio
    import json
    from pathlib import Path

    from extractors.powerpoint import main as powerpoint_main
    from extractors.pdf import main as pdf_main
    from extractors.word import main as word_main

    from src.path.path_definition import get_project_dir

    filename = r"data/Attire for Sales Professionals 241113 updated 3.pptx"
    persona = "台灣的被動電子元件/電感製造商的新進業務(Sales)，需要拜訪下游OEM/ODM廠來完成業務。"
    os.environ["env"] = "DEV"

    if filename.endswith("pptx"):

        request_id = powerpoint_main.run(pptx_path=filename)

    elif filename.endswith("pdf"):

        request_id = pdf_main.run(pdf_path=filename)

    elif filename.endswith("docx"):

        request_id = word_main.run(docx_path=filename)

    else:
        raise ValueError(f"{Path(filename).suffix} is not supported. QUIT")

    logging.info("##################")
    logging.info(f"Request ID: {request_id}")
    logging.info("##################")

    input_dir = os.path.join(get_project_dir(), "data", request_id)

    input_filename = os.path.join(input_dir, "input.json")

    with open(input_filename, "r", encoding="utf-8") as f:
        course_requirement = json.load(f)

    user_input = course_requirement["course_requirement"]

    result = asyncio.run(run_pipeline(user_input=user_input, request_id=request_id, persona=persona))
    logging.info("Done.")
