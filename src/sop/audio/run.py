import asyncio
import json
import logging
import os
from textwrap import dedent
from typing import List

from langchain_core.messages import HumanMessage
from mutagen.mp3 import MP3
from openai import AsyncOpenAI

from initialization import credential_init
from model_orchestration import get_model_config
from src.sop.audio.generation_pipeline import create_pipeline
from src.sop.audio.structured_output import TTSScript, TTSScripts


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Text to Speech")


credential_init()

def run_script(messages: List[HumanMessage], persona: str):

    env = os.environ["env"]

    MODEL_NAME = "image_caption"

    model = get_model_config(env)[MODEL_NAME]

    pipeline = create_pipeline(model=model)

    output = pipeline.invoke({"messages": messages,
                              "persona": persona})

    return output


async def process_tts_async(client, speech_file_path: str, text: str, semaphore: asyncio.Semaphore,
                            instruction: str):
    async with semaphore:
        # Use slide_number for the filename as requested
        logger.info(f"Process {speech_file_path}")
        while True:
            try:
                async with client.audio.speech.with_streaming_response.create(
                    model="gpt-4o-mini-tts",
                    voice="marin",
                    instructions=instruction,
                    input=text
                ) as response:
                    await response.stream_to_file(speech_file_path)

                break
            except Exception as e:
                logger.info(f"Error processing audio {speech_file_path}, retrying... {e}")
                await asyncio.sleep(5)

        audio = MP3(speech_file_path)
        duration = audio.info.length
        logger.info(f"Processed audio {speech_file_path}, duration: {duration:.2f} seconds")


async def process_concurrent(client, scripts: List[TTSScript], output_dir: str, instruction: str,
                             max_concurrent: int = 4):
    # Updated folder path to be under TeachingMonster/data/image
    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = []

    for slide_number, script in enumerate(scripts, start=1):
        text = script.script

        speech_file_path = os.path.join(output_dir, f"slide_{slide_number}_audio.mp3")

        if os.path.isfile(speech_file_path):
            continue

        if text and slide_number is not None:
            tasks.append(process_tts_async(client, speech_file_path, text, semaphore, instruction))

    await asyncio.gather(*tasks)


def main(messages: List[HumanMessage], source_dir: str, persona: str):

    instruction = dedent("""
    Speak like a clear, confident corporate training facilitator delivering an internal enterprise course.
    Maintain a warm yet professional tone—approachable and authoritative without being stiff or overly casual.
    Pace is measured and natural: slightly deliberate for new concepts, brisk and efficient for review or procedural steps.
    Use natural prosody with gentle emphasis on key terms, clear pauses between ideas, and a calm, reassuring cadence.
    Convey quiet enthusiasm that signals expertise and engagement, but never force cheerfulness.
    Articulate domain terminology crisply; avoid idioms, slang, or culture-specific references.
    Sound like a credible colleague guiding adult professionals through operational material.
    """)

    filename = os.path.join(source_dir, "blueprint.json")

    if not os.path.isfile(filename):
        scripts = run_script(messages=messages, persona=persona)

        with open(filename, "w", encoding="utf-8") as f:
            f.write(scripts.model_dump_json(indent=2))
    else:
        with open(filename, "r", encoding="utf-8") as f:
            scripts = TTSScripts.model_validate_json(f.read())

    client = AsyncOpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

    output_dir = os.path.join(source_dir, "audio")

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    asyncio.run(process_concurrent(client, scripts.scripts, output_dir, instruction, max_concurrent=4))