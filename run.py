"""Master pipeline orchestrator for educational video generation.

Executes four sequential stages:
    1. Blueprint generation (structured lesson plan)
    2. Adaptation (persona-aware content rewriting)
    3. Slide image + TTS audio generation
    4. Video assembly via moviepy
"""

import hashlib
import json
import logging
import time
import argparse
import os
from pathlib import Path
from textwrap import dedent

log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "pipeline.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main process")


from src.logic.writers.blueprint import run as run_blueprint
from src.logic.writers.adaptation import run as run_adaptation
from src.logic.writers.image import run as run_image
from src.logic.writers.audio import run as run_tts
from src.logic.writers.video_gen import run as run_video


def generate_8char_random(str1, str2):
    combined = str1 + str2
    hash_object = hashlib.md5(combined.encode())
    hash_hex = hash_object.hexdigest()
    return hash_hex[:8]


def main(request_id, course_requirement, student_persona):
    """Execute the full video generation pipeline.

    Args:
        request_id: Unique identifier for this generation request.
        course_requirement: Description of the course topic and learning goals.
        student_persona: Description of the target student's grade level and background.

    Raises:
        Exception: Re-raises any exception that occurs during pipeline execution.
    """

    env = os.environ['env']

    logger.info(f"==========================================================")
    logger.info(f"STARTING PIPELINE for request_id: {request_id}")
    logger.info(f"Requirement: {course_requirement}")
    logger.info(f"Persona: {student_persona}")
    logger.info(f"Environment: {env}")
    logger.info(f"==========================================================\r\n")

    try:
        blueprint_start_time = time.perf_counter()

        logger.info("Step 1: Generating Blueprint...")
        cache_key = run_blueprint.main(request_id=request_id, course_requirement=course_requirement,
                                        persona=student_persona)
        blueprint_elapsed = time.perf_counter() - blueprint_start_time
        logger.info(f"Blueprint generation time: {blueprint_elapsed:.2f} seconds")

        # logger.info("Step 2: Adaptation Layer...")
        # run_adaptation.main(request_id=request_id)

        logger.info("Step 3: Generating Images with txt2img...")
        run_image.main(request_id=request_id, cache_key=cache_key)
        image_elapsed = time.perf_counter() - blueprint_start_time
        logger.info(f"Blueprint generation time: {image_elapsed:.2f} seconds")

        logger.info("Step 4: Generating Audio with TTS...")
        run_tts.main(request_id=request_id, cache_key=cache_key)
        image_elapsed = time.perf_counter() - blueprint_start_time
        logger.info(f"Blueprint generation time: {image_elapsed:.2f} seconds")

        logger.info("Step 5: Assembling Final Video...")
        run_video.main(request_id=request_id, cache_key=cache_key)
        image_elapsed = time.perf_counter() - blueprint_start_time
        logger.info(f"Blueprint generation time: {image_elapsed:.2f} seconds")

        logger.info(f"==========================================================")
        logger.info(f"PIPELINE COMPLETED SUCCESSFULLY for {request_id}")
        logger.info(f"==========================================================")
    except Exception as e:
        logger.exception(f"Pipeline failed for {request_id}: {str(e)}")
        raise e

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TeachingMonster Master Pipeline")
    parser.add_argument("--request_id", type=str, help="Unique request identifier")
    parser.add_argument("--requirement", type=str, help="Course requirements")
    parser.add_argument("--persona", type=str, help="Student persona")
    
    args = parser.parse_args()

    import json

    from extractors.powerpoint import main as powerpoint_main
    from extractors.pdf import main as pdf_main

    from src.path.path_definition import get_project_dir

    os.environ['env'] = "DEV"

    filename = r"data/Our Shared Core Values and Code of Conduct_ITG_150122.pdf"

    # student_persona = "台灣的被動電子元件/電感製造商的越南地區新進業務(Sales)，需要拜訪下游製造商來完成業務。使用越南文"
    student_persona = "台灣的被動電子元件/電感製造商的新進員工"

    if filename.endswith("pptx"):

        request_id = powerpoint_main.run(pptx_path=filename)

    elif filename.endswith("pdf"):

        request_id = pdf_main.run(pdf_path=filename)

    print(request_id)

    input_dir = os.path.join(get_project_dir(), "data", request_id)

    input_filename = os.path.join(input_dir, "input.json")

    with open(input_filename, "r", encoding="utf-8") as f:
        course_requirement = json.load(f)

    course_requirement = json.dumps(course_requirement)

    main(request_id, course_requirement, student_persona)