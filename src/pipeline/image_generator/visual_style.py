"""Visual style director: generate unified style for the entire deck."""
from textwrap import dedent

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from src.logic import build_standard_chat_prompt_template


class VisualStyle(BaseModel):
    """Unified visual style for the entire presentation (causal ordering)."""
    # Step 1: Decide the overall style category first.
    style_category: str = Field(
        ...,
        description="One of: realistic, flat_diagrammatic, or hybrid. This is the FIRST decision.",
    )
    # Step 2: Justify why this category fits the content and audience.
    rationale: str = Field(
        ...,
        description="Why this style_category serves this audience and content.",
    )
    # Step 3: Define emotional tone based on style + audience.
    tone_descriptor: str = Field(
        ...,
        description="Emotional/tone register for the entire presentation, derived from style_category and PERSONA.",
    )
    # Step 4: List anti-patterns (constraints) informed by style + tone.
    anti_patterns: str = Field(
        ...,
        description="Visual pitfalls to avoid, explicitly derived from style_category and tone_descriptor.",
    )
    # Step 5: Synthesize everything into the final visual guidance string.
    visual_guidance: str = Field(
        ...,
        description="FINAL OUTPUT: Detailed visual direction that synthesizes style_category, tone_descriptor, and anti_patterns into one actionable string for image generation.",
    )


SYSTEM_PROMPT = dedent('''
# Goal
Analyze the enterprise training content and prescribe ONE consistent visual style for every image in the entire presentation.

# Role
Visual style director for enterprise internal training. You determine a single, coherent rendering approach that makes every image a teaching aid, not decoration.

# Inputs
- <COURSE_REQUIREMENT>: topic, learning goals, key points
- <STUDENT_PERSONA>: target audience (region, language ability, business/technical background)
- <PRESENTATION_CONTENT>: the full slide sequence with titles, content, and speaker notes

# Rules
1. Think step by step in this exact order:
   (a) Pick ONE style_category for the entire presentation: realistic, flat_diagrammatic, or hybrid. No slide-by-slide variation.
   (b) Write rationale: why does this style_category serve THIS audience and THIS content?
   (c) Set tone_descriptor: based on style_category and PERSONA, what is the emotional register? (warm/approachable for onboarding; precise/authoritative for senior technical audiences)
   (d) List anti_patterns: what visual mistakes must be avoided, given the chosen style_category and tone_descriptor?
   (e) FINALLY, synthesize everything into visual_guidance: a single, detailed visual direction string that includes unified color palette, composition rules, detail level, and rendering approach. This MUST be consistent with (a)-(d) above.
2. Concrete objects (products, equipment, real-world scenarios) → realistic.
3. Abstract mechanisms (workflows, processes, systems, data flows) → flat_diagrammatic.
4. If both concrete and abstract appear significantly → hybrid, with consistent framing/color/lighting unifying both modes.
5. Every image must advance understanding beyond text alone. Decorative images are forbidden.
6. For cross-regional audiences, avoid culture-specific symbols or color meanings that do not translate.

# Constraints
- The output fields MUST follow the causal order: style_category → rationale → tone_descriptor → anti_patterns → visual_guidance.
- visual_guidance MUST be the LAST field and MUST explicitly synthesize all previous decisions.
- Anti-patterns must be explicitly listed and specific to this presentation content type.
- Tone descriptor must reflect the target audience professional maturity, not educational grade.
- Output must be valid JSON. No markdown, no extra commentary.

# Output
Format instruction: {format_instructions}
IMPORTANT: Generate the fields in this exact order: style_category, rationale, tone_descriptor, anti_patterns, visual_guidance.
''')


def create_visual_style_pipeline(model) -> Runnable:
    """Build the visual-style generation pipeline."""
    output_parser = PydanticOutputParser(pydantic_object=VisualStyle)
    format_instructions = output_parser.get_format_instructions()

    input_ = {
        "system": {
            "template": SYSTEM_PROMPT,
            "partial_variables": {"format_instructions": format_instructions},
        },
        "human": {
            "template": dedent("""
                <COURSE_REQUIREMENT>:
                {course_requirement}

                <STUDENT_PERSONA>:
                {student_persona}

                <PRESENTATION_CONTENT>:
                {content}
            """),
        },
    }

    pipeline = build_standard_chat_prompt_template(input_) | model | output_parser
    return pipeline


def generate_visual_style(model, course_requirement, persona, slides_content):
    """Generate a unified VisualStyle for the entire deck."""
    pipeline = create_visual_style_pipeline(model)
    result = pipeline.invoke({
        "course_requirement": course_requirement,
        "student_persona": persona,
        "content": slides_content,
    })
    return result