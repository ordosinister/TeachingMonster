"""Text-to-Speech audio generation for slide narration.

Generates voice profiles calibrated to student personas and synthesizes
MP3 audio clips for each slide's speaker notes.
"""

import asyncio
import json
import os
import logging
from pathlib import Path
from textwrap import dedent
from typing import List, Literal

"""Text-to-Speech audio generation for slide narration.

Generates voice profiles calibrated to student personas and synthesizes
MP3 audio clips for each slide"s speaker notes.
"""

logger = logging.getLogger("Text to Speech")

from openai import AsyncOpenAI
from mutagen.mp3 import MP3

from src.path.path_definition import get_project_dir
from initialization import credential_init
from model_orchestration import get_model_config
from src.logic.writers.tts.generation_pipeline import create_presentation_pipeline


credential_init()

async def process_tts_async(client, slide_number: int, text: str, output_dir: str, semaphore: asyncio.Semaphore,
                            instructions: str):
    async with semaphore:
        # Use slide_number for the filename as requested
        speech_file_path = os.path.join(output_dir, f"slide_{slide_number}_audio.mp3")

        if os.path.isfile(speech_file_path):
            return "Success"

        while True:
            try:
                async with client.audio.speech.with_streaming_response.create(
                    model="gpt-4o-mini-tts",
                    voice="marin",
                    instructions=instructions,
                    input=text
                ) as response:
                    await response.stream_to_file(speech_file_path)

                break
            except Exception as e:
                logger.info(f"Error processing slide {slide_number}, retrying... {e}")
                await asyncio.sleep(5)

        audio = MP3(speech_file_path)
        duration = audio.info.length
        logger.info(f"Processed slide {slide_number}, duration: {duration:.2f} seconds")
        return duration

async def process_concurrent(client, script: List[dict], request_id: str, instructions: str, max_concurrent: int = 5):
    # Updated folder path to be under TeachingMonster/data/slide
    output_dir = os.path.join(get_project_dir(), "data", request_id, "audio")
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = []

    for item in script:
        slide_number = item.get('slide_number')
        text = item.get('speaker_notes', '') + " " + item.get('transition_to_next', '')
        if text and slide_number is not None:
            tasks.append(process_tts_async(client, slide_number, text, output_dir, semaphore, instructions))

    results = await asyncio.gather(*tasks)
    return results

def main(request_id: str, subject: Literal["physics", "biology", "mathematics", "computer_science"]):

    env = os.environ['env']

    source_dir = os.path.join(get_project_dir(), "data", request_id)
    filename = os.path.join(source_dir, f"blueprint_adapted.json")
    
    with open(filename, "r", encoding="utf-8") as f:
        # Preserving the specific double-loading behavior found in the original file
        script = json.load(f)

    pipeline = create_presentation_pipeline(get_model_config(env)["sub"])

    input_path = Path(f"data/{request_id}/input.json")

    with open(input_path, "r", encoding="utf-8") as f:
        input_data = json.load(f)
    course_requirement = input_data["course_requirement"]
    student_persona = input_data["student_persona"]

    vibe = pipeline.invoke({"course_requirement": course_requirement, "student_persona": student_persona})

    instructions = dedent(f"""\
    # Role
    You are an AP {subject} teacher and you speak in plain English with soft, intimate tone, and remove all the Latex notation. Decode all the abbreviation according to the context."
    
    # Vibe:                     
    {vibe}                
    """)

    client = AsyncOpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    asyncio.run(process_concurrent(client, script['slides'], request_id, instructions, max_concurrent=4))

if __name__ == "__main__":

    course_requirement = dedent("""
    Big Concept: Geometric Properties and Relationships
Topic: Multi-scenario Applications of Triangle Centers
Bloom's Taxonomy: analyze, evaluate, apply
Learning Goal: Guide students to differentiate between the functional roles of the Incenter and Circumcenter based on distance requirements, and model at least TWO distinct real-world applications
Key Learning Points: Incenter (equidistant to sides), Circumcenter (equidistant to vertices), Optimization, Modeling.
              """)

    student_persona = dedent("""
             Grade: 9th Grade
Focus Time: 15 minutes
Background Knowledge: Basic definitions of medians, angle bisectors, and perpendicular bisectors; ability to read coordinates.
              """)

    main(request_id="celery_2500_1777682484", subject='physics', course_requirement=course_requirement,
         student_persona=student_persona)