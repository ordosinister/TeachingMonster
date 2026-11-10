"""HTML embedder: embed generated images into slide HTML files."""
import logging
import os
import re

logger = logging.getLogger("html_embedder")

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Slide {slide_num} - TeachingMonster</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #1a1a2e;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 20px;
    font-family: "Segoe UI", "Microsoft JhengHei", "PingFang TC", sans-serif;
  }}
  .slide-wrapper {{
    width: 100%;
    max-width: 1100px;
  }}
  .meta {{
    text-align: center;
    margin-bottom: 16px;
    color: #aab6fe;
    font-size: 0.9rem;
  }}
</style>
</head>
<body>
<div class="meta">Slide {slide_num} / {total_slides} | Image Ratio: {image_ratio}</div>
<div class="slide-wrapper">
{slide_body}
</div>
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
            f"</div>"
        )
    else:
        replacement = (
            f"<img src=\"{image_src}\" style=\"flex:1 1 auto; width:100%; height:100%; object-fit:cover; display:block;\" alt=\"slide image\">"
        )
    
    return slide_html[:start] + replacement + slide_html[end:]


def embed_images(layouts, image_paths, output_dir):
    """Generate slide HTML files with embedded image references."""
    slides_dir = os.path.join(output_dir, "slides")
    os.makedirs(slides_dir, exist_ok=True)
    
    total = len(layouts)
    html_paths = []
    
    for idx, (layout, image_path) in enumerate(zip(layouts, image_paths), start=1):
        if not image_path:
            logger.info("Slide %d has no image, skipping embed", idx)
            rel_src = ""
        else:
            rel_src = f"../images/slide_{idx:02d}_image.png"
        
        slide_body = _embed_in_slide_html(layout.slide_html, rel_src)
        
        full_html = _HTML_TEMPLATE.format(
            slide_num=idx,
            total_slides=total,
            image_ratio=layout.image_ratio,
            slide_body=slide_body,
        )
        output_path = os.path.join(slides_dir, f"slide_{idx:02d}.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_html)
        
        html_paths.append(output_path)
        logger.info("Saved slide %d HTML to %s", idx, output_path)
    
    return html_paths
