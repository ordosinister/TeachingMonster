"""Pydantic models for slide layout generation (two-stage)."""

from pydantic import BaseModel, Field


class SlideImagePrompt(BaseModel):
    """Stage A: Detailed visual prompt for image generation."""
    image_prompt: str = Field(
        ...,
        description='Detailed English prompt in two-part format. Start with \"Positive Prompt: [the detailed visual description, style, colors, composition]\" then append \"Negative Prompt: [elements to avoid, quality issues, unwanted details]\". Both parts are included in this single field. The Negative Prompt section should incorporate ANTI_PATTERNS and character-specific negative prompts when applicable.',
    )
    image_type: str = Field(
        ...,
        description="Image type: None, GeneralImage, or MatplotlibImage.",
    )
    prompt_rationale: str = Field(
        ...,
        description="Brief Chinese explanation of why this image type and prompt were chosen.",
    )


class SlideLayout(BaseModel):
    """Stage B: HTML layout design informed by image_prompt."""
    slide_html: str = Field(
        ...,
        description="Complete HTML div string for the slide (16:9, inline CSS only). Must include title zone, bullet zone, and dashed image-placeholder zone.",
    )
    image_ratio: str = Field(
        ...,
        description="Recommended image aspect ratio for embedding: 16:9, 4:3, or 1:1.",
    )
    design_rationale: str = Field(
        ...,
        description="Brief Chinese explanation of why this layout and ratio were chosen given the image_prompt.",
    )