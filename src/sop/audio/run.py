import asyncio
import io
import logging
import os
from textwrap import dedent
from typing import List

import pymupdf
import whisper
from langchain_core.messages import HumanMessage
from mutagen.mp3 import MP3
from openai import AsyncOpenAI
from PIL import Image

from initialization import credential_init
from model_orchestration import get_model_config
from src.path.path_definition import get_project_dir
from src.sop.audio.generation_pipeline import create_pipeline
from src.sop.audio.correction_pipeline import create_pipeline as create_correction_pipeline
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



def _pdf_pages_to_images(pdf_filename: str, output_dir: str, dpi: int = 200):
    """Convert each PDF page to an even-dimensioned PNG."""
    pdf_doc = pymupdf.open(pdf_filename)
    os.makedirs(output_dir, exist_ok=True)

    for page_number, page in enumerate(pdf_doc, start=1):
        pixmap = page.get_pixmap(dpi=dpi)
        image_bytes = pixmap.tobytes("jpeg")
        image = Image.open(io.BytesIO(image_bytes))

        width, height = image.size
        new_width = width - (width % 2)
        new_height = height - (height % 2)

        if (width, height) != (new_width, new_height):
            image = image.crop((0, 0, new_width, new_height))

        filepath = os.path.join(output_dir, f"slide_{page_number}_image.png")
        image.save(filepath, format="PNG")
        logger.info("Saved page %d as %s", page_number, filepath)


def main(messages: List[HumanMessage], source_dir: str, persona: str, pdf_filename: str = ""):

    instruction = dedent("""
    **Voice Affect:** Clear, warm, confident, and approachable. Speak with the natural voice of an experienced Taiwanese corporate training instructor. Maintain a pleasant, reassuring, and professional vocal presence. Use natural variations in pitch and tone to keep the narration engaging without sounding overly animated or theatrical.

**Tone:** Warm, professional, informative, and supportive. Sound like a senior training instructor guiding Taiwanese professionals through structured learning material. Maintain a balance between expertise and approachability. Convey genuine enthusiasm for the subject while avoiding exaggerated excitement, excessive formality, or an artificial presentation style.

**Pacing:** Measured, smooth, and natural. Speak at a comfortable pace that allows Taiwanese Mandarin listeners to follow and understand the material easily. Slow down slightly when introducing new concepts, explaining technical terminology, or discussing important details. Use a moderately brisk pace when reviewing familiar information, explaining procedures, or transitioning between topics. Avoid speaking too quickly or compressing syllables.

**Emotion:** Calm, confident, patient, and encouraging. Convey the experience and reliability of a knowledgeable training instructor. Maintain a positive and supportive attitude that helps learners feel comfortable, engaged, and confident in understanding the material. Avoid exaggerated emotional expressions or forced enthusiasm.

**Personality:** Friendly, articulate, knowledgeable, and trustworthy. Sound like an experienced Taiwanese corporate educator who explains complex topics in a clear and accessible manner. Be approachable without becoming overly casual. Communicate with the natural confidence of a professional colleague guiding adult learners through workplace training. Avoid sounding robotic, excessively scripted, or like a formal news broadcaster.

**Pauses:** Use natural and purposeful pauses between sentences, key concepts, instructional steps, and major sections. Allow slightly longer pauses after important explanations, unfamiliar terminology, or complex information so learners have sufficient time to process what they hear. Use shorter pauses during continuous explanations to maintain a smooth and coherent flow. Avoid unnecessary dramatic pauses.

**Accent:** Speak fluent, standard Taiwan Mandarin (Taiwanese Mandarin) with a natural and neutral Taiwanese accent. Use authentic Taiwanese Mandarin speech characteristics throughout the narration. Avoid Beijing-style pronunciation, exaggerated retroflexion, or strongly regional mainland Chinese accents. Maintain a consistent Taiwanese Mandarin accent from beginning to end.

**Pronunciation:** Follow standard Taiwanese Mandarin pronunciation and articulation. Use natural Taiwanese Mandarin vowel and consonant sounds, with relatively light retroflexion characteristic of standard Taiwan Mandarin. Maintain accurate Mandarin tones, clear syllable articulation, and natural sentence-level intonation. Pronounce technical terminology, English loanwords, abbreviations, and professional vocabulary clearly and consistently. Avoid unnatural pronunciation, excessive emphasis, or exaggerated enunciation.

**Vocabulary:** Use Traditional Chinese (Taiwan) vocabulary, expressions, and linguistic conventions. Prefer terminology commonly used in Taiwanese workplaces, corporate training materials, and professional communication. Use natural Taiwanese expressions rather than Mainland Chinese vocabulary or regional expressions. Maintain consistent terminology throughout the narration. Avoid slang, internet expressions, colloquialisms, and overly literary language. When explaining technical concepts, prioritize clarity, precision, and accessibility for Taiwanese adult learners.
    """)

    # Extract PDF pages to images if a PDF file is provided
    if pdf_filename and os.path.isfile(pdf_filename):
        image_dir = os.path.join(source_dir, "image")
        _pdf_pages_to_images(pdf_filename, image_dir)

    logger.info("TTS generation started: source_dir=%s persona=%s", source_dir, persona)
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

    logger.info("Generating %d audio tracks in %s", len(scripts.scripts), output_dir)
    asyncio.run(process_concurrent(client, scripts.scripts, output_dir, instruction, max_concurrent=4))
    logger.info("TTS generation complete")

    # --- SST + Correction + Subtitle Generation ---
    logger.info("Starting STT + correction process")

    download_root = os.path.join(get_project_dir(), "whisper")
    kwargs = {"word_timestamps": True, "language": "zh"}
    whisper_model = whisper.load_model("small", device="cpu", download_root=download_root)

    # Build correction pipeline
    correction_model = get_model_config(os.environ["env"]).get("main")
    correction_pipeline = create_correction_pipeline(correction_model)

    from src.sop.audio.structured_output import CorrectedSubtitles

    for slide_number, script in enumerate(scripts.scripts, start=1):
        speech_file_path = os.path.join(output_dir, f"slide_{slide_number}_audio.mp3")
        logger.info("Transcribing slide %d: %s", slide_number, speech_file_path)

        result = whisper_model.transcribe(speech_file_path, **kwargs)

        # Build STT segments string for LLM prompt
        stt_segments_lines = []
        for idx2, seg in enumerate(result["segments"], start=1):
            stt_segments_lines.append(
                f"Segment {idx2}: start={seg['start']:.2f}s end={seg['end']:.2f}s text=\"{seg['text'].strip()}\""
            )
        stt_segments_str = "\n".join(stt_segments_lines)

        ground_truth = script.script

        logger.info("Running correction for slide %d", slide_number)
        corrected = correction_pipeline.invoke({
            "ground_truth": ground_truth,
            "stt_segments": stt_segments_str,
        })

        # Save corrected subtitles
        subtitle_path = os.path.join(source_dir, f"slide_{slide_number}_subtitles.json")
        with open(subtitle_path, "w", encoding="utf-8") as f:
            f.write(corrected.model_dump_json(indent=2))
        logger.info("Slide %d corrected: %d segments saved to %s", slide_number, len(corrected.segments), subtitle_path)

    logger.info("STT + correction complete for all slides")
