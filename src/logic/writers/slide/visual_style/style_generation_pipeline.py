from textwrap import dedent

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from src.logic import build_standard_chat_prompt_template


class VisualStyleOutput(BaseModel):
    style_category: str = Field(
        description="One of: realistic, flat_diagrammatic, or hybrid. Realistic for presentations dominated by concrete observable subjects; flat_diagrammatic for abstract mechanisms; hybrid when both appear significantly."
    )
    rationale: str = Field(
        description="Why this style was chosen for the entire presentation based on content analysis across all slides."
    )
    visual_guidance: str = Field(
        description="Detailed visual direction for the entire presentation: rendering approach, detail level, color palette, composition rules. This will be applied consistently to every slide image."
    )
    anti_patterns: str = Field(
        description="Explicit list of visual pitfalls to avoid across this entire presentation."
    )
    tone_descriptor: str = Field(
        description="The emotional/tonal register for the entire presentation, matched to student persona."
    )


STYLE_SYSTEM_PROMPT = dedent("""
# ROLE
Visual style director for science education. Pick one consistent rendering style for the entire presentation based on: concrete objects -> realistic, abstract mechanisms -> flat diagrammatic. Every image is a teaching aid, not decoration.

# INPUTS
<COURSE REQUIREMENT>, <STUDENT PERSONA>, <PRESENTATION CONTENT>.

# TASK
Analyze the dominant content type across all slides and prescribe ONE style for every slide:

## realistic -- for observable specimens, lab equipment, natural phenomena.
Scientific illustration: accurate texture, natural light, true proportions. Abstract concepts get realistic anchors + clean diagram overlays. Avoid glossy renders, AI smoothness, unnatural saturation.

## flat_diagrammatic -- for pathways, flows, algorithms, math, forces, mechanisms without physical form.
Clean vector-like: flat colors, clear hierarchy, labeled components, logical layout. Even concrete references stay flat. Avoid fake 3D, gradients, photo-bashing, visual clutter.

## hybrid -- genuine mix of both, neither dominates.
Realistic rules for concrete elements, flat rules for abstract. Consistent framing/lighting/color unifies both modes.

# VISUAL QUALITY

## What exceptional visuals do
- Illuminate concepts: image alone must advance understanding beyond text.
- Earn attention: the most visually striking moment = the most conceptually important moment.
- Guide the eye: composition must lead immediately to the focal point. No hunting.

## Anti-patterns (NEVER recommend)
- Glossy AI / plastic surfaces / CGI sheen
- Stock photo look (posed, generic, sterile)
- Cartoonish oversimplification (clip-art, mascots)
- Uncanny valley (cold/unsettling photorealism)
- Decorative abstraction (art that teaches nothing)
- Style whiplash (inconsistent rendering across slides)
- Cheap / samey / uncanny (templated interchangeability, budget feel, near-human unease)
- Flashy empty spectacle (explosions, particle storms, neon glows with zero conceptual content)
- Hunting for relevance (clutter, competing focal points, unclear hierarchy, buried key element)

# TONE
Younger: warm, curious, inviting. Advanced: precise, systematic, authoritative. Mixed: intriguing, not confusing.

# CHAIN OF THOUGHT
1. Scan content: concrete or abstract dominant?
2. Pick style category.
3. Adjust tone/complexity for student persona.
4. Ensure style supports learning goals.
5. Compose detailed visual guidance for all slides.
6. List anti-patterns to avoid.

# OUTPUT
JSON: style_category, rationale, visual_guidance, anti_patterns, tone_descriptor.
""")


def create_visual_style_pipeline(model):

    output_parser = PydanticOutputParser(pydantic_object=VisualStyleOutput)
    format_instructions = output_parser.get_format_instructions()

    input_ = {
        "system": {"template": STYLE_SYSTEM_PROMPT},
        "human": {
            "template": dedent("""
<COURSE REQUIREMENT>:
{course_requirement}

<STUDENT PERSONA>:
{student_persona}

<PRESENTATION CONTENT>:
{content}

Output format instructions: {format_instructions}

            """),
            "input_variable": ["course_requirement", "student_persona", "content"],
            "partial_variables": {"format_instructions": format_instructions}
        }
    }

    chat_prompt_template = build_standard_chat_prompt_template(input_)

    pipeline = chat_prompt_template | model | output_parser

    return pipeline