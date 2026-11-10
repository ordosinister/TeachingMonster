from pydantic import BaseModel, Field


class VisualStyleOutput(BaseModel):
    style_category: str = Field(
        description="One of: realistic, flat_diagrammatic, or hybrid. Realistic for presentations dominated by concrete observable subjects; flat_diagrammatic for abstract mechanisms; hybrid when both appear significantly."
    )
    rationale: str = Field(
        description="Why this style was chosen for the entire presentation based on content analysis across all slides."
    )
    visual_guidance: str = Field(
        description="Detailed visual direction for the entire presentation: rendering approach, detail level, color palette, composition rules. This will be applied consistently to every image."
    )
    anti_patterns: str = Field(
        description="Explicit list of visual pitfalls to avoid across this entire presentation."
    )
    tone_descriptor: str = Field(
        description="The emotional/tonal register for the entire presentation, matched to target audience persona."
    )
