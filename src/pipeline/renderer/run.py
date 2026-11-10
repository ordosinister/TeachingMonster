"""Renderer: embed images + audio into HTML, then render to MP4 via Playwright + ffmpeg."""

import base64
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile

from src.pipeline.html_embedder.run import embed_images

logger = logging.getLogger("renderer")

_PLAYER_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<title>TeachingMonster Player</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: 100%; height: 100%; overflow: hidden; background: #000; }
  #stage { position: relative; width: 100%; height: 100%; }
  .slide {
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    opacity: 0; transition: opacity 0.8s ease-in-out;
    display: flex; align-items: center; justify-content: center;
    z-index: 0;
  }
  .slide.active { opacity: 1; z-index: 10; }
  .slide > div { width: 100%; height: 100%; }
</style>
</head>
<body>
<div id="stage">
{{SLIDES_HTML}}
</div>
<script>
const durations = {{DURATIONS_JS}};
let current = 0;
const slides = document.querySelectorAll('.slide');

function show(idx) {
  slides.forEach((s, i) => s.classList.toggle('active', i === idx));
}

function next() {
  current++;
  if (current >= slides.length) return;
  show(current);
  setTimeout(next, durations[current] * 1000);
}

show(0);
setTimeout(next, durations[0] * 1000);
</script>
</body>
</html>
"""

_PLACEHOLDER_RE = re.compile(
    r"""<div[^>]*\bstyle=(?:"[^"]*?border:\s*\d+px\s+dashed[^"]*"|'[^']*?border:\s*\d+px\s+dashed[^']*')[^>]*>.*?</div>""",
    re.DOTALL | re.IGNORECASE,
)

def _embed_in_slide_html(slide_html, image_src):
    """Replace image placeholder with an <img> tag inside the slide_html."""
    match = _PLACEHOLDER_RE.search(slide_html)
    if not match:
        placeholder_idx = slide_html.find("slide_image")
        if placeholder_idx == -1:
            logger.warning("No image placeholder found in slide HTML")
            return slide_html
        div_start = slide_html.rfind("<div", 0, placeholder_idx)
        if div_start == -1:
            return slide_html
        div_end = slide_html.find("</div>", placeholder_idx)
        if div_end == -1:
            return slide_html
        div_end += len("</div>")
        match_span = (div_start, div_end)
    else:
        match_span = match.span()

    start, end = match_span
    matched_html = slide_html[start:end]
    style_match = re.search(r"style=(?:\"([^\"]*)\"|'([^']*)')", matched_html, re.IGNORECASE)
    
    if style_match:
        original_style = style_match.group(1) or style_match.group(2)
        new_style = re.sub(r"border:\s*\d+px\s+dashed\s*[^;]*;?\s*", "", original_style, flags=re.IGNORECASE)
        new_style = re.sub(r"background-color:[^;]*;?\s*", "", new_style, flags=re.IGNORECASE)
        new_style = re.sub(r"background:[^;]*;?\s*", "", new_style, flags=re.IGNORECASE)
        new_style = re.sub(r"\s+", " ", new_style).strip().rstrip(";")
        
        replacement = (
            f"<div style=\"{new_style}\">"
            f"<img src=\"{image_src}\" style=\"max-width:100%; max-height:100%; object-fit:contain; display:block;\" alt=\"slide image\">"
            "</div>"
        )
    else:
        replacement = (
            f"<img src=\"{image_src}\" style=\"flex:1 1 auto; width:100%; height:100%; object-fit:cover; display:block;\" alt=\"slide image\">"
        )
    
    return slide_html[:start] + replacement + slide_html[end:]

def _build_slide_divs(layouts, image_paths, output_dir):
    """Build slide divs with base64-embedded images for the player."""
    divs = []
    for idx, (layout, image_path) in enumerate(zip(layouts, image_paths), start=1):
        if image_path and os.path.isfile(image_path):
            with open(image_path, "rb") as fimg:
                b64 = base64.b64encode(fimg.read()).decode("ascii")
            img_src = f"data:image/png;base64,{b64}"
        else:
            img_src = ""
        slide_body = _embed_in_slide_html(layout.slide_html, img_src)
        active = ' active' if idx == 1 else ''
        div_html = f'  <div class="slide{active}">\n{slide_body}\n  </div>'
        divs.append(div_html)
    return "\n".join(divs)
def _build_player_html(slide_divs_html, durations, output_path):
    """Build player HTML with auto-advancing slides."""
    durations_js = json.dumps([round(d, 2) for d in durations])
    
    html = _PLAYER_TEMPLATE.replace("{{SLIDES_HTML}}", slide_divs_html)
    html = html.replace("{{DURATIONS_JS}}", durations_js)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    logger.info("Player HTML saved to %s", output_path)
    return output_path

async def _record_video_with_playwright(player_html_path, output_dir, total_duration):
    """Record player HTML to silent video via Playwright."""
    from playwright.async_api import async_playwright
    
    video_dir = os.path.join(output_dir, "video_raw")
    os.makedirs(video_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=video_dir,
            record_video_size={"width": 1920, "height": 1080},
        )
        page = await context.new_page()
        file_url = "file:///" + os.path.abspath(player_html_path).replace("\\", "/")
        await page.goto(file_url, wait_until="networkidle")
        # Extra wait to ensure all slide images load
        await page.wait_for_timeout(1000)
        buffer_ms = 2000
        wait_ms = int((total_duration * 1000) + buffer_ms)
        await page.wait_for_timeout(wait_ms)
        await context.close()
        await browser.close()
    
    video_files = [
        f for f in os.listdir(video_dir) if f.endswith('.webm')
    ]
    if not video_files:
        raise RuntimeError("No video file generated by Playwright")
    # Pick the most recently modified webm (newest run)
    video_files.sort(
        key=lambda fn: os.path.getmtime(os.path.join(video_dir, fn)),
        reverse=True,
    )
    
    raw_video = os.path.join(video_dir, video_files[0])
    return raw_video

def _mix_audio_to_video(video_path, audio_paths, audio_durations, output_path):
    """Mix audio tracks into video using ffmpeg concat."""
    concat_lines = []
    for ap, dur in zip(audio_paths, audio_durations):
        if ap and os.path.isfile(ap):
            abs_path = os.path.abspath(ap).replace("\\", "/")
            concat_lines.append(f"file '{abs_path}'")
            concat_lines.append(f"duration {round(dur, 2)}")
    
    if not concat_lines:
        logger.warning("No valid audio files, copying video without audio")
        shutil.copy(video_path, output_path)
        return output_path
    
    with tempfile.TemporaryDirectory() as tmpdir:
        concat_file = os.path.join(tmpdir, "audio_concat.txt")
        with open(concat_file, "w", encoding="utf-8") as f:
            f.write("\n".join(concat_lines) + "\n")
        
        merged_audio = os.path.join(tmpdir, "merged_audio.mp3")
        
        cmd_concat = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c", "copy", merged_audio,
        ]
        logger.info("Merging audio: %s", " ".join(cmd_concat))
        subprocess.run(cmd_concat, check=True, capture_output=True)
        
        cmd_mix = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", merged_audio,
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest", output_path,
        ]
        logger.info("Mixing audio into video: %s", " ".join(cmd_mix))
        subprocess.run(cmd_mix, check=True, capture_output=True)
    
    logger.info("Final video saved to %s", output_path)
    return output_path

async def render_video(
    layouts,
    image_paths,
    audio_paths,
    audio_durations,
    output_dir,
):
    """Full render pipeline: embed images + build player + record video + mix audio.

    Returns dict with keys:
        - slide_html_paths: list of per-slide HTML files
        - player_path: path to player.html
        - raw_video_path: silent webm from Playwright
        - final_video_path: mp4 with audio mixed in
    """
    logger.info("=== Renderer Step 1: Embed images into slide HTML ===")
    slide_html_paths = embed_images(layouts, image_paths, output_dir)
    
    logger.info("=== Renderer Step 2: Build player HTML ===")
    slide_divs = _build_slide_divs(layouts, image_paths, output_dir)
    
    normalized_durations = []
    for ap, dur in zip(audio_paths, audio_durations):
        if ap and dur and dur > 0:
            normalized_durations.append(dur)
        else:
            normalized_durations.append(5.0)
    
    player_path = os.path.join(output_dir, "player.html")
    _build_player_html(slide_divs, normalized_durations, player_path)
    
    logger.info("=== Renderer Step 3: Record video with Playwright ===")
    total_duration = sum(normalized_durations)
    raw_video = await _record_video_with_playwright(player_path, output_dir, total_duration)
    
    logger.info("=== Renderer Step 4: Mix audio into video ===")
    final_video = os.path.join(output_dir, "output.mp4")
    _mix_audio_to_video(raw_video, audio_paths, normalized_durations, final_video)
    
    return {
        "slide_html_paths": slide_html_paths,
        "player_path": player_path,
        "raw_video_path": raw_video,
        "final_video_path": final_video,
    }
