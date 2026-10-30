"""Pydantic models for lesson blueprint structured output."""

from typing import List, Optional

from pydantic import BaseModel, Field


class SlideBase(BaseModel):
    slide_number: int = Field(..., description="Slide order")
    slide_title: str = Field(..., description="Title displayed at the top")
    slide_content: List[str] = Field(..., description="Bullet points shown on the slide")
    speaker_notes: str = Field(..., description="Lecture narration for TTS")
    transition_to_next: str = Field(..., description="One sentence transition to next slide")


class StudentProfileInterpretation(BaseModel):
    knowledge_gaps: List[str] = Field(..., description="Gaps blocking understanding")
    teaching_adjustments: List[str] = Field(..., description="Strategies to bridge gaps")


class LessonBlueprint(BaseModel):
    title: str = Field(..., description="Course or lesson title")
    student_profile: StudentProfileInterpretation
    slides: List[SlideBase] = Field(
        ...,
        description="Full sequence of slides"
    )
    extension_topic: Optional[str] = Field(
        default=None,
        description="Optional advanced topic for further exploration"
    )
