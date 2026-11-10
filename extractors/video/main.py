import hashlib
import json
import logging
import os
import shutil
import time

from extractors.video.generation_pipeline import create_pipeline
from extractors.video.parser import extract_keyframes, keyframes_to_base64_messages

from src.path.path_definition import get_project_dir

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("extractors.video.main")


def run(video_path: str, scene_threshold: float = 0.3):

    logging.info(f"Processing video file: {video_path}")

    env = os.environ["env"]

    pipeline = create_pipeline(env=env)

    start_time = time.time()

    # Extract keyframes using ffmpeg scene detection
    image_files, output_dir = extract_keyframes(
        video_path=video_path,
        scene_threshold=scene_threshold,
    )

    # Build hash from video path + scene_threshold for cache key
    hash_input = f"{video_path}|{scene_threshold}"
    hash_result = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    logging.info(
        f"request_id: {hash_result}, "
        f"keyframes: {len(image_files)}, "
        f"Elapsed seconds: {round(time.time() - start_time, 2)}"
    )

    input_dir = os.path.join(get_project_dir(), "data", hash_result)

    if os.path.isdir(input_dir):
        logger.info(f"Cache hit: {input_dir}")
        shutil.rmtree(output_dir, ignore_errors=True)
        return hash_result

    messages = keyframes_to_base64_messages(image_files)

    response = pipeline.invoke(
        {"messages": messages}
    )

    logging.info(f"Elapsed seconds: {round(time.time() - start_time, 2)}")

    # Cleanup temporary frame directory
    shutil.rmtree(output_dir, ignore_errors=True)

    if not os.path.isdir(input_dir):
        os.makedirs(input_dir)

    input_filename = os.path.join(input_dir, "input.json")

    with open(input_filename, "w", encoding="utf-8") as f:
        json.dump(
            {"course_requirement": response, "reference": video_path},
            f,
            ensure_ascii=False,
        )

    return hash_result


if __name__ == "__main__":

    os.environ["env"] = "DEV"

    request_id = run(
        video_path=r"data/sample_video.mp4",
        scene_threshold=0.3,
    )

    print(request_id)