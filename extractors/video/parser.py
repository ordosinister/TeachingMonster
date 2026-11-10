import io
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from PIL import Image
from langchain_core.messages import HumanMessage

from extractors.shared.utils import image_to_base64


def _find_ffmpeg() -> str:
    """Locate ffmpeg executable."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    # Common Windows locations
    candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
    ]
    for cand in candidates:
        if os.path.isfile(cand):
            return cand
    raise FileNotFoundError(
        "ffmpeg not found. Please install ffmpeg and ensure it is on PATH."
        " Visit https://ffmpeg.org/download.html"
    )


def extract_keyframes(video_path: str, scene_threshold: float = 0.1) -> tuple[list, Path]:
    """Extract keyframes from video using ffmpeg scene detection.

    Args:
        video_path: Path to the video file.
        scene_threshold: Scene change detection threshold (0.0-1.0).
                         Higher values = fewer keyframes.

    Returns:
        Tuple of (image_file_tuples, temp_output_dir)
        image_file_tuples: List of (filename, bytes, mime_type) for each keyframe.
    """
    ffmpeg_path = _find_ffmpeg()
    video_path = Path(video_path).resolve()

    # Create temporary directory for frames
    output_dir = Path(video_path).parent / f"video_frames_{uuid.uuid4().hex[:8]}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # ffmpeg scene detection: select frames where scene change > threshold
    # -vf "select=gt(scene\,0.3)" filters for scene changes
    # -vsync vfr prevents duplicate frame numbers
    # -q:v 2 sets high JPEG quality
    frame_pattern = output_dir / "frame_%04d.jpg"
    cmd = [
        ffmpeg_path,
        "-i", str(video_path),
        "-vf", f"select=gt(scene\\,{scene_threshold}),scale='min(1920,iw)':-1,showinfo",
        "-fps_mode", "vfr",
        "-q:v", "2",
        "-f", "image2",
        str(frame_pattern),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        # Cleanup on failure
        shutil.rmtree(output_dir, ignore_errors=True)
        raise RuntimeError(
            f"ffmpeg scene detection failed (rc={result.returncode}): {result.stderr[:500]}"
        )

    # Collect extracted frames
    frames = sorted(output_dir.glob("frame_*.jpg"))
    if not frames:
        shutil.rmtree(output_dir, ignore_errors=True)
        raise RuntimeError(
            "No keyframes extracted. The video may have no scene changes "
            "or scene_threshold may be too high."
        )

    image_files = []
    for frame_path in frames:
        image_bytes = frame_path.read_bytes()
        image_files.append(
            (frame_path.name, image_bytes, "image/jpeg")
        )

    return image_files, output_dir


def keyframes_to_base64_messages(image_files: list) -> list[HumanMessage]:
    """Convert extracted keyframe images to LangChain HumanMessage list.

    Args:
        image_files: List of (filename, bytes, mime_type) tuples.

    Returns:
        List of HumanMessage containing Base64 image data.
    """
    messages = []

    for idx, (filename, image_bytes, _) in enumerate(image_files, start=1):
        image = Image.open(io.BytesIO(image_bytes))
        image_str = image_to_base64(image)
        messages.append(
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": f"Keyframe No.: {idx}; filepath: {filename}",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_str}"
                        },
                    },
                ]
            )
        )

    return messages

if __name__ == "__main__":

    import os

    from path.path_definition import get_project_dir

    video_path = os.path.join(get_project_dir(), "data", "Basic Etiquette-220721.mp4")

    extract_keyframes(video_path=video_path)