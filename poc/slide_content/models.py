"""Pydantic models for slide content generation."""

from typing import List

from pydantic import BaseModel, Field


class SlideBase(BaseModel):
    """Single slide content (no layout / HTML)."""
    slide_title: str = Field(..., description="Title displayed at the top of the slide")
    slide_image: str = Field(..., description="Detailed English prompt for image generation")
    slide_content: List[str] = Field(..., description="Bullet points shown on the image")
    speaker_notes: str = Field(..., description="Lecture narration for TTS")


class LessonBlueprint(BaseModel):
    """Complete 4-slide lesson blueprint."""
    slides: List[SlideBase] = Field(
        ...,
        description="Full sequence of slides (exactly 4 slides)"
    )