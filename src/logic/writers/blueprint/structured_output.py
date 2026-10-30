"""Pydantic models for lesson blueprint structured output."""

from typing import List, Optional

from pydantic import BaseModel, Field


class SlideBase(BaseModel):
    slide_number: int = Field(..., description="Slide order")
    slide_type: str = Field(..., description="Slide type: base, puzzle, concept_check, algorithm")
    slide_title: str = Field(..., description="Title displayed at the top")
    slide_content: List[str] = Field(..., description="Bullet points shown on the slide")
    speaker_notes: str = Field(..., description="Lecture narration for TTS")
    transition_to_next: str = Field(..., description="One sentence transition to next slide")
    jargon: str = Field(description="Comma-separated jargon terms needing pre-explanation")


class StudentProfileInterpretation(BaseModel):
    knowledge_gaps: List[str] = Field(..., description="Gaps blocking understanding")
    teaching_adjustments: List[str] = Field(..., description="Strategies to bridge gaps")


class LessonBlueprint(BaseModel):
    title: str = Field(..., description="Course or lesson title")
    subject: str = Field(..., description="Subject domain")
    target_level: str = Field(..., description="Target difficulty level")
    student_profile: StudentProfileInterpretation
    slides: List[SlideBase] = Field(
        ...,
        description="Full sequence of slides"
    )
    extension_topic: Optional[str] = Field(
        default=None,
        description="Optional advanced topic for further exploration"
    )
