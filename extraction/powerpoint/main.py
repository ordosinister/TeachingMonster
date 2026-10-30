import hashlib
import json
import os
import time
import shutil
from typing import Literal

from extraction.powerpoint.parser import parse_pptx
from extraction.shared.pipeline import create_pipeline
from extraction.shared.utils import pptx_to_base64_messages
from extraction.system_prompts.pptx import SYSTEM_PROMPT

from src.path.path_definition import get_project_dir

def run(env: Literal["DEV", "PROD"], pptx_path: str):

    pipeline = create_pipeline(env=env, system_prompt=SYSTEM_PROMPT)

    start_time = time.time()

    slides_data, output_dir = parse_pptx(pptx_path)

    powerpoint_input = json.dumps(slides_data, ensure_ascii=False)

    hash_result = hashlib.sha256(powerpoint_input.encode("utf-8")).hexdigest()

    input_dir = os.path.join(get_project_dir(), "data", hash_result)

    if os.path.isdir(input_dir):
        return input_dir

    messages = pptx_to_base64_messages(slides_data)

    response = pipeline.invoke(
        {"messages": messages}
    )

    print(f"Elapsed seconds: {round(time.time() - start_time, 2)}")

    shutil.rmtree(output_dir)

    if not os.path.isdir(input_dir):
        os.makedirs(input_dir)

    input_filename = os.path.join(input_dir, "input.json")

    with open(input_filename, "w", encoding="utf-8") as f:
        json.dump({"course_requirement": response,
                        "reference": pptx_path}, f)

    return input_dir


if __name__ == "__main__":

    content = run(env="DEV", pptx_path=r"data/Attire for Sales Professionals 241113 updated 3.pptx")

    print(content)

