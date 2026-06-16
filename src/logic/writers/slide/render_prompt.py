"""Prompt builder for gpt-image-2 slide rendering."""

from textwrap import dedent
from typing import List


def build_render_prompt(
    slide_title: str,
    slide_content: List[str],
    visual_instruction: str,
) -> str:
    """Build the gpt-image-2 render prompt for a single slide.

    Args:
        slide_title: The slide's title text.
        slide_content: List of bullet-point strings for the slide.
        visual_instruction: The visual content instruction (diagram description
            or matplotlib compositing instruction).

    Returns:
        Formatted prompt string ready for gpt-image-2 images.edit().
    """
    bullets = chr(10).join(f"{item}" for item in slide_content)

    return dedent(f"""
        STRICT TEMPLATE RULES:
        - Use the provided image as the fixed layout and background
        - Preserve its structure, spacing, and visual hierarchy
        - Do NOT alter the template design

        TEXT PLACEMENT:

        Title (place in the title area exactly):
        {slide_title}

        Bullet Points (place in the content area, left-aligned):
        {bullets}

        TEXT REQUIREMENTS (CRITICAL):
        - Preserve all numbers, equations, and units EXACTLY
        - IMPORTANT OVERRIDE: $...$ delimiters are LaTeX markup, NOT slide content. Strip the $ symbols from the final image entirely. Render only the enclosed expression as properly formatted mathematical notation (italic variables, upright numbers, proper spacing).
        - Do NOT reword, summarize, or simplify
        - Ensure high readability and clean alignment
        - Use consistent bullet spacing
        - Content must be appropriate for AP-aligned coursework (academically rigorous and precise)

        VISUAL CONTENT:
        {visual_instruction}
        - Place it in the designated visual area of the template
        - Ensure it does NOT overlap with text
        - Keep proportions clean and uncluttered

        LAYOUT RULES:
        - Maintain clear separation between text and visuals
        - Do not overcrowd the slide
        - Adjust diagram scale if needed to fit cleanly

        STYLE:
        - Professional educational slide
        - Clean, minimal, high contrast
        - No unnecessary decorations
        - Designed for AP curriculum presentation standards
        - Color coding rule: Blue is used exclusively for key concepts (important terms and core ideas)
        - Key formulas appear in a subtle box or highlight -- exam-ready emphasis

        The final result must look like a polished, academically rigorous AP presentation slide rendered on the provided template.
    """)
