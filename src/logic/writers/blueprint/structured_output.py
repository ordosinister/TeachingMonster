"""Pydantic models for lesson blueprint structured output.

Defines the schema for parsed LLM output including slides,
student profile interpretation, and adaptability metadata.
"""

from typing import List, Optional, Union, Literal

from pydantic import BaseModel, Field


class SlideBase(BaseModel):
 slide_number: int = Field(..., description="Slide order in the presentation")
 slide_type: str = Field(..., description="The type of the slide for rendering purposes (e.g., 'base', 'puzzle', 'concept_check', 'algorithm')")
 slide_title: str = Field(
 ...,
 description="<SLIDE_TITLE>. Title displayed at the top of the slide"
 )
 slide_content: List[str] = Field(
 ...,
 description="<SLIDE_CONTENT>. Short bullet points shown on the slide. Keep concise and readable."
 )
 speaker_notes: str = Field(
 ...,
 description="<SPEAKER_NOTES>. Detailed lecture narration for TTS. Explain slide content in conversational teaching style"
 )
 transition_to_next: str = Field(
 ...,
 description="<TRANSITION_TO_NEXT>. One sentence transition connecting this slide to the next concept"
 )

 jargon: str = Field(description="Jargon terms used in this slide that may need pre-explanation or substitution. List comma-separated terms that are not yet taught in knowledge_gaps")


class ConceptCheckSlide(SlideBase):
 slide_type: Literal["concept_check"] = "concept_check"
 question: str = Field(..., description="Conceptual question testing understanding")
 expected_thinking_process: str = Field(..., description="Reasoning students should follow")
 correct_insight: str = Field(..., description="Key conceptual insight behind the answer")

class PuzzleSlide(SlideBase):
 slide_type: Literal["puzzle"] = "puzzle"
 puzzle_question: str = Field(..., description="A surprising or curiosity-inducing question")
 hint: Optional[str] = None
 learning_purpose: str = Field(..., description="Why this puzzle helps learning")

class AlgorithmWalkthroughSlide(SlideBase):
 slide_type: Literal["algorithm"] = "algorithm"
 algorithm_steps: List[str] = Field(..., description="Step-by-step breakdown of the algorithm")
 visualization_description: Optional[str] = Field(None, description="Description of how the algorithm should be visualized")
 key_insight: str = Field(..., description="The critical '\''aha!\'' moment of the algorithm")

class StudentProfileInterpretation(BaseModel):
 inferred_level: str = Field(..., description="Estimated academic level")
 knowledge_gaps: List[str] = Field(..., description="Potential gaps to scaffold around")
 teaching_adjustments: List[str] = Field(..., description="How explanations will be adapted")

class LessonBlueprint(BaseModel):
 title: str = Field(..., description="Course or lesson title")
 subject: str = Field(..., description="Physics, Biology, Computer Science, or Mathematics")
 target_level: str = Field(..., description="Approximate AP difficulty alignment")
 student_profile: StudentProfileInterpretation
 
 slides: List[
 Union[
 SlideBase,
 ConceptCheckSlide,
 PuzzleSlide,
 AlgorithmWalkthroughSlide
 ]
 ] = Field(
 ..., 
 description="The full sequence of slides. This sequence MUST include: 1. The Teaching Arc (Introduction & Progression), 2. Main Content slides, 3. Final Synthesis, and 4. Challenge Question."
 )

 extension_topic: Optional[str] = Field(
 default=None,
 description="Advanced topic for further exploration"
 )

class Slides(BaseModel):
 slides: List[
 Union[
 SlideBase,
 ConceptCheckSlide,
 PuzzleSlide,
 AlgorithmWalkthroughSlide
 ]
 ]

class AdaptabilityOutput(BaseModel):
 slides: List[SlideBase] = Field(...,description="updated_script")
 advise: List[str] = Field(...,description="advise")