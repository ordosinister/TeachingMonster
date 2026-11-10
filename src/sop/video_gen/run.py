"""Video assembly: synchronizes image images and audio into MP4.

Uses moviepy to concatenate image images with their corresponding TTS
audio tracks into a final 1080p educational video.
"""

import os
import logging
from pathlib import Path

import numpy as np
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Video Generation")


def main(source_dir, buffer_seconds: float = 0.5):
    """Assemble image images and audio into a final MP4 video.
    Args:
        buffer_seconds: Silent buffer duration between slides (default 0.5s).
    """

    # Define paths based on your structure
    image_dir = os.path.join(source_dir, "image")
    audio_dir = os.path.join(source_dir, "audio")
    output_dir = os.path.join(source_dir, "video")

    num_of_slides = len(os.listdir(image_dir))

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    output_filename = os.path.join(output_dir, f"final_presentation_{Path(output_dir).stem}.mp4")

    video_clips = []

    logger.info("Processing assets and generating clips...")
    for slide_num, _ in enumerate(range(num_of_slides), start=1):

        img_path = os.path.join(image_dir, f"slide_{slide_num}_image.png")
        aud_path = os.path.join(audio_dir, f"slide_{slide_num}_audio.mp3")

        if os.path.exists(img_path) and os.path.exists(aud_path):
            logger.info(f"Adding Slide {slide_num}...")

            # 1. Load audio
            audio_clip = AudioFileClip(aud_path)
            total_duration = audio_clip.duration + buffer_seconds

            # 2. Create image clip and set duration to match the audio
            img_clip = ImageClip(img_path).with_duration(total_duration)
            img_clip = img_clip.with_audio(audio_clip)

            video_clips.append(img_clip)

    logging.info("Concatenating all clips into final video... (this may take a few minutes)")
    final_video = concatenate_videoclips(video_clips, method="chain")

    # Write the final file
    # final_video.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac",  preset="ultrafast")
    final_video.write_videofile(
        output_filename,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        ffmpeg_params=[
            "-pix_fmt", "yuv420p",
        ],
    )

if __name__ == "__main__":

    from src.path.path_definition import get_project_dir

    source_dir = os.path.join(get_project_dir(), "data", "4b8ef1cdda6afef808ebbef4a76be7399289e0742329eb206eb2c59577955270")

    main(source_dir)