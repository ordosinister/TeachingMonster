"""Video assembly: synchronizes image images and audio into MP4.

Uses moviepy to concatenate image images with their corresponding TTS
audio tracks into a final 1080p educational video.
"""

import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Video Generation")

import numpy as np
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

from src.path.path_definition import get_project_dir


def create_silent_clip(duration, fps=24):
    """Create a black silent clip for buffering between slides.

    Args:
        duration: Duration of the clip in seconds.
        fps: Frames per second (default 24).

    Returns:
        An ImageClip of a black 1080p frame.
    """
    """Creates a black frame silent clip for buffering between slides."""
    # Create a black image (1080p)
    black_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
    clip = ImageClip(black_image).with_duration(duration).with_fps(fps)
    return clip


def main(request_id: str, cache_key: str, buffer_seconds: float = 0.5):
    """Assemble image images and audio into a final MP4 video.

    Reads blueprint.json for image ordering, pairs each image image
    with its audio track, concatenates with buffers, and writes the
    final video file.

    Args:
        request_id: Unique request identifier for file path resolution.
        cache_key
        buffer_seconds: Silent buffer duration between slides (default 0.5s).
    """

    # Define paths based on your structure
    base_slide_dir = os.path.join(get_project_dir(), "data", request_id, cache_key)
    image_dir = os.path.join(base_slide_dir, "image")
    audio_dir = os.path.join(base_slide_dir, "audio")
    output_dir = os.path.join(base_slide_dir, "video")

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    output_filename = os.path.join(output_dir, f"final_presentation_{request_id}.mp4")

    # Load the script to determine order and image numbers
    filename = os.path.join(base_slide_dir, f"blueprint.json")
    with open(filename, "r", encoding="utf-8") as f:
        # Using double-load to match the behavior in run_classification.py
        script_data = json.load(f)

    video_clips = []

    print("Processing assets and generating clips...")
    for item in script_data['slides']:
        slide_num = item.get('slide_number')
        if slide_num is None:
            continue

        img_path = os.path.join(image_dir, f"slide_{slide_num}_image.png")
        aud_path = os.path.join(audio_dir, f"slide_{slide_num}_audio.mp3")

        if os.path.exists(img_path) and os.path.exists(aud_path):
            print(f"Adding Slide {slide_num}...")

            # 1. Load audio and get its duration
            audio_clip = AudioFileClip(aud_path)
            total_duration = audio_clip.duration + buffer_seconds

            # 2. Create image clip and set duration to match the audio
            img_clip = ImageClip(img_path).with_duration(total_duration)
            img_clip = img_clip.with_audio(audio_clip)

            video_clips.append(img_clip)

    print("Concatenating all clips into final video... (this may take a few minutes)")
    final_video = concatenate_videoclips(video_clips, method="chain")

    w, h = final_video.size

    new_w = w - (w % 2)
    new_h = h - (h % 2)

    final_video = final_video.cropped(
        x1=0,
        y1=0,
        x2=new_w,
        y2=new_h
    )

    print(f"Final resolution: {new_w}x{new_h}")

    # Write the final file
    # final_video.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac",  preset="ultrafast")
    final_video.write_videofile(
        output_filename,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        audio_bitrate="192k",
        ffmpeg_params=[
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart"
        ],
        logger="bar"
    )

if __name__ == "__main__":

    request_id = "01aa1889f2d4c3e75f4c6013db743e09b4edaca190cc45fe98270d81afb08331"
    cache_key = "a97294bb5efc6db3"

    main(request_id=request_id, cache_key=cache_key)