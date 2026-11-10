
"""Audio generation entry point (async TTS via OpenAI)."""
import asyncio
import logging
import os
from textwrap import dedent

from openai import AsyncOpenAI
from mutagen.mp3 import MP3

from src.pipeline.audio_generator.pipeline import create_tts_vibe_pipeline

logger = logging.getLogger("audio_generator")


_MAX_RETRIES = 3
_DEFAULT_INSTRUCTIONS = dedent("""
# Role
You are an enterprise internal training narrator. You speak clearly and naturally, adapting your language to the audience's proficiency.
Remove any formatting notation (LaTeX, markup) and decode abbreviations according to the business context. Maintain a professional yet approachable tone.

# Vibe:
{vibe}
""")


async def _generate_one_audio(
    client,
    slide_number,
    text,
    output_path,
    instructions,
    max_retries=_MAX_RETRIES,
):
    """Generate a single MP3 audio file for one slide."""
    if os.path.isfile(output_path):
        try:
            audio = MP3(output_path)
            duration = audio.info.length
            logger.info("Audio slide_%d already exists (%.2fs)", slide_number, duration)
            return output_path, duration
        except Exception:
            pass  # corrupted file, regenerate

    for attempt in range(max_retries + 1):
        try:
            async with client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice="marin",
                instructions=instructions,
                input=text,
            ) as response:
                await response.stream_to_file(output_path)

            audio = MP3(output_path)
            duration = audio.info.length
            logger.info("Generated audio slide_%d (%.2fs)", slide_number, duration)
            return output_path, duration

        except Exception as exc:
            logger.warning("Audio slide_%d failed (attempt %d/%d): %s", slide_number, attempt + 1, max_retries + 1, exc)
            if attempt == max_retries:
                raise
            await asyncio.sleep(5)

    return None, 0.0


async def generate_audios(
    slides,
    output_dir,
    instructions,
    semaphore_limit=4,
):
    """Generate TTS audio for all slides concurrently."""
    client = AsyncOpenAI()
    os.makedirs(output_dir, exist_ok=True)
    semaphore = asyncio.Semaphore(semaphore_limit)

    async def _invoke(idx, slide):
        text = slide.get("speaker_notes", "")
        if not text.strip():
            logger.info("Skipping slide_%d (empty speaker_notes)", idx + 1)
            return None, 0.0
        async with semaphore:
            output_path = os.path.join(output_dir, f"slide_{idx + 1:02d}_audio.mp3")
            return await _generate_one_audio(client, idx + 1, text, output_path, instructions)

    tasks = [
        _invoke(idx, slide)
        for idx, slide in enumerate(slides)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    output_paths = []
    durations = []
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("Slide %d audio failed: %s", idx + 1, result)
            output_paths.append(None)
            durations.append(0.0)
        else:
            path, dur = result
            output_paths.append(path)
            durations.append(dur)

    logger.info("Audio generation complete: %d/%d succeeded",
                 sum(1 for p in output_paths if p), len(output_paths))
    return output_paths, durations


def build_instructions(vibe: str) -> str:
    """Build TTS instructions string from vibe description."""
    return _DEFAULT_INSTRUCTIONS.format(vibe=vibe)
