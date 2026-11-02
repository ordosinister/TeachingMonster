import asyncio
import json
import logging
import os
from pathlib import Path
from textwrap import dedent
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Text to Speech")

from openai import AsyncOpenAI
from mutagen.mp3 import MP3

from initialization import credential_init
from model_orchestration import get_model_config
from src.logic.writers.audio.generation_pipeline import create_presentation_pipeline
from src.path.path_definition import get_project_dir


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
                logger.info(f"Error processing image {slide_number}, retrying... {e}")
                await asyncio.sleep(5)

        audio = MP3(speech_file_path)
        duration = audio.info.length
        logger.info(f"Processed image {slide_number}, duration: {duration:.2f} seconds")
        return duration

async def process_concurrent(client, script: List[dict], request_id: str, cache_key: str, instructions: str, max_concurrent: int = 5):
    # Updated folder path to be under TeachingMonster/data/image
    output_dir = os.path.join(get_project_dir(), "data", request_id, cache_key, "audio")
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

def main(request_id: str, cache_key: str):

    env = os.environ['env']

    source_dir = os.path.join(get_project_dir(), "data", request_id, cache_key)

    filename = os.path.join(source_dir, f"blueprint_adapted.json")
    if os.path.isfile(filename):
        with open(filename, "r", encoding="utf-8") as f:
            script = json.load(f)
    else:
        filename = os.path.join(source_dir, f"blueprint.json")
        with open(filename, "r", encoding="utf-8") as f:
            script = json.load(f)

    pipeline = create_presentation_pipeline(get_model_config(env)["sub"])

    input_path = os.path.join(get_project_dir(), "data", request_id, cache_key, "input.json")

    with open(input_path, "r", encoding="utf-8") as f:
        input_data = json.load(f)

    course_requirement = input_data["course_requirement"]
    student_persona = input_data["persona"]

    vibe = pipeline.invoke({"course_requirement": course_requirement, "student_persona": student_persona})

    instructions = dedent(f"""\
    # Role
    You are an enterprise internal training narrator. You speak clearly and naturally, adapting your language to the audience's proficiency. 
    Remove any formatting notation (LaTeX, markup) and decode abbreviations according to the business context. Maintain a professional yet approachable tone.
    
    # Vibe:                     
    {vibe}                
    """)

    client = AsyncOpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    asyncio.run(process_concurrent(client, script['slides'], request_id, cache_key,
                                   instructions, max_concurrent=4))

if __name__ == "__main__":

    os.environ['env'] = 'DEV'

    request_id="01aa1889f2d4c3e75f4c6013db743e09b4edaca190cc45fe98270d81afb08331"
    cache_key="a97294bb5efc6db3"

    main(request_id=request_id, cache_key=cache_key)